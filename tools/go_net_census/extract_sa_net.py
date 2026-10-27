#!/usr/bin/env python3
"""Extract the network-facing contract surface of sa_std.

Usage: extract_sa_net.py <sa_std_dir> <sa_std_h> <out.json>
Layers scanned (the SA contract layer; SA text-layer internals are not
distinguished definition-vs-call, so the census uses the layers a
consumer can actually bind to):
  .sai  @extern names          -> layer "sai"
  .sal  #def names             -> layer "sal"
  .sa   [MACRO] names          -> layer "macro"
  .sla  fn definitions         -> layer "sla"
  sa_std.h  C prototypes       -> layer "h"
Only symbols whose names carry a network token right after the
sa_/sa_std_ prefix (or an ALL-CAPS macro/def token) are kept.
"""
import json
import os
import re
import sys
from collections import Counter

TOKENS = ("net", "http", "http2", "http3", "h2", "ws", "tls", "dtls", "ssh", "dns",
          "url", "quic", "netx")
CAP_TOKENS = ("NET", "HTTP", "HTTP2", "HTTP3", "H2", "WS", "TLS", "DTLS", "SSH", "DNS",
              "URL", "QUIC", "NETX")


def net_symbol(name):
    m = re.match(r"sa_(?:std_)?([a-z0-9]+)", name)
    if m and m.group(1) in TOKENS:
        return True
    m = re.match(r"sa_([a-z0-9]+)", name)
    return bool(m and m.group(1) in TOKENS)


def cap_symbol(name):
    parts = name.split("_")
    return any(p in CAP_TOKENS for p in parts[:3])


def main():
    std_dir, h_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = []
    seen = set()

    def add(symbol, layer, fname):
        key = (symbol, layer)
        if key in seen:
            return
        seen.add(key)
        rows.append({"symbol": symbol, "layer": layer, "file": fname})

    for root, _dirs, files in os.walk(std_dir):
        for fn in sorted(files):
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if fn.endswith(".sai"):
                for m in re.finditer(r"@extern\s+(\w+)", text):
                    if net_symbol(m.group(1)):
                        add(m.group(1), "sai", fn)
            elif fn.endswith(".sal"):
                for m in re.finditer(r"^#def\s+(\w+)", text, re.M):
                    if cap_symbol(m.group(1)):
                        add(m.group(1), "sal", fn)
            elif fn.endswith(".sa"):
                for m in re.finditer(r"\[MACRO\]\s+(\w+)", text):
                    if cap_symbol(m.group(1)):
                        add(m.group(1), "macro", fn)
            elif fn.endswith(".sla"):
                for m in re.finditer(r"^\s*(?:pub\s+)?fn\s+(\w+)", text, re.M):
                    if net_symbol(m.group(1)):
                        add(m.group(1), "sla", fn)
    with open(h_path, encoding="utf-8", errors="replace") as f:
        htext = f.read()
    for m in re.finditer(r"\b(sa_\w+)\s*\(", htext):
        if net_symbol(m.group(1)):
            add(m.group(1), "h", os.path.basename(h_path))

    rows.sort(key=lambda r: (r["layer"], r["symbol"]))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    c = Counter(r["layer"] for r in rows)
    for layer in ("sai", "sal", "macro", "sla", "h"):
        print(f"{layer}: {c.get(layer, 0)}")
    print(f"TOTAL: {len(rows)}")


if __name__ == "__main__":
    main()
