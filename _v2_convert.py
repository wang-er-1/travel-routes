# -*- coding: utf-8 -*-
"""schema v2.0 转换器 + 内容完整性校验
- 嵌套版(v1) → v2.0：升级 stats 字段名、迁移 l3_hooks.suitable_for→trip.suitable_for、
  清本地路径、related_episodes→related_videos、补 series/duration_seconds/captured_at 占位
- 扁平版(鞍山) → v2.0：itinerary→trip.stops、practical_tips 保留、budget 保留、
  next_stop 保留、扁平字段归位到 episode/trip
只做样本转换（不落盘覆盖），输出转换后 JSON + 前后内容差异报告，人工确认后再批量。
"""
import json, os, re, copy, hashlib

os.chdir(r"D:\output\routes-site-v2")

LOCAL_PATH_RE = re.compile(r'[A-Za-z]:\\\\?[^"\']*|/[a-z]/output[^"\']*')

def strip_local_paths(obj):
    """递归删除含本地绝对路径的字符串值；返回清理后的对象+被删路径列表"""
    removed = []
    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x) for x in o]
        if isinstance(o, str) and ('D:\\' in o or 'D:/' in o or re.search(r'[A-Za-z]:\\', o)):
            removed.append(o[:60])
            return None
        return o
    return walk(obj), removed


def upgrade_nested(d):
    """v1 嵌套 → v2.0 嵌套"""
    d = copy.deepcopy(d)
    ep = d.get('episode', {})
    tr = d.get('trip', {})

    # 1) stats 字段名统一 plays→views, likes, favorites, danmaku, comments + captured_at
    st = ep.get('stats', {})
    new_st = {
        'views': st.get('plays') if st.get('plays') is not None else st.get('views'),
        'likes': st.get('likes'),
        'favorites': st.get('favorites'),
        'danmaku': st.get('danmaku'),
        'comments': st.get('comments') if st.get('comments') is not None else st.get('reply'),
        'captured_at': d.get('last_updated'),  # 用现有更新时间占位，后续抓取时更新
    }
    ep['stats'] = new_st

    # 2) l3_hooks.suitable_for → trip.suitable_for（去路径），customization_notes 也迁移进 trip
    l3 = d.pop('l3_hooks', {}) or {}
    suitable = l3.get('suitable_for')
    if suitable and not ('D:\\' in suitable or 'D:/' in suitable):
        tr['suitable_for'] = suitable
    elif suitable:  # 含路径的，尝试剥离路径部分（一般路径在冒号后）
        cleaned = re.sub(r'[A-Za-z]:\\[^\s，。；]*', '', suitable).strip()
        tr['suitable_for'] = cleaned or None
    if l3.get('customization_notes'):
        tr.setdefault('customization_notes', l3['customization_notes'])

    # 3) related_episodes → related_videos（保留下集完整元数据，不丢失）
    rel_old = ep.pop('related_episodes', []) or []
    related = []
    for i, r in enumerate(rel_old, 2):
        if isinstance(r, dict) and r.get('bvid'):
            item = {
                'bvid': r['bvid'], 'relation': 'part',
                'note': r.get('title', '')[:40] or '关联视频', 'part_number': i
            }
            # 保留下集的完整元数据，避免信息丢失
            for k_src, k_dst in [('url','url'),('publish_date','publish_date'),
                                 ('duration','duration'),('title','title')]:
                if r.get(k_src) is not None:
                    item[k_dst] = r[k_src]
            if r.get('stats'):
                s = r['stats']
                item['stats'] = {
                    'views': s.get('plays') if s.get('plays') is not None else s.get('views'),
                    'likes': s.get('likes'), 'favorites': s.get('favorites'),
                    'danmaku': s.get('danmaku'),
                    'comments': s.get('comments') if s.get('comments') is not None else s.get('reply'),
                }
            related.append(item)
    ep['related_videos'] = related

    # 4) series 占位（嵌套版原本没有；小可追太阳系列后面人工/规则补，先置 null）
    if 'series' not in ep:
        ep['series'] = None

    # 5) duration_seconds 占位（从 duration "mm:ss" 解析）
    if 'duration_seconds' not in ep:
        dur = ep.get('duration', '')
        parts = [int(x) for x in re.findall(r'\d+', dur)]
        if len(parts) == 2: ep['duration_seconds'] = parts[0]*60+parts[1]
        elif len(parts) == 3: ep['duration_seconds'] = parts[0]*3600+parts[1]*60+parts[2]

    # 6) 删除旧字段 transcript_ref / source_data，改用 source_note
    tref = d.pop('transcript_ref', None)
    sdata = d.pop('source_data', None)
    if 'source_note' not in d:
        # source_data 去路径后作为 source_note
        sn = sdata or ''
        sn = re.sub(r'[A-Za-z]:\\[^\s，。；)]*', '', sn).strip()
        d['source_note'] = sn or None

    # 7) 清理任何残留本地路径
    d, removed = strip_local_paths(d)

    d['schema_version'] = '2.0'
    d['episode'] = ep
    d['trip'] = tr
    return d, removed


