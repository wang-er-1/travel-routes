# -*- coding: utf-8 -*-
"""schema v2.0 转换器（按 Codex 15条收口意见）
嵌套v1 / 扁平(鞍山) → v2.0 统一嵌套结构。
支持 dry-run（输出到 _v2_samples/ 或内存，不覆盖 episodes/）。

Codex 15条修订对照：
 1 trip.location→locations 数组   2 theme→themes   3 tips 统一 [{category,text}]
 4 stops[].order(从1) + lodging 字符串→对象   5 费用全进 budget(total/per_person/note/price_as_of/items)
 6 episode.part_number(当前集自身)   7 series 带 series_id
 8 catalog.updated_at 用 last_updated（转换器不管catalog，见 gen_catalog.py）
 9 source_type=bilibili_video(catalog)  10 content_hash SHA-256(catalog)
 11 catalog.related_videos 对象  12 catalog regions/destinations
 13 stats.captured_at 带时区ISO   14 data_status 语义 + last_checked_at
 15 JSON Schema + validate.py 另见独立文件
"""
import json, os, re, copy, hashlib
from datetime import datetime

os.chdir(r"D:\output\routes-site-v2")

TZ = "+08:00"

def to_iso_tz(date_str):
    """'2026-08-18' → '2026-08-18T00:00:00+08:00'；已是ISO则原样；None→None"""
    if not date_str:
        return None
    if 'T' in date_str and re.search(r'[+-]\d{2}:\d{2}$', date_str):
        return date_str
    m = re.match(r'^(\d{4}-\d{2}-\d{2})$', date_str.strip())
    if m:
        return f"{m.group(1)}T00:00:00{TZ}"
    return None

def has_local_path(s):
    return isinstance(s, str) and bool(re.search(r'[A-Za-z]:\\|/[a-z]/output', s))

def strip_path_from_text(s):
    """从一段文字里剥掉本地路径片段，保留正常文字"""
    if not isinstance(s, str):
        return s
    cleaned = re.sub(r'[A-Za-z]:\\\\?[^\s，。；、)）"\']*', '', s)
    cleaned = re.sub(r'/[a-z]/output[^\s，。；、)）"\']*', '', cleaned)
    return cleaned.strip(' :：（(')

def deep_strip_paths(obj, removed):
    if isinstance(obj, dict):
        return {k: deep_strip_paths(v, removed) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_strip_paths(x, removed) for x in obj]
    if isinstance(obj, str) and has_local_path(obj):
        cleaned = strip_path_from_text(obj)
        removed.append(obj[:70])
        return cleaned or None
    return obj

def parse_dur_seconds(dur):
    if not dur: return None
    p = [int(x) for x in re.findall(r'\d+', dur)]
    if len(p) == 2: return p[0]*60 + p[1]
    if len(p) == 3: return p[0]*3600 + p[1]*60 + p[2]
    return None

def norm_stats_nested(st, captured):
    return {
        "views": st.get('plays') if st.get('plays') is not None else st.get('views'),
        "likes": st.get('likes'),
        "favorites": st.get('favorites'),
        "danmaku": st.get('danmaku'),
        "comments": st.get('comments') if st.get('comments') is not None else st.get('reply'),
        "captured_at": captured,
    }

def tips_to_objs(raw_tips):
    """旧字符串贴士 → [{category:'其他', text}]；已是对象则规整"""
    out = []
    for t in raw_tips or []:
        if isinstance(t, str) and t.strip():
            out.append({"category": "其他", "text": t.strip()})
        elif isinstance(t, dict):
            cat = t.get('category') or '其他'
            txt = t.get('text') or t.get('tip') or ''
            if txt: out.append({"category": cat, "text": txt})
    return out

def lodging_to_obj(l):
    """住宿：字符串→对象；对象原样；None→None"""
    if l is None: return None
    if isinstance(l, dict): return l
    if isinstance(l, str) and l.strip():
        return {"place": l.strip(), "price": None, "notes": None}
    return None


