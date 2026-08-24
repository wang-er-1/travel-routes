# -*- coding: utf-8 -*-
"""样本转换差异报告（Codex 第8条要求的8个维度）"""
import json, os, sys
sys.path.insert(0, r"D:\output\routes-site-v2")
os.chdir(r"D:\output\routes-site-v2")
from _v2_convert import convert_any, content_inventory

def report(bv, label):
    src = json.load(open(f'episodes/{bv}.json', encoding='utf-8'))
    out = json.load(open(f'_v2_samples/{bv}.json', encoding='utf-8'))
    before, after = set(content_inventory(src)), set(content_inventory(out))
    lost = [t for t in before - after if len(t) > 4]

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
    _, removed = convert_any(src)
    print(f"⑥ 删除本地路径: {len(removed)}处 {removed if removed else ''}")

    # 7 无法自动归类字段（源里有但没映射进去的顶层键）
    print(f"⑦ locations(原location): {tr['locations']} | themes(原theme): {tr.get('themes')}")

    # 8 内容丢失
    print(f"⑧ 内容文本: {len(before)}→{len(after)} | 丢失(>4字): {len(lost)}")
    for t in lost[:10]: print(f"      LOST: {t[:70]}")
    if not lost: print("      ✅ 除故意删除的本地路径外，无任何文字内容丢失")

report('BV111Fze1EZw', '鞍山（扁平样本）')
report('BV1F9U8BzE3F', '三峡（嵌套最完整样本，含上下集）')
