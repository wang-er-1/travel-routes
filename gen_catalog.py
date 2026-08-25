# -*- coding: utf-8 -*-
"""catalog.json 生成器（Codex 规范）
- 读取 episodes/*.json（v2.0），生成仓库根 catalog.json
- content_hash = sha256:<hex>（按最终JSON UTF-8文件内容计算）
- updated_at 必须来自 JSON 的 last_updated（≠视频 publish_date）
- source_type = bilibili_video
- regions / destinations 数组（跨省/跨城多值）
- related_videos 保留对象 {bvid, relation, part_number}
生成时机：路线 JSON 写入后 → 生成 catalog → 最后跑 schema + catalog + 一致性校验
"""
import json, os, glob, hashlib, re, sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def sha256_of(path):
    with open(path, 'rb') as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()

def load_bv(filepath):
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)

def series_to_cat(series):
    if not series:
        return None
    return {
        "title": series.get("title"),
        "series_id": series.get("series_id"),
        "episode_number": series.get("episode_number"),
    }

def main():
    files = sorted(glob.glob("episodes/*.json"))
    routes = []
    for f in files:
        d = load_bv(f)
        if d.get('schema_version') != '2.0':
            print(f"[skip] {f} 非 v2.0（{d.get('schema_version')}），未加入 catalog")
            continue
        ep = d.get('episode', {})
        tr = d.get('trip', {})
        bv = ep.get('bvid') or os.path.basename(f).replace('.json', '')

        # regions / destinations 从 locations 提取（destinations 按 city→district→town→village 层级）
        regions, destinations = [], []
        for loc in tr.get('locations', []):
            if loc.get('region') and loc['region'] not in regions:
                regions.append(loc['region'])
            # 最细粒度的行政层级作为目的地（city 优先，其次 district/town/village）
            for level in ('city', 'district', 'town', 'village'):
                v = loc.get(level)
                if v and v not in destinations:
                    destinations.append(v)
                    break
        # 兜底：从 route_summary / stops 提取粗粒度目的地（负向前瞻排除"北关市场"这类"市+场"误匹配）
        if not destinations:
            for m in re.finditer(r'([\u4e00-\u9fff]{2,4}(?:市|县|镇|乡))(?![场集区])', tr.get('route_summary') or ''):
                cand = m.group(1)
                if cand not in destinations:
                    destinations.append(cand)
                if len(destinations) >= 3:
                    break

        # related_videos 对象（不简化成 BV 字符串）
        related = []
        for rv in ep.get('related_videos', []):
            item = {"bvid": rv.get('bvid'), "relation": rv.get('relation', 'series')}
            if rv.get('part_number') is not None:
                item["part_number"] = rv["part_number"]
            related.append(item)

        routes.append({
            "source_id": bv,
            "source_type": "bilibili_video",
            "content_hash": sha256_of(f),
            "blogger": ep.get('blogger'),
            "series": series_to_cat(ep.get('series')),
            "title": tr.get('title') or ep.get('title'),
            "regions": regions,
            "destinations": destinations,
            "data_status": d.get('data_status', 'draft'),
            "updated_at": d.get('last_updated'),          # 必须来自 last_updated
            "json_path": f"episodes/{bv}.json",
            "page_path": f"pages/{bv}.html" if os.path.exists(f"pages/{bv}.html") else None,
            "related_videos": related,
        })

    catalog = {
        "schema_version": "2.0",
        "generated_at": datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')[:-2] + ":00",
        "count": len(routes),
        "routes": routes,
    }
    with open("catalog.json", "w", encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"catalog.json 生成: {len(routes)} 条 (schema v2.0, generated_at={catalog['generated_at']})")


if __name__ == '__main__':
    main()
