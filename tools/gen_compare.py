# -*- coding: utf-8 -*-
"""把 rust-vs-sa-sla-详细对比.md 渲染成帮助主题页 09_rust_compare/09_full_report.html。

只使用 Python 标准库，避免引入外部依赖；转换规则贴近现有 8 页风格：
- 顶级标题 <h1>，## -> <h2>，### -> <h3>，#### -> <h3>（与现有页最大深度保持一致）
- 表格直接翻译 GFM 表格；行内代码 ``code``；代码围栏 ``` 保留为 <pre><code>
- 其它段落以 <p> 包裹；项目符号/有序列表维持嵌套；引用转 <blockquote>
- 链接走相对路径（外部链接保留绝对，并加 target=_blank）
- 文件以 UTF-8 写出（无 BOM）
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "rust-vs-sa-sla-详细对比.md"
DEST = ROOT / "content" / "09_rust_compare" / "09_full_report.html"

TITLE = "Rust vs SA / SLA 详细对比（综合报告）"

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def inline(text: str) -> str:
    text = IMG.sub("", text)
    text = LINK.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>'
        if m.group(2).startswith(("http://", "https://", "mailto:"))
        else f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    text = INLINE_CODE.sub(r"<code>\1</code>", text)
    text = BOLD.sub(r"<b>\1</b>", text)
    text = ITALIC.sub(r"<i>\1</i>", text)
    return text


def split_row(line: str) -> list[str]:
    s = line.strip()
    if not s.startswith("|"):
        return []
    body = s.strip("|")
    return [c.strip() for c in body.split("|")]


def is_separator(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def render_table(block: list[str]) -> str:
    rows = [split_row(l) for l in block if split_row(l)]
    if not rows:
        return ""
    header = rows[0]
    body_rows: list[list[str]] = []
    for r in rows[1:]:
        if is_separator(r):
            continue
        body_rows.append(r)
    out = ["<table>"]
    out.append("<tr>" + "".join(f"<th>{inline(h)}</th>" for h in header) +</tr>")
    for r in body_rows:
        if len(r) < len(header):
            r = r + [""] * (len(header) - len(r))
        cells = r[: len(header)]
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) +</tr>")
    out.append("</table>")
    return "\n".join(out)


def is_list_item(line: str) -> tuple[int, bool, str] | None:
    m = re.match(r"^( *)([-*]|\d+\.)\s+(.*)$", line)
    if not m:
        return None
    depth = len(m.group(1)) // 2
    marker = m.group(2)
    body = m.group(3)
    ordered = marker.endswith(".")
    return depth, ordered, body


def is_horizontal_rule(line: str) -> bool:
    return re.fullmatch(r"\s*-{3,}\s*", line) is not None


def render(md: str) -> str:
    lines = md.splitlines()
    html: list[str] = []
    i = 0
    n = len(lines)
    list_stack: list[tuple[bool, int]] = []  # (ordered, depth)

    def open_list(tag: str, depth: int) -> None:
        html.append("<" + tag + ">")
        list_stack.append((tag == "ol", depth))

    def close_lists_to(target_depth: int) -> None:
        while list_stack and list_stack[-1][1] > target_depth:
            tag = "ol" if list_stack[-1][0] else "ul"
            html.append("</" + tag + ">")
            list_stack.pop()

    def close_all_lists() -> None:
        while list_stack:
            tag = "ol" if list_stack[-1][0] else "ul"
            html.append("</" + tag + ">")
            list_stack.pop()

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        if not stripped:
            close_all_lists()
            i += 1
            continue

        # 代码围栏
        if stripped.startswith("```"):
            close_all_lists()
            lang = stripped[3:].strip()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过闭合围栏
            cls = f' class="language-{lang}"' if lang else ""
            html.append(f'<pre><code{cls}>' + "\n".join(buf)</code</pre>")
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_all_lists()
            level = min(len(m.group(1)), 3)
            html.append("<h" + str(level) + ">" + inline(m.group(2)) +</h" + str(level) + ">")
            i += 1
            continue

        # 水平线
        if is_horizontal_rule(stripped):
            close_all_lists()
            html.append("<hr>")
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < n and is_separator(split_row(lines[i + 1])):
            close_all_lists()
            block: list[str] = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            html.append(render_table(block))
            continue

        # 引用
        if stripped.startswith(">"):
            close_all_lists()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            html.append("<blockquote>" + " ".join(inline(b) for b in buf) +</blockquote>")
            continue

        # 列表
        li = is_list_item(stripped)
        if li:
            depth, ordered, body = li
            tag = "ol" if ordered else "ul"
            # 关闭更深嵌套
            close_lists_to(depth)
            # 类型不匹配或层级跳跃：关掉并重建
            if list_stack and (list_stack[-1][1] != depth or list_stack[-1][0] != ordered):
                close_all_lists()
            if not list_stack or list_stack[-1][1] != depth:
                open_list(tag, depth)
            elif list_stack[-1][1] == depth and list_stack[-1][0] != ordered:
                close_all_lists()
                open_list(tag, depth)
            html.append("  " * (depth + 1) + "<li>" + inline(body) +</li>")
            i += 1
            continue

        # 段落
        close_all_lists()
        buf = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if not nxt:
                break
            if (
                nxt.startswith("```")
                or nxt.startswith("#")
                or nxt.startswith("|")
                or nxt.startswith(">")
                or is_list_item(nxt)
                or is_horizontal_rule(nxt)
            ):
                break
            buf.append(nxt)
            i += 1
        html.append("<p>" + inline(" ".join(buf)) +</p>")

    close_all_lists()
    return "\n".join(html)


def build_page(body_html: str, source_note: str) -> str:
    related = "\n".join(
        f'<li><a href="{fn}.html">{title</a</li>'
        for fn, title in [
            ("01_positioning", "定位与设计哲学：SLA 不是 Rust 克隆"),
            ("02_syntax_matrix", "语法对照实测矩阵"),
            ("03_ownership", "所有权与借用：Referee 对比 borrow checker"),
            ("04_macros", "宏与元编程对比"),
            ("05_stdlib_errors_async", "标准库、错误处理与 async 对照"),
            ("06_surface_compat", "Rust 表层兼容性：哪些代码能原样解析"),
            ("07_rosetta_bc2sa", "rosetta 对照集与 bc2sa 桥接生态"),
            ("08_migration", "从 Rust 迁移到 SLA：改写清单与场景选择"),
        ]
    )
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>{TITLE</title>\n"
        "<link rel=\"stylesheet\" href=\"../../assets/help.css\">\n"
       </head>\n"
        "<body class=\"topic\">\n"
        "<div class=\"topic-header\">与 Rust 对比 > 详细对比综合报告</div>\n"
        f"<h1>{TITLE</h1>\n"
        f"<div class=\"note\"><span class=\"label\">来源</span>{source_note</div>\n"
        + body_html + "\n"
        "<h2>关联阅读</h2>\n"
        "<ul>\n" + related + "\n</ul>\n"
        "<p>本报告侧重<b>横向广度</b>（16 节覆盖定位、IR、性能、工具链），
        "前 8 页是<b>纵深切片</b>（每个主题独立深挖）。如对某节需要更深入示例，请优先看对应专页</p>\n"
       </body>\n"
       </html>\n"
    )


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    body = render(md)
    note = (
        "本主题页由 <code>tools/gen_compare.py</code> 直接渲染上级目录 
        "<code>rust-vs-sa-sla-详细对比.md</code> 生成（2026-09-01 同步）。
        "文中给出的百分比、倍率、打分均为报告内口径；如与官方 FAQ / 
        "<code>rust_vs_sla_final_cn.md</code> v0.2 快照有出入，请以官方为准。"
    )
    page = build_page(body, note)
    DEST.write_text(page, encoding="utf-8")
    print(f"wrote {DEST.relative_to(ROOT)}  ({len(page):,} chars)")


if __name__ == "__main__":
    main()
