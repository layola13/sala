# -*- coding: utf-8 -*-
"""从 sci/sa_std 真实契约文件生成「标准库 API 总索引」页面。

扫描 sa_std 下全部 .sai/.sal/.sa，抽取：
  @extern   → 函数契约（含紧邻上方 // 注释作为说明）
  #def      → 布局常量
  [MACRO]   → 汇编宏
输出 content/06_stdlib/ 下 4 个页面：
  15_api_index.html    统计 + 模块地图
  16_api_externs.html  全部 extern 签名
  17_api_macros.html   全部宏名
  18_api_layout.html   全部布局常量

用法：python tools/gen_api_index.py
"""
import html
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # sahelp/
SA_STD = ROOT.parent / "sci" / "sa_std"
OUT = ROOT / "content" / "06_stdlib"

RE_EXTERN = re.compile(r"^@extern\s+(\w+)\s*\((.*)\)\s*->\s*(\S+)\s*$")
RE_DEF = re.compile(r"^#def\s+(\w+)\s*=\s*(.*?)\s*$")
RE_MACRO = re.compile(r"^\[MACRO\]\s+(\S+)(?:\s+(.*?))?\s*$")

CSS_HREF = "../../assets/help.css"


def scan():
    """返回 {module_path: {"sai": [...], "sal": [...], "sa": [...]}}，module 为相对 sa_std 的路径(去扩展名)。"""
    mods = OrderedDict()
    for path in sorted(SA_STD.rglob("*")):
        if path.suffix not in (".sai", ".sal", ".sa") or not path.is_file():
            continue
        rel = path.relative_to(SA_STD).as_posix()
        module = rel.rsplit(".", 1)[0]
        mod = mods.setdefault(module, {"sai": [], "sal": [], "sa": [], "files": set()})
        mod["files"].add(rel)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".sai":
            pending_comments = []
            for line in text.splitlines():
                s = line.strip()
                m = RE_EXTERN.match(s)
                if m:
                    mod["sai"].append({"name": m.group(1), "params": m.group(2),
                                       "ret": m.group(3), "doc": " ".join(pending_comments)})
                    pending_comments = []
                elif s.startswith("//"):
                    pending_comments.append(s.lstrip("/").strip())
                elif s:
                    pending_comments = []
        elif path.suffix == ".sal":
            for line in text.splitlines():
                m = RE_DEF.match(line.strip())
                if m:
                    mod["sal"].append((m.group(1), m.group(2)))
        else:  # .sa
            for line in text.splitlines():
                m = RE_MACRO.match(line.strip())
                if m:
                    mod["sa"].append((m.group(1), (m.group(2) or "").strip()))
    return mods


def head(title, crumb):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="{CSS_HREF}">
</head>
<body class="topic">
<div class="topic-header">{crumb}</div>
<h1>{title}</h1>

