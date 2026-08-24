# -*- coding: utf-8 -*-
"""提交前校验脚本（Codex 第15条）
检查 episodes/*.json + catalog.json：
  - 符合 route.schema.v2.json / catalog.schema.v2.json
  - 无本地绝对路径（D:\\... 或 /x/output）
  - 枚举值合法（data_status、relation、source_type）
  - 必填项齐全
  - catalog 与 episodes 一致性（content_hash、updated_at 来自 last_updated）
退出码非0 = 校验失败，可用于 pre-commit 阻断提交。
用法: python validate.py            # 校验全部
      python validate.py _v2_samples # 校验指定目录的样本
"""
import json, os, re, sys, glob, hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

# Windows 中文终端输出安全
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
try:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("需要 jsonschema: pip install jsonschema"); sys.exit(2)

PATH_RE = re.compile(r'[A-Za-z]:\\|/[a-z]/output')
errors = []

def err(where, msg):
    errors.append(f"[{where}] {msg}")

def find_local_paths(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items(): hits += find_local_paths(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj): hits += find_local_paths(v, f"{path}[{i}]")
    elif isinstance(obj, str) and PATH_RE.search(obj):
        hits.append(f"{path}={obj[:50]}")
    return hits

def sha256_file(fp):
    with open(fp, 'rb') as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()

def validate_routes(ep_dir="episodes"):
    route_schema = json.load(open("route.schema.v2.json", encoding='utf-8'))
    validator = Draft7Validator(route_schema)
    files = sorted(glob.glob(f"{ep_dir}/*.json"))
    print(f"校验 {ep_dir}/ 共 {len(files)} 条")
    ok = 0
    for f in files:
        bv = os.path.basename(f).replace('.json', '')
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            err(bv, f"JSON解析失败: {e}"); continue
        # 只校验 v2.0（v1 旧文件跳过 schema 但仍查路径）
        if d.get('schema_version') == '2.0':
            for e in sorted(validator.iter_errors(d), key=lambda x: list(x.path)):
                err(bv, f"schema: {'.'.join(map(str,e.path))}: {e.message[:80]}")
            # bvid 与文件名一致
            if d.get('episode', {}).get('bvid') != bv:
                err(bv, f"bvid与文件名不符: {d.get('episode',{}).get('bvid')}")
        else:
            err(bv, f"schema_version={d.get('schema_version')} 非2.0（待转换）")
        # 本地路径（所有文件都查）
        for hit in find_local_paths(d):
            err(bv, f"本地路径: {hit}")
        if not [e for e in errors if e.startswith(f"[{bv}]")]:
            ok += 1
    return ok, len(files)

def validate_catalog():
    if not os.path.exists("catalog.json"):
        print("catalog.json 不存在（尚未生成，跳过）"); return
    cat_schema = json.load(open("catalog.schema.v2.json", encoding='utf-8'))
    cat = json.load(open("catalog.json", encoding='utf-8'))
    for e in Draft7Validator(cat_schema).iter_errors(cat):
        err("catalog", f"{'.'.join(map(str,e.path))}: {e.message[:80]}")
    # 一致性：count、content_hash、updated_at=last_updated
    routes = cat.get('routes', [])
    if cat.get('count') != len(routes):
        err("catalog", f"count={cat.get('count')} 但routes有{len(routes)}条")
    for r in routes:
        bv = r.get('source_id'); jp = r.get('json_path', '')
        if not os.path.exists(jp):
            err("catalog", f"{bv}: json_path不存在 {jp}"); continue
        real_hash = sha256_file(jp)
        if r.get('content_hash') != real_hash:
            err("catalog", f"{bv}: content_hash不符（文件已变但catalog没更新）")
        d = json.load(open(jp, encoding='utf-8'))
        if r.get('updated_at') != d.get('last_updated'):
            err("catalog", f"{bv}: updated_at={r.get('updated_at')} ≠ last_updated={d.get('last_updated')}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "episodes"
    ok, total = validate_routes(target)
    if target == "episodes":
        validate_catalog()
    print("=" * 50)
    if errors:
        print(f"❌ 校验失败，{len(errors)} 个问题：")
        for e in errors[:40]: print("  ", e)
        if len(errors) > 40: print(f"  ...还有{len(errors)-40}个")
        sys.exit(1)
    else:
        print(f"✅ 全部通过：{ok}/{total} 条路线 + catalog 一致")
        sys.exit(0)
