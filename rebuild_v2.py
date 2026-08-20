# -*- coding: utf-8 -*-
"""路线库V2.1改造：7项优化（返回按钮/横滑表格/费用清单/贴士表/联系站长/底部说明）"""
import os, re, glob, json

ROOT = r"D:\output\routes-site-v2"
EMAIL = "2799787505@qq.com"

# ---------- 新版移动端CSS（替换旧的） ----------
MOBILE_CSS = """
@media (max-width: 640px) {
  body { padding: 20px 14px 60px; font-size: 14.5px; }
  h1 { font-size: 22px; }
  table { font-size: 13px; }
  thead { display: none; }
  .statbar { gap: 6px; }
  .stat { padding: 6px 10px; font-size: 12px; }
  .btn { width: 100%; text-align: center; }
  /* 贴士表卡片化（仅此表） */
  table.tips-card, table.tips-card tbody, table.tips-card tr, table.tips-card td { display: block; width: 100%; }
  table.tips-card tr { margin: 0 0 14px; border: 1px solid #eee; border-radius: 10px; padding: 4px 0; background: #fff; }
  table.tips-card td { border: none !important; padding: 7px 14px; }
  table.tips-card td:first-child { font-weight: 600; color: #c23a1a; }
}
"""

# ---------- 新版移动端JS（替换旧的）：总览/费用表横滑，贴士表卡片化 ----------
MOBILE_JS = """
<script>
(function(){
  if (window.innerWidth > 640) return;
  document.querySelectorAll('table').forEach(function(t){
    var heads = [];
    t.querySelectorAll('thead th').forEach(function(th){ heads.push(th.textContent.trim()); });
    var joined = heads.join('');
    if (joined.indexOf('贴士') > -1 || joined.indexOf('小tips') > -1) {
      t.className = 'tips-card';  // 贴士表：卡片化，不显示标签
    } else {
      // 其他表（路线总览/费用清单）：横向滑动
      var w = document.createElement('div');
      w.style.cssText = 'overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0;';
      t.parentNode.insertBefore(w, t);
      w.appendChild(t);
    }
  });
})();
</script>
"""

# ---------- 联系站长块（场景放宽） ----------
CONTACT = """
<div style="margin-top:34px;padding:14px 18px;background:#fdf6f2;border:1px solid #f0d9cf;border-radius:8px;font-size:13.5px;color:#7a4a3a;">
  <strong>联系站长</strong>：纠错、合作、交流均可 —— <a href="mailto:%s" style="color:#c23a1a;">%s</a>
</div>
""" % (EMAIL, EMAIL)

def get_blogger(bv):
    try:
        d = json.load(open(os.path.join(ROOT, "episodes", bv + ".json"), encoding="utf-8"))
        return d.get("blogger") or d.get("episode", {}).get("blogger") or ""
    except Exception:
        return ""

for f in glob.glob(os.path.join(ROOT, "pages", "*.html")):
    s = open(f, encoding="utf-8").read()
    orig = s
    bv = os.path.basename(f).replace(".html", "")

    # ---- 7.1 返回按钮（body 之后） ----
    back_btn = '<p style="margin:0 0 18px;"><a href="../index.html" style="color:#c23a1a;text-decoration:none;font-weight:600;font-size:14px;">← 返回路线库首页</a></p>'
    if "返回路线库首页" not in s:
        s = s.replace("<body>", "<body>\n" + back_btn, 1)

    # ---- 7.2 费用清单：列头去"视频内" ----
    s = s.replace("金额（视频内）", "金额")

    # ---- 7.4 费用清单：表格下注移到标题下 ----
    # 提取表格下的"注：以上为..."
    m = re.search(r'<p class="note">(注：以上为[^<]*)</p>', s)
    if m:
        note_text = m.group(1)
        # 标题下加说明（含拍摄时点）
        s = s.replace('<p class="note">%s</p>' % note_text, "", 1)  # 先删原注
        # 在费用清单标题后插入
        s = re.sub(r'(<h2>[三四]、费用清单</h2>)', r'\1\n<p class="note">%s</p>' % note_text, s, count=1)

    # ---- 7.5 贴士表：3列→2列，出处合并进正文 ----
    # 表头：删出处列
    s = re.sub(r'<th[^>]*>出处</th>', '', s)
    s = s.replace('<th style="width:78%">小tips</th>', '<th>贴士</th>')
    # 行：第3个td（出处）并入第2个td末尾
    def merge_src(match):
        row = match.group(0)
        tds = re.findall(r'<td>(.*?)</td>', row, re.S)
        if len(tds) == 3:
            num, content, src = tds
            src = re.sub(r'<[^>]+>', '', src).strip()
            if src:
                content = content + ' <em style="color:#999;font-style:normal;font-size:12px;">（%s）</em>' % src
            return '<tr><td>%s</td><td>%s</td></tr>' % (num, content)
        return row
    s = re.sub(r'<tr><td>\d+</td>.*?</tr>', merge_src, s, flags=re.S)

    # ---- 7.6 联系站长块（替换旧的纠错块） ----
    s = re.sub(r'<div style="margin-top:34px;padding:12px 16px[^"]*">.*?发现信息有误.*?</div>', CONTACT, s, flags=re.S)
    if "联系站长" not in s:
        s = s.replace("<hr>", CONTACT + "\n<hr>", 1)

    # ---- 7.7 底部整理说明重写 ----
    blogger = get_blogger(bv)
    # 作品名：title 去博主前缀
    tm = re.search(r'<title>([^·]+)·([^<]+)</title>', s)
    if tm:
        blogger_html = tm.group(1)
        work = tm.group(2)
    else:
        work = re.search(r'<title>([^<]+)</title>', s).group(1)
        blogger_html = blogger
    # 发布日期
    dm = re.search(r'发布 <b>([\d-]+)</b>', s)
    date = dm.group(1) if dm else ""
    new_note = ('<p class="note">本页整理自 B 站公开视频《%s》（创作者：%s，发布于 %s）。'
                '价格为视频拍摄时信息，出行前请以官方实时信息为准。完整内容请观看原视频。</p>'
                % (work, blogger_html or blogger, date))
    # 删除旧的整理说明note（从"整理说明："或"数据状态"开头的整段）
    s = re.sub(r'<p class="note">(?:整理说明|数据状态)：.*?</p>', '', s, flags=re.S)
    # 追加新note（在</body>前）
    s = s.replace("</body>", new_note + "\n</body>", 1)

    # ---- 替换移动端CSS/JS ----
    s = re.sub(r'@media \(max-width: 640px\) \{.*?\n\}', MOBILE_CSS.strip(), s, flags=re.S)
    s = re.sub(r'<script>\s*\(function\(\)\{[^<]*innerWidth > 640[^<]*</script>', MOBILE_JS, s, flags=re.S)

    if s != orig:
        open(f, "w", encoding="utf-8").write(s)
        print("V2.1改造:", os.path.basename(f))

# ---------- 首页：联系站长块 ----------
f = os.path.join(ROOT, "index.html")
s = open(f, encoding="utf-8").read()
orig = s
s = re.sub(r'<div style="margin-top:34px;padding:12px 16px[^"]*">.*?发现信息有误.*?</div>', CONTACT, s, flags=re.S)
if "联系站长" not in s:
    s = s.replace('<p class="note">', CONTACT + '\n<p class="note">', 1)
if s != orig:
    open(f, "w", encoding="utf-8").write(s)
    print("V2.1改造: index.html")
print("DONE")
