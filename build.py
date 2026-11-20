# -*- coding: utf-8 -*-
"""sahelp 构建脚本（双语）。

扫描各语言源的 <section>/_manifest.json，生成：
  dist/                     — 英文版（主版本）CHM 风格 HTML 帮助查看器（default.html + 主题页）
  dist/cn/                  — 中文版查看器（结构同上）
  build/chm/                — 英文版 HTML Help Workshop 工程文件（hhc.exe 可编译为 .chm）
  build/chm-cn/             — 中文版 HTML Help Workshop 工程文件

语言源：英文 = content/，中文 = cn/content/。

用法：
  python build.py            # 构建（双语）
  python build.py --serve    # 构建后启动本地 HTTP 服务预览（英文版）
"""
import json
import os
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 章节顺序与标题（双语）；dir 必须与各语言源 content/ 下的目录名一致。
SECTIONS = [
    {"dir": "01_overview",   "title": {"en": "Getting Started", "cn": "入门指南"}},
    {"dir": "02_sla_lang",   "title": {"en": "SLA Language Reference", "cn": "SLA 语言参考"}},
    {"dir": "09_rust_compare", "title": {"en": "Comparison with Rust", "cn": "与 Rust 对比"}},
    {"dir": "17_rust_beginners", "title": {"en": "From Rust for Beginners", "cn": "给 Rust 程序员的 SLA 入门"}},
    {"dir": "03_sa_asm",     "title": {"en": "SA Assembly and SAB", "cn": "SA 汇编与 SAB"}},
    {"dir": "04_cli",        "title": {"en": "Command-Line Reference", "cn": "命令行参考"}},
    {"dir": "05_plugins",    "title": {"en": "Plugin Reference", "cn": "插件参考"}},
    {"dir": "10_db",         "title": {"en": "db Database Plugin", "cn": "db 数据库插件"}},
    {"dir": "11_ecs",        "title": {"en": "ECS Development (sla_ecs)", "cn": "ECS 开发（sla_ecs）"}},
    {"dir": "12_vm",         "title": {"en": "vm Virtual Machine", "cn": "vm 虚拟机"}},
    {"dir": "13_build",      "title": {"en": "Cross-Platform Builds", "cn": "多平台编译"}},
    {"dir": "06_stdlib",     "title": {"en": "Standard Library", "cn": "标准库"}},
    {"dir": "07_ui",         "title": {"en": "SAX / MUI UI Development", "cn": "SAX / MUI 界面开发"}},
    {"dir": "08_faq",        "title": {"en": "FAQ and Troubleshooting", "cn": "FAQ 与故障排查"}},
    {"dir": "14_zig017_perf", "title": {"en": "Zig 0.17 Upgrade Comparison", "cn": "Zig 0.17 升级对比"}},
    {"dir": "15_sa2c", "title": {"en": "sa→C Backend", "cn": "sa→C 后端"}},
    {"dir": "16_policy", "title": {"en": "Runtime Permissions and Auditing", "cn": "运行时权限与审计"}},
]

# 双语构建配置：英文为主版本（content/ → dist/），中文版在 cn/ 下（cn/content/ → dist/cn/）。
# viewer_switch = 查看器工具栏的语言切换链接（相对当前语言 dist 根目录）；
# topic_switch = 主题页页脚的语言切换链接前缀（相对 dist/content/<sec>/ 页）与文案。
LANGS = [
    {
        "code": "en",
        "content": ROOT / "content",
        "dist": ROOT / "dist",
        "chm": ROOT / "build" / "chm",
        "help_title": "SA / SLA Help Documentation",
        "chm_dist_rel": "../dist",
        "chm_compiled": "SA_SLDA_Help.chm",
        "chm_language": "0x409 英语(美国)",
        "chm_font": "Segoe UI,9,0",
        "viewer_switch": ("cn/default.html", "中文版"),
        "topic_switch": ("../../cn/content/", "中文版"),
    },
    {
        "code": "cn",
        "content": ROOT / "cn" / "content",
        "dist": ROOT / "dist" / "cn",
        "chm": ROOT / "build" / "chm-cn",
        "help_title": "SA / SLA 帮助文档",
        "chm_dist_rel": "../../dist/cn",
        "chm_compiled": "SA_SLDA_Help_CN.chm",
        "chm_language": "0x804 中文(中华人民共和国)",
        "chm_font": "微软雅黑,9,0",
        "viewer_switch": ("../default.html", "English"),
        "topic_switch": ("../../../content/", "English version"),
    },
]


