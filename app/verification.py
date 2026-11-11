"""中标通知发送前异议核对规则。

输入：公示目录抓取到的全部记录、标段号、拟发时间。
规则：
1. 只使用发布时间不晚于拟发时间的记录；
2. 取该标段发布时间不晚于拟发时间的候选人公示，按发布时间取最新一条，
   以其“异议期截止时间”作为该标段的异议期；
3. 异议按受理时间筛选：仅受理时间不晚于异议期截止时间的异议参与核对；
4. 办结记录必须引用该标段相关异议的编号，且发布时间不晚于拟发时间；
5. 拟发时间晚于异议期截止时间、且每项相关异议均有有效办结记录时，才可发送；
6. 抓取失败、候选人公示缺失、办结记录引用的受理详情缺失时，无法核定。
"""

from __future__ import annotations

from datetime import datetime

from publicity import PublicityRecord, ScrapeFailure

STATUS_SENDABLE = "sendable"
STATUS_NOT_SENDABLE = "not_sendable"
STATUS_CANNOT_VERIFY = "cannot_verify"

STATUS_LABELS = {
    STATUS_SENDABLE: "可发送",
    STATUS_NOT_SENDABLE: "不可发送",
    STATUS_CANNOT_VERIFY: "无法核定",
}

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
)


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def normalize_time_input(raw: str) -> str | None:
    """把用户输入的拟发时间归一化为 YYYY-MM-DD HH:MM；无法识别返回 None。"""
    raw = (raw or "").strip().replace("T", " ")
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return None


def _problem(message: str, url: str | None = None) -> dict:
    return {"message": message, "url": url}


def _record_link(record: PublicityRecord) -> dict:
    return {
        "notice_no": record.notice_no,
        "type_label": record.type_label,
        "publish_time": record.publish_time,
        "objection_deadline": record.objection_deadline,
        "resolve_time": record.resolve_time,
        "url": record.url,
    }


