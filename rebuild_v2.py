# -*- coding: utf-8 -*-
"""路线库v2改造脚本：话术优化 + 移动端表格卡片化 + 纠错入口"""
import os, re, glob

ROOT = r"D:\output\routes-site-v2"
CONTACT = "contact@example.com"  # TODO: 用户提供真实邮箱后替换

# ---------- 注入片段 ----------
MOBILE_CSS = """
@media (max-width: 640px) {
  body { padding: 20px 14px 60px; font-size: 14.5px; }
  h1 { font-size: 22px; }
  table, thead, tbody, tr, th, td { display: block; width: 100%; }
  thead { display: none; }
  tr { margin: 0 0 14px; border: 1px solid #eee; border-radius: 10px; padding: 4px 0; background: #fff; }
  td { border: none !important; padding: 7px 14px; }
  td[data-label]:before { content: attr(data-label); display: block; font-weight: 600; color: #c23a1a; font-size: 12px; margin-bottom: 1px; }
  .statbar { gap: 6px; }
  .stat { padding: 6px 10px; font-size: 12px; }
  .btn { width: 100%; text-align: center; }
}
"""

MOBILE_JS = """
<script>
(function(){
  if (window.innerWidth > 640) return;
  document.querySelectorAll('table').forEach(function(t){
    var heads = [];
    t.querySelectorAll('thead th').forEach(function(th){ heads.push(th.textContent.trim()); });
    t.querySelectorAll('tbody tr').forEach(function(tr){
      tr.querySelectorAll('td').forEach(function(td,i){
        if (heads[i] && !td.getAttribute('data-label')) td.setAttribute('data-label', heads[i]);
      });
    });
  });
})();
</script>
"""

CORRECTION_HTML = """
<div style="margin-top:34px;padding:12px 16px;background:#fdf6f2;border:1px solid #f0d9cf;border-radius:8px;font-size:13px;color:#7a4a3a;">
  <strong>发现信息有误？</strong> 本站信息整理自公开视频，独立核验中，欢迎反馈纠错：
  <a href="mailto:%s" style="color:#c23a1a;">联系站长</a>（附视频时间点可更快修正）
</div>
""" % CONTACT

# ---------- 详情页处理 ----------
for f in glob.glob(os.path.join(ROOT, "pages", "*.html")):
    s = open(f, encoding="utf-8").read()
    orig = s
    # 1) 话术：Tips标题去博主名
    s = s.replace("四、赖导小tips合集", "四、路线实用贴士")
    s = s.replace("五、赖导小tips合集", "五、路线实用贴士")
    s = s.replace("四、小tips合集", "四、路线实用贴士")
    s = s.replace("五、小tips合集", "五、路线实用贴士")
    # 2) 话术：副标题"内容整理"→"公开视频整理"
    s = s.replace("B站视频内容整理", "公开视频整理")
    # 3) 注入移动端CSS
    if "max-width: 640px" not in s:
        s = s.replace("</style>", MOBILE_CSS + "\n</style>", 1)
    # 4) 注入移动端JS
    if "innerWidth > 640" not in s:
        s = s.replace("</body>", MOBILE_JS + "\n</body>", 1)
    # 5) 纠错入口（页脚，整理说明之前）
    if "发现信息有误" not in s:
        s = s.replace('<hr>', CORRECTION_HTML + "\n<hr>", 1) if '<hr>' in s else s.replace("</body>", CORRECTION_HTML + "\n</body>", 1)
    if s != orig:
        open(f, "w", encoding="utf-8").write(s)
        print("改造:", os.path.basename(f))

# ---------- 首页处理 ----------
f = os.path.join(ROOT, "index.html")
s = open(f, encoding="utf-8").read()
orig = s
# lead 话术：声明前置（独立整理、非合作背书、价格时效）
old_lead = '把喜欢的旅行博主的视频，整理成能直接用的路线图：每期视频 → 完整路线、交通方式、花费清单、实用小tips。按博主分组浏览，也可去原视频看完整内容。原创内容版权归原作者所有，本站仅做结构化整理。'
new_lead = '把旅行博主公开视频，整理成能直接用的路线图：完整路线、交通方式、花费清单、实用贴士。本站独立整理，与创作者无合作/背书关系；原创内容版权归原作者所有，价格为视频拍摄时信息，出行前请核实。按博主分组浏览，也可去原视频看完整内容。'
if old_lead in s:
    s = s.replace(old_lead, new_lead)
    print("lead话术更新")
# 移动端CSS注入
if "max-width: 640px" not in s:
    s = s.replace("</style>", MOBILE_CSS + "\n</style>", 1)
# 纠错入口
if "发现信息有误" not in s:
    s = s.replace('<p class="note">', CORRECTION_HTML + '\n<p class="note">', 1)
if s != orig:
    open(f, "w", encoding="utf-8").write(s)
    print("首页改造完成")
print("DONE")