def load_manifests(lang):
    """返回 (sections, all_topics)。topic 增加 section_title / relpath 字段。"""
    content = lang["content"]
    sections, all_topics = [], []
    for sec in SECTIONS:
        mfile = content / sec["dir"] / "_manifest.json"
        if not mfile.exists():
            print(f"[warn] 缺少清单: {mfile.relative_to(ROOT)}")
            continue
        data = json.loads(mfile.read_text(encoding="utf-8"))
        topics = []
        for t in data.get("topics", []):
            t = dict(t)
            t["section"] = sec["dir"]
            t["section_title"] = sec["title"][lang["code"]]
            t["relpath"] = f"{sec['dir']}/{t['file']}"
            topics.append(t)
        sections.append({**sec, "title": sec["title"][lang["code"]], "topics": topics})
        all_topics.extend(topics)
    return sections, all_topics


def extract_text(html: str) -> str:
    """去掉 script/style/标签，留纯文本供搜索。"""
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt)


def check_links(lang, all_topics):
    """检查主题页内相对链接在 dist 布局下是否可达。

    主题页在 dist 中位于 content/<relpath>，故按该虚拟位置解析相对 href：
    落在 content/ 下的映射回语言源 content/ 查存在性，落在 assets/ 下的查仓库
    assets/，查看器框架页（default/index.html）由构建生成、视为存在。
    """
    content = lang["content"]
    problems = []
    for t in all_topics:
        page = content / t["relpath"]
        for m in re.finditer(r'href="([^"#]+?)(?:#[^"]*)?"', page.read_text(encoding="utf-8")):
            href = m.group(1)
            if re.match(r"^[a-z]+:", href):  # http:// mailto: 等
                continue
            target = Path(os.path.normpath((Path("content") / t["relpath"]).parent / href))
            parts = target.parts
            if parts and parts[0] == "content":
                ok = (content / Path(*parts[1:])).exists()
            elif parts and parts[0] == "assets":
                ok = (ROOT / target).exists()
            elif len(parts) == 1 and parts[0] in ("default.html", "index.html"):
                ok = True
            else:
                ok = False
            if not ok:
                problems.append(f"{t['relpath']} -> {href} (不存在)")
    return problems


# ---------------------------------------------------------------- dist 输出

COPYRIGHT_HTML_CN = (
    '<footer class="copyright">© 2026 layola13 · SA / SLA 帮助文档 · 转载请注明出处<br>'
    'SA 编译器（<a href="https://github.com/layola13/sci">sci</a>）为 Apache License 2.0 '
    '授权发布，版权归 NOTICE 所列作者所有；本文档提及的各插件与上游组件遵循各自原始许可证。</footer>'
)


def _inject_copyright(html: str, lang_code: str) -> str:
    if "class=\"copyright\"" in html:
        return html
    return html.replace("</body>", COPYRIGHT_HTML[lang_code] + "\n</body>")


COPYRIGHT_HTML_EN = (
    '<footer class="copyright">© 2026 layola13 · SA / SLA Help Documentation · Please credit the source when reposting<br>'
    'The SA compiler (<a href="https://github.com/layola13/sci">sci</a>) is released under the Apache License 2.0, '
    'with copyright held by the authors listed in NOTICE; the plugins and upstream components mentioned in this '
    'documentation remain under their respective original licenses.</footer>'
)

