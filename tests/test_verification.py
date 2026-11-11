"""公示目录解析与中标通知核对规则测试。"""

import pytest

from publicity import ScrapeError, parse_publicity_detail
from verification import (
    STATUS_CANNOT_VERIFY,
    STATUS_NOT_SENDABLE,
    STATUS_SENDABLE,
    analyze,
    normalize_time_input,
)

URL = "http://example.com/publicity/detail/{}"


def html(record_type, fields):
    body = "\n".join(f'<dt>{k}</dt><dd id="{v}">{text}</dd>' for k, v, text in fields)
    return f"""<!DOCTYPE html><html><body>
<div class="notice" data-notice-type="{record_type}">
  <h2>某公示记录</h2>
  <dl>{body}</dl>
</div></body></html>"""


def test_parse_candidate_publicity():
    r = parse_publicity_detail(
        html(
            "candidate_publicity",
            [
                ("公告编号", "notice-no", "PG-1"),
                ("标段号", "lot-no", "BD-1"),
                ("发布时间", "publish-time", "2026-11-05 09:00"),
                ("异议期截止时间", "objection-deadline", "2026-11-10 17:00"),
            ],
        ),
        URL.format("PG-1"),
    )
    assert r.record_type == "candidate_publicity"
    assert r.lot_no == "BD-1"
    assert r.objection_deadline == "2026-11-10 17:00"
    assert r.publish_time == "2026-11-05 09:00"


def test_parse_objection_acceptance():
    r = parse_publicity_detail(
        html(
            "objection_acceptance",
            [
                ("公告编号", "notice-no", "OBJ-1"),
                ("标段号", "lot-no", "BD-1"),
                ("发布时间", "publish-time", "2026-11-06 11:00"),
                ("异议编号", "objection-no", "OBJ-1"),
                ("受理时间", "accept-time", "2026-11-06 10:00"),
            ],
        ),
        URL.format("OBJ-1"),
    )
    assert r.objection_no == "OBJ-1"
    assert r.accept_time == "2026-11-06 10:00"


def test_parse_resolution_optional_lot_and_resolve_time():
    r = parse_publicity_detail(
        html(
            "objection_resolution",
            [
                ("公告编号", "notice-no", "RL-1"),
                ("发布时间", "publish-time", "2026-11-09 15:00"),
                ("异议编号", "objection-no", "OBJ-1"),
                ("办结时间", "resolve-time", "2026-11-09 14:00"),
            ],
        ),
        URL.format("RL-1"),
    )
    assert r.lot_no is None
    assert r.objection_no == "OBJ-1"
    assert r.resolve_time == "2026-11-09 14:00"


def test_parse_missing_required_field():
    with pytest.raises(ScrapeError, match="异议期截止时间"):
        parse_publicity_detail(
            html(
                "candidate_publicity",
                [
                    ("公告编号", "notice-no", "PG-1"),
                    ("标段号", "lot-no", "BD-1"),
                    ("发布时间", "publish-time", "2026-11-05 09:00"),
                ],
            ),
            URL.format("PG-1"),
        )


def test_parse_unknown_type():
    with pytest.raises(ScrapeError, match="未知公告类型"):
        parse_publicity_detail(
            html("tender", [("公告编号", "notice-no", "N-1")]), URL.format("N-1")
        )


def test_normalize_time_input_accepts_datetime_local():
    assert normalize_time_input("2026-11-15T10:00") == "2026-11-15 10:00"
    assert normalize_time_input("2026/11/15 10:00:00") == "2026-11-15 10:00"
    assert normalize_time_input("不是时间") is None


# ---------------------------------------------------------------------------
# 核对规则
# ---------------------------------------------------------------------------

PUB_URL = URL.format("PG-1")
OBJ_URL = URL.format("OBJ-1")


def rec(**kwargs):
    from publicity import PublicityRecord

    defaults = dict(
        notice_no="N",
        record_type="",
        publish_time="2026-11-01 09:00",
        lot_no=None,
        objection_no=None,
        accept_time=None,
        objection_deadline=None,
        title="N",
        url=URL.format("N"),
    )
    defaults.update(kwargs)
    return PublicityRecord(**defaults)


def publicity(lot="BD-1", publish="2026-11-05 09:00", deadline="2026-11-10 17:00"):
    return rec(
        notice_no="PG-1",
        record_type="candidate_publicity",
        publish_time=publish,
        lot_no=lot,
        objection_deadline=deadline,
        url=PUB_URL,
    )


def acceptance(no="OBJ-1", lot="BD-1", publish="2026-11-06 11:00", accept="2026-11-06 10:00"):
    return rec(
        notice_no=no,
        record_type="objection_acceptance",
        publish_time=publish,
        lot_no=lot,
        objection_no=no,
        accept_time=accept,
        url=URL.format(no),
    )


