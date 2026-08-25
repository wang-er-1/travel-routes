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
import json, os, glob, hashlib, sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def sha256_of(path):
    """换行无关的 canonical 哈希：读原始字节后把 CRLF/CR 统一成 LF 再算。
    保证 Windows(CRLF) 与 Linux/远端(LF) 对同一内容得到相同 content_hash，
    避免"本地通过、远端哈希变化"。validate.py 必须用同一函数。"""
    with open(path, 'rb') as f:
        data = f.read()
    data = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return "sha256:" + hashlib.sha256(data).hexdigest()

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

# location 层级：从最细最有辨识度 → 最粗。destinations 取每个 location 第一个命中的层级。
LOC_LEVELS_FINE_FIRST = ("village", "town", "county", "district",
                         "city", "province", "region", "country")
# location_terms 收集顺序：从粗到细，保证同一 location 内 terms 有稳定行政顺序
LOC_LEVELS_COARSE_FIRST = ("country", "region", "province", "city",
                           "district", "county", "town", "village")


def extract_destinations_and_terms(tr):
    """按 Codex C 方案（职责分离）从 trip 提取：
      destinations: 面向展示，每个 location 取最细且最有辨识度的非空层级
                    (village→town→county/district→city→province→region→country)；
                    locations 无可用值时，从有序 stops[].name 取前3个不重复名称忠实兜底。
      location_terms: locations 中全部非空层级，去重，供搜索/筛选。
    不再从 route_summary 用后缀正则猜地点（曾误判"大环岛市/世纪广场市/晋江早市"）。"""
    locations = tr.get("locations", []) or []
    destinations, seen_d = [], set()
    location_terms, seen_t = [], set()

    for loc in locations:
        # destinations：该 location 取最细有辨识度层级
        for lv in LOC_LEVELS_FINE_FIRST:
            v = loc.get(lv)
            if v and v not in seen_d:
                destinations.append(v)
                seen_d.add(v)
                break
        # location_terms：该 location 全部非空层级（粗→细），去重
        for lv in LOC_LEVELS_COARSE_FIRST:
            v = loc.get(lv)
            if v and v not in seen_t:
                location_terms.append(v)
                seen_t.add(v)

    # locations 无任何可用值 → 从有序 stops[].name 取前3个不重复名称忠实兜底
    if not destinations:
        for s in tr.get("stops", []):
            nm = s.get("name")
            if nm and nm not in seen_d:
                destinations.append(nm)
                seen_d.add(nm)
            if len(destinations) >= 3:
                break

    return destinations, location_terms

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

        # regions 从 locations 提取
        regions = []
        for loc in tr.get('locations', []):
            if loc.get('region') and loc['region'] not in regions:
                regions.append(loc['region'])
        # destinations（展示，取最细层级）+ location_terms（搜索，全层级去重）
        # 职责分离，不再用 route_summary 后缀正则猜地点
        destinations, location_terms = extract_destinations_and_terms(tr)

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
            "location_terms": location_terms,
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
    # 固定 UTF-8 + LF 输出（newline='' 关闭 Python 文本层的行尾翻译，
    # 手动以 \n 结尾），确保 Windows 上也写出纯 LF 字节，与 .gitattributes 一致。
    text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    with open("catalog.json", "w", encoding='utf-8', newline='') as f:
        f.write(text)
    print(f"catalog.json 生成: {len(routes)} 条 (schema v2.0, generated_at={catalog['generated_at']})")


if __name__ == '__main__':
    main()