def analyze(
    records: list[PublicityRecord],
    lot_no: str,
    proposed_time: str,
    *,
    directory_url: str = "",
    errors: list[ScrapeFailure] | None = None,
    list_pages: list[str] | None = None,
    detail_pages: list[str] | None = None,
) -> dict:
    """按上述规则核对，返回可直接交给模板的结果字典。"""
    errors = errors or []
    normalized_proposed = normalize_time_input(proposed_time)
    if normalized_proposed is None:
        raise ValueError(f"拟发时间格式无法识别：{proposed_time!r}")
    proposed_time = normalized_proposed
    proposed = _dt(proposed_time)

    # 无法核定的问题（抓取失败 / 关联详情缺失）
    problems = [_problem(f"抓取失败：{e.message}", e.url) for e in errors]

    # 规则 1：只使用发布时间不晚于拟发时间的记录
    usable = [r for r in records if _dt(r.publish_time) <= proposed]
    late_count = len(records) - len(usable)

    # 规则 2：该标段的候选人公示，取不晚于拟发时间的最新一条
    lot_publicities = [
        r for r in records if r.record_type == "candidate_publicity" and r.lot_no == lot_no
    ]
    usable_publicities = [r for r in lot_publicities if _dt(r.publish_time) <= proposed]
    publicity = None
    deadline = None
    if usable_publicities:
        publicity = max(usable_publicities, key=lambda r: (r.publish_time, r.notice_no))
        deadline = publicity.objection_deadline
        if not deadline:
            problems.append(_problem("候选人公示缺少异议期截止时间", publicity.url))
    elif lot_publicities:
        problems.append(
            _problem(
                f"标段 {lot_no} 的候选人公示发布时间均晚于拟发时间，无法确定适用公示",
                lot_publicities[0].url,
            )
        )
    else:
        problems.append(
            _problem(
                f"未找到标段 {lot_no} 的候选人公示（仅使用发布时间不晚于拟发时间的记录）",
                directory_url or None,
            )
        )

    deadline_dt = _dt(deadline) if deadline else None
    time_after_deadline = bool(deadline_dt and proposed > deadline_dt)

    # 规则 3：该标段、受理时间不晚于异议期截止时间的异议
    acceptance_records = [
        r for r in records if r.record_type == "objection_acceptance" and r.lot_no == lot_no
    ]
    relevant_raw: list[PublicityRecord] = []
    ignored_objections: list[dict] = []
    for r in acceptance_records:
        if _dt(r.publish_time) > proposed:
            ignored_objections.append(
                {
                    "objection_no": r.objection_no,
                    "reason": "发布时间晚于拟发时间",
                    "url": r.url,
                }
            )
            continue
        if not r.accept_time:
            problems.append(_problem(f"异议 {r.objection_no or r.notice_no} 缺少受理时间", r.url))
            continue
        if deadline_dt is None or _dt(r.accept_time) > deadline_dt:
            ignored_objections.append(
                {
                    "objection_no": r.objection_no,
                    "reason": f"受理时间晚于异议期截止时间 {deadline}" if deadline else "异议期未知",
                    "url": r.url,
                }
            )
            continue
        relevant_raw.append(r)

    # 同一异议编号如有多条受理记录，采用发布时间最新的一条
    relevant_by_no: dict[str, PublicityRecord] = {}
    for r in relevant_raw:
        key = r.objection_no or r.notice_no
        current = relevant_by_no.get(key)
        if current is None or (r.publish_time, r.notice_no) > (current.publish_time, current.notice_no):
            relevant_by_no[key] = r

    # 全部受理记录（用于判断办结记录引用的异议详情是否存在）
    acceptances_by_no: dict[str, list[PublicityRecord]] = {}
    for r in records:
        if r.record_type == "objection_acceptance" and r.objection_no:
            acceptances_by_no.setdefault(r.objection_no, []).append(r)

    # 规则 4：办结记录须引用同标段异议编号，且发布时间不晚于拟发时间
    usable_resolutions = [
        r for r in records if r.record_type == "objection_resolution" and _dt(r.publish_time) <= proposed
    ]

    objections: list[dict] = []
    for objection_no, acceptance in sorted(
        relevant_by_no.items(), key=lambda item: (item[1].accept_time or "", item[0])
    ):
        resolutions = []
        for r in usable_resolutions:
            if r.objection_no != objection_no:
                continue
            if r.lot_no is not None and r.lot_no != lot_no:
                continue  # 办结记录不属于该标段，不能用于办结该异议
            resolutions.append(_record_link(r))
        objections.append(
            {
                "objection_no": objection_no,
                "lot_no": acceptance.lot_no,
                "accept_time": acceptance.accept_time,
                "publish_time": acceptance.publish_time,
                "source_url": acceptance.url,
                "resolved": bool(resolutions),
                "resolutions": resolutions,
            }
        )

    # 检查办结记录引用的受理详情是否缺失。
    # 引用其他标段异议的办结记录不算有效办结（由上面的同标段过滤处理），
    # 不视为“关联详情缺失”；只有完全找不到对应受理记录时才无法核定。
    for r in usable_resolutions:
        if r.lot_no is not None and r.lot_no != lot_no:
            continue  # 与本次核对标段无关
        if not acceptances_by_no.get(r.objection_no or ""):
            problems.append(
                _problem(
                    f"办结记录 {r.notice_no} 引用的异议编号 {r.objection_no} 未找到对应受理记录",
                    r.url,
                )
            )

    unresolved = [o for o in objections if not o["resolved"]]

    # 不可发送事项：时间条件不满足，或存在未办结异议
    blockers: list[dict] = []
    if deadline is not None and not time_after_deadline:
        blockers.append(
            _problem(
                f"拟发时间 {proposed_time} 不晚于公示异议期截止时间 {deadline}",
                publicity.url if publicity else directory_url or None,
            )
        )
    for o in unresolved:
        blockers.append(
            _problem(
                f"异议 {o['objection_no']} 尚未办结（受理时间 {o['accept_time']}）",
                o["source_url"],
            )
        )

    if problems:
        status = STATUS_CANNOT_VERIFY
    elif blockers:
        status = STATUS_NOT_SENDABLE
    else:
        status = STATUS_SENDABLE

    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "lot_no": lot_no,
        "proposed_time": proposed_time,
        "directory_url": directory_url,
        "publicity": _record_link(publicity) if publicity else None,
        "objection_deadline": deadline,
        "time_after_deadline": time_after_deadline,
        "objections": objections,
        "unresolved": unresolved,
        "blockers": blockers,
        "problems": problems,
        "ignored_objections": ignored_objections,
        "record_count": len(records),
        "usable_record_count": len(usable),
        "late_record_count": late_count,
        "list_pages": list_pages or [],
        "detail_pages": detail_pages or [],
        "errors": [{"url": e.url, "message": e.message, "phase": e.phase} for e in errors],
    }


def verify(directory_url: str, lot_no: str, proposed_time: str) -> dict:
    """抓取公示目录并核对。proposed_time 须已归一化。"""
    from publicity import ScrapeError, scrape_publicity

    try:
        scraped = scrape_publicity(directory_url)
    except ScrapeError as exc:
        return analyze(
            [],
            lot_no,
            proposed_time,
            directory_url=directory_url,
            errors=[ScrapeFailure(exc.url, exc.message, "list")],
        )
    return analyze(
        scraped.records,
        lot_no,
        proposed_time,
        directory_url=directory_url,
        errors=scraped.errors,
        list_pages=scraped.list_pages,
        detail_pages=scraped.detail_pages,
    )
