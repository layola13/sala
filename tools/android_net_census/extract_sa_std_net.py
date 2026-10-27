#!/usr/bin/env python3
"""Extract the sa_std network-facing symbol surface from sci's sa_std tree.

Sources: the network .sai contract files (extern declarations), plus the
matching .sal/.sla/.sa files for macro / wrapper level symbols.

Outputs in --outdir:
  sa_std_net_symbols.tsv : file, kind, symbol
  (stdout: per-file counts and keyword probes for dns/url/etc.)

Usage: extract_sa_std_net.py <sa_std_dir> <outdir>
"""
import re
import sys
from pathlib import Path

SAI_FILES = [
    "net.sai",
    "netx.sai",
    "http_client.sai",
    "http_server.sai",
    "http2.sai",
    "ws_client.sai",
    "tls_client.sai",
    "tls_server.sai",
    "dtls.sai",
    "quic.sai",
    "ssh.sai",
]
EXTRA_FILES = [
    "net.sa",
    "net.sal",
    "netx.sal",
    "http2.sal",
    "quic.sal",
    "tls_server.sal",
    "dtls.sal",
    "plugin_http_server.sla",
    "plugin_http_server.sa",
    "plugin_http_async.sa",
]
EXTERN_RE = re.compile(r"^@extern\s+([A-Za-z_][A-Za-z0-9_]*)")
FN_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)")
MACRO_RE = re.compile(r"^\s*\[MACRO\]\s*([A-Za-z_][A-Za-z0-9_]*)")
KEYWORDS = ["dns", "resolve", "lookup", "getaddrinfo", "url", "uri", "cookie",
            "proxy", "hostname", "ifaddr", "interface"]


def main() -> int:
    std = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in SAI_FILES:
        p = std / name
        if not p.exists():
            print(f"MISSING {name}")
            continue
        n = 0
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = EXTERN_RE.match(line.strip())
            if m:
                rows.append((name, "extern", m.group(1)))
                n += 1
        print(f"{name}: {n} externs")
    for name in EXTRA_FILES:
        p = std / name
        if not p.exists():
            continue
        n = 0
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            for kind, rx in (("fn", FN_RE), ("macro", MACRO_RE)):
                m = rx.match(line)
                if m:
                    rows.append((name, kind, m.group(1)))
                    n += 1
        print(f"{name}: {n} fn/macro")
    with (outdir / "sa_std_net_symbols.tsv").open("w", encoding="utf-8") as f:
        f.write("file\tkind\tsymbol\n")
        for row in rows:
            f.write("\t".join(row) + "\n")
    syms = [r[2] for r in rows]
    print(f"total symbols: {len(syms)}")
    for kw in KEYWORDS:
        hits = [s for s in syms if kw in s.lower()]
        print(f"kw {kw}: {len(hits)} {hits[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
