"""示例公告站：模拟公开招标公告网站。

页面结构（与采集端解析约定一致）：
- 招标公告列表 /list.html?page=N，详情 /detail/<公告编号>.html
    - 容器 div.notice，data-notice-type = tender|correction|cancellation
    - #project-no 项目编号、#notice-no 公告编号、#publish-time 发布时间
    - #deadline 截标时间（如有）、#target-notice 更正/撤销所指公告编号（如有）
- 公示目录 /publicity.html?page=N，详情 /publicity/detail/<公告编号>.html
    - 容器 div.notice，data-notice-type =
      candidate_publicity|objection_acceptance|objection_resolution
    - #notice-no / #publish-time 公共字段；#lot-no 标段号
    - 候选人公示： #objection-deadline 异议期截止时间
    - 异议受理： #objection-no 异议编号、#accept-time 受理时间
    - 异议办结： #objection-no 引用的异议编号、#resolve-time 办结时间（可选）

故障注入：
- GET /admin/fail?on=1：招标公告详情 NT-2026-0004 返回 500；
- GET /admin/fail-publicity?on=1：公示详情 RL-2026-001 返回 500。
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from data import (
    ANNOUNCEMENTS,
    PAGE_SIZE,
    PUBLICITY_PAGE_SIZE,
    PUBLICITY_TYPE_LABELS,
    TYPE_LABELS,
    get_by_notice_no,
    get_publicity_by_notice_no,
    sorted_announcements,
    sorted_publicity,
)

app = FastAPI(title="示例公告站")
templates = Jinja2Templates(directory="templates")

# 故障注入状态：开启后 FAIL_NOTICE 对应的详情页返回 500
FAIL_STATE = {"on": False}
FAIL_NOTICE = "NT-2026-0004"

# 公示目录故障注入：开启后 FAIL_PUBLICITY_NOTICE 对应的详情页返回 500
FAIL_PUBLICITY_STATE = {"on": False}
FAIL_PUBLICITY_NOTICE = "RL-2026-001"


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/list.html?page=1")


@app.get("/list.html", response_class=HTMLResponse)
def list_page(request: Request, page: int = 1):
    items_all = sorted_announcements()
    total_pages = max(1, (len(items_all) + PAGE_SIZE - 1) // PAGE_SIZE)
    if page < 1 or page > total_pages:
        return HTMLResponse("<h1>404 页码不存在</h1>", status_code=404)
    start = (page - 1) * PAGE_SIZE
    items = []
    for a in items_all[start : start + PAGE_SIZE]:
        items.append({**a, "type_label": TYPE_LABELS[a["type"]]})
    return templates.TemplateResponse(
        request,
        "list.html",
        {
            "items": items,
            "page": page,
            "total_pages": total_pages,
            "pages": list(range(1, total_pages + 1)),
            "fail_on": FAIL_STATE["on"],
            "fail_notice": FAIL_NOTICE,
        },
    )


@app.get("/detail/{notice_no}.html", response_class=HTMLResponse)
def detail_page(request: Request, notice_no: str):
    if FAIL_STATE["on"] and notice_no == FAIL_NOTICE:
        return HTMLResponse(
            f"<h1>500 Internal Server Error</h1><p>故障注入已开启：{notice_no} 暂时不可用。</p>",
            status_code=500,
        )
    a = get_by_notice_no(notice_no)
    if a is None:
        return HTMLResponse(f"<h1>404 公告不存在：{notice_no}</h1>", status_code=404)
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"a": {**a, "type_label": TYPE_LABELS[a["type"]]}, "fail_on": FAIL_STATE["on"]},
    )


@app.get("/publicity.html", response_class=HTMLResponse)
def publicity_list(request: Request, page: int = 1):
    items_all = sorted_publicity()
    total_pages = max(1, (len(items_all) + PUBLICITY_PAGE_SIZE - 1) // PUBLICITY_PAGE_SIZE)
    if page < 1 or page > total_pages:
        return HTMLResponse("<h1>404 页码不存在</h1>", status_code=404)
    start = (page - 1) * PUBLICITY_PAGE_SIZE
    items = []
    for r in items_all[start : start + PUBLICITY_PAGE_SIZE]:
        items.append({**r, "type_label": PUBLICITY_TYPE_LABELS[r["type"]]})
    return templates.TemplateResponse(
        request,
        "publicity_list.html",
        {
            "items": items,
            "page": page,
            "total_pages": total_pages,
            "pages": list(range(1, total_pages + 1)),
            "fail_publicity_on": FAIL_PUBLICITY_STATE["on"],
            "fail_publicity_notice": FAIL_PUBLICITY_NOTICE,
        },
    )


@app.get("/publicity/detail/{notice_no}.html", response_class=HTMLResponse)
def publicity_detail(request: Request, notice_no: str):
    if FAIL_PUBLICITY_STATE["on"] and notice_no == FAIL_PUBLICITY_NOTICE:
        return HTMLResponse(
            f"<h1>500 Internal Server Error</h1><p>公示目录故障注入已开启：{notice_no} 暂时不可用。</p>",
            status_code=500,
        )
    r = get_publicity_by_notice_no(notice_no)
    if r is None:
        return HTMLResponse(f"<h1>404 公示记录不存在：{notice_no}</h1>", status_code=404)
    return templates.TemplateResponse(
        request,
        "publicity_detail.html",
        {
            "r": {**r, "type_label": PUBLICITY_TYPE_LABELS[r["type"]]},
            "fail_publicity_on": FAIL_PUBLICITY_STATE["on"],
        },
    )


@app.get("/admin/fail", response_class=HTMLResponse)
def admin_fail(on: int = 0):
    FAIL_STATE["on"] = bool(on)
    # 兼容旧演示入口：同一个开关也开启公示详情故障
    FAIL_PUBLICITY_STATE["on"] = bool(on)
    state = "已开启" if FAIL_STATE["on"] else "已关闭"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>故障注入</title></head>
<body>
<h1>故障注入{state}</h1>
<p>开启后，招标公告详情页 <code>/detail/{FAIL_NOTICE}.html</code> 与公示详情页
<code>/publicity/detail/{FAIL_PUBLICITY_NOTICE}.html</code> 均将返回 500。</p>
<p>也可单独控制公示目录故障：<a href="/admin/fail-publicity?on=1">开启</a> /
<a href="/admin/fail-publicity?on=0">关闭</a>
（当前：{"开" if FAIL_PUBLICITY_STATE["on"] else "关"}）。</p>
<p><a href="/admin/fail?on=1">开启故障</a> · <a href="/admin/fail?on=0">关闭故障</a> ·
<a href="/list.html?page=1">公告列表</a> · <a href="/publicity.html?page=1">公示目录</a></p>
</body></html>"""


@app.get("/admin/fail-publicity", response_class=HTMLResponse)
def admin_fail_publicity(on: int = 0):
    FAIL_PUBLICITY_STATE["on"] = bool(on)
    state = "已开启" if FAIL_PUBLICITY_STATE["on"] else "已关闭"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>公示目录故障注入</title></head>
<body>
<h1>公示目录故障注入{state}</h1>
<p>开启后，详情页 <code>/publicity/detail/{FAIL_PUBLICITY_NOTICE}.html</code> 将返回 500，
用于验证核对页“抓取失败 → 无法核定 + 问题网址”的展示。</p>
<p><a href="/admin/fail-publicity?on=1">开启</a> · <a href="/admin/fail-publicity?on=0">关闭</a> ·
<a href="/publicity.html?page=1">返回公示目录</a></p>
</body></html>"""


@app.get("/admin/status")
def admin_status():
    return {
        "fail_on": FAIL_STATE["on"],
        "fail_notice": FAIL_NOTICE,
        "fail_publicity_on": FAIL_PUBLICITY_STATE["on"],
        "fail_publicity_notice": FAIL_PUBLICITY_NOTICE,
        "announcements": len(ANNOUNCEMENTS),
        "publicity_records": len(sorted_publicity()),
    }
