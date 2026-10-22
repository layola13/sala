#!/usr/bin/env python3
"""Aggregate slarust benchmark results and emit Markdown tables."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load(name):
    path = RESULTS / name
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def median(xs):
    xs = sorted(xs)
    if not xs:
        return 0.0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def main():
    rows = []
    native = load("native.jsonl")
    wasm = load("wasm.jsonl")
    compile_ = load("compile.jsonl")

    by = {}
    for r in native:
        by.setdefault((r["bench"], r["lang"]), []).append(r["ms"])
    native_med = {k: median(v) for k, v in by.items()}

    by = {}
    for r in wasm:
        by.setdefault((r["bench"], r["lang"]), []).append(r.get("run_ms", r["ms"]))
    wasm_med = {k: median(v) for k, v in by.items()}

    benches = sorted({r["bench"] for r in native})
    print("## Native runtime (median ms)\n")
    print("| bench | SLA | Rust | Rust/SLA | SLA checksum | Rust checksum |")
    print("|---|---:|---:|---:|---:|---:|")
    for b in benches:
        s = native_med.get((b, "sla"), 0)
        r = native_med.get((b, "rust"), 0)
        sc = next((x.get("checksum", "") for x in native if x["bench"] == b and x["lang"] == "sla"), "")
        rc = next((x.get("checksum", "") for x in native if x["bench"] == b and x["lang"] == "rust"), "")
        print(f"| {b} | {s:.1f} | {r:.1f} | {(r / s if s else 0):.3f} | {sc} | {rc} |")

    print("\n## WASM runtime (median ms, Wasmtime 25.0.2 WASI)\n")
    print("| bench | SLA | Rust | Rust/SLA | SLA checksum | Rust checksum |")
    print("|---|---:|---:|---:|---:|---:|")
    for b in sorted({r["bench"] for r in wasm}):
        s = wasm_med.get((b, "sla"), 0)
        r = wasm_med.get((b, "rust"), 0)
        sc = next((x.get("checksum", "") for x in wasm if x["bench"] == b and x["lang"] == "sla"), "")
        rc = next((x.get("checksum", "") for x in wasm if x["bench"] == b and x["lang"] == "rust"), "")
        print(f"| {b} | {s:.1f} | {r:.1f} | {(r / s if s else 0):.3f} | {sc} | {rc} |")

    for cold, title in [(True, "Cold compile time"), (False, "Warm/incremental compile time")]:
        print(f"\n## {title} (median ms)\n")
        print("| bench | target | SLA | Rust | Rust/SLA |")
        print("|---|---|---:|---:|---:|")
        by = {}
        for r in compile_:
            if r["cold"] != cold:
                continue
            by.setdefault((r["bench"], r["target"], r["lang"]), []).append(r["ms"])
        for (b, t) in sorted({(r["bench"], r["target"]) for r in compile_}):
            s = median(by.get((b, t, "sla"), []))
            r = median(by.get((b, t, "rust"), []))
            if s or r:
                print(f"| {b} | {t} | {s:.0f} | {r:.0f} | {(r / s if s else 0):.3f} |")

    print("\n## Artifact size (bytes, cold build)\n")
    print("| bench | SLA native | Rust native | SLA wasm | Rust wasm |")
    print("|---|---:|---:|---:|---:|")
    sizes = {}
    for r in compile_:
        if r["cold"]:
            sizes.setdefault((r["bench"], r["target"], r["lang"]), []).append(r["bytes"])
    for b in benches:
        vals = []
        for t, l in [("native", "sla"), ("native", "rust"), ("wasm", "sla"), ("wasm", "rust")]:
            xs = sizes.get((b, t, l), [])
            vals.append(median(xs) if xs else 0)
        print(f"| {b} | {vals[0]:.0f} | {vals[1]:.0f} | {vals[2]:.0f} | {vals[3]:.0f} |")

    print("\n## Native peak RSS (median KB)\n")
    print("| bench | SLA | Rust | Rust/SLA |")
    print("|---|---:|---:|---:|")
    rss = {}
    for r in native:
        rss.setdefault((r["bench"], r["lang"]), []).append(r["maxrss_kb"])
    for b in benches:
        s = median(rss.get((b, "sla"), []))
        rr = median(rss.get((b, "rust"), []))
        print(f"| {b} | {s:.0f} | {rr:.0f} | {(rr / s if s else 0):.3f} |")

    print("\n## WASM peak RSS (median KB)\n")
    print("| bench | SLA | Rust | Rust/SLA |")
    print("|---|---:|---:|---:|")
    rss = {}
    for r in wasm:
        rss.setdefault((r["bench"], r["lang"]), []).append(r["maxrss_kb"])
    for b in sorted({r["bench"] for r in wasm}):
        s = median(rss.get((b, "sla"), []))
        rr = median(rss.get((b, "rust"), []))
        print(f"| {b} | {s:.0f} | {rr:.0f} | {(rr / s if s else 0):.3f} |")


if __name__ == "__main__":
    main()
