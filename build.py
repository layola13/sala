# -*- coding: utf-8 -*-
"""sahelp 构建脚本。

扫描 content/<section>/_manifest.json，生成：
  dist/                     — CHM 风格 HTML 帮助查看器（default.html + 主题页）
  build/chm/help.hhc|.hhk|.hhp — HTML Help Workshop 工程文件（可用 hhc.exe 编译为 .chm）

用法：
  python build.py            # 构建
  python build.py --serve    # 构建后启动本地 HTTP 服务预览
"""
import json
import os
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
DIST = ROOT / "dist"
CHM = ROOT / "build" / "chm"

HELP_TITLE = "SA / SLA 帮助文档"

# 章节顺序与标题；dir 必须与 content/ 下目录名一致。
SECTIONS = [
    {"dir": "01_overview",   "title": "入门指南"},
    {"dir": "02_sla_lang",   "title": "SLA 语言参考"},
    {"dir": "09_rust_compare", "title": "与 Rust 对比"},
    {"dir": "03_sa_asm",     "title": "SA 汇编与 SAB"},
    {"dir": "04_cli",        "title": "命令行参考"},
    {"dir": "05_plugins",    "title": "插件参考"},
    {"dir": "10_db",         "title": "db 数据库插件"},
    {"dir": "11_ecs",        "title": "ECS 开发（sla_ecs）"},
    {"dir": "12_vm",         "title": "vm 虚拟机"},
    {"dir": "06_stdlib",     "title": "标准库"},
    {"dir": "07_ui",         "title": "SAX / MUI 界面开发"},
    {"dir": "08_faq",        "title": "FAQ 与故障排查"},
]


def load_manifests():
    """返回 (sections, all_topics)。topic 增加 section_title / relpath 字段。"""
    sections, all_topics = [], []
    for sec in SECTIONS:
        mfile = CONTENT / sec["dir"] / "_manifest.json"
        if not mfile.exists():
            print(f"[warn] 缺少清单: {mfile.relative_to(ROOT)}")
            continue
        data = json.loads(mfile.read_text(encoding="utf-8"))
        topics = []
        for t in data.get("topics", []):
            t = dict(t)
            t["section"] = sec["dir"]
            t["section_title"] = sec["title"]
            t["relpath"] = f"{sec['dir']}/{t['file']}"
            topics.append(t)
        sections.append({**sec, "topics": topics})
        all_topics.extend(topics)
    return sections, all_topics


def extract_text(html: str) -> str:
    """去掉 script/style/标签，留纯文本供搜索。"""
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt)


def check_links(all_topics):
    """检查主题页内相对链接是否指向存在的文件。"""
    problems = []
    for t in all_topics:
        page = CONTENT / t["relpath"]
        for m in re.finditer(r'href="([^"#]+?)(?:#[^"]*)?"', page.read_text(encoding="utf-8")):
            href = m.group(1)
            if re.match(r"^[a-z]+:", href):  # http:// mailto: 等
                continue
            target = (page.parent / href).resolve()
            if not target.exists():
                problems.append(f"{t['relpath']} -> {href} (不存在)")
    return problems


# ---------------------------------------------------------------- dist 输出

COPYRIGHT_HTML = (
    '<footer class="copyright">© 2026 layola13 · SA / SLA 帮助文档 · 转载请注明出处<br>'
    'SA 编译器（<a href="https://github.com/layola13/sci">sci</a>）为 Apache License 2.0 '
    '授权发布，版权归 NOTICE 所列作者所有；本文档提及的各插件与上游组件遵循各自原始许可证。</footer>'
)


def _inject_copyright(html: str) -> str:
    if "class=\"copyright\"" in html:
        return html
    return html.replace("</body>", COPYRIGHT_HTML + "\n</body>")