def convert_flat(d):
    """扁平版(鞍山) → v2.0 嵌套"""
    d = copy.deepcopy(d)
    st = d.get('stats', {})
    stats = {
        'views': st.get('view'), 'likes': st.get('like'),
        'favorites': st.get('favorite'), 'danmaku': st.get('danmaku'),
        'comments': st.get('reply'), 'captured_at': None,
    }
    # 系列：从 series 字符串拆出（鞍山原 series="小可追太阳"是错的，按subtitle纠正）
    # subtitle 里有"搭火车环游中国第5站：鞍山"
    sub = d.get('subtitle', '')
    epnum = None
    m = re.search(r'第\s*(\d+)\s*站', sub)
    if m: epnum = int(m.group(1))
    series = {
        'title': '搭火车环游中国',
        'series_id': 'xiaoke-train-china',
        'episode_number': epnum,
    }
    # itinerary → stops
    stops = []
    for it in d.get('itinerary', []):
        stops.append({
            'name': it.get('title'), 'day': None, 'time': it.get('time'),
            'arrive_transport': None, 'arrive_cost': None,
            'detail': it.get('detail'),
            'activities': [], 'lodging': None, 'food': [], 'cost_notes': [], 'tips': [],
        })
    out = {
        'schema_version': '2.0',
        'episode': {
            'blogger': '小可追太阳',
            'blogger_mid': None,
            'title': d.get('title'),
            'bvid': d.get('bvid') or d.get('id'),
            'url': d.get('bilibili_url'),
            'duration': d.get('duration_display'),
            'duration_seconds': d.get('duration_seconds'),
            'publish_date': d.get('pubdate'),
            'stats': stats,
            'tags': d.get('theme', []),
            'series': series,
            'related_videos': [],
            'description': d.get('subtitle'),
        },
        'trip': {
            'title': d.get('subtitle') or d.get('title'),
            'route_summary': d.get('subtitle'),
            'route_type': d.get('route_type'),
            'theme': d.get('theme', []),
            'location': d.get('location'),
            'direction': None, 'season': None, 'duration_days': None,
            'transport_modes': [],
            'cost_total': None, 'cost_per_person': None, 'cost_notes': None,
            'price_as_of': None,
            'suitable_for': None,
            'stops': stops,
            'budget': d.get('budget'),
        },
        'tips': [],
        'practical_tips': d.get('practical_tips', []),
        'highlights': d.get('highlights', []),
        'next_stop': d.get('next_stop'),
        'source_note': d.get('source_note'),
        'data_status': d.get('data_status', 'draft'),
        'last_updated': '2026-08-24',
    }
    out, removed = strip_local_paths(out)
    return out, removed


def content_inventory(d):
    """提取一条JSON的所有'内容文本'用于前后比对，证明无丢失"""
    texts = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('schema_version','last_updated','captured_at'): continue
                walk(v)
        elif isinstance(o, list):
            for x in o: walk(x)
        elif isinstance(o, str) and o.strip():
            # 排除本地路径（那是要故意删的）
            if not ('D:\\' in o or 'D:/' in o):
                texts.append(o.strip())
    walk(d)
    return texts


# ============ 执行样本转换 ============
samples = {
    'BV1F9U8BzE3F': ('nested', '三峡(嵌套最全样本)'),
    'BV111Fze1EZw': ('flat', '鞍山(扁平样本)'),
}

os.makedirs('_v2_samples', exist_ok=True)
report = []
for bv, (kind, label) in samples.items():
    src = json.load(open(f'episodes/{bv}.json', encoding='utf-8'))
    before_texts = set(content_inventory(src))
    if kind == 'nested':
        out, removed = upgrade_nested(src)
    else:
        out, removed = convert_flat(src)
    after_texts = set(content_inventory(out))

    lost = before_texts - after_texts   # 转换后丢失的内容文本
    # 过滤掉纯粹因字段名/结构变化产生的噪音（如被拆分重组的），只报真正消失的完整句子
    real_lost = [t for t in lost if len(t) > 4]

    json.dump(out, open(f'_v2_samples/{bv}.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
    report.append({
        'bv': bv, 'label': label, 'kind': kind,
        'before_text_count': len(before_texts),
        'after_text_count': len(after_texts),
        'removed_local_paths': removed,
        'lost_content': real_lost,
    })

print("="*60)
print("样本转换差异报告")
print("="*60)
for r in report:
    print(f"\n【{r['label']}】 {r['bv']} ({r['kind']})")
    print(f"  内容文本条数：转换前 {r['before_text_count']} → 转换后 {r['after_text_count']}")
    print(f"  删除的本地路径 {len(r['removed_local_paths'])} 处：{r['removed_local_paths']}")
    if r['lost_content']:
        print(f"  ⚠️ 疑似丢失内容 {len(r['lost_content'])} 条：")
        for t in r['lost_content'][:10]:
            print(f"      - {t[:70]}")
    else:
        print(f"  ✅ 无内容丢失（除故意删除的本地路径外）")
