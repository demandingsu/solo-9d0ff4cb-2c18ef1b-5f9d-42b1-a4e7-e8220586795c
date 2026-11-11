"""示例公告站的公告数据。

字段与采集端约定的页面结构一一对应：
- notice_no    公告编号
- project_no   项目编号
- type         公告类型：tender 招标公告 / correction 更正公告 / cancellation 撤销公告
- title        公告标题
- publish_time 发布时间（YYYY-MM-DD HH:MM）
- deadline     截标时间（撤销公告无）
- target       更正 / 撤销所指的公告编号（招标公告无）
- body         正文
"""

TYPE_LABELS = {
    "tender": "招标公告",
    "correction": "更正公告",
    "cancellation": "撤销公告",
}

ANNOUNCEMENTS = [
    {
        "notice_no": "NT-2026-0001",
        "project_no": "PRJ-2026-001",
        "type": "tender",
        "title": "市政道路改造工程施工招标",
        "publish_time": "2026-11-01 09:00",
        "deadline": "2026-11-20 17:00",
        "target": None,
        "body": "现就市政道路改造工程进行公开招标，欢迎符合条件的投标人参加投标。",
    },
    {
        "notice_no": "NT-2026-0003",
        "project_no": "PRJ-2026-002",
        "type": "tender",
        "title": "办公楼物业服务采购",
        "publish_time": "2026-11-02 09:00",
        "deadline": "2026-11-22 12:00",
        "target": None,
        "body": "现就办公楼物业服务进行公开招标，服务期一年。",
    },
    {
        "notice_no": "NT-2026-0005",
        "project_no": "PRJ-2026-003",
        "type": "tender",
        "title": "智慧园区网络设备采购",
        "publish_time": "2026-11-03 09:00",
        "deadline": "2026-11-24 17:00",
        "target": None,
        "body": "现就智慧园区网络设备采购进行公开招标。",
    },
    {
        "notice_no": "NT-2026-0008",
        "project_no": "PRJ-2026-004",
        "type": "tender",
        "title": "职工食堂食材配送服务",
        "publish_time": "2026-11-04 09:00",
        "deadline": "2026-11-21 17:00",
        "target": None,
        "body": "现就职工食堂食材配送服务进行公开招标。",
    },
    {
        "notice_no": "NT-2026-0002",
        "project_no": "PRJ-2026-001",
        "type": "correction",
        "title": "市政道路改造工程施工招标更正公告",
        "publish_time": "2026-11-05 10:00",
        "deadline": "2026-11-25 17:00",
        "target": "NT-2026-0001",
        "body": "因工程量清单调整，现将截标时间由 2026-11-20 17:00 更正为 2026-11-25 17:00，其余内容不变。",
    },
    {
        "notice_no": "NT-2026-0004",
        "project_no": "PRJ-2026-002",
        "type": "cancellation",
        "title": "办公楼物业服务采购撤销公告",
        "publish_time": "2026-11-06 14:00",
        "deadline": None,
        "target": "NT-2026-0003",
        "body": "因采购计划调整，现撤销办公楼物业服务采购招标公告，本项目停止办理。",
    },
    {
        "notice_no": "NT-2026-0006",
        "project_no": "PRJ-2026-003",
        "type": "correction",
        "title": "智慧园区网络设备采购更正公告（一）",
        "publish_time": "2026-11-07 09:30",
        "deadline": "2026-11-26 10:00",
        "target": "NT-2026-0005",
        "body": "现将截标时间由 2026-11-24 17:00 更正为 2026-11-26 10:00。",
    },
    {
        "notice_no": "NT-2026-0009",
        "project_no": "PRJ-2026-005",
        "type": "tender",
        "title": "医疗设备采购项目",
        "publish_time": "2026-11-08 09:00",
        "deadline": "2026-11-30 17:00",
        "target": None,
        "body": "现就医疗设备采购项目进行公开招标。",
    },
    {
        "notice_no": "NT-2026-0007",
        "project_no": "PRJ-2026-003",
        "type": "correction",
        "title": "智慧园区网络设备采购更正公告（二）",
        "publish_time": "2026-11-09 16:00",
        "deadline": "2026-11-28 10:00",
        "target": "NT-2026-0006",
        "body": "现将截标时间由 2026-11-26 10:00 更正为 2026-11-28 10:00。",
    },
    {
        "notice_no": "NT-2026-0010",
        "project_no": "PRJ-2026-005",
        "type": "correction",
        "title": "医疗设备采购项目更正公告",
        "publish_time": "2026-11-10 11:00",
        "deadline": "2026-12-02 17:00",
        "target": "NT-2026-0009",
        "body": "现将截标时间由 2026-11-30 17:00 更正为 2026-12-02 17:00。",
    },
    {
        "notice_no": "NT-2026-0011",
        "project_no": "PRJ-2026-005",
        "type": "cancellation",
        "title": "医疗设备采购项目撤销公告",
        "publish_time": "2026-11-11 09:00",
        "deadline": None,
        "target": "NT-2026-0009",
        "body": "因技术参数重大调整，现撤销医疗设备采购项目招标公告，本项目停止办理。",
    },
]

