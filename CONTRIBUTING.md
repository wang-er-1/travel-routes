# 旅踪集 · 路线数据协作规范（CONTRIBUTING）

> 本仓库（travel-routes）是旅踪集路线数据的统一存储。多台电脑 / 多个智能体协作整理B站旅行视频 → 结构化路线JSON，供旅踪集后台读取。
> **本文件是协作准绳。开工前请先 `git pull`，并阅读根目录 `SCHEMA_PROPOSAL.md`（完整规范）和 `route.schema.v2.json`（字段定义），一切以这两份为准。**

---

## 你的任务

把B站旅行视频整理成一条结构化路线，写成 `episodes/BV号.json`，符合 schema v2.0，提交到本仓库。HTML 展示页可继续生成（`pages/BV号.html`），但**后台只读 JSON、不抓 HTML**。

## 铁律（必须遵守）

1. **一视频一文件**：`episodes/BV号.json`，`schema_version` 固定 `"2.0"`。
2. **先同步再改**：开工前 `git pull`；提交前跑 `python validate.py` 校验通过才能 push；遇冲突先 pull 再处理，**绝不强制覆盖**（`git push -f` 禁用）。
3. **同BV更新不新建**：相同 BV 号已存在就更新原文件，不重复创建。
4. **博主 ≠ 系列**：`episode.blogger` 是博主名（如"小可追太阳"）；`episode.series` 是对象 `{title, series_id, episode_number}`，`series.title` 里**不能**写博主名（如系列名是"搭火车环游中国"）。无系列则 `series: null`。
5. **上下集分开存**：每集各一个 JSON，用 `episode.related_videos: [{bvid, relation, note, part_number}]` 标注关联（`relation`: `part`=同一旅程上下集 / `series`=同系列前后站）；当前集自己在 `episode.part_number` 填自己是第几集。**是否合并显示由后台决定**，JSON 只如实记录关联。
6. **状态只有两个**：`data_status` = `draft`（尚未对照原视频核对）或 `verified`（已对照原视频核对结构和内容）。**绝不写 `published`**——审核、发布、撤回、归档全部由旅踪集后台管理。`verified` 不代表票价/班次/营业时间现在仍有效，相关事实的最后复核日期填 `last_checked_at`。
7. **禁止私人信息**：JSON 里**绝对不能**出现本地电脑路径（`D:\...`、`/x/output/...`）、密码、Cookie、密钥、账号等。逐字转写文稿只留在本地，**不进 JSON**（来源用一句话写进 `source_note`）。
8. **不直连数据库**：不连接旅踪集正式数据库，数据只通过本仓库交换。

## 字段要点（详见 route.schema.v2.json）

- **stats** 字段名统一：`views / likes / favorites / danmaku / comments / captured_at`。数值为整数或 null。`captured_at` 用带时区的完整 ISO 时间，如 `2026-08-24T23:00:00+08:00`。
- **地点** 用 `trip.locations` **数组**（单城市放一个对象，跨城市/跨省放多个）：`{city, province, region, country}`。
- **主题** 用 `trip.themes`（复数，字符串数组）。
- **路线级贴士** 统一 `tips: [{category, text}]`（分类如 交通/餐饮/住宿/拍摄/季节/人文/其他）。站点内部 `stops[].tips` 是字符串数组，保留。
- **站点** `trip.stops[]` 每项有 `order`（从1连续递增）；`time` 可选；`lodging` 是对象 `{place, price, notes}` 或 null；`arrive_transport`（交通）、`food`、`cost_notes`、`activities`、`detail`、`tips` 按实填。
- **费用** 全部进 `trip.budget`：`{total, per_person, note, price_as_of, items:[{item, price, note}]}`。视频没提就 `budget: null`；站点级细节仍可放 `stops[].cost_notes`。
- **亮点** `highlights`（字符串数组）；**来源** `source_note`（一句话，无本地路径）；**更新时间** `last_updated`（YYYY-MM-DD）。

## 提交前自检

```bash
git pull origin main            # 先同步
python validate.py              # 校验全部 episodes + catalog（必须通过）
git add episodes/BV号.json pages/BV号.html
git commit -m "新增/更新 <地点>（BV号）"
git push origin main
```

`validate.py` 会检查：符合 route.schema.v2.json、无本地绝对路径、枚举值合法（data_status/relation/source_type）、必填项齐全、catalog 与 episodes 一致。**不通过不要 push。**

## 参考样本

- `_v2_samples/BV111Fze1EZw.json`（鞍山，单集标准范例）
- `_v2_samples/BV1F9U8BzE3F.json`（三峡，带上下集关联的范例）

照着这两个产出即可。

## 完成后报告

每次整理完，报告：
- 新增 / 更新了哪些 BV 号
- 是否有上下集（及关联的 BV）
- 是否存在资料缺失（如视频无口播导致某些字段拿不到）
