#!/usr/bin/env python3
"""Extract the sa_std network surface from sci sa_std declaration files + sa_std.h.

Sources (fixed list, network domain):
  .sai/.sal/.sla declaration surfaces and .sa implementations for
  net / netx / http_client / http_server / http2 / ws_client /
  tls_client / tls_server / dtls / quic / ssh + plugin_http_* facades.
Symbols: line-start `name(` declarations, `fn name(`, `#def NAME`,
`@name` SA labels (with [MACRO] detection), and sa_* prototypes /
SA_* #defines in sa_std.h.
Output: sa_surface.tsv in the output directory.
"""
import os, re, sys

BASES = ["net", "netx", "http_client", "http_server", "http2", "ws_client",
         "tls_client", "tls_server", "dtls", "quic", "ssh",
         "plugin_http_async", "plugin_http_server"]
EXTS = [".sai", ".sal", ".sla", ".sa"]
KEYWORDS = {"if", "for", "while", "return", "switch", "sizeof", "assert"}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()[:240]


def from_decl_file(path, rows):
    fname = os.path.basename(path)
    for line in open(path, encoding='utf-8', errors='replace'):
        s = line.strip()
        m = re.match(r"#def\s+(\S+)", s)
        if m:
            rows.append((fname, m.group(1), 'const', norm(s)))
            continue
        m = re.match(r"@extern\s+([A-Za-z_][\w]*)\s*\(", s)
        if m:
            rows.append((fname, m.group(1), 'fn', norm(s)))
            continue
        m = re.match(r"(?:fn\s+)?([A-Za-z_][\w]*)\s*\(", s)
        if m and m.group(1) not in KEYWORDS and not s.startswith(("//", "#", "*")):
            rows.append((fname, m.group(1), 'fn', norm(s)))


def from_sa_file(path, rows):
    fname = os.path.basename(path)
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    for idx, line in enumerate(lines):
        m = re.match(r"@([A-Za-z_][\w]*)\s*[:\(]", line)
        if m:
            kind = 'fn'
            for back in range(max(0, idx - 2), idx):
                if '[MACRO]' in lines[back]:
                    kind = 'macro'
            rows.append((fname, m.group(1), kind, norm(line)))


def from_header(path, rows):
    fname = os.path.basename(path)
    seen = set()
    for line in open(path, encoding='utf-8', errors='replace'):
        s = line.strip()
        m = re.match(r"#define\s+(SA_[A-Z0-9_]+)", s)
        if m:
            rows.append((fname, m.group(1), 'const', norm(s)))
            continue
        for m in re.finditer(r"\b(sa_[a-z0-9_]+)\s*\(", s):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                rows.append((fname, m.group(1), 'fn', norm(s)))


def main():
    std_dir, header, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    used = []
    for base in BASES:
        for ext in EXTS:
            p = os.path.join(std_dir, base + ext)
            if os.path.exists(p):
                used.append(base + ext)
                if ext == '.sa':
                    from_sa_file(p, rows)
                else:
                    from_decl_file(p, rows)
    from_header(header, rows)
    # dedupe identical (file, symbol, kind)
    uniq = sorted(set(rows))
    with open(os.path.join(out_dir, 'sa_surface.tsv'), 'w') as f:
        f.write("file\tsymbol\tkind\tsignature\n")
        for r in uniq:
            f.write("\t".join(r) + "\n")
    from collections import Counter
    print("files used:", ", ".join(used))
    print("rows:", len(uniq), Counter(r[2] for r in uniq))
    print("by file:", Counter(r[0] for r in uniq))


if __name__ == '__main__':
    main()