PAGE_SIZE = 5


def sorted_announcements():
    """列表页按发布时间倒序展示。"""
    return sorted(ANNOUNCEMENTS, key=lambda a: (a["publish_time"], a["notice_no"]), reverse=True)


def get_by_notice_no(notice_no):
    for a in ANNOUNCEMENTS:
        if a["notice_no"] == notice_no:
            return a
    return None


# ---------------------------------------------------------------------------
# 中标通知核对演示数据：候选人公示 / 异议受理 / 异议办结
# ---------------------------------------------------------------------------

PUBLICITY_TYPE_LABELS = {
    "candidate_publicity": "候选人公示",
    "objection_acceptance": "异议受理",
    "objection_resolution": "异议办结",
}

PUBLICITY_PAGE_SIZE = 4

PUBLICITY_RECORDS = [
    # --- 候选人公示 ---
    {
        "notice_no": "PG-2026-101",
        "type": "candidate_publicity",
        "title": "标段一（BD-2026-01）中标候选人公示",
        "publish_time": "2026-11-05 09:00",
        "lot_no": "BD-2026-01",
        "objection_no": None,
        "accept_time": None,
        "objection_deadline": "2026-11-10 17:00",
        "resolve_time": None,
        "body": "标段一中标候选人公示，异议期截止 2026-11-10 17:00。",
    },
    {
        "notice_no": "PG-2026-102",
        "type": "candidate_publicity",
        "title": "标段二（BD-2026-02）中标候选人公示",
        "publish_time": "2026-11-05 10:00",
        "lot_no": "BD-2026-02",
        "objection_no": None,
        "accept_time": None,
        "objection_deadline": "2026-11-11 17:00",
        "resolve_time": None,
        "body": "标段二中标候选人公示，异议期截止 2026-11-11 17:00。",
    },
    {
        "notice_no": "PG-2026-103",
        "type": "candidate_publicity",
        "title": "标段三（BD-2026-03）中标候选人公示",
        "publish_time": "2026-11-06 09:00",
        "lot_no": "BD-2026-03",
        "objection_no": None,
        "accept_time": None,
        "objection_deadline": "2026-11-12 17:00",
        "resolve_time": None,
        "body": "标段三中标候选人公示，异议期截止 2026-11-12 17:00。",
    },
    {
        "notice_no": "PG-2026-104",
        "type": "candidate_publicity",
        "title": "标段四（BD-2026-04）中标候选人公示",
        "publish_time": "2026-11-06 10:00",
        "lot_no": "BD-2026-04",
        "objection_no": None,
        "accept_time": None,
        "objection_deadline": "2026-11-12 17:00",
        "resolve_time": None,
        "body": "标段四中标候选人公示，异议期截止 2026-11-12 17:00。",
    },
    {
        "notice_no": "PG-2026-105",
        "type": "candidate_publicity",
        "title": "标段五（BD-2026-05）中标候选人公示",
        "publish_time": "2026-11-07 09:00",
        "lot_no": "BD-2026-05",
        "objection_no": None,
        "accept_time": None,
        "objection_deadline": "2026-11-13 17:00",
        "resolve_time": None,
        "body": "标段五中标候选人公示，异议期截止 2026-11-13 17:00。",
    },
    # --- 异议受理 ---
    {
        "notice_no": "OBJ-2026-001",
        "type": "objection_acceptance",
        "title": "标段一异议受理通知（OBJ-2026-001）",
        "publish_time": "2026-11-06 11:00",
        "lot_no": "BD-2026-01",
        "objection_no": "OBJ-2026-001",
        "accept_time": "2026-11-06 10:00",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段一评标结果的异议。",
    },
    {
        "notice_no": "OBJ-2026-002",
        "type": "objection_acceptance",
        "title": "标段一异议受理通知（OBJ-2026-002）",
        "publish_time": "2026-11-09 16:00",
        "lot_no": "BD-2026-01",
        "objection_no": "OBJ-2026-002",
        "accept_time": "2026-11-09 15:30",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段一评标结果的第二项异议。",
    },
    {
        "notice_no": "OBJ-2026-003",
        "type": "objection_acceptance",
        "title": "标段二异议受理通知（OBJ-2026-003）",
        "publish_time": "2026-11-08 10:00",
        "lot_no": "BD-2026-02",
        "objection_no": "OBJ-2026-003",
        "accept_time": "2026-11-08 09:30",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段二评标结果的异议。",
    },
    {
        "notice_no": "OBJ-2026-004",
        "type": "objection_acceptance",
        "title": "标段二异议受理通知（OBJ-2026-004）",
        "publish_time": "2026-11-10 16:00",
        "lot_no": "BD-2026-02",
        "objection_no": "OBJ-2026-004",
        "accept_time": "2026-11-10 15:00",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段二评标结果的第二项异议（尚未办结）。",
    },
    {
        "notice_no": "OBJ-2026-005",
        "type": "objection_acceptance",
        "title": "标段三异议受理通知（OBJ-2026-005）",
        "publish_time": "2026-11-13 09:00",
        "lot_no": "BD-2026-03",
        "objection_no": "OBJ-2026-005",
        "accept_time": "2026-11-12 18:30",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "异议期截止后才受理的异议，不应纳入本次核对。",
    },
    {
        "notice_no": "OBJ-2026-006",
        "type": "objection_acceptance",
        "title": "标段三异议受理通知（OBJ-2026-006）",
        "publish_time": "2026-11-09 15:00",
        "lot_no": "BD-2026-03",
        "objection_no": "OBJ-2026-006",
        "accept_time": "2026-11-09 14:00",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段三评标结果的异议。",
    },
    {
        "notice_no": "OBJ-2026-007",
        "type": "objection_acceptance",
        "title": "标段四异议受理通知（OBJ-2026-007）",
        "publish_time": "2026-11-09 11:00",
        "lot_no": "BD-2026-04",
        "objection_no": "OBJ-2026-007",
        "accept_time": "2026-11-09 10:00",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "已受理投标人对标段四评标结果的异议。",
    },
    {
        "notice_no": "OBJ-2026-009",
        "type": "objection_acceptance",
        "title": "标段一异议受理通知（OBJ-2026-009，逾期受理）",
        "publish_time": "2026-11-11 09:00",
        "lot_no": "BD-2026-01",
        "objection_no": "OBJ-2026-009",
        "accept_time": "2026-11-11 08:00",
        "objection_deadline": None,
        "resolve_time": None,
        "body": "异议期截止后才受理的异议，不应纳入标段一本次核对。",
    },
    # --- 异议办结 ---
    {
        "notice_no": "RL-2026-001",
        "type": "objection_resolution",
        "title": "标段一异议办结通知（OBJ-2026-001）",
        "publish_time": "2026-11-09 15:00",
        "lot_no": "BD-2026-01",
        "objection_no": "OBJ-2026-001",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-09 14:00",
        "body": "异议 OBJ-2026-001 已办结，维持原评标结果。",
    },
    {
        "notice_no": "RL-2026-002",
        "type": "objection_resolution",
        "title": "标段一异议办结通知（OBJ-2026-002）",
        "publish_time": "2026-11-10 11:00",
        "lot_no": "BD-2026-01",
        "objection_no": "OBJ-2026-002",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-10 10:30",
        "body": "异议 OBJ-2026-002 已办结，维持原评标结果。",
    },
    {
        "notice_no": "RL-2026-003",
        "type": "objection_resolution",
        "title": "标段二异议办结通知（OBJ-2026-003）",
        "publish_time": "2026-11-09 10:00",
        "lot_no": "BD-2026-02",
        "objection_no": "OBJ-2026-003",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-09 09:30",
        "body": "异议 OBJ-2026-003 已办结。",
    },
    {
        "notice_no": "RL-2026-004",
        "type": "objection_resolution",
        "title": "标段三异议办结通知（OBJ-2026-006）",
        "publish_time": "2026-11-11 10:00",
        "lot_no": "BD-2026-03",
        "objection_no": "OBJ-2026-006",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-11 09:30",
        "body": "异议 OBJ-2026-006 已办结。",
    },
    {
        "notice_no": "RL-2026-005",
        "type": "objection_resolution",
        "title": "标段三异议办结通知（OBJ-2026-005）",
        "publish_time": "2026-11-14 10:00",
        "lot_no": "BD-2026-03",
        "objection_no": "OBJ-2026-005",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-14 09:30",
        "body": "逾期受理异议 OBJ-2026-005 已办结（不影响本次核对）。",
    },
    {
        "notice_no": "RL-2026-006",
        "type": "objection_resolution",
        "title": "标段四异议办结通知（OBJ-2026-007）",
        "publish_time": "2026-11-10 10:00",
        "lot_no": "BD-2026-04",
        "objection_no": "OBJ-2026-007",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-10 09:30",
        "body": "异议 OBJ-2026-007 已办结。",
    },
    {
        "notice_no": "RL-2026-007",
        "type": "objection_resolution",
        "title": "标段四异议办结通知（引用缺失异议 OBJ-2026-999）",
        "publish_time": "2026-11-11 09:00",
        "lot_no": "BD-2026-04",
        "objection_no": "OBJ-2026-999",
        "accept_time": None,
        "objection_deadline": None,
        "resolve_time": "2026-11-11 08:30",
        "body": "办结记录引用了不存在的异议编号 OBJ-2026-999，用于演示关联详情缺失。",
    },
]


def sorted_publicity():
    """公示目录按发布时间倒序展示。"""
    return sorted(
        PUBLICITY_RECORDS, key=lambda r: (r["publish_time"], r["notice_no"]), reverse=True
    )


def get_publicity_by_notice_no(notice_no):
    for r in PUBLICITY_RECORDS:
        if r["notice_no"] == notice_no:
            return r
    return None

