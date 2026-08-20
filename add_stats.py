# -*- coding: utf-8 -*-
"""注入不蒜子访问统计：首页(总访问+访客) + 详情页(本页访问)"""
import os, re, glob

ROOT = r"D:\output\routes-site-v2"

BSZ_JS = '<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>'

# 首页：页脚加 总访问量 + 总访客
f = os.path.join(ROOT, "index.html")
s = open(f, encoding="utf-8").read()
if "busuanzi" not in s:
    stat_html = '''
<p class="note" style="margin-top:14px;padding-top:8px;border-top:none;">
  本站总访问量 <b id="busuanzi_value_site_pv"></b> 次 ｜ 访客数 <b id="busuanzi_value_site_uv"></b> 人
</p>'''
    s = s.replace("</body>", stat_html + "\n" + BSZ_JS + "\n</body>", 1)
    open(f, "w", encoding="utf-8").write(s)
    print("index.html: 统计已注入")

# 详情页：页脚加 本页访问量
for f in glob.glob(os.path.join(ROOT, "pages", "*.html")):
    s = open(f, encoding="utf-8").read()
    if "busuanzi" in s:
        continue
    page_stat = '<p class="note" style="margin-top:10px;padding-top:8px;border-top:none;">本页被访问 <b id="busuanzi_value_page_pv"></b> 次</p>'
    s = s.replace("</body>", page_stat + "\n" + BSZ_JS + "\n</body>", 1)
    open(f, "w", encoding="utf-8").write(s)
    print(os.path.basename(f), ": 统计已注入")
print("DONE")
