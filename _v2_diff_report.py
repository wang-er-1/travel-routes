# -*- coding: utf-8 -*-
"""样本转换差异报告（Codex 第8条要求的8个维度）"""
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
from _v2_convert import convert_any, leaf_inventory, strict_diff

def report(bv, label):
    src = json.load(open(f'episodes/{bv}.json', encoding='utf-8'))
    out = json.load(open(f'_v2_samples/{bv}.json', encoding='utf-8'))
    before, after = leaf_inventory(src), leaf_inventory(out)
    real_lost, allowed = strict_diff(src, out)

    ep, tr = out['episode'], out['trip']
    print(f"\n{'='*64}\n【{label}】 {bv}\n{'='*64}")

    # 1 字段映射（顶层结构对比）
    print("① 字段映射:")
    print(f"   顶层: {list(src.keys())}")
    print(f"      → {list(out.keys())}")
    print(f"   stats字段名: {list((src.get('episode',{}) or src).get('stats',{}).keys())}")
    print(f"      → {list(ep['stats'].keys())}")

    # 2 stops 数量
    src_stops = len((src.get('trip',{}).get('stops')) or src.get('itinerary') or [])
    print(f"② stops数量: {src_stops} → {len(tr['stops'])}  (order 1..{len(tr['stops'])})")

    # 3 tips/highlights 数量
    src_tips = len(src.get('tips') or []) + len(src.get('practical_tips') or [])
    print(f"③ 路线级tips: {src_tips} → {len(out['tips'])} (统一{{category,text}})"
          f" | highlights: {len(src.get('highlights') or [])} → {len(out['highlights'])}")

    # 4 预算与费用
    b = tr.get('budget')
    print(f"④ 费用→budget: {'有' if b else 'null'}", end="")
    if b: print(f" (total={b['total']} per_person={b['per_person']} items={len(b['items'])} note={'有' if b['note'] else '无'})")
    else: print()

    # 5 系列与关联视频
    print(f"⑤ series: {json.dumps(ep['series'], ensure_ascii=False)}")
    print(f"   episode.part_number(自身): {ep['part_number']}")
    print(f"   related_videos: {len(ep['related_videos'])}条", end="")
    if ep['related_videos']:
        rv=ep['related_videos'][0]
        print(f" → bvid={rv['bvid']} relation={rv['relation']} part={rv.get('part_number')} 保留元数据={'stats' in rv}")
    else: print()

    # 6 删除的绝对路径
    _, removed, _ = convert_any(src)
    print(f"⑥ 删除本地路径: {len(removed)}处 {removed if removed else ''}")

    # 7 无法自动归类字段（源里有但没映射进去的顶层键）
    print(f"⑦ locations(原location): {tr['locations']} | themes(原theme): {tr.get('themes')}")

    # 8 叶子数据差异（严格多重集差值）
    print(f"⑧ 叶子数据: {len(before)}→{len(after)} | 真实丢失: {len(real_lost)} | 允许差异: {len(allowed)}")
    for kind, t, c in real_lost[:10]: print(f"      LOST x{c}: {t[:70]}")
    for kind, t, c, why in allowed: print(f"      允许 x{c} [{why}]: {t[:50]}")
    if not real_lost: print("      ✅ 除允许差异（结构去重/移除转写引用）外，无叶子数据丢失")

report('BV111Fze1EZw', '鞍山（扁平样本）')
report('BV1F9U8BzE3F', '三峡（嵌套最完整样本，含上下集）')
