# 旅踪集 · 路线数据 Schema 规范 v2.0（决策已敲定）

> 目的：家庭电脑 + 工作电脑两台机器整理的路线数据，格式统一、旅踪集后台能直接读取。
> 起草：家庭电脑侧（负责视频→路线转换）。决策：Codex（后台侧）已于 2026-08 正式确认，见下。
> **本文件为定稿，两台电脑生成数据一律遵循本规范。**

---

## 决策结论（Codex 已确认）

- **决策A —— 基准结构**：**不采用扁平结构**。以现有 14 条的 `episode / trip / stops` 嵌套结构为基础，**升级为 `schema_version: "2.0"`**；把鞍山（BV111Fze1EZw）扁平数据转换进新嵌套结构。
  - 吸收鞍山结构的优点字段：`location`、`route_type`、`theme`、详细 `itinerary`、`practical_tips`、`budget`、`next_stop`、`source_note`
  - **但不得丢失原 14 条的节点交通、费用、住宿、餐饮、提示信息**
  - 后台会分别保存"原始 JSON"和"审核后标准版本"，**不要为方便建表而压扁或删减内容**（信息尽量全）
- **决策B —— 系列/上下集**：用 `series`(对象) + `related_videos`(数组)。**博主与系列必须分开**（鞍山 blogger=小可追太阳，series.title=搭火车环游中国，episode_number=5，绝不能把"小可追太阳"当系列名）。
- **决策C —— 状态**：`data_status` = `draft` / `verified`，仅表示整理与核验状态。**JSON 不含 published**；审核/发布/撤回/归档全部由后台管理。
- **stats 字段统一**：`views / likes / favorites / danmaku / comments / captured_at`（数值为整数或 null，captured_at 为统计抓取时间）。
- **本地路径清理**：递归删除所有 `D:\output\...` 绝对路径；`transcript_ref` 里的路径删除，但 `l3_hooks.suitable_for` 的"适合什么人"正文**迁移到 `trip.suitable_for` 保留**，不整列删。

---

## 一、Schema v2.0 字段定义（嵌套结构）

```jsonc
{
  "schema_version": "2.0",

  "episode": {
    "blogger": "小可追太阳",          // 博主名（必填，与系列分开）
    "blogger_mid": "1066572839",     // B站UP主ID，可选
    "title": "视频标题",
    "bvid": "BV111Fze1EZw",
    "url": "https://www.bilibili.com/video/BV111Fze1EZw",
    "duration": "18:10",
    "duration_seconds": 1090,        // 便于后台排序/计算
    "publish_date": "2025-02-02",
    "stats": {                       // 统一字段名
      "views": 826717, "likes": 17940, "favorites": 8543,
      "danmaku": 2272, "comments": 1760,
      "captured_at": "2026-08-24"    // 统计抓取时间
    },
    "tags": ["工业遗产", "东北美食"],

    // === 系列与关联（博主≠系列）===
    "series": {                      // 无系列则 null
      "title": "搭火车环游中国",       // 系列名（不含博主名）
      "series_id": "xiaoke-train-china",  // 稳定标识
      "episode_number": 5            // 第几站/第几集
    },
    "related_videos": [              // 关联视频，无则 []
      {"bvid": "BV1TwS7BmETP", "relation": "part", "note": "下集", "part_number": 2}
      // relation: "part"(同一旅程上下集) / "series"(同系列前后站)
      // part_number: 属于上下集时填顺序，否则可省略
    ],
    "description": "视频简介"
  },

  "trip": {
    "title": "路线标题",
    "route_summary": "A→B→C 一句话路线总览",
    "route_type": "城市人文一日",     // 吸收自鞍山
    "theme": ["工业遗产", "城市探索"], // 吸收自鞍山
    "location": {                    // 吸收自鞍山
      "city": "鞍山", "province": "辽宁", "region": "东北", "country": "中国"
    },
    "direction": "方向描述",
    "season": "季节建议",
    "duration_days": 1,
    "transport_modes": ["火车", "步行", "打车"],
    "cost_total": null,
    "cost_per_person": null,
    "cost_notes": "费用总说明",
    "price_as_of": "2025-02",
    "suitable_for": "适合什么人（从旧 l3_hooks.suitable_for 迁移，去路径）",

    "stops": [                       // 路线顺序（核心，保留原14条全部细节）
      {
        "name": "站点名",
        "day": 1,
        "time": "上午",              // 吸收自鞍山 itinerary
        "arrive_transport": "火车",   // 节点交通（不可丢）
        "arrive_cost": "—",
        "detail": "详细介绍（吸收自鞍山itinerary.detail，长文叙述）",
        "activities": ["看点1", "看点2"],
        "lodging": {"place": "住宿名", "price": "169元/晚", "notes": "..."},  // 住宿不可丢
        "food": ["美食1(价格)"],      // 餐饮不可丢
        "cost_notes": ["费用明细"],   // 费用不可丢
        "tips": ["本站提示"]          // 提示不可丢
      }
    ],

    "budget": {                      // 吸收自鞍山，视频没提则 null
      "note": "视频中实际消费",
      "items": [{"item": "项目", "price": "约20元", "note": "明细"}]
    }
  },

  "tips": ["整条路线级贴士1", "贴士2"],       // 保留
  "practical_tips": [                        // 吸收自鞍山（带分类），可与 tips 二选一或并存
    {"category": "交通|餐饮|住宿|拍摄|季节|人文", "tip": "具体建议"}
  ],
  "highlights": ["亮点1", "亮点2"],           // 保留

  "next_stop": "下一站文字描述（系列片用，吸收自鞍山）",  // 可选
  "source_note": "来源说明（一句话，无本地路径）",       // 吸收自鞍山
  "data_status": "draft",                    // draft / verified（不写 published）
  "last_updated": "2026-08-24"
}
```