def resolution(ref="OBJ-1", lot="BD-1", publish="2026-11-09 15:00"):
    return rec(
        notice_no=f"RL-{ref}",
        record_type="objection_resolution",
        publish_time=publish,
        lot_no=lot,
        objection_no=ref,
        url=URL.format(f"RL-{ref}"),
    )


def test_sendable_when_after_deadline_and_all_resolved():
    records = [
        publicity(),
        acceptance("OBJ-1"),
        acceptance("OBJ-2", publish="2026-11-09 16:00", accept="2026-11-09 15:30"),
        resolution("OBJ-1"),
        resolution("OBJ-2", publish="2026-11-10 11:00"),
    ]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_SENDABLE
    assert result["objection_deadline"] == "2026-11-10 17:00"
    assert len(result["objections"]) == 2
    assert not result["unresolved"]


def test_not_sendable_when_proposed_time_not_after_deadline():
    result = analyze([publicity(), acceptance()], "BD-1", "2026-11-10 17:00")
    assert result["status"] == STATUS_NOT_SENDABLE
    assert result["time_after_deadline"] is False
    assert "不晚于" in result["blockers"][0]["message"]


def test_not_sendable_lists_unresolved_objection_and_source():
    result = analyze([publicity(), acceptance()], "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_NOT_SENDABLE
    assert len(result["unresolved"]) == 1
    assert result["unresolved"][0]["objection_no"] == "OBJ-1"
    assert result["unresolved"][0]["source_url"] == OBJ_URL
    assert any(b["url"] == OBJ_URL for b in result["blockers"])


def test_resolution_must_reference_same_lot():
    # 办结记录属于其他标段：不能用于办结 BD-1 的异议
    records = [publicity(), acceptance(), resolution("OBJ-1", lot="BD-2")]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_NOT_SENDABLE
    assert result["unresolved"][0]["objection_no"] == "OBJ-1"


def test_resolution_referencing_other_lot_objection_does_not_resolve_target():
    # 办结记录虽声明属于 BD-1，但引用的是 BD-2 的异议编号：不算 BD-1 的办结
    records = [
        publicity(),
        acceptance("OBJ-1"),
        acceptance("OBJ-2", lot="BD-2"),
        resolution("OBJ-2", lot="BD-1"),
    ]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_NOT_SENDABLE
    assert result["unresolved"][0]["objection_no"] == "OBJ-1"


def test_records_published_after_proposed_time_are_ignored():
    # 异议受理与办结都在拟发时间之后发布：不参与核对
    records = [
        publicity(),
        acceptance(publish="2026-11-16 11:00", accept="2026-11-06 10:00"),
        resolution(publish="2026-11-16 15:00"),
    ]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    # 没有可用异议，视为无相关异议；时间条件满足 -> 可发送
    assert result["status"] == STATUS_SENDABLE
    assert result["late_record_count"] == 2


def test_objection_accepted_after_deadline_is_ignored():
    records = [
        publicity(),
        acceptance("OBJ-1", accept="2026-11-11 08:00", publish="2026-11-11 09:00"),
    ]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_SENDABLE
    assert result["ignored_objections"][0]["objection_no"] == "OBJ-1"


def test_missing_publicity_is_cannot_verify_with_url():
    result = analyze([], "BD-1", "2026-11-15 10:00", directory_url="http://example.com/dir")
    assert result["status"] == STATUS_CANNOT_VERIFY
    assert any(p["url"] == "http://example.com/dir" for p in result["problems"])


def test_dangling_resolution_reference_is_cannot_verify_with_url():
    records = [publicity(), acceptance(), resolution("OBJ-1"), resolution("OBJ-999", publish="2026-11-11 09:00")]
    result = analyze(records, "BD-1", "2026-11-15 10:00")
    assert result["status"] == STATUS_CANNOT_VERIFY
    assert any(
        "OBJ-999" in p["message"] and p["url"] == URL.format("RL-OBJ-999")
        for p in result["problems"]
    )


def test_scrape_error_is_cannot_verify_with_url():
    from publicity import ScrapeFailure

    result = analyze(
        [publicity()],
        "BD-1",
        "2026-11-15 10:00",
        errors=[ScrapeFailure("http://example.com/bad", "HTTP 500", "detail")],
    )
    assert result["status"] == STATUS_CANNOT_VERIFY
    assert result["problems"][0]["url"] == "http://example.com/bad"


def test_latest_usable_publicity_governs_objection_period():
    records = [
        publicity(deadline="2026-11-10 17:00"),
        publicity(deadline="2026-11-20 17:00", publish="2026-11-15 09:00"),
    ]
    result = analyze(records, "BD-1", "2026-11-18 10:00")
    assert result["objection_deadline"] == "2026-11-20 17:00"
    assert result["time_after_deadline"] is False
