# -*- coding: utf-8 -*-
"""schema v2.0 转换器（按 Codex 8条复核意见修订）

Codex 复核修正对照：
 1. 路径不写死：BASE 取脚本所在仓库目录（家庭/公司电脑通用）
 2. Windows 中文终端输出 ✅ 不炸 UnicodeEncodeError
 3. transcript_ref 不无条件删：内容含本地路径才删；自然语言（如"适合人群"）迁移到 trip.suitable_for
    ——BV16NpQznEXC/BV1eh9YBUEYp/BV1UetHeTEsH 三条 transcript_ref 装的是适合人群文字，必须保留
 4. （文档同步在 SCHEMA_PROPOSAL.md 另改）
 5. catalog 生成见 gen_catalog.py
 6. 零丢失检查升级：比较全部有意义的叶子数据（含短文字、数字、重复内容），不只 >4 字集合
 7. locations 不生成全 null 占位对象：优先从 stops 提取，否则空数组并在报告里列待补
 8. related_videos 不默认 part / 不自动设第1集：仅当 trip.title 含"上/下两集"等明确关系时才转
"""
import json, os, re, copy, hashlib, sys

# ---- 修1：脚本所在仓库目录（不再写死 D:\output\routes-site-v2）----
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

# ---- 修2：Windows 中文终端输出安全 ----
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
try:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TZ = "+08:00"
# 严格盘符：字母+冒号+反斜杠（D:\...）；MSYS：/x/output/...
LOCAL_PATH_RE = re.compile(r'[A-Za-z]:\\|/[a-z]/output')

def has_local_path(s):
    return isinstance(s, str) and bool(LOCAL_PATH_RE.search(s))

def strip_path_from_text(s):
    """从一段文字里剥掉本地路径片段，保留正常文字（不误伤 https:// 等公网URL）"""
    if not isinstance(s, str):
        return s
    # 只剥 Windows 盘符路径（冒号后必须跟反斜杠）和 MSYS 路径
    cleaned = re.sub(r'[A-Za-z]:\\[^\s，。；、)）"\']*', '', s)
    cleaned = re.sub(r'/[a-z]/output[^\s，。；、)）"\']*', '', cleaned)
    return cleaned.strip(' :：（(')

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

def deep_strip_paths(obj, removed):
    """递归：字符串里含本地路径→剥离路径片段（保留周围文字）；纯路径串→置 None 并记录"""
    if isinstance(obj, dict):
        return {k: deep_strip_paths(v, removed) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_strip_paths(x, removed) for x in obj]
    if isinstance(obj, str) and has_local_path(obj):
        cleaned = strip_path_from_text(obj)
        if cleaned != obj:
            removed.append(obj[:70])
        return cleaned if cleaned else None
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

def tips_to_objs(raw):
    """字符串贴士→[{category:'其他',text}]；对象规整"""
    out = []
    for t in raw or []:
        if isinstance(t, str) and t.strip():
            out.append({"category": "其他", "text": t.strip()})
        elif isinstance(t, dict):
            cat = t.get('category') or '其他'
            txt = t.get('text') or t.get('tip') or ''
            if txt: out.append({"category": cat, "text": txt})
    return out

def lodging_to_obj(l):
    if l is None: return None
    if isinstance(l, dict): return l
    if isinstance(l, str) and l.strip():
        return {"place": l.strip(), "price": None, "notes": None}
    return None

def extract_locations(tr):
    """修7：locations 优先取 trip.location；否则从 stops 提取；再否则空数组+报告"""
    loc = tr.pop('location', None)
    if loc and any(loc.get(k) for k in ('city','province','region')):
        return [loc], []
    # 从 stops 的 name / arrive_transport 提取候选地名（启发式：排除明显非地名的站名）
    pending = []
    for s in tr.get('stops', []):
        nm = s.get('name') or ''
        if nm and not re.search(r'酒店|饭店|公园|广场|餐厅|景区|博物馆|村$|镇$|码头', nm):
            pending.append(nm)
    # 只在确有把握时填充：这里仅记录待补，不瞎猜行政归属
    return [], pending

def is_explicit_part(d):
    """修8：仅当 trip.title / episode.title 含明确的上下集标记时才认为 related 是 part"""
    title = (d.get('trip', {}) or {}).get('title', '') or (d.get('episode', {}) or {}).get('title', '')
    return ('上/下两集' in title or '上下两集' in title or '上集' in title or '下集' in title
            or '上/下' in title or '上下集' in title)

