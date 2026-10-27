#!/usr/bin/env python3
"""Extract the sa_std network-facing surface (sci main 8a943911) into a TSV inventory.
Method: @extern declarations in .sai files; sa_* symbol tokens in .sa/.sal/.sla files.
Usage: extract_sa_net.py <sa_std_dir> <out_tsv>
"""
import os, re, sys, collections

STD = sys.argv[1] if len(sys.argv) > 1 else "/content/sa_all/sci/sa_std"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/content/unreal-census-work/sa_net_surface.tsv"

GROUPS = {
    "transport": ["net.sai", "net.sal", "net.sa", "netx.sai", "netx.sal", "netx.sa"],
    "http": ["http_client.sai", "http_server.sai", "http2.sai", "http2.sal", "http2.sa",
             "plugin_http_async.sa", "plugin_http_server.sa", "plugin_http_server.sla"],
    "tls_ws_quic_ssh": ["tls_client.sai", "tls_client.sa", "tls_server.sai", "tls_server.sal",
                        "tls_server.sa", "ws_client.sai", "ws_client.sa", "dtls.sai", "dtls.sal",
                        "dtls.sa", "quic.sai", "quic.sal", "quic.sa", "ssh.sai"],
    "encoding_compress": ["encoding/base64.sai", "encoding/json.sai", "encoding/json.sal",
                          "encoding/json.sa", "encoding/toml.sai", "compress.sai"],
}

rows = []
for group, files in GROUPS.items():
    syms = collections.Counter()
    for fn in files:
        p = os.path.join(STD, fn)
        if not os.path.exists(p):
            print(f"MISSING {p}")
            continue
        t = open(p, encoding="utf-8", errors="ignore").read()
        if fn.endswith(".sai"):
            found = re.findall(r"@extern\s+([A-Za-z_][\w]*)", t)
        else:
            found = re.findall(r"\b(sa_(?:std_)?[a-z][a-z0-9_]*)\b", t)
        for s in set(found):
            syms[s] += 1
            rows.append((group, fn, s))
    print(f"{group}: {len(syms)} unique symbols across {len(files)} files")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("group\tfile\tsymbol\n")
    for g, fn, s in sorted(set(rows)):
        f.write(f"{g}\t{fn}\t{s}\n")
print("total unique (group,file,symbol) rows:", len(set(rows)))
print("wrote", OUT)
