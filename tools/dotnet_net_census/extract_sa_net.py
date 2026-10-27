#!/usr/bin/env python3
"""Agent AS census: extract sa_std network-facing surface from sci @ 8a943911.
Sources: sa_std/*.sai (@extern), *.sal (#def), *.sa ([MACRO] / @fn labels),
         sci/src/runtime/sa_std.h (C decls, net-family prefixes only).
Output: TSV  subsystem \t origin \t kind \t name \t file
"""
import os, re, sys, collections

STD = "/content/sa_all/sci/sa_std"
HDR = "/content/sa_all/sci/src/runtime/sa_std.h"

# file stem -> subsystem label
GROUPS = {
    "net": "net", "netx": "netx",
    "http_client": "http", "http_server": "http", "multipart": "http",
    "http2": "http2",
    "ws_client": "ws",
    "tls_client": "tls", "tls_server": "tls", "dtls": "tls",
    "quic": "quic", "ssh": "ssh",
    "plugin_http_server": "http_facade", "plugin_http_async": "http_facade",
}

rows = []
seen = set()

def add(sub, origin, kind, name, fname):
    key = (sub, origin, kind, name)
    if key in seen:
        return
    seen.add(key)
    rows.append((sub, origin, kind, name, fname))

ext_re = re.compile(r"@extern\s+([A-Za-z_][A-Za-z0-9_]*)")
def_re = re.compile(r"#def\s+([A-Za-z_][A-Za-z0-9_]*)")
mac_re = re.compile(r"\[MACRO\]\s+([A-Za-z_][A-Za-z0-9_]*)")
lab_re = re.compile(r"^@([A-Za-z_][A-Za-z0-9_]*)\s*:", re.M)

for fname in sorted(os.listdir(STD)):
    stem, dot, ext = fname.rpartition(".")
    if stem not in GROUPS:
        continue
    path = os.path.join(STD, fname)
    if not os.path.isfile(path):
        continue
    text = open(path, encoding="utf-8", errors="replace").read()
    sub = GROUPS[stem]
    if ext == "sai":
        for m in ext_re.finditer(text):
            add(sub, "sai", "extern", m.group(1), fname)
    elif ext == "sal":
        for m in def_re.finditer(text):
            add(sub, "sal", "const", m.group(1), fname)
    elif ext in ("sa", "sla"):
        for m in mac_re.finditer(text):
            add(sub, ext, "macro", m.group(1), fname)
        for m in lab_re.finditer(text):
            add(sub, ext, "fn", m.group(1), fname)

# sa_std.h: net-family C declarations only
HPREFIX = ("sa_std_net", "sa_net_", "sa_netx", "sa_http", "sa_std_http",
           "sa_ws", "sa_std_ws", "sa_tls", "sa_dtls", "sa_quic", "sa_ssh",
           "sa_std_url", "sa_std_last_error")
h_re = re.compile(r"\b(sa_[a-z0-9_]+)\s*\(")
if os.path.isfile(HDR):
    for m in h_re.finditer(open(HDR, encoding="utf-8", errors="replace").read()):
        name = m.group(1)
        if name.startswith(HPREFIX):
            sub = "h"
            for pfx, s in (("netx", "netx"), ("http2", "http2"), ("http", "http"),
                           ("ws", "ws"), ("tls", "tls"), ("dtls", "tls"),
                           ("quic", "quic"), ("ssh", "ssh"), ("net", "net"),
                           ("url", "net")):
                if pfx in name:
                    sub = s
                    break
            add(sub, "h", "h_decl", name, "sa_std.h")

rows.sort()
out = sys.stdout
out.write("subsystem\torigin\tkind\tname\tfile\n")
for r in rows:
    out.write("\t".join(r) + "\n")

cnt = collections.Counter((r[0], r[2]) for r in rows)
sys.stderr.write("== counts by subsystem x kind ==\n")
for (sub, kind), n in sorted(cnt.items()):
    sys.stderr.write(f"{sub}\t{kind}\t{n}\n")
sys.stderr.write(f"TOTAL\t{len(rows)}\n")