"""


def foot(nav):
    nav_html = "<p>" + " | ".join(
        f'<a href="{f}">{t}</a>' for f, t in nav) + "</p>"
    return f"""<h2>本节导航</h2>
{nav_html}
</body>
</html>
"""


NAV = [("15_api_index.html", "API 总索引"),
       ("16_api_externs.html", "extern 函数契约"),
       ("17_api_macros.html", "汇编宏清单"),
       ("18_api_layout.html", "布局常量清单")]


def family(mod):
    return mod.split("/")[0] if "/" in mod else "(顶层)"


def group_by_family(items_with_module):
    fams = OrderedDict()
    for mod, item in items_with_module:
        fams.setdefault(family(mod), []).append((mod, item))
    return fams


def write_externs(mods, stats):
    rows = []
    for mod, data in mods.items():
        if not data["sai"]:
            continue
        rows.append(f'<h3><code>{html.escape(mod)}.sai</code>（{len(data["sai"])} 个）</h3>\n<table>')
        for e in data["sai"]:
            sig = f"{e['name']}({e['params']}) -> {e['ret']}"
            doc = html.escape(e["doc"]) if e["doc"] else ""
            rows.append(f"<tr><td><code>{html.escape(sig)}</code></td><td>{doc}</td></tr>")
        rows.append("</table>")
    body = "\n".join(rows) if rows else "<p>无 extern 契约。</p>"
    page = (head("extern 函数契约全表", "标准库 &gt; API 总索引 &gt; extern 函数契约")
            + f"<p>共 <b>{stats['externs']}</b> 个 <code>@extern</code> 契约，按模块（即导入路径去掉 "
              "<code>sa_std/</code> 前缀与扩展名）分组。说明列取自契约文件中紧邻的注释。</p>\n"
            + body + "\n" + foot(NAV))
    (OUT / "16_api_externs.html").write_text(page, encoding="utf-8")


def write_macros(mods, stats):
    parts = []
    for mod, data in mods.items():
        if not data["sa"]:
            continue
        names = ", ".join(html.escape(n) for n, _ in data["sa"])
        parts.append(f'<h3><code>{html.escape(mod)}.sa</code>（{len(data["sa"])} 个）</h3>\n'
                     f'<p>{names}</p>')
    body = "\n".join(parts) if parts else "<p>无宏定义。</p>"
    page = (head("汇编宏清单", "标准库 &gt; API 总索引 &gt; 汇编宏清单")
            + f"<p>共 <b>{stats['macros']}</b> 个 <code>[MACRO]</code> 宏，按模块（实现文件）分组。"
              "宏经 <code>@import</code> 对应 <code>.sa</code> 文件后可直接调用；"
              "各宏的参数形状与实现见 <code>sci/sa_std/</code> 下同名源文件。</p>\n"
            + body + "\n" + foot(NAV))
    (OUT / "17_api_macros.html").write_text(page, encoding="utf-8")


def write_layout(mods, stats):
    parts = []
    for mod, data in mods.items():
        if not data["sal"]:
            continue
        items = ", ".join(f'<code title="{html.escape(v)}">{html.escape(k)}</code>'
                          for k, v in data["sal"])
        parts.append(f'<h3><code>{html.escape(mod)}.sal</code>（{len(data["sal"])} 个）</h3>\n'
                     f'<p class="api-names">{items}</p>')
    body = "\n".join(parts) if parts else "<p>无布局常量。</p>"
    page = (head("布局常量清单", "标准库 &gt; API 总索引 &gt; 布局常量清单")
            + f"<p>共 <b>{stats['defs']}</b> 个 <code>#def</code> 布局常量，按模块分组；"
              "悬停可看值。这些常量描述聚合类型的字段偏移等布局信息，供手写 SA 访问容器字段。</p>\n"
            + body + "\n" + foot(NAV))
    (OUT / "18_api_layout.html").write_text(page, encoding="utf-8")


def write_index(mods, stats):
    rows = ["<table><tr><th>模块（@import 路径去 sa_std/ 与扩展名）</th><th>文件类型</th>"
            "<th>extern</th><th>宏</th><th>布局常量</th></tr>"]
    for mod, data in mods.items():
        kinds = []
        if data["sai"]: kinds.append(".sai")
        if data["sal"]: kinds.append(".sal")
        if data["sa"]:  kinds.append(".sa")
        rows.append(f"<tr><td><code>{html.escape(mod)}</code></td>"
                    f"<td>{' + '.join(kinds)}</td>"
                    f"<td>{len(data['sai']) or ''}</td>"
                    f"<td>{len(data['sa']) or ''}</td>"
                    f"<td>{len(data['sal']) or ''}</td></tr>")
    rows.append("</table>")
    page = (head("API 总索引", "标准库 &gt; API 总索引")
            + f"""<p>本节是 <code>sa_std</code> 覆盖 API 的<b>完整索引</b>，由构建脚本直接扫描
<code>sci/sa_std/</code> 下全部 <b>{stats['files']}</b> 个契约/实现文件生成，与源码逐字一致：</p>
<ul>
<li><b>{stats['externs']}</b> 个 <code>@extern</code> 函数契约（宿主 Zig 运行时提供实现）→ 见 <a href="16_api_externs.html">extern 函数契约</a></li>
<li><b>{stats['macros']}</b> 个汇编宏（<code>.sa</code> 实现）→ 见 <a href="17_api_macros.html">汇编宏清单</a></li>
<li><b>{stats['defs']}</b> 个 <code>#def</code> 布局常量（<code>.sal</code>）→ 见 <a href="18_api_layout.html">布局常量清单</a></li>
</ul>
<p>怎么用这些契约见<a href="13_usage_guide.html">「如何使用 sa_std」</a>；各域的讲解页见本章 02–12 页。
下表是模块地图（模块数：<b>{len(mods)}</b>）：</p>
"""
            + "\n".join(rows) + "\n" + foot(NAV))
    (OUT / "15_api_index.html").write_text(page, encoding="utf-8")


def main():
    mods = scan()
    stats = {
        "files": sum(len(m["files"]) for m in mods.values()),
        "externs": sum(len(m["sai"]) for m in mods.values()),
        "macros": sum(len(m["sa"]) for m in mods.values()),
        "defs": sum(len(m["sal"]) for m in mods.values()),
    }
    write_index(mods, stats)
    write_externs(mods, stats)
    write_macros(mods, stats)
    write_layout(mods, stats)
    print(f"[ok] sa_std: {stats['files']} 文件 / {len(mods)} 模块 / "
          f"{stats['externs']} extern / {stats['macros']} 宏 / {stats['defs']} 布局常量")


if __name__ == "__main__":
    main()
