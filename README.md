# 截标时间核对 / 中标通知发送前异议核对工具

面向采购专员的网页工具，包含两块核对能力：

1. **截标时间核对**：从公开招标公告站抓取公告，按项目串起公告链，
   自动应用更正与撤销，给出每个项目的**最终截标时间 / 停办状态**及**依据链接**。
2. **中标通知发送前核对**：扫描候选人公示目录，按标段号与拟发时间，
   核对公示期内**异议是否全部办结**，给出**可发送 / 不可发送 / 无法核定**结论及来源。

仓库包含两个服务：

| 服务 | 目录 | 说明 |
| --- | --- | --- |
| 核对工具 | `app/` | FastAPI 网页：截标时间核对 + 中标通知异议核对；SQLite 保存采集轮次 |
| 示例公告站 | `sample_site/` | FastAPI 模拟公告站：3 页招标公告 + 5 页公示目录，支持故障注入 |

## 快速开始（Docker Compose）

```bash
docker compose up --build
```

- 核对工具：http://localhost:8000/
  - 截标时间核对：默认已填入示例站列表网址，点击 **开始抓取**；
  - 中标通知核对：点击 **中标通知发送前核对** 表单或打开 http://localhost:8000/verify 。
- 示例公告站：
  - 招标公告列表：http://localhost:8080/list.html?page=1
  - 候选人公示 / 异议目录：http://localhost:8080/publicity.html?page=1

## 中标通知发送前核对

在核对工具首页或 `/verify` 填写：

| 输入 | 说明 |
| --- | --- |
| 公示目录 URL | 列出候选人公示、异议受理、异议办结详情的目录页（同源分页会被自动遍历） |
| 标段号 | 要发中标通知的标段，如 `BD-2026-01` |
| 拟发时间 | 计划发出中标通知的时间 |

核对规则：

1. 只使用**发布时间不晚于拟发时间**的记录；
2. 取该标段发布时间不晚于拟发时间的**最新候选人公示**，以其
   **异议期截止时间**作为该标段异议期；
3. 异议按**受理时间不晚于异议期截止时间**筛选，晚受理的异议不纳入核对；
4. **办结记录必须引用该标段相关异议的编号**（可带 `#lot-no`，也可仅靠异议编号
   与同标段受理记录关联），且发布时间不晚于拟发时间；
5. 只有**拟发时间晚于异议期截止时间，且每项相关异议均已办结**时才显示
   **可发送**；否则显示 **不可发送**，并列出未办结事项、时间条件及来源链接；
6. 抓取失败、候选人公示缺失、办结记录引用的受理详情缺失时显示
   **无法核定**，并列出问题网址。

页面会同时展示：相关异议的受理时间、办结状态、办结记录来源，以及按规则
未纳入核对的异议（例如受理时间晚于异议期）和抓取失败页面。

### 离线演示场景（示例站）

公示目录默认地址为 `http://sample-site:8000/publicity.html?page=1`。拟发时间例如
`2026-11-15 10:00`：

| 标段号 | 预期结论 | 说明 |
| --- | --- | --- |
| `BD-2026-01` | 可发送 | 两项异议均在异议期内受理且已办结，逾期受理的异议不纳入 |
| `BD-2026-02` | 不可发送 | 异议 `OBJ-2026-004` 尚未办结，页面列出其受理来源 |
| `BD-2026-03` | 可发送 | 逾期受理的 `OBJ-2026-005` 不纳入核对 |
| `BD-2026-04` | 无法核定 | 办结记录 `RL-2026-007` 引用了不存在的异议 `OBJ-2026-999` |
| `BD-2026-05` | 可发送 | 异议期内无相关异议 |

演示抓取失败：

```bash
# 让公示详情 RL-2026-001 返回 500（也可用 /admin/fail?on=1，该开关会同时开启公告故障）
curl "http://localhost:8080/admin/fail-publicity?on=1"
# 在 http://localhost:8000/verify 核对 BD-2026-01 → 显示“无法核定”及该问题网址
curl "http://localhost:8080/admin/fail-publicity?on=0"
# 关闭后重新核对 → 恢复“可发送”
```

## 截标时间核对（原有功能）

