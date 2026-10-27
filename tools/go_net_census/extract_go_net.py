#!/usr/bin/env python3
"""Extract the exported API surface of Go net-family packages.

Usage: extract_go_net.py <go_src_dir> <out.json>
Reads golang/go source (sparse checkout of src/net + src/crypto/tls),
parses non-test .go files textually (comments/strings stripped first)
and emits one JSON row per exported item:
  {pkg, kind, name, receiver, file}
kind in: func, method, type, interface-method, interface-embed,
         field, const, var
Coverage boundary: declarations are taken at face value from source text;
generic instantiations, build-tag variants are unioned and deduped;
struct fields and interface method sets ARE included; doc-comment-only
API (e.g. //go:linkname surfaces) is not.
"""
import json
import os
import re
import sys

PKGS = {
    "net": "net",
    "net/netip": "net/netip",
    "net/url": "net/url",
    "net/http": "net/http",
    "net/http/httputil": "net/http/httputil",
    "net/http/httptest": "net/http/httptest",
    "net/http/cookiejar": "net/http/cookiejar",
    "crypto/tls": "crypto/tls",
    "net/smtp": "net/smtp",
    "net/mail": "net/mail",
    "net/rpc": "net/rpc",
    "net/rpc/jsonrpc": "net/rpc/jsonrpc",
    "net/textproto": "net/textproto",
}


def strip_noise(text):
    """Replace comments and string/char literals with spaces, keep newlines."""
    out = []
    i, n = 0, len(text)
    state = None  # None | 'line' | 'block' | 'str' | 'raw' | 'char'
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"; out.append("  "); i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; out.append("  "); i += 2; continue
            if c == '"':
                state = "str"; out.append(" "); i += 1; continue
            if c == "`":
                state = "raw"; out.append(" "); i += 1; continue
            if c == "'":
                state = "char"; out.append(" "); i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                state = None; out.append("\n")
            else:
                out.append(" ")
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = None; out.append("  "); i += 2; continue
            out.append("\n" if c == "\n" else " "); i += 1; continue
        if state == "raw":
            if c == "`":
                state = None
            out.append("\n" if c == "\n" else " "); i += 1; continue
        # str / char
        if c == "\\":
            out.append("  "); i += 2; continue
        if (state == "str" and c == '"') or (state == "char" and c == "'"):
            state = None
        out.append("\n" if c == "\n" else " "); i += 1; continue
    return "".join(out)


def balanced_block(text, open_idx):
    """Return (block_text, end_idx) for the brace block starting at open_idx ('{')."""
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1], i + 1
        i += 1
    return text[open_idx:], len(text)


def depth1_lines(block):
    """Yield lines of a brace block that sit at relative depth 1."""
    inner = block[1:-1] if block.endswith("}") else block[1:]
    depth = 1
    cur = []
    for ch in inner:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "\n":
            if depth == 1:
                yield "".join(cur)
            cur = []
        else:
            cur.append(ch)
    if cur and depth == 1:
        yield "".join(cur)


def parse_members(block, mode):
    """Parse depth-1 lines of a struct/interface block -> list of names."""
    names = []
    for line in depth1_lines(block):
        line = line.strip()
        if not line:
            continue
        if mode == "interface":
            m = re.match(r"([A-Z]\w*)\s*\(", line)
            if m:
                names.append(("interface-method", m.group(1)))
                continue
            m = re.match(r"(?:[\w.]+\.)?([A-Z]\w*)\s*$", line)
            if m:
                names.append(("interface-embed", m.group(1)))
                continue
            # type-set elements (~T, unions) are not methods; ignore
        else:  # struct fields
            # strip trailing struct tag remnants already stripped as strings
            m = re.match(r"([A-Z]\w*(?:\s*,\s*[A-Z]\w*)*)\s+\S", line)
            if m:
                for nm in m.group(1).split(","):
                    names.append(("field", nm.strip()))
                continue
            m = re.match(r"\*?(?:[\w.]+\.)?([A-Z]\w*)(?:\[.*\])?\s*$", line)
            if m:  # embedded field
                names.append(("field", m.group(1)))
    return names