COPYRIGHT_HTML = {"cn": COPYRIGHT_HTML_CN, "en": COPYRIGHT_HTML_EN}


def _inject_lang_switch(html: str, lang, relpath: str) -> str:
    if "class=\"lang-switch\"" in html:
        return html
    prefix, label = lang["topic_switch"]
    link = (f'<div class="lang-switch" style="margin:16px 0 8px;font-size:13px;">'
            f'<a href="{prefix}{relpath}">{label}</a></div>')
    return html.replace("</body>", link + "\n</body>")


def write_dist(lang, sections, all_topics):
    content, dist = lang["content"], lang["dist"]
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)

    # 1. 复制内容页（保持 content/<sec>/<page>.html 结构），并注入版权页脚
    for src_dir, dirs, files in os.walk(content):
        rel = os.path.relpath(src_dir, content)
        dest = dist / "content" if rel == "." else dist / "content" / rel
        dest.mkdir(parents=True, exist_ok=True)
        for fn in files:
            data = (Path(src_dir) / fn).read_text(encoding="utf-8")
            if fn.endswith(".html"):
                relpath = fn if rel == "." else f"{rel.replace(os.sep, '/')}/{fn}"
                data = _inject_lang_switch(data, lang, relpath)
                data = _inject_copyright(data, lang["code"])
            (dest / fn).write_text(data, encoding="utf-8")
    # 2. 资源
    shutil.copytree(ROOT / "assets", dist / "assets")

    # 3. TOC 数据（嵌套树）+ 扁平索引 + 搜索数据
    tree = []
    by_id = {}
    for t in all_topics:
        by_id[(t["section"], t["id"])] = {**t, "children": []}
    for t in all_topics:
        node = by_id[(t["section"], t["id"])]
        parent = t.get("parent")
        if parent and (t["section"], parent) in by_id:
            by_id[(t["section"], parent)]["children"].append(node)
        else:
            tree.append(node)

    def slim(n):
        return {
            "t": n["title"],
            "f": "content/" + n["relpath"],
            "c": [slim(c) for c in n["children"]],
        }

    toc_js = "var TOC = " + json.dumps(
        [{"t": s["title"], "f": None, "c": [slim(x) for x in s["topics"] and
          [by_id[(s['dir'], t['id'])] for t in s['topics'] if not t.get('parent')]]}
         for s in sections], ensure_ascii=False, indent=1) + ";"

    index_entries = sorted(
        ({"k": kw, "t": t["title"], "f": "content/" + t["relpath"]}
         for t in all_topics for kw in t.get("keywords", [])),
        key=lambda e: e["k"].lower())
    index_js = "var INDEX = " + json.dumps(index_entries, ensure_ascii=False) + ";"

    pages_js = "var PAGES = " + json.dumps(
        [{"t": t["title"], "f": "content/" + t["relpath"],
          "txt": extract_text((content / t["relpath"]).read_text(encoding="utf-8"))}
         for t in all_topics], ensure_ascii=False) + ";"

    (dist / "toc_data.js").write_text(toc_js, encoding="utf-8")
    (dist / "index_data.js").write_text(index_js, encoding="utf-8")
    (dist / "search_data.js").write_text(pages_js, encoding="utf-8")

    # 4. 查看器框架页
    viewer = viewer_html(lang)
    (dist / "default.html").write_text(viewer, encoding="utf-8")
    # GitHub Pages 等静态托管以 index.html 为入口
    (dist / "index.html").write_text(viewer, encoding="utf-8")

    print(f"[ok] dist({lang['code']}) 已生成：{len(all_topics)} 个主题，"
          f"{sum(len(s['topics']) for s in sections)} 条目")


# ---------------------------------------------------------------- CHM 工程

