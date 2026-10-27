#!/usr/bin/env python3
"""extract_sa_net.py — mechanically extract the sa_std network surface from
sci (baseline main 8a943911): @extern declarations in the network .sai
contract files plus #def constants in their .sal companions.

Usage: extract_sa_net.py <sa_std_dir> <out.tsv>
Output columns: file  kind(extern|const)  name
"""
import os
import re
import sys

NET_FILES = [
    "net.sai", "net.sal", "netx.sai",
    "http_client.sai", "http_server.sai", "http2.sai",
    "ws_client.sai", "ws_server.sai",
    "tls_client.sai", "tls_server.sai", "dtls.sai",
    "quic.sai", "ssh.sai", "multipart.sai",
]

EXTERN_RE = re.compile(r"^@extern\s+([A-Za-z0-9_]+)\s*\(")
DEF_RE = re.compile(r"^#def\s+([A-Za-z0-9_]+)")


def main():
    std_dir, out = sys.argv[1], sys.argv[2]
    rows = []
    missing = []
    for name in NET_FILES:
        p = os.path.join(std_dir, name)
        if not os.path.exists(p):
            missing.append(name)
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = EXTERN_RE.match(line.strip())
                if m:
                    rows.append((name, "extern", m.group(1)))
                    continue
                m = DEF_RE.match(line.strip())
                if m:
                    rows.append((name, "const", m.group(1)))
    rows.sort()
    with open(out, "w", encoding="utf-8") as f:
        f.write("file\tkind\tname\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    by_file = {}
    for fn, _, _ in rows:
        by_file[fn] = by_file.get(fn, 0) + 1
    print("total:", len(rows))
    print("by_file:", by_file)
    print("missing_files:", missing)


if __name__ == "__main__":
    main()