def upgrade_nested(d):
    """v1 嵌套 → v2.0"""
    d = copy.deepcopy(d)
    ep = d.get('episode', {})
    tr = d.get('trip', {})
    removed = []

    captured = to_iso_tz(d.get('last_updated'))
    ep['stats'] = norm_stats_nested(ep.get('stats', {}), captured)

    # l3_hooks → trip.suitable_for / customization_notes（去路径）
    l3 = d.pop('l3_hooks', {}) or {}
    if l3.get('suitable_for'):
        v = l3['suitable_for']
        tr['suitable_for'] = strip_path_from_text(v) if has_local_path(v) else v
    if l3.get('customization_notes'):
        tr['customization_notes'] = l3['customization_notes']

    # related_episodes → related_videos（保留下集完整元数据）
    related = []
    for i, r in enumerate(ep.pop('related_episodes', []) or [], 2):
        if isinstance(r, dict) and r.get('bvid'):
            item = {"bvid": r['bvid'], "relation": "part",
                    "note": (r.get('title') or '关联视频')[:40], "part_number": i}
            for k in ('url', 'publish_date', 'duration', 'title'):
                if r.get(k) is not None: item[k] = r[k]
            if r.get('stats'):
                item['stats'] = norm_stats_nested(r['stats'], None)
                item['stats'].pop('captured_at', None)
            related.append(item)
    ep['related_videos'] = related
    # 当前集自身 part_number：有上集关系时它是第1集
    ep['part_number'] = 1 if related else None

    ep.setdefault('series', None)
    if 'duration_seconds' not in ep:
        ep['duration_seconds'] = parse_dur_seconds(ep.get('duration'))

    # === trip 收口 ===
    # location → locations 数组
    loc = tr.pop('location', None)
    if loc:
        tr['locations'] = [loc]
    else:
        tr.setdefault('locations', [{"city": None, "province": None, "region": None, "country": "中国"}])
    # theme → themes
    if 'theme' in tr: tr['themes'] = tr.pop('theme')
    tr.setdefault('themes', [])

    # stops：加 order、lodging 转对象
    for idx, s in enumerate(tr.get('stops', []), 1):
        s['order'] = idx
        s['lodging'] = lodging_to_obj(s.get('lodging'))
        s.setdefault('time', None)
        s.setdefault('detail', None)
        for k in ('activities', 'food', 'cost_notes', 'tips'):
            s.setdefault(k, [])

    # 费用统一进 budget（旧 cost_total/per_person/cost_notes 迁入，不丢）
    old_budget = tr.pop('budget', None) or {}
    budget = {
        "total": tr.pop('cost_total', None) or old_budget.get('total'),
        "per_person": tr.pop('cost_per_person', None) or old_budget.get('per_person'),
        "note": tr.pop('cost_notes', None) or old_budget.get('note'),
        "price_as_of": tr.pop('price_as_of', None) or old_budget.get('price_as_of'),
        "items": old_budget.get('items', []),
    }
    if any(v not in (None, [], '') for v in budget.values()):
        tr['budget'] = budget
    else:
        tr['budget'] = None

    # === 路线级 tips 统一 [{category,text}]，合并旧 tips + practical_tips ===
    merged = tips_to_objs(d.pop('tips', [])) + tips_to_objs(d.pop('practical_tips', []))
    d['tips'] = merged

    # source_note（旧 source_data 去路径），删 transcript_ref
    sdata = d.pop('source_data', None)
    d.pop('transcript_ref', None)
    if not d.get('source_note'):
        d['source_note'] = strip_path_from_text(sdata) if sdata else None

    d.setdefault('next_stop', None)
    d.setdefault('last_checked_at', None)
    d['schema_version'] = '2.0'
    d['data_status'] = d.get('data_status', 'draft')
    d['episode'] = ep
    d['trip'] = tr

    d = deep_strip_paths(d, removed)
    return d, removed


