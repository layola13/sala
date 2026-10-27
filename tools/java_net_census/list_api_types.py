#!/usr/bin/env python3
"""Analysis helper: list API types with member counts (Java census)."""
import csv, sys
from collections import Counter

types = list(csv.DictReader(open("out/java_types.tsv"), delimiter="\t"))
mem = list(csv.DictReader(open("out/java_members.tsv"), delimiter="\t"))


def is_api(t, byfqn):
    # Refined rule (same as classify_gap.py): public, or a non-private member
    # type of an interface (implicitly public). Other nested types are internal.
    mods = t["modifiers"]
    if "private" in mods:
        return False
    if "public" in mods:
        return True
    fqn = t["fqn"]
    if "." not in fqn[len(t["package"]) + 1:]:
        return False
    p = byfqn.get(fqn.rsplit(".", 1)[0])
    return bool(p) and p["kind"] in ("interface", "@interface") and is_api(p, byfqn)


byfqn = {t["fqn"]: t for t in types}
mc = Counter(m["fqn"] for m in mem)
cur = None
for t in sorted((t for t in types if is_api(t, byfqn)),
                key=lambda x: (x["package"], x["fqn"])):
    if t["package"] != cur:
        cur = t["package"]
        print("##", cur)
    print("%s [%s] members=%d" % (t["fqn"], t["kind"], mc.get(t["fqn"], 0)))
