#!/usr/bin/env python3
"""Headline numbers for the Java net census: API vs internal types, member totals."""
import csv
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
api = [t for t in types if is_api(t, byfqn)]
apiset = {t["fqn"] for t in api}
amem = [m for m in mem if m["fqn"] in apiset]
print("types extracted:", len(types), "| API types:", len(api),
      "| internal:", len(types) - len(api))
print("API types by package:", dict(Counter(t["package"] for t in api)))
print("API types by kind:", dict(Counter(t["kind"] for t in api)))
print("members extracted:", len(mem), "| on API types:", len(amem),
      dict(Counter(m["member_kind"] for m in amem)))
sa = list(csv.DictReader(open("out/sa_surface.tsv"), delimiter="\t"))
print("SA rows:", len(sa), "| unique symbols:", len({r['symbol'] for r in sa}))