def convert_flat(d):
    """扁平(鞍山) → v2.0"""
    d = copy.deepcopy(d)
    removed = []
    st = d.get('stats', {})
    stats = {
        "views": st.get('view'), "likes": st.get('like'),
        "favorites": st.get('favorite'), "danmaku": st.get('danmaku'),
        "comments": st.get('reply'), "captured_at": None,
    }
    sub = d.get('subtitle', '')
    m = re.search(r'第\s*(\d+)\s*站', sub)
    series = {"title": "搭火车环游中国", "series_id": "xiaoke-train-china",
              "episode_number": int(m.group(1)) if m else None}

    stops = []
    for i, it in enumerate(d.get('itinerary', []), 1):
        stops.append({
            "order": i, "name": it.get('title'), "day": None, "time": it.get('time'),
            "arrive_transport": None, "arrive_cost": None, "detail": it.get('detail'),
            "activities": [], "lodging": None, "food": [], "cost_notes": [], "tips": [],
        })

    loc = d.get('location') or {}
    budget_raw = d.get('budget')
    budget = None
    if budget_raw:
        budget = {"total": None, "per_person": None, "note": budget_raw.get('note'),
                  "price_as_of": None, "items": budget_raw.get('items', [])}

    out = {
        "schema_version": "2.0",
        "episode": {
            "blogger": "小可追太阳", "blogger_mid": None,
            "title": d.get('title'), "bvid": d.get('bvid') or d.get('id'),
            "url": d.get('bilibili_url'), "duration": d.get('duration_display'),
            "duration_seconds": d.get('duration_seconds'),
            "publish_date": d.get('pubdate'), "part_number": None,
            "stats": stats, "tags": d.get('theme', []),
            "series": series, "related_videos": [],
            "description": d.get('subtitle'),
        },
        "trip": {
            "title": d.get('subtitle') or d.get('title'),
            "route_summary": d.get('subtitle'),
            "route_type": d.get('route_type'),
            "themes": d.get('theme', []),
            "locations": [loc] if loc else [{"city": None, "province": None, "region": None, "country": "中国"}],
            "direction": None, "season": None, "duration_days": None,
            "transport_modes": [], "suitable_for": None,
            "stops": stops, "budget": budget,
        },
        "tips": tips_to_objs(d.get('practical_tips', [])),
        "highlights": d.get('highlights', []),
        "next_stop": d.get('next_stop'),
        "source_note": d.get('source_note'),
        "data_status": d.get('data_status', 'draft'),
        "last_updated": "2026-08-24",
        "last_checked_at": None,
    }
    out = deep_strip_paths(out, removed)
    return out, removed


def convert_any(d):
    """自动判断版本并转换"""
    if 'itinerary' in d and 'episode' not in d:
        return convert_flat(d)
    return upgrade_nested(d)


# ============ 内容完整性比对 ============
def content_inventory(d):
    texts = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('schema_version', 'last_updated', 'captured_at', 'last_checked_at',
                         'order', 'part_number', 'duration_seconds'): continue
                walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
        elif isinstance(o, str) and o.strip() and not has_local_path(o):
            texts.append(o.strip())
    walk(d)
    return texts


if __name__ == '__main__':
    import sys
    # 样本转换：鞍山(扁平) + 三峡(嵌套最全)
    samples = {'BV1F9U8BzE3F': '三峡(嵌套最全)', 'BV111Fze1EZw': '鞍山(扁平)'}
    os.makedirs('_v2_samples', exist_ok=True)
    for bv, label in samples.items():
        src = json.load(open(f'episodes/{bv}.json', encoding='utf-8'))
        before = content_inventory(src)
        out, removed = convert_any(src)
        after = content_inventory(out)
        json.dump(out, open(f'_v2_samples/{bv}.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        lost = [t for t in set(before) - set(after) if len(t) > 4]
        print(f"[{label}] {bv}: 内容 {len(set(before))}→{len(set(after))} | 删路径{len(removed)} | 丢失{len(lost)}")
        for t in lost[:8]: print("   LOST:", t[:70])
    print("样本已写入 _v2_samples/（未覆盖 episodes/）")
