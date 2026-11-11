"""候选人公示 / 异议受理 / 异议办结目录的抓取与解析。

页面结构约定（与示例公告站一致）：
- 目录页：公告链接 ul.notice-list a[href]；分页导航 nav.pagination a[href]
- 详情页：容器 div.notice[data-notice-type]
    - candidate_publicity（候选人公示）
        #notice-no、#lot-no、#publish-time、#objection-deadline
    - objection_acceptance（异议受理）
        #notice-no、#lot-no、#publish-time、#objection-no、#accept-time
    - objection_resolution（异议办结）
        #notice-no、#publish-time、#objection-no（所引用的异议编号）
        #lot-no（可选，办结记录所属标段）、#resolve-time（可选）

只跟随与起始目录网址同源的链接。与原有公告抓取不同，这里单页失败不会中断
整轮抓取，而是记录到 errors 中，便于页面显示“无法核定”及问题网址。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from scraper import (
    MAX_DETAIL_PAGES,
    MAX_LIST_PAGES,
    USER_AGENT,
    ScrapeError,
    _norm_time,
    _normalize,
    _text,
    same_origin,
)

TYPE_LABELS = {
    "candidate_publicity": "候选人公示",
    "objection_acceptance": "异议受理",
    "objection_resolution": "异议办结",
}


@dataclass
class PublicityRecord:
    notice_no: str
    record_type: str  # candidate_publicity / objection_acceptance / objection_resolution
    publish_time: str  # 归一化为 YYYY-MM-DD HH:MM
    lot_no: str | None = None
    objection_no: str | None = None  # 受理：本异议编号；办结：所引用的异议编号
    accept_time: str | None = None
    objection_deadline: str | None = None
    resolve_time: str | None = None
    title: str = ""
    url: str = ""

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.record_type, self.record_type)


@dataclass
class ScrapeFailure:
    """单页抓取或解析失败。"""

    url: str
    message: str
    phase: str = "detail"  # list / detail


@dataclass
class PublicityScrapeResult:
    records: list[PublicityRecord] = field(default_factory=list)
    list_pages: list[str] = field(default_factory=list)
    detail_pages: list[str] = field(default_factory=list)
    errors: list[ScrapeFailure] = field(default_factory=list)


def _fetch_soup(client: httpx.Client, url: str) -> BeautifulSoup:
    try:
        resp = client.get(url)
    except httpx.HTTPError as exc:
        raise ScrapeError(url, f"请求失败：{exc}") from exc
    if resp.status_code >= 400:
        raise ScrapeError(url, f"HTTP {resp.status_code}")
    return BeautifulSoup(resp.text, "html.parser")


def _require(values: dict[str, str | None], url: str, required: list[str]) -> None:
    missing = [label for label in required if not values.get(label)]
    if missing:
        raise ScrapeError(url, "缺少必要字段：" + "、".join(missing))


def parse_publicity_detail(html: str, url: str) -> PublicityRecord:
    """解析单个公示/异议详情页 HTML（独立出来便于测试）。"""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.notice")
    if root is None:
        raise ScrapeError(url, "页面结构不符：未找到 div.notice 容器")
    record_type = (root.get("data-notice-type") or "").strip()
    if record_type not in TYPE_LABELS:
        raise ScrapeError(url, f"未知公告类型：{record_type!r}")

    notice_no = _text(root, "#notice-no")
    publish_raw = _text(root, "#publish-time")
    lot_no = _text(root, "#lot-no")
    objection_no = _text(root, "#objection-no")
    accept_raw = _text(root, "#accept-time")
    deadline_raw = _text(root, "#objection-deadline")
    resolve_raw = _text(root, "#resolve-time")

    values = {
        "公告编号": notice_no,
        "发布时间": publish_raw,
        "标段号": lot_no,
        "异议编号": objection_no,
        "受理时间": accept_raw,
        "异议期截止时间": deadline_raw,
    }
    required_by_type = {
        "candidate_publicity": ["公告编号", "发布时间", "标段号", "异议期截止时间"],
        "objection_acceptance": ["公告编号", "发布时间", "标段号", "异议编号", "受理时间"],
        "objection_resolution": ["公告编号", "发布时间", "异议编号"],
    }
    _require(values, url, required_by_type[record_type])

    title_el = root.select_one("h2")
    return PublicityRecord(
        notice_no=notice_no,
        record_type=record_type,
        publish_time=_norm_time(publish_raw, url, "发布时间"),
        lot_no=lot_no,
        objection_no=objection_no,
        accept_time=_norm_time(accept_raw, url, "受理时间") if accept_raw else None,
        objection_deadline=_norm_time(deadline_raw, url, "异议期截止时间") if deadline_raw else None,
        resolve_time=_norm_time(resolve_raw, url, "办结时间") if resolve_raw else None,
        title=title_el.get_text(strip=True) if title_el else notice_no,
        url=url,
    )


def scrape_publicity(directory_url: str) -> PublicityScrapeResult:
    """从公示目录网址出发，抓取同源分页与全部详情页。

    单页失败不会抛出，而是记入 result.errors；起始网址本身非法时抛 ScrapeError。
    """
    parsed = urlparse(directory_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ScrapeError(directory_url, "公示目录网址必须是 http(s) 网址")

    result = PublicityScrapeResult()
    visited_lists: set[str] = set()
    queue = [directory_url]
    detail_urls: list[str] = []
    seen_details: set[str] = set()

    with httpx.Client(
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        # 1) 遍历同源分页，收集详情页链接
        while queue:
            url = queue.pop(0)
            if url in visited_lists:
                continue
            if len(visited_lists) >= MAX_LIST_PAGES:
                result.errors.append(ScrapeFailure(url, f"分页数量超过上限 {MAX_LIST_PAGES}", "list"))
                break

            try:
                soup = _fetch_soup(client, url)
            except ScrapeError as exc:
                result.errors.append(ScrapeFailure(exc.url, exc.message, "list"))
                visited_lists.add(url)
                continue

            items = soup.select("ul.notice-list a[href]")
            nav_links = soup.select("nav.pagination a[href]")
            if not items and not nav_links:
                result.errors.append(
                    ScrapeFailure(
                        url,
                        "页面结构不符：未找到目录列表（ul.notice-list）或分页导航（nav.pagination）",
                        "list",
                    )
                )

            for a in items:
                href = _normalize(a["href"], url)
                if not same_origin(href, directory_url):
                    continue  # 跨源链接不跟随
                if href not in seen_details:
                    seen_details.add(href)
                    detail_urls.append(href)

            visited_lists.add(url)
            result.list_pages.append(url)
            for a in nav_links:
                href = _normalize(a["href"], url)
                if same_origin(href, directory_url) and href not in visited_lists and href not in queue:
                    queue.append(href)

        # 2) 逐个抓取详情页，单页失败记录后继续
        for index, durl in enumerate(detail_urls):
            if index >= MAX_DETAIL_PAGES:
                result.errors.append(ScrapeFailure(durl, f"详情页数量超过上限 {MAX_DETAIL_PAGES}", "detail"))
                break
            try:
                soup = _fetch_soup(client, durl)
            except ScrapeError as exc:
                result.errors.append(ScrapeFailure(exc.url, exc.message, "detail"))
                continue
            result.detail_pages.append(durl)
            try:
                result.records.append(parse_publicity_detail(str(soup), durl))
            except ScrapeError as exc:
                result.errors.append(ScrapeFailure(exc.url, exc.message, "detail"))
            except Exception as exc:  # 兜底：解析异常也要带出问题网址
                result.errors.append(ScrapeFailure(durl, f"解析失败：{exc!r}", "detail"))

    return result