def write_dist(sections, all_topics):
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # 1. 复制内容页（保持 content/<sec>/<page>.html 结构），并注入版权页脚
    for src_dir, dirs, files in os.walk(CONTENT):
        rel = os.path.relpath(src_dir, CONTENT)
        dest = DIST / "content" if rel == "." else DIST / "content" / rel
        dest.mkdir(parents=True, exist_ok=True)
        for fn in files:
            data = (Path(src_dir) / fn).read_text(encoding="utf-8")
            if fn.endswith(".html"):
                data = _inject_copyright(data)
            (dest / fn).write_text(data, encoding="utf-8")
    # 2. 资源
    shutil.copytree(ROOT / "assets", DIST / "assets")

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
          "txt": extract_text((CONTENT / t["relpath"]).read_text(encoding="utf-8"))}
         for t in all_topics], ensure_ascii=False) + ";"

    (DIST / "toc_data.js").write_text(toc_js, encoding="utf-8")
    (DIST / "index_data.js").write_text(index_js, encoding="utf-8")
    (DIST / "search_data.js").write_text(pages_js, encoding="utf-8")

    # 4. 查看器框架页
    (DIST / "default.html").write_text(VIEWER_HTML.replace("__TITLE__", HELP_TITLE), encoding="utf-8")
    # GitHub Pages 等静态托管以 index.html 为入口
    (DIST / "index.html").write_text(VIEWER_HTML.replace("__TITLE__", HELP_TITLE), encoding="utf-8")

    print(f"[ok] dist/ 已生成：{len(all_topics)} 个主题，"
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


def write_chm_project(sections, all_topics):
    if CHM.exists():
        shutil.rmtree(CHM)
    CHM.mkdir(parents=True)

    # .hhc 目录文件
    lines = ["<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML//EN\">",
             "<HTML>", "<BODY>", "<OBJECT type=\"text/site properties\">",
             "<param name=\"Window Styles\" value=\"0x800025\">",
             "<param name=\"Explain\" value=\"Menuhelp\">", "</OBJECT>", "<UL>"]
    def _topic_node(t, by_parent):
        kids = [_topic_node(c, by_parent) for c in by_parent.get(t["id"], [])]
        return {"title": t["title"], "file": "../dist/content/" + t["relpath"],
                "children": kids}

    for s in sections:
        by_parent = {}
        for t in s["topics"]:
            by_parent.setdefault(t.get("parent"), []).append(t)
        tops = by_parent.get(None, [])
        if not tops:
            tops = s["topics"][:1]          # 兜底：无显式 overview 时挂第一个
        # 章节节点指向其首个主题页，子树完整收录全部层级
        chapter = {"title": s["title"], "file": "../dist/content/" + tops[0]["relpath"],
                   "children": [_topic_node(t, by_parent) for t in tops]}
        lines.append("<UL>")
        lines.extend(_hhc_node(**chapter))
        lines.append("</UL>")
    lines += ["</UL>", "</BODY>", "</HTML>"]
    _write_chm_text(CHM / "help.hhc", "\n".join(lines))

    # .hhk 关键字索引
    kl = ["<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML//EN\">",
          "<HTML>", "<BODY>", "<UL>"]
    for e in sorted(({(e["k"]): e for t in all_topics for e in
                      ({"k": kw, "f": "../dist/content/" + t["relpath"]} for kw in t.get("keywords", []))}
                     ).values(), key=lambda x: x["k"].lower()):
        kl.append(f"<LI> <OBJECT type=\"text/sitemap\">"
                  f"<param name=\"Name\" value=\"{escape(e['k'])}\">"
                  f"<param name=\"Local\" value=\"{e['f']}\"></OBJECT>")
    kl += ["</UL>", "</BODY>", "</HTML>"]
    _write_chm_text(CHM / "help.hhk", "\n".join(kl))

    # .hhp 工程文件
    topics = "\n".join("../dist/content/" + t["relpath"] for t in all_topics)
    css = "../dist/assets/help.css"
    hhp = f"""[OPTIONS]
Compatibility=1.1 or later
Compiled file=..\\..\\SA_SLDA_Help.chm
Contents file=help.hhc
Index file=help.hhk
Default Topic=..\\dist\\content\\{sections[0]['topics'][0]['relpath'].replace('/', '\\') if sections and sections[0]['topics'] else 'index.html'}
Title={HELP_TITLE}
Language=0x804 中文(中华人民共和国)
Default Font=微软雅黑,9,0

[FILES]
{topics}
{css}
"""
    _write_chm_text(CHM / "help.hhp", hhp)
    print("[ok] build/chm/ 已生成 hhc/hhk/hhp（用 HTML Help Workshop 的 hhc.exe 编译为 .chm）")


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


def main():
    serve = "--serve" in sys.argv
    sections, all_topics = load_manifests()
    if not all_topics:
        print("没有找到任何主题。请先在 content/<章节>/_manifest.json 中登记主题。")
        return 1

    problems = check_links(all_topics)
    for p in problems:
        print(f"[warn] 死链: {p}")

    write_dist(sections, all_topics)
    write_chm_project(sections, all_topics)

    if serve:
        import http.server
        os.chdir(DIST) if False else None
        handler = http.server.SimpleHTTPRequestHandler
        with http.server.HTTPServer(("127.0.0.1", 8765), handler) as httpd:
            import os
            os.chdir(DIST)
            print("预览地址: http://127.0.0.1:8765/default.html  (Ctrl+C 退出)")
            httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