def _write_chm_text(path, text):
    """hhc.exe 按系统 ANSI 代码页解析 .hhp/.hhc/.hhk，中文标题需写 ANSI（cp936）才不乱码。"""
    try:
        path.write_bytes(text.encode("mbcs"))
    except (UnicodeEncodeError, LookupError):   # 非 CJK 系统回退 UTF-8
        path.write_text(text, encoding="utf-8")


def _hhc_node(title, file=None, children=None):
    out = ["<LI> <OBJECT type=\"text/site properties\">",
           "<param name=\"ImageNumber\" value=\"11\">", "</OBJECT>"]
    out.append(f"<LI> <OBJECT type=\"text/sitemap\">"
               f"<param name=\"Name\" value=\"{escape(title)}\">")
    if file:
        out.append(f"<param name=\"Local\" value=\"{file}\">")
    out.append("</OBJECT>")
    for c in children or []:
        out.append("<UL>")
        out.extend(_hhc_node(**c) if isinstance(c, dict) else c)
        out.append("</UL>")
    return out


def write_chm_project(lang, sections, all_topics):
    chm = lang["chm"]
    dist_rel = lang["chm_dist_rel"]
    if chm.exists():
        shutil.rmtree(chm)
    chm.mkdir(parents=True)

    # .hhc 目录文件
    lines = ["<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML//EN\">",
             "<HTML>", "<BODY>", "<OBJECT type=\"text/site properties\">",
             "<param name=\"Window Styles\" value=\"0x800025\">",
             "<param name=\"Explain\" value=\"Menuhelp\">", "</OBJECT>", "<UL>"]
    def _topic_node(t, by_parent):
        kids = [_topic_node(c, by_parent) for c in by_parent.get(t["id"], [])]
        return {"title": t["title"], "file": dist_rel + "/content/" + t["relpath"],
                "children": kids}

    for s in sections:
        by_parent = {}
        for t in s["topics"]:
            by_parent.setdefault(t.get("parent"), []).append(t)
        tops = by_parent.get(None, [])
        if not tops:
            tops = s["topics"][:1]          # 兜底：无显式 overview 时挂第一个
        # 章节节点指向其首个主题页，子树完整收录全部层级
        chapter = {"title": s["title"], "file": dist_rel + "/content/" + tops[0]["relpath"],
                   "children": [_topic_node(t, by_parent) for t in tops]}
        lines.append("<UL>")
        lines.extend(_hhc_node(**chapter))
        lines.append("</UL>")
    lines += ["</UL>", "</BODY>", "</HTML>"]
    _write_chm_text(chm / "help.hhc", "\n".join(lines))

    # .hhk 关键字索引
    kl = ["<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML//EN\">",
          "<HTML>", "<BODY>", "<UL>"]
    for e in sorted(({(e["k"]): e for t in all_topics for e in
                      ({"k": kw, "f": dist_rel + "/content/" + t["relpath"]} for kw in t.get("keywords", []))}
                     ).values(), key=lambda x: x["k"].lower()):
        kl.append(f"<LI> <OBJECT type=\"text/sitemap\">"
                  f"<param name=\"Name\" value=\"{escape(e['k'])}\">"
                  f"<param name=\"Local\" value=\"{e['f']}\"></OBJECT>")
    kl += ["</UL>", "</BODY>", "</HTML>"]
    _write_chm_text(chm / "help.hhk", "\n".join(kl))

    # .hhp 工程文件
    topics = "\n".join(dist_rel + "/content/" + t["relpath"] for t in all_topics)
    css = dist_rel + "/assets/help.css"
    hhp = f"""[OPTIONS]
Compatibility=1.1 or later
Compiled file=..\\..\\{lang['chm_compiled']}
Contents file=help.hhc
Index file=help.hhk
Default Topic={dist_rel.replace('/', '\\')}\\content\\{sections[0]['topics'][0]['relpath'].replace('/', '\\') if sections and sections[0]['topics'] else 'index.html'}
Title={lang['help_title']}
Language={lang['chm_language']}
Default Font={lang['chm_font']}

[FILES]
{topics}
{css}
"""
    _write_chm_text(chm / "help.hhp", hhp)
    print(f"[ok] {chm.relative_to(ROOT)}/ 已生成 hhc/hhk/hhp（用 HTML Help Workshop 的 hhc.exe 编译为 .chm）")


VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<link rel="stylesheet" href="assets/help.css">
<style>
  html,body,#viewer{height:100%;}
</style>
</head>
<body>
<div id="viewer">
  <div class="toolbar">
    <button id="btn-toc" title="显示/隐藏导航窗格">▤ 导航</button>
    <span class="sep"></span>
    <button id="btn-back" title="后退">&lt;&lt; 后退</button>
    <button id="btn-fwd" title="前进">前进 &gt;&gt;</button>
    <button id="btn-home" title="回到首页">⌂ 首页</button>
    <button id="btn-print" title="打印当前主题">🖨 打印</button>
    <span class="spacer"></span>
    <span class="title">__TITLE__</span>
    <span class="sep"></span>
    <span class="copyright">© 2026 layola13</span>
  </div>
  <div class="main">
    <div class="navpane" id="navpane">
      <div class="tabs">
        <button class="tab active" data-tab="toc">目录</button>
        <button class="tab" data-tab="idx">索引</button>
        <button class="tab" data-tab="search">搜索</button>
      </div>

      <div class="tabpage" id="tab-toc"><div class="tree" id="tree"></div></div>

      <div class="tabpage hidden" id="tab-idx">
        <input id="index-input" placeholder="键入关键字查找…" autocomplete="off">
        <ul class="index-list" id="index-list"></ul>
      </div>

      <div class="tabpage hidden" id="tab-search">
        <input id="search-input" placeholder="输入要查找的文字…" autocomplete="off">
        <button class="tab" style="flex:none;margin-top:6px;padding:3px 12px;" id="search-go">列出主题</button>
        <div id="search-results"></div>
      </div>
    </div>

    <iframe class="contentpane" name="content" id="contentframe"></iframe>
  </div>
  <div class="statusbar" id="statusbar">就绪</div>
</div>

