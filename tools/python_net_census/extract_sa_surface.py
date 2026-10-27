#!/usr/bin/env python3
"""Extract the network-facing surface of sa_std (sci) at a fixed baseline.

Sources scanned (all under <sci>/sa_std unless noted):
  .sai  -> @extern declarations          (kind=extern)
  .sal  -> #def constants, [MACRO] names (kind=const / macro)
  .sa   -> [MACRO] names, @extern        (kind=macro / extern)
  .sla  -> fn definitions                (kind=fn)
  src/runtime/sa_std.h -> C ABI functions whose names carry a network
  prefix family (kind=c_func), counted uniquely.

Usage: extract_sa_surface.py <sci_root> <out_tsv> <out_summary_json>
"""
import json
import re
import sys
from pathlib import Path

FILES = [
    "net.sai", "net.sa", "net.sal",
    "netx.sai", "netx.sa", "netx.sal",
    "http2.sai", "http2.sa", "http2.sal",
    "http_client.sai", "http_server.sai", "multipart.sai",
    "tls_client.sai", "tls_client.sa",
    "tls_server.sai", "tls_server.sa", "tls_server.sal",
    "dtls.sai", "dtls.sa", "dtls.sal",
    "quic.sai", "quic.sa", "quic.sal",
    "ws_client.sai", "ws_client.sa",
    "ssh.sai",
    "plugin_http_server.sa", "plugin_http_async.sa",
    "plugin_async.sa", "plugin_async.sla",
]

EXTERN_RE = re.compile(r"^@extern\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
DEF_RE = re.compile(r"^#def\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
MACRO_RE = re.compile(r"^\[MACRO\]\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
FN_RE = re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
H_FUNC_RE = re.compile(r"\b(sa_[a-z0-9_]+)\s*\(")
H_NET_PREFIX = re.compile(
    r"^sa_(?:std_net|std_http|std_url|std_ws|net_|netx_|http_|http2_|ws_|tls_|"
    r"dtls_|quic_|ssh_|dns_|url_)"
)


def main():
    sci = Path(sys.argv[1])
    std = sci / "sa_std"
    out_tsv, out_json = Path(sys.argv[2]), Path(sys.argv[3])
    rows = []
    missing = []
    for rel in FILES:
        p = std / rel
        if not p.exists():
            missing.append(rel)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        suffix = p.suffix
        if suffix in (".sai", ".sa"):
            for name in EXTERN_RE.findall(text):
                rows.append((rel, "extern", name, ""))
        if suffix in (".sal", ".sa"):
            for name in MACRO_RE.findall(text):
                rows.append((rel, "macro", name, ""))
        if suffix == ".sal":
            for name in DEF_RE.findall(text):
                rows.append((rel, "const", name, ""))
        if suffix == ".sla":
            for name in FN_RE.findall(text):
                rows.append((rel, "fn", name, ""))
    h_path = sci / "src/runtime/sa_std.h"
    h_text = h_path.read_text(encoding="utf-8", errors="replace")
    h_all = sorted(set(H_FUNC_RE.findall(h_text)))
    h_net = [n for n in h_all if H_NET_PREFIX.match(n)]
    for n in h_net:
        rows.append(("sa_std.h", "c_func", n, ""))
    with out_tsv.open("w", encoding="utf-8") as fh:
        fh.write("source\tkind\tname\tdetail\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    per_file = {}
    for src, kind, _n, _d in rows:
        per_file.setdefault(src, {}).setdefault(kind, 0)
        per_file[src][kind] += 1
    unique_sa_names = sorted({n for _s, _k, n, _d in rows if _s != "sa_std.h"})
    summary = {
        "per_source": per_file,
        "missing_files": missing,
        "sa_layer_unique_names": len(unique_sa_names),
        "sa_std_h_total_funcs": len(h_all),
        "sa_std_h_net_funcs": len(h_net),
        "total_rows": len(rows),
    }
    out_json.write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
