# 旅踪集 · 路线数据 Schema 规范 v2.0（决策已敲定）

> 目的：家庭电脑 + 工作电脑两台机器整理的路线数据，格式统一、旅踪集后台能直接读取。
> 起草：家庭电脑侧（负责视频→路线转换）。决策：Codex（后台侧）已于 2026-08 正式确认，见下。
> **本文件为定稿，两台电脑生成数据一律遵循本规范。**

---

## 决策结论（Codex 已确认 + 15条收口）

- **决策A —— 基准结构**：以 14 条嵌套 `episode/trip/stops` 为基础升级 `schema_version:"2.0"`，鞍山扁平数据转入。吸收鞍山的 locations/route_type/themes/详细itinerary(→stops.detail)/practical_tips/budget/next_stop/source_note，**不丢原14条节点交通/费用/住宿/餐饮/提示**。后台分别存原始JSON和审核版，**不为建表压扁删减**。
- **决策B —— 系列/上下集**：`series`(对象:title/series_id/episode_number) + `related_videos`(数组)。**博主≠系列**（鞍山 blogger=小可追太阳，series.title=搭火车环游中国，episode_number=5）。
- **决策C —— 状态**：`data_status`=draft/verified；**无published**（后台管发布）。

### Codex 15条收口（均已落地，见 route.schema.v2.json / catalog.schema.v2.json）
1. `trip.location`→`trip.locations`**数组**（跨城市多对象）
2. `theme`→`themes`（复数，数组）
3. 路线级贴士统一 `tips:[{category,text}]`（旧字符串→category="其他"，鞍山分类直接迁入）；`stops[].tips` 保留
4. `stops[]` 每项加 `order`(从1)；`time` 可选；`lodging` 明确对象或null（旧字符串无损转对象）
5. 费用统一进 `trip.budget`：total/per_person/note/price_as_of/items；旧 cost_total/per_person/cost_notes 迁入；`stops[].cost_notes` 保留
6. `episode.part_number`（当前集自身是上/下集第几）
7. `series` 带 `series_id`；catalog 的 series 也保留 series_id
8. `catalog.updated_at` 来自 JSON `last_updated`（≠视频 publish_date）
9. `catalog.source_type` = `bilibili_video`
10. `content_hash` = `sha256:<hex>`（按最终JSON UTF-8文件内容算）
11. catalog `related_videos` 保留对象 {bvid,relation,part_number}
12. catalog 用 `regions:[]` + `destinations:[]`（非单一 region）
13. `stats.captured_at` 带时区完整ISO（如 2026-08-24T23:00:00+08:00）
14. 状态语义：draft=未核对原视频；verified=已对照原视频核对结构与内容（不代表票价/班次现时有效）；增 `last_checked_at` 记录事实最后复核日
15. 双份 JSON Schema（route/catalog）+ 提交前校验脚本 validate.py

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
      "captured_at": null    // 历史数据无真实抓取时间填 null；真实刷新时写带时区ISO，如 2026-08-24T23:00:00+08:00
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
    "route_type": "城市人文一日",
    "themes": ["工业遗产", "城市探索"],        // 复数数组
    "locations": [                             // 数组；单城市1个对象，跨省多个
      {"city": "鞍山", "province": "辽宁", "region": "东北", "country": "中国"}
    ],
    "direction": "方向描述",
    "season": "季节建议",
    "duration_days": 1,
    "transport_modes": ["火车", "步行", "打车"],
    "suitable_for": "适合什么人（自然语言）",
    "customization_notes": "定制备注（可选）",

    "stops": [                       // 路线顺序（核心，保留原14条全部细节）
      {
        "order": 1,                  // 从1连续
        "name": "站点名",
        "day": 1,
        "time": "上午",              // 可选
        "arrive_transport": "火车",   // 节点交通（不可丢）
        "arrive_cost": "—",
        "detail": "详细介绍（长文叙述）",
        "activities": ["看点1", "看点2"],
        "lodging": {"place": "住宿名", "price": "169元/晚", "notes": "..."},  // 对象或null
        "food": ["美食1(价格)"],      // 餐饮不可丢
        "cost_notes": ["费用明细"],   // 费用不可丢
        "tips": ["本站提示"]          // 提示不可丢
      }
    ],

    "budget": {                      // 费用统一入口，视频没提则 null
      "total": null,
      "per_person": null,
      "note": "费用总说明",
      "price_as_of": "2025-02",
      "items": [{"item": "项目", "price": "约20元", "note": "明细"}]
    }
  },

  "tips": [                                    // 路线级贴士统一对象（不再有 practical_tips）
    {"category": "交通", "text": "具体建议"}
  ],
  "highlights": ["亮点1", "亮点2"],

  "next_stop": "下一站文字描述（系列片用，可选）",
  "source_note": "来源说明（一句话，无本地路径）",
  "data_status": "draft",                    // draft / verified（不写 published）
  "last_updated": "2026-08-24",              // 数据更新时间（≠视频发布日期）
  "last_checked_at": null                    // 票价/班次等事实最后复核日期
}
```

## 二、字段覆盖 Codex 第5条核对

| 要保留 | 字段 | ✓ |
|---|---|---|
| 博主 | `episode.blogger` | ✓ |
| 标题 | `episode.title` / `trip.title` | ✓ |
| BV号 | `episode.bvid` | ✓ |
| 原视频 | `episode.url` | ✓ |
| 路线顺序 | `trip.stops[]`（有序，order从1） | ✓ |
| 地点 | `trip.locations[]` + `stops[].name` | ✓ |
| 交通 | `stops[].arrive_transport` + `transport_modes` | ✓ |
| 费用 | `trip.budget` + `stops[].cost_notes` | ✓ |
| 吃住 | `stops[].food` + `stops[].lodging` | ✓ |
| 提示 | `tips[]`（{category,text}）+ `stops[].tips` | ✓ |
| 亮点 | `highlights[]` | ✓ |
| 更新时间 | `last_updated`（数据更新时间，≠publish_date） | ✓ |
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
      "source_type": "bilibili_video",
      "content_hash": "sha256:...",     // 按最终JSON UTF-8文件内容计算的SHA-256
      "blogger": "小可追太阳",
      "series": {"title": "搭火车环游中国", "series_id": "xiaoke-train-china", "episode_number": 5},
      "title": "在中国钢铁之城...",
      "regions": ["东北"],
      "destinations": ["鞍山"],
      "data_status": "draft",
      "updated_at": "2026-08-24",      // 来自JSON的last_updated（≠视频publish_date）
      "json_path": "episodes/BV111Fze1EZw.json",
      "page_path": "pages/BV111Fze1EZw.html",
      "related_videos": [{"bvid": "BV...", "relation": "part", "part_number": 2}]
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