def parse_file(path, pkg):
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    if "//go:build ignore" in raw:
        return []
    text = strip_noise(raw)
    m = re.search(r"^package\s+(\w+)", text, re.M)
    if not m:
        return []
    rows = []
    lines = text.split("\n")
    # byte offset of each line start for block lookups
    offsets = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1

    def block_after(line_idx, col_hint=0):
        """Find first '{' at/after given line and return its balanced block."""
        start = offsets[line_idx] + col_hint
        j = text.find("{", start)
        if j < 0:
            return None
        blk, _ = balanced_block(text, j)
        return blk

    i = 0
    in_group = None  # 'type' | 'const' | 'var'
    group_indent = None
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if in_group:
            if stripped == ")":
                in_group = None
                i += 1
                continue
            if stripped:
                if in_group == "type":
                    m = re.match(r"([A-Z]\w*)\s*(?:\[.*?\])?\s*(.*)$", stripped)
                    if m:
                        handle_type(m.group(1), m.group(2), i, rows, pkg, path, lines, block_after, member_line=i, grouped=True)
                else:  # const / var members
                    seg = stripped.split("=")[0].strip()
                    for nm in seg.split(","):
                        nm = nm.strip().split()
                        if nm and re.match(r"^[A-Z]\w*$", nm[0]):
                            rows.append((pkg, in_group, nm[0], "", path))
            i += 1
            continue
        m = re.match(r"func\s*\(([^)]*)\)\s*([A-Z]\w*)\s*[(\[]", line)
        if m:
            recv = m.group(1)
            recv = re.sub(r"\[.*\]", "", recv)
            toks = recv.replace("*", " ").split()
            base = toks[-1] if toks else ""
            rows.append((pkg, "method", m.group(2), base, path))
            i += 1
            continue
        m = re.match(r"func\s+([A-Z]\w*)\s*[(\[]", line)
        if m:
            rows.append((pkg, "func", m.group(1), "", path))
            i += 1
            continue
        m = re.match(r"(type|const|var)\s*\($", line)
        if m:
            in_group = m.group(1)
            i += 1
            continue
        m = re.match(r"type\s+([A-Z]\w*)\s*(?:\[.*?\])?\s*(.*)$", line)
        if m:
            handle_type(m.group(1), m.group(2), i, rows, pkg, path, lines, block_after, member_line=i, grouped=False)
            i += 1
            continue
        m = re.match(r"(const|var)\s+(.+)$", line)
        if m:
            seg = m.group(2).split("=")[0].strip()
            for nm in seg.split(","):
                nm = nm.strip().split()
                if nm and re.match(r"^[A-Z]\w*$", nm[0]):
                    rows.append((pkg, m.group(1), nm[0], "", path))
            i += 1
            continue
        i += 1
    return [(p, k, n, r, os.path.basename(f)) for (p, k, n, r, f) in rows]


def handle_type(name, rest, line_idx, rows, pkg, path, lines, block_after, member_line, grouped):
    rows.append((pkg, "type", name, "", path))
    kind = None
    if rest.startswith("struct"):
        kind = "struct"
    elif rest.startswith("interface"):
        kind = "interface"
    if kind is None:
        return
    blk = None
    # block may start on this line or a following one (grouped: 'Name struct' then '{' same line usually)
    blk = block_after(line_idx)
    if blk is None:
        return
    for mkind, mname in parse_members(blk, kind):
        rows.append((pkg, mkind, mname, name, path))


def main():
    src = sys.argv[1]
    out_path = sys.argv[2]
    all_rows = []
    seen = set()
    for rel, pkg in PKGS.items():
        d = os.path.join(src, rel)
        if not os.path.isdir(d):
            print(f"MISSING DIR {d}", file=sys.stderr)
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".go") or fn.endswith("_test.go"):
                continue
            for row in parse_file(os.path.join(d, fn), pkg):
                # Methods/fields on unexported receiver types are not part of
                # the package's public surface (unreachable by name).
                if row[3] and row[3][0].islower():
                    continue
                key = (row[0], row[1], row[2], row[3])
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append({
                    "pkg": row[0], "kind": row[1], "name": row[2],
                    "receiver": row[3], "file": row[4],
                })
    all_rows.sort(key=lambda r: (r["pkg"], r["kind"], r["receiver"], r["name"]))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(r["pkg"] for r in all_rows)
    for pkg in PKGS.values():
        print(f"{pkg}: {c.get(pkg, 0)}")
    print(f"TOTAL: {len(all_rows)}")


if __name__ == "__main__":
    main()