## 二、字段覆盖 Codex 第5条核对

| 要保留 | 字段 | ✓ |
|---|---|---|
| 博主 | `episode.blogger` | ✓ |
| 标题 | `episode.title` / `trip.title` | ✓ |
| BV号 | `episode.bvid` | ✓ |
| 原视频 | `episode.url` | ✓ |
| 路线顺序 | `trip.stops[]`（有序） | ✓ |
| 地点 | `trip.location` + `stops[].name` | ✓ |
| 交通 | `stops[].arrive_transport` + `transport_modes` | ✓ |
| 费用 | `trip.budget` + `stops[].cost_notes` + `cost_notes` | ✓ |
| 吃住 | `stops[].food` + `stops[].lodging` | ✓ |
| 提示 | `tips` + `practical_tips` + `stops[].tips` | ✓ |
| 亮点 | `highlights[]` | ✓ |
| 更新时间 | `last_updated` | ✓ |
| 核验状态 | `data_status` | ✓ |

---

## 三、catalog.json（仓库根目录）

```jsonc
{
  "schema_version": "2.0",
  "generated_at": "2026-08-24T23:00:00+08:00",
  "count": 15,
  "routes": [
    {
      "source_id": "BV111Fze1EZw",     // 值为BV号
      "source_type": "bilibili",
      "content_hash": "sha1:...",       // 或 content_version，后台判断变化用
      "blogger": "小可追太阳",
      "series": {"title": "搭火车环游中国", "episode_number": 5},
      "title": "在中国钢铁之城...",
      "region": "鞍山",
      "data_status": "draft",
      "updated_at": "2025-02-02",
      "json_path": "episodes/BV111Fze1EZw.json",
      "page_path": "pages/BV111Fze1EZw.html",
      "related_videos": ["BV..."]
    }
  ]
}
```
后台通过 `source_id + updated_at + content_hash` 判断新增和变化。

---

## 四、转换执行计划（Codex 第8条）

1. 先只转 2 条样本：① 鞍山扁平样本 ② 一条字段最完整的嵌套样本
2. 提供转换前后**字段差异报告**，证明无内容丢失
3. 你确认后再一次性转 15 条
4. 全程保留备份 + 独立提交，可回滚

---

## 五、协作规则（两台电脑 + 后台）

1. 一视频 = 一 `episodes/BV号.json`
2. 整理前先 `git pull`
3. 相同 BV 已存在则更新，不重复创建
4. 上下集分别保存 + `related_videos` 注明，是否合并由后台决定
5. HTML 可继续生成，后台只读 JSON、不抓 HTML
6. 不上传本地路径/密码/Cookie/密钥/私人信息
7. 不直连正式数据库，不把"已核验"当"已发布"
8. 冲突先 pull 再处理，不强制覆盖
9. 每次完成报告：新增/更新哪些 BV、是否有上下集、是否有资料缺失