<script src="toc_data.js"></script>
<script src="index_data.js"></script>
<script src="search_data.js"></script>
<script>
(function(){
  var frame = document.getElementById('contentframe');
  var statusbar = document.getElementById('statusbar');
  var historyStack = [], histPos = -1;

  function show(url, pushHist){
    frame.src = url;
    if(pushHist !== false){
      historyStack = historyStack.slice(0, histPos+1);
      historyStack.push(url); histPos = historyStack.length-1;
    }
    updateBtns();
    document.querySelectorAll('#tree a').forEach(function(a){
      a.classList.toggle('current', a.getAttribute('href') === url);
    });
  }
  function updateBtns(){
    document.getElementById('btn-back').disabled = histPos <= 0;
    document.getElementById('btn-fwd').disabled = histPos >= historyStack.length-1;
  }
  window.addEventListener('message', function(e){
    if(e.data && e.data.type==='nav') show(e.data.url);
    else if(e.data && e.data.type==='status') statusbar.textContent = e.data.text || '就绪';
  });
  document.getElementById('btn-back').onclick = function(){ if(histPos>0){histPos--; show(historyStack[histPos], false);} };
  document.getElementById('btn-fwd').onclick = function(){ if(histPos<historyStack.length-1){histPos++; show(historyStack[histPos], false);} };
  document.getElementById('btn-home').onclick = function(){ show(firstPage()); };
  document.getElementById('btn-print').onclick = function(){ frame.contentWindow.print(); };
  document.getElementById('btn-toc').onclick = function(){
    var np = document.getElementById('navpane');
    np.style.display = np.style.display === 'none' ? '' : 'none';
  };

  // ---- 目录树 ----
  function firstPage(){
    var a = document.querySelector('#tree a');
    return a ? a.getAttribute('href') : '';
  }
  function buildTree(nodes, ul){
    nodes.forEach(function(n){
      var li = document.createElement('li');
      var hasKids = n.c && n.c.length;
      var row = document.createElement('div');
      row.className = 'node';
      var tog = document.createElement('span');
      tog.className = 'toggle';
      tog.textContent = hasKids ? '+' : ' ';
      row.appendChild(tog);
      if(n.f){
        var a = document.createElement('a');
        a.href = n.f; a.textContent = n.t; a.target = 'content';
        a.onclick = function(ev){ ev.preventDefault(); show(n.f); };
        row.appendChild(a);
      } else {
        var sp = document.createElement('span'); sp.textContent = n.t; row.appendChild(sp);
      }
      li.appendChild(row);
      var sub = null;
      if(hasKids){
        sub = document.createElement('ul'); sub.style.display='none';
        buildTree(n.c, sub); li.appendChild(sub);
        tog.onclick = function(){
          var open = sub.style.display === 'none';
          sub.style.display = open ? '' : 'none';
          tog.textContent = open ? '-' : '+';
        };
      }
      ul.appendChild(li);
    });
  }
  var treeRoot = document.getElementById('tree');
  var ul = document.createElement('ul'); treeRoot.appendChild(ul); buildTree(TOC, ul);

  // ---- 索引 ----
  var idxInput = document.getElementById('index-input'), idxList = document.getElementById('index-list');
  function renderIndex(prefix){
    idxList.innerHTML = '';
    var kw = prefix.toLowerCase();
    INDEX.forEach(function(e){
      if(kw && e.k.toLowerCase().indexOf(kw) !== 0) return;
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = e.f; a.textContent = e.k + ' — ' + e.t;
      a.onclick = function(ev){ ev.preventDefault(); switchTab('toc'); show(e.f); };
      li.appendChild(a); idxList.appendChild(li);
    });
  }
  idxInput.addEventListener('input', function(){ renderIndex(idxInput.value.trim()); });
  renderIndex('');

  // ---- 搜索 ----
  function switchTab(name){
    document.querySelectorAll('.tabs .tab').forEach(function(b){
      b.classList.toggle('active', b.dataset.tab === name);
    });
    ['toc','idx','search'].forEach(function(t){
      document.getElementById('tab-'+t).classList.toggle('hidden', t !== name);
    });
  }
  document.querySelectorAll('.tabs .tab').forEach(function(b){
    b.onclick = function(){ switchTab(b.dataset.tab); };
  });

  function doSearch(){
    var q = document.getElementById('search-input').value.trim().toLowerCase();
    var box = document.getElementById('search-results');
    box.innerHTML = '';
    if(!q) return;
    var hits = [];
    PAGES.forEach(function(p){
      var lower = p.txt.toLowerCase(), pos = lower.indexOf(q), count = 0, i = pos;
      while(i !== -1){ count++; i = lower.indexOf(q, i + q.length); }
      if(count) hits.push({p:p, count:count, pos:pos});
    });
    hits.sort(function(a,b){ return b.count - a.count; });
    hits.forEach(function(h){
      var start = Math.max(0, h.pos - 40);
      var snip = h.p.txt.substr(start, 120).replace(new RegExp(q,'gi'), function(m){ return '<mark>'+m+'</mark>'; });
      var div = document.createElement('div'); div.className = 'search-hit';
      var a = document.createElement('a'); a.href = h.p.f; a.textContent = h.p.t;
      a.onclick = function(ev){ ev.preventDefault(); switchTab('toc'); show(h.p.f); };
      div.appendChild(a);
      var s = document.createElement('div'); s.className='snippet';
      s.innerHTML = '…'+snip+'…（'+h.count+' 处匹配）';
      div.appendChild(s);
      box.appendChild(div);
    });
    if(!hits.length) box.innerHTML = '<p style="color:#888">未找到包含 “'+q+'” 的主题。</p>';
    statusbar.textContent = '找到 '+hits.length+' 个主题';
  }
  document.getElementById('search-go').onclick = doSearch;
  document.getElementById('search-input').addEventListener('keydown', function(e){ if(e.key==='Enter') doSearch(); });

  // 初始页
  var init = firstPage();
  if(init) show(init);
})();
</script>
</body>
</html>
"""


# 英文版查看器：VIEWER_HTML 为中文原版，英文版按下列对照替换界面文案。
VIEWER_EN_REPLACEMENTS = [
    ('<html lang="zh-CN">', '<html lang="en">'),
    ('title="显示/隐藏导航窗格">▤ 导航<', 'title="Show/hide navigation pane">▤ Navigation<'),
    ('title="后退">&lt;&lt; 后退<', 'title="Back">&lt;&lt; Back<'),
    ('title="前进">前进 &gt;&gt;<', 'title="Forward">Forward &gt;&gt;<'),
    ('title="回到首页">⌂ 首页<', 'title="Home">⌂ Home<'),
    ('title="打印当前主题">🖨 打印<', 'title="Print current topic">🖨 Print<'),
    ('data-tab="toc">目录<', 'data-tab="toc">Contents<'),
    ('data-tab="idx">索引<', 'data-tab="idx">Index<'),
    ('data-tab="search">搜索<', 'data-tab="search">Search<'),
    ('placeholder="键入关键字查找…"', 'placeholder="Type a keyword to search…"'),
    ('placeholder="输入要查找的文字…"', 'placeholder="Type the text to find…"'),
    ('id="search-go">列出主题<', 'id="search-go">List topics<'),
    ('<div class="statusbar" id="statusbar">就绪</div>', '<div class="statusbar" id="statusbar">Ready</div>'),
    ("e.data.text || '就绪'", "e.data.text || 'Ready'"),
    ("'…'+snip+'…（'+h.count+' 处匹配）'", "'…'+snip+'… ('+h.count+' matches)'"),
    ("未找到包含 “'+q+'” 的主题。", "No topics contain \"'+q+'\"."),
    ("'找到 '+hits.length+' 个主题'", "'Found '+hits.length+' topic(s)'"),
    ('// ---- 目录树 ----', '// ---- TOC tree ----'),
    ('// ---- 索引 ----', '// ---- Index ----'),
    ('// ---- 搜索 ----', '// ---- Search ----'),
    ('// 初始页', '// Initial page'),
]


def viewer_html(lang):
    """按语言生成查看器框架页，并注入工具栏的语言切换链接。"""
    html = VIEWER_HTML.replace("__TITLE__", lang["help_title"])
    if lang["code"] == "en":
        for cn, en in VIEWER_EN_REPLACEMENTS:
            html = html.replace(cn, en)
    href, label = lang["viewer_switch"]
    html = html.replace(
        '<span class="copyright">© 2026 layola13</span>',
        '<span class="copyright">© 2026 layola13</span>'
        f'<span class="sep"></span><a href="{href}" style="color:#fff;">{label}</a>')
    return html


def main():
    serve = "--serve" in sys.argv
    for lang in LANGS:
        sections, all_topics = load_manifests(lang)
        if not all_topics:
            print(f"没有找到任何主题（{lang['code']}）。请先在对应语言源的 <章节>/_manifest.json 中登记主题。")
            return 1

        problems = check_links(lang, all_topics)
        for p in problems:
            print(f"[warn] 死链({lang['code']}): {p}")

        write_dist(lang, sections, all_topics)
        write_chm_project(lang, sections, all_topics)

    if serve:
        import http.server
        handler = http.server.SimpleHTTPRequestHandler
        with http.server.HTTPServer(("127.0.0.1", 8765), handler) as httpd:
            import os
            os.chdir(LANGS[0]["dist"])
            print("预览地址: http://127.0.0.1:8765/default.html  (Ctrl+C 退出)")
            httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
