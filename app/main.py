"""核对工具（FastAPI 网页）。

- 截标时间核对：输入公告列表网址，抓取同源分页与详情，按项目串起公告链；
- 中标通知发送前核对：输入公示目录网址、标段号与拟发时间，核对公示期异议
  是否全部办结，给出可发送 / 不可发送 / 无法核定结论及来源。
"""

import os
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import analysis
import db
import scraper
import verification

DEFAULT_START_URL = os.environ.get("DEFAULT_START_URL", "http://sample-site:8000/list.html?page=1")
DEFAULT_PUBLICITY_URL = os.environ.get(
    "DEFAULT_PUBLICITY_URL", "http://sample-site:8000/publicity.html?page=1"
)
# 演示用拟发时间预填值（留空则不预填）
DEFAULT_PROPOSED_TIME = os.environ.get("DEFAULT_PROPOSED_TIME", "")
# 展示层网址改写：容器内部地址 → 浏览器可访问地址（可选）
URL_REWRITE_FROM = os.environ.get("URL_REWRITE_FROM", "")
URL_REWRITE_TO = os.environ.get("URL_REWRITE_TO", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="截标时间核对工具", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


def public_url(url: str) -> str:
    """把采集用的内部网址改写成浏览器可访问的网址（未配置时原样返回）。"""
    if URL_REWRITE_FROM and URL_REWRITE_TO and url.startswith(URL_REWRITE_FROM):
        return URL_REWRITE_TO + url[len(URL_REWRITE_FROM) :]
    return url


def internal_url(url: str) -> str:
    """把用户粘贴的浏览器网址反向映射回容器内部网址（未配置时原样返回）。"""
    if URL_REWRITE_FROM and URL_REWRITE_TO and url.startswith(URL_REWRITE_TO):
        return URL_REWRITE_FROM + url[len(URL_REWRITE_TO) :]
    return url


templates.env.filters["public_url"] = public_url


@app.get("/", response_class=HTMLResponse)
def index(request: Request, msg: str = ""):
    rounds = db.get_rounds()
    latest_ok = db.get_latest_success_round()
    projects = None
    if latest_ok is not None:
        projects = analysis.build_projects(db.get_announcements(latest_ok["id"]))
    last_round = rounds[0] if rounds else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "default_start_url": DEFAULT_START_URL,
            "default_publicity_url": DEFAULT_PUBLICITY_URL,
            "default_proposed_time": DEFAULT_PROPOSED_TIME.replace(" ", "T"),
            "msg": msg,
            "last_round": last_round,
            "latest_ok": latest_ok,
            "projects": projects,
            "rounds": rounds,
        },
    )


@app.post("/scrape")
def do_scrape(start_url: str = Form(...)):
    start_url = start_url.strip()
    round_id = db.create_round(start_url)
    try:
        result = scraper.scrape(start_url)
    except scraper.ScrapeError as exc:
        # 任一页面失败：记录出错网址，本轮不产生数据，页面仍展示上一轮结果
        db.finish_round_failed(round_id, exc.url, exc.message)
        msg = f"第 {round_id} 轮抓取失败：{exc.url}（{exc.message}）。已保留上一轮结果。"
        return RedirectResponse(f"/?msg={quote(msg)}", status_code=303)
    except Exception as exc:  # 兜底，避免未预期异常丢轮次
        db.finish_round_failed(round_id, start_url, f"未预期错误：{exc!r}")
        msg = f"第 {round_id} 轮抓取失败：{start_url}（{exc!r}）。已保留上一轮结果。"
        return RedirectResponse(f"/?msg={quote(msg)}", status_code=303)

    db.finish_round_success(round_id, result.announcements, len(result.list_pages), len(result.detail_pages))
    msg = (
        f"第 {round_id} 轮抓取成功：{len(result.list_pages)} 个列表页、"
        f"{len(result.detail_pages)} 个详情页，共 {len(result.announcements)} 条公告。"
    )
    return RedirectResponse(f"/?msg={quote(msg)}", status_code=303)


def _verify_context(
    request: Request,
    *,
    directory_url: str,
    lot_no: str,
    proposed_time: str,
    result: dict | None = None,
    form_error: str = "",
):
    # datetime-local 输入框使用 T 分隔；同时兼容用户直接粘贴的空格格式
    proposed_time = proposed_time or DEFAULT_PROPOSED_TIME
    time_input = proposed_time.replace(" ", "T") if proposed_time else ""
    return templates.TemplateResponse(
        request,
        "verify.html",
        {
            "default_publicity_url": DEFAULT_PUBLICITY_URL,
            "form": {
                "directory_url": directory_url or DEFAULT_PUBLICITY_URL,
                "lot_no": lot_no,
                "proposed_time": time_input,
            },
            "result": result,
            "form_error": form_error,
        },
    )


@app.get("/verify", response_class=HTMLResponse)
def verify_form(request: Request, directory_url: str = "", lot_no: str = "", proposed_time: str = ""):
    return _verify_context(
        request,
        directory_url=directory_url,
        lot_no=lot_no,
        proposed_time=proposed_time,
    )


@app.post("/verify", response_class=HTMLResponse)
def do_verify(
    request: Request,
    directory_url: str = Form(...),
    lot_no: str = Form(...),
    proposed_time: str = Form(...),
):
    directory_url = internal_url(directory_url.strip())
    lot_no = lot_no.strip()
    proposed_raw = proposed_time.strip()
    normalized = verification.normalize_time_input(proposed_raw)

    if not lot_no:
        return _verify_context(
            request,
            directory_url=directory_url,
            lot_no=lot_no,
            proposed_time=proposed_raw,
            form_error="请填写标段号。",
        )
    if normalized is None:
        return _verify_context(
            request,
            directory_url=directory_url,
            lot_no=lot_no,
            proposed_time=proposed_raw,
            form_error=f"拟发时间格式无法识别：{proposed_raw!r}（示例：2026-11-15 10:00）。",
        )

    try:
        result = verification.verify(directory_url, lot_no, normalized)
    except Exception as exc:  # 兜底：任何未预期错误都按“无法核定”展示问题网址
        result = verification.analyze(
            [],
            lot_no,
            normalized,
            directory_url=directory_url,
            errors=[verification.ScrapeFailure(directory_url, f"核对过程发生未预期错误：{exc!r}", "list")],
        )

    return _verify_context(
        request,
        directory_url=directory_url,
        lot_no=lot_no,
        proposed_time=normalized,
        result=result,
    )
