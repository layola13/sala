#!/usr/bin/env python3
"""Classify every Go net-family API item against the sa_std surface.

Usage: compare_go_net.py <go_net_api.json> <sa_net_api.json> <rules.py> <out.tsv>
Rules live in rules.py as RULES: ordered list of dicts with optional
matchers (pkg, kind, receiver, name, name_re) and fields
(cat, sa, note). First match wins. Categories:
  equiv    已有等价 (sa_std already covers it, possibly under another name)
  direct   可直接对应 (semantics map cleanly onto sa_std's model; not done)
  model    需建模 (needs an object/state model sa_std does not expose today)
  mismatch 模型不合 (depends on Go runtime semantics SA does not adopt)
Any cited sa_* / SA_* / MACRO token in a rule's `sa` text is verified
against the extracted SA inventory; unknown tokens are reported.
"""
import importlib.util
import json
import re
import sys
from collections import Counter

CATS = ("equiv", "direct", "model", "mismatch")


def load_rules(path):
    spec = importlib.util.spec_from_file_location("rules", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.RULES


def match(rule, row):
    if "pkg" in rule and rule["pkg"] != row["pkg"]:
        return False
    if "kind" in rule and rule["kind"] != row["kind"]:
        return False
    if "kind_in" in rule and row["kind"] not in rule["kind_in"]:
        return False
    if "receiver" in rule and rule["receiver"] != row["receiver"]:
        return False
    if "name" in rule and rule["name"] != row["name"]:
        return False
    if "name_in" in rule and row["name"] not in rule["name_in"]:
        return False
    if "name_re" in rule and not re.search(rule["name_re"], row["name"]):
        return False
    if "receiver_re" in rule and not re.search(rule["receiver_re"], row["receiver"]):
        return False
    return True


def main():
    go = json.load(open(sys.argv[1]))
    sa = json.load(open(sys.argv[2]))
    rules = load_rules(sys.argv[3])
    out_path = sys.argv[4]

    sa_symbols = {r["symbol"] for r in sa}
    sa_prefixes = set()
    for s in sa_symbols:
        sa_prefixes.add(s)

    def token_ok(tok):
        if tok in sa_symbols:
            return True
        if tok.endswith("_*"):
            stem = tok[:-1]
            return any(s.startswith(stem) for s in sa_symbols)
        if tok.endswith("*"):
            stem = tok[:-1]
            return any(s.startswith(stem) for s in sa_symbols)
        return False

    # Go 1.27 declares a few names as both const and var (cipher-suite IDs);
    # they are one API item -- keep the const row, drop the var duplicate.
    const_keys = {(r["pkg"], r["receiver"], r["name"]) for r in go if r["kind"] == "const"}
    deduped, dropped = [], 0
    for r in go:
        if r["kind"] == "var" and (r["pkg"], r["receiver"], r["name"]) in const_keys:
            dropped += 1
            continue
        deduped.append(r)
    go = deduped
    print(f"(const/var duplicates dropped: {dropped})")

    bad_tokens = Counter()
    results = []
    unclassified = []
    for row in go:
        hit = None
        for rule in rules:
            if match(rule, row):
                hit = rule
                break
        if hit is None:
            unclassified.append(row)
            results.append({**row, "cat": "UNCLASSIFIED", "sa": "", "note": ""})
            continue
        for tok in re.findall(r"(?:sa_[a-z0-9_]+|SA_[A-Z0-9_]+|[A-Z][A-Z0-9]+_[A-Z0-9_]+)\*?", hit["sa"]):
            if not token_ok(tok):
                bad_tokens[tok] += 1
        results.append({**row, "cat": hit["cat"], "sa": hit["sa"], "note": hit.get("note", "")})

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("pkg\tkind\tname\treceiver\tcat\tsa_counterpart\tnote\tfile\n")
        for r in results:
            f.write("\t".join([r["pkg"], r["kind"], r["name"], r["receiver"],
                                r["cat"], r["sa"], r["note"], r["file"]]) + "\n")
    print("== by pkg x cat")
    by = {}
    for r in results:
        by.setdefault(r["pkg"], Counter())[r["cat"]] += 1
    for pkg in sorted(by):
        c = by[pkg]
        print(f"{pkg}: total={sum(c.values())} " +
              " ".join(f"{k}={c.get(k, 0)}" for k in CATS + ("UNCLASSIFIED",)))
    print("== totals", Counter(r["cat"] for r in results))
    if bad_tokens:
        print("== UNVERIFIED SA TOKENS (fix rules):")
        for t, n in bad_tokens.most_common():
            print(" ", t, n)
    if unclassified:
        print(f"== UNCLASSIFIED {len(unclassified)}")
        for r in unclassified:
            print(" ", r["pkg"], r["kind"], r["receiver"], r["name"])


if __name__ == "__main__":
    main()