1. **抓取**：输入与示例站同结构的列表网址，点击抓取。工具只跟随与起始网址
   **同源**的分页链接（`nav.pagination`）与详情链接（`ul.notice-list`），
   逐个读取详情页的：项目编号、公告编号、公告类型、发布时间、截标时间、
   更正/撤销所指公告编号。
2. **分析**：同一项目编号的公告按发布时间串链——
   - 招标公告确立截标时间；
   - 更正公告更新截标时间（链上记录 `旧值 → 新值`）；
   - 撤销公告将项目标记为 **停办**。
   页面展示每个项目的最终状态、当前截标时间，以及每条公告的来源链接（依据）。
3. **轮次持久化（SQLite）**：每次抓取是一个轮次，公告快照挂在轮次下，
   保存于 SQLite（容器卷 `app-data`，`/data/app.db`）。
   - **任一页面失败**：轮次标记失败并记录出错网址与原因，页面红色横幅提示，
     项目结果仍展示上一轮成功数据；
   - **重抓不叠加**：公告只在整轮全部成功后于单事务内写入，失败轮次不留
     半截数据；页面始终只展示最近一次成功轮次的结果。

### 演示失败处理

```bash
# 开启故障注入：招标公告详情页 NT-2026-0004 返回 500
curl "http://localhost:8080/admin/fail?on=1"
# 在 http://localhost:8000/ 点击“开始抓取” → 第 N 轮失败，报出该网址，结果仍是上一轮
# 关闭故障后重抓 → 新一轮成功，数据整体替换，不叠加
curl "http://localhost:8080/admin/fail?on=0"
```

## 页面结构约定（解析契约）

### 招标公告列表（原有）

- 列表页 `list.html?page=N`：公告链接在 `ul.notice-list a`，分页链接在 `nav.pagination a`；
- 详情页 `detail/<公告编号>.html`：容器 `div.notice[data-notice-type]`
  （`tender`/`correction`/`cancellation`），字段元素
  `#project-no`、`#notice-no`、`#publish-time`、`#deadline`（如有）、
  `#target-notice`（更正/撤销必填）。

### 公示目录（中标通知核对）

- 目录页 `publicity.html?page=N`：记录链接在 `ul.notice-list a`，分页链接在
  `nav.pagination a`；只跟随同源链接；
- 详情页 `publicity/detail/<公告编号>.html`：容器 `div.notice[data-notice-type]`，
  类型与字段如下（公共字段 `#notice-no`、`#publish-time`）：

| `data-notice-type` | 含义 | 必填字段 |
| --- | --- | --- |
| `candidate_publicity` | 候选人公示 | `#lot-no` 标段号、`#objection-deadline` 异议期截止时间 |
| `objection_acceptance` | 异议受理 | `#lot-no` 标段号、`#objection-no` 异议编号、`#accept-time` 受理时间 |
| `objection_resolution` | 异议办结 | `#objection-no` 所引用的异议编号；`#lot-no`、`#resolve-time` 可选 |

任一详情页抓取或解析失败不会中断整轮核对，而是记录问题网址并给出 **无法核定**。

## 配置（环境变量）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_PATH` | `/data/app.db`（容器） | SQLite 文件路径 |
| `DEFAULT_START_URL` | `http://sample-site:8000/list.html?page=1` | 截标核对表单预填的列表网址 |
| `DEFAULT_PUBLICITY_URL` | `http://sample-site:8000/publicity.html?page=1` | 中标通知核对表单预填的公示目录网址 |
| `DEFAULT_PROPOSED_TIME` | 见 compose（`2026-11-15 10:00`） | 中标通知核对表单预填的拟发时间，留空则不预填 |
| `URL_REWRITE_FROM` / `URL_REWRITE_TO` | 见 compose | 把结果页中的内部网址改写为浏览器可访问地址 |

## 本地开发与测试

```bash
pip install -r app/requirements.txt -r sample_site/requirements.txt pytest
python -m pytest tests/            # 单元测试：公告链分析 + 详情页解析 + 异议核对规则
# 手动联调：
cd sample_site && uvicorn main:app --port 8080 &
cd app && DB_PATH=/tmp/app.db DEFAULT_START_URL=http://localhost:8080/list.html?page=1 \
  DEFAULT_PUBLICITY_URL=http://localhost:8080/publicity.html?page=1 \
  DEFAULT_PROPOSED_TIME="2026-11-15 10:00" \
  uvicorn main:app --port 8000
```