def upgrade_nested(d):
    """v1 嵌套 → v2.0"""
    d = copy.deepcopy(d)
    ep = d.get('episode', {})
    tr = d.get('trip', {})
    removed = []

    # 决策1：历史 captured_at 一律 null（不用 last_updated 补午夜时间）
    ep['stats'] = norm_stats_nested(ep.get('stats', {}), None)

    # 修3：l3_hooks.suitable_for（路径删 / 文字保留）→ trip.suitable_for；customization_notes 迁移
    l3 = d.pop('l3_hooks', {}) or {}
    suit_src = l3.get('suitable_for')
    if suit_src:
        tr['suitable_for'] = deep_strip_paths(suit_src, removed)
    cust = l3.get('customization_notes')
    if cust:
        tr['customization_notes'] = deep_strip_paths(cust, removed)

    # 修3：transcript_ref / source_data —— 内容判断：纯路径→删；自然语言→并入 source_note / suitable_for
    tref = d.pop('transcript_ref', None)
    if tref:
        if has_local_path(tref) and not re.search(r'[\u4e00-\u9fff]{4,}', tref):
            removed.append(tref[:70])          # 纯路径：删
        else:
            cleaned = deep_strip_paths(tref, removed)
            if cleaned:
                # 含中文字符的说明性文字：若像"适合人群"描述进 suitable_for，否则进 source_note
                if re.search(r'适合|人|爱好者|人群|出发|往返|顺路', cleaned) and not tr.get('suitable_for'):
                    tr['suitable_for'] = cleaned
                else:
                    d['source_note'] = cleaned
    sdata = d.pop('source_data', None)
    if sdata:
        d['source_note'] = deep_strip_paths(sdata, removed) or d.get('source_note')

    # 修8：related_videos 仅在明确上下集时转 part；否则 relation 由后续人工/规则定，绝不默认
    rel_old = ep.pop('related_episodes', []) or []
    related = []
    explicit_part = is_explicit_part(d)
    for r in rel_old:
        if not (isinstance(r, dict) and r.get('bvid')): continue
        item = {"bvid": r['bvid'],
                "relation": "part" if explicit_part else "series",
                "note": (r.get('title') or '关联视频')[:40]}
        if explicit_part:
            item['part_number'] = 2  # 主文件是上集，关联的是下集；上下集对调时人工修正
        for k in ('url', 'publish_date', 'duration', 'title'):
            if r.get(k) is not None: item[k] = r[k]
        if r.get('stats'):
            item['stats'] = norm_stats_nested(r['stats'], None)
            item['stats'].pop('captured_at', None)
        related.append(item)
    ep['related_videos'] = related
    # 当前集自身 part_number：只有明确上下集才设（主文件视为第1集）
    ep['part_number'] = 1 if (explicit_part and related) else None

    ep.setdefault('series', None)
    if 'duration_seconds' not in ep:
        ep['duration_seconds'] = parse_dur_seconds(ep.get('duration'))

    # 修7：locations
    tr['locations'], pending_locs = extract_locations(tr)
    if pending_locs:
        tr['_pending_locations'] = pending_locs  # 报告用，schema 不允许则转换后删

    # theme → themes
    if 'theme' in tr: tr['themes'] = tr.pop('theme')
    tr.setdefault('themes', [])

    # stops：order / lodging 对象 / 默认字段
    for idx, s in enumerate(tr.get('stops', []), 1):
        s['order'] = idx
        s['lodging'] = lodging_to_obj(s.get('lodging'))
        s.setdefault('time', None)
        s.setdefault('detail', None)
        for k in ('activities', 'food', 'cost_notes', 'tips'):
            s.setdefault(k, [])

    # 费用统一进 budget
    old_budget = tr.pop('budget', None) or {}
    budget = {
        "total": tr.pop('cost_total', None) or old_budget.get('total'),
        "per_person": tr.pop('cost_per_person', None) or old_budget.get('per_person'),
        "note": tr.pop('cost_notes', None) or old_budget.get('note'),
        "price_as_of": tr.pop('price_as_of', None) or old_budget.get('price_as_of'),
        "items": old_budget.get('items', []),
    }
    tr['budget'] = budget if any(v not in (None, [], '') for v in budget.values()) else None

    # tips 统一
    d['tips'] = tips_to_objs(d.pop('tips', [])) + tips_to_objs(d.pop('practical_tips', []))

    d.setdefault('next_stop', None)
    d.setdefault('last_checked_at', None)
    d['schema_version'] = '2.0'
    d['data_status'] = d.get('data_status', 'draft')
    d['episode'] = ep
    d['trip'] = tr

    d = deep_strip_paths(d, removed)
    # 清理内部报告字段
    d['trip'].pop('_pending_locations', None)
    return d, removed, pending_locs


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
    locations = [loc] if any(loc.get(k) for k in ('city','province','region')) else []

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
            "locations": locations,
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
    return out, removed, []


def convert_any(d):
    if 'itinerary' in d and 'episode' not in d:
        return convert_flat(d)
    return upgrade_nested(d)


# ---- 修6：叶子级零丢失检查（含短文字、数字、重复内容）----
def leaf_inventory(d):
    """提取全部有意义的叶子：字符串（含短词）、数字、布尔；保留重复
    注意：只排除结构性字段（schema_version/order 等机器值），
    source_note/next_stop 等是内容，必须纳入比对。"""
    leaves = []
    SKIP_KEYS = {'schema_version', 'last_updated', 'captured_at', 'last_checked_at',
                 'order', 'part_number', 'duration_seconds', 'data_status',
                 'content_hash', 'generated_at'}
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in SKIP_KEYS: continue
                walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
        elif isinstance(o, str):
            s = o.strip()
            if s and not has_local_path(s):
                leaves.append(('str', s))
        elif isinstance(o, (int, float)) and o is not False:
            leaves.append(('num', str(o)))
        elif isinstance(o, bool):
            leaves.append(('bool', str(o)))
    walk(d)
    return leaves


if __name__ == '__main__':
    # 样本转换：鞍山(扁平) + 三峡(嵌套最全)
    samples = {'BV1F9U8BzE3F': '三峡(嵌套最全)', 'BV111Fze1EZw': '鞍山(扁平)'}
    os.makedirs('_v2_samples', exist_ok=True)
    for bv, label in samples.items():
        src = json.load(open(f'episodes/{bv}.json', encoding='utf-8'))
        before = leaf_inventory(src)
        out, removed, pending = convert_any(src)
        after = leaf_inventory(out)
        json.dump(out, open(f'_v2_samples/{bv}.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        lost = [t for t in before if t not in after]
        print(f"[{label}] {bv}: 叶子 {len(before)}→{len(after)} | 删路径{len(removed)} | 丢失{len(lost)} | 待补locations={len(pending)}")
        for kind, t in lost[:10]: print("   LOST:", t[:60])
        if pending: print("   待补地点:", pending[:5])
    print("样本已写入 _v2_samples/（未覆盖 episodes/）")
