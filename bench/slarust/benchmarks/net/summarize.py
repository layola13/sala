#!/usr/bin/env python3
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = [json.loads(x) for x in (ROOT / "results.jsonl").read_text().splitlines() if x.strip()]
levels = sorted({r["concurrency"] for r in rows})
servers = ["sla", "rust", "go"]
summary = {}
for s in servers:
    for c in levels:
        rs = [r for r in rows if r["server"] == s and r["concurrency"] == c]
        if not rs:
            continue
        summary[(s, c)] = {
            "rps": st.median(r["rps"] for r in rs),
            "p50_us": st.median(r["p50_us"] for r in rs),
            "p95_us": st.median(r["p95_us"] for r in rs),
            "p99_us": st.median(r["p99_us"] for r in rs),
            "rss_mb": st.median(r["rss_kb"] for r in rs) / 1024.0,
            "errors": sum(r["errors"] for r in rs),
        }

print("| 并发 | SLA rps | Rust rps | Go rps | SLA p50/p95/p99 ms | Rust p50/p95/p99 ms | Go p50/p95/p99 ms | SLA RSS MB | Rust RSS MB | Go RSS MB |")
print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for c in levels:
    a, b, d = (summary.get((s, c)) for s in servers)
    def lat(x):
        return f'{x["p50_us"]/1000:.2f}/{x["p95_us"]/1000:.2f}/{x["p99_us"]/1000:.2f}'
    print(f'| {c} | {a["rps"]:.0f} | {b["rps"]:.0f} | {d["rps"]:.0f} | '
          f'{lat(a)} | {lat(b)} | {lat(d)} | {a["rss_mb"]:.0f} | {b["rss_mb"]:.0f} | {d["rss_mb"]:.0f} |')

print()
for c in levels:
    a, b, d = (summary[(s, c)] for s in servers)
    print(f'c={c}: Rust/SLA={b["rps"]/a["rps"]:.1f}x Go/SLA={d["rps"]/a["rps"]:.1f}x')

out = {f"{s}@{c}": v for (s, c), v in summary.items()}
(ROOT / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
