#!/usr/bin/env python3
"""crawl_network_docc.py — mechanically enumerate the public symbol surface of
Apple's Network framework from the official DocC data endpoints
(developer.apple.com/tutorials/data/documentation/network/...).

Source grade: 3 (Apple developer documentation surface, NOT SDK headers and
NOT source code). Every emitted row is marked grade=doc.

Breadth-first crawl restricted to the com.apple.network bundle: start at the
framework root page, follow `references` entries of kind=symbol whose URL is
inside the bundle, fetch each symbol page once. Per symbol we record title,
symbolKind, interface language and iOS introduction version from the page's
own metadata — nothing is inferred or filled in by hand.

Usage: crawl_network_docc.py <out_symbols.tsv> <out_stats.json>
"""
import json
import sys
import time
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor

BASE = "https://developer.apple.com/tutorials/data/"
BUNDLE_PREFIX = "doc://com.apple.network/documentation/Network"
MAX_PAGES = 8000

OUT = sys.argv[1] if len(sys.argv) > 1 else "network_symbols.tsv"
STATS = sys.argv[2] if len(sys.argv) > 2 else "network_crawl_stats.json"


def fetch(url_id):
    path = url_id.split("documentation/", 1)[1]
    u = BASE + "documentation/" + path.lower() + ".json"
    req = urllib.request.Request(u, headers={"User-Agent": "sala-std-census/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    t0 = time.time()
    seen = {}
    errors = []
    queue = deque([BUNDLE_PREFIX])
    queued = {BUNDLE_PREFIX}

    def handle(url_id, d):
        seen[url_id] = d
        # references is a dict keyed by the referenced identifier's URL;
        # the values carry kind/title but no url field of their own.
        for u, r in (d.get("references") or {}).items():
            if r.get("kind") != "symbol":
                continue
            if u.startswith(BUNDLE_PREFIX) and u not in queued:
                queued.add(u)
                queue.append(u)

    while queue and len(seen) < MAX_PAGES:
        wave = [queue.popleft() for _ in range(min(len(queue), 64))]
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(fetch, u): u for u in wave}
            for f in futs:
                u = futs[f]
                try:
                    handle(u, f.result())
                except Exception as e:  # noqa: BLE001 - recorded, not hidden
                    errors.append((u, str(e)[:160]))
        print(f"visited={len(seen)} queued={len(queue)} errors={len(errors)}", flush=True)

    rows = []
    by_kind = {}
    ios_versions = []
    for url_id, d in seen.items():
        if url_id == BUNDLE_PREFIX:
            continue  # framework root page itself is not a symbol
        md = d.get("metadata") or {}
        kind = md.get("symbolKind")
        if not kind:
            continue  # framework root / non-symbol pages carry no symbolKind
        title = md.get("title", "")
        lang = (d.get("identifier") or {}).get("interfaceLanguage", "")
        path = url_id.split("/documentation/Network", 1)[1].strip("/")
        segs = path.split("/") if path else []
        owner = segs[0] if len(segs) > 1 else ""
        ios = ""
        for p in md.get("platforms") or []:
            if p.get("name") == "iOS":
                ios = p.get("introducedAt", "")
                if ios:
                    ios_versions.append(ios)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        rows.append((owner, kind, owner, title, lang, ios, url_id))

    rows.sort()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("framework\tmodule\tkind\towner\tname\tlang\tios_since\tgrade\tref\n")
        for owner, kind, mod, title, lang, ios, url_id in rows:
            f.write(f"Network\t{mod}\t{kind}\t{owner}\t{title}\t{lang}\t{ios}\tdoc\t{url_id}\n")

    def vkey(v):
        return tuple(int(x) for x in v.split(".") if x.isdigit())

    stats = {
        "pages_visited": len(seen),
        "fetch_errors": len(errors),
        "error_sample": errors[:10],
        "symbols": len(rows),
        "by_kind": by_kind,
        "max_ios_introducedAt": max(ios_versions, key=vkey) if ios_versions else None,
        "seconds": round(time.time() - t0, 1),
    }
    with open(STATS, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
