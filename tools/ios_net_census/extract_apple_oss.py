#!/usr/bin/env python3
"""extract_apple_oss.py — mechanically extract the public C function surface
that Apple itself publishes as open source for the iOS networking bottom
layers (source grade: oss = Apple open-source release):

  * Libinfo (apple-oss-distributions/Libinfo): lookup.subproj/netdb.h and
    netdb_async.h — the DNS resolver public headers (getaddrinfo family).
  * xnu (apple-oss-distributions/xnu): bsd/sys/socket.h and bsd/netinet/in.h
    fetched verbatim — the POSIX socket declarations Apple ships.

Extraction = lines that form a C prototype ending in ');' at top level,
after joining continuation lines; names taken from the declarator. Macros,
typedefs and constants are not counted as functions (noted as boundary).

Usage: extract_apple_oss.py <workdir> <out.tsv>
  <workdir> must contain: libinfo/ (clone), xnu_socket.h, xnu_in.h
"""
import os
import re
import sys

PROTO_RE = re.compile(r"^([A-Za-z_][\w\s\*]*?)\b([A-Za-z_]\w*)\s*\((.*)$", re.S)
SKIP_PREFIX = ("#", "typedef", "struct", "union", "enum", "extern \"C\"")


def extract(path, module, ref, out):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # strip comments and preprocessor lines
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))
    # remove brace blocks (struct/union/enum bodies, incl. nested) so that
    # prototypes following a type definition stay parseable
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{[^{}]*\}", " ", text)
    # statements separated by ';'
    for raw in text.split(";"):
        stmt = " ".join(raw.split())
        if "(" in stmt and stmt.rstrip().endswith(")"):
            m = PROTO_RE.match(stmt)
            if m and not stmt.startswith(SKIP_PREFIX):
                name = m.group(2)
                if name not in ("__asm", "__attribute__", "sizeof"):
                    out.append((module, name, ref))
    return out


def main():
    work, out_path = sys.argv[1], sys.argv[2]
    rows = []
    li = os.path.join(work, "libinfo", "lookup.subproj")
    for hdr in ("netdb.h", "netdb_async.h"):
        p = os.path.join(li, hdr)
        if os.path.exists(p):
            extract(p, f"Libinfo/{hdr}", "apple-oss-distributions/Libinfo:lookup.subproj/" + hdr, rows)
    for fn, mod in (("xnu_socket.h", "xnu/bsd/sys/socket.h"), ("xnu_in.h", "xnu/bsd/netinet/in.h")):
        p = os.path.join(work, fn)
        if os.path.exists(p):
            extract(p, mod, "apple-oss-distributions/xnu:" + mod, rows)
    seen = set()
    uniq = []
    for r in rows:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    uniq.sort()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("framework\tmodule\tkind\towner\tname\tlang\tios_since\tgrade\tref\n")
        for mod, name, ref in uniq:
            f.write(f"POSIX-AppleOSS\t{mod}\tfunc\t\t{name}\tc\t\toss\t{ref}\n")
    print("apple-oss functions:", len(uniq))
    for mod, name, _ in uniq:
        print(" ", mod, name)


if __name__ == "__main__":
    main()
