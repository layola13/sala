#!/usr/bin/env python3
"""Cold/warm compile and runtime benchmark harness for SLA vs Rust."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLA = os.environ.get("SLA", "sla")
SA_LIB = os.environ.get(
    "SA_LIB", "/tools/node/lib/node_modules/@slalang/sla/node_modules/@salang/sa-linux-x64/bin"
)
WASMTIME = os.environ.get("WASMTIME", "/tmp/wasmtime-v25.0.2-x86_64-linux/wasmtime")
RUST_DIR = ROOT / "benchmarks/rust"
SLA_SRC = ROOT / "benchmarks/sla"
OUT = ROOT / "results"
ART = ROOT / "artifacts"

BENCHES = [
    "hello",
    "fib",
    "loopsum",
    "sieve",
    "matmul",
    "sort",
    "hashmap",
    "nbody",
    "mandelbrot",
    "vecpush",
    "bytes",
]


def base_env():
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".cargo/bin") + ":" + env.get("PATH", "")
    ld = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = SA_LIB + ((":" + ld) if ld else "")
    return env


def run_measured(cmd, cwd=None, env=None, timeout=900):
    env = env or base_env()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        t0 = time.perf_counter()
        p = subprocess.Popen(cmd, cwd=cwd or ROOT, env=env, stdout=out, stderr=err)
        try:
            pid, status, ru = os.wait4(p.pid, 0)
        except BaseException:
            p.kill()
            raise
        elapsed = (time.perf_counter() - t0) * 1000.0
        p.returncode = os.waitstatus_to_exitcode(status)
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8", "replace")
        stderr = err.read().decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError(
            f"command failed ({p.returncode}): {' '.join(map(str, cmd))}\n"
            f"stdout: {stdout[-2000:]}\nstderr: {stderr[-4000:]}"
        )
    return {
        "ms": elapsed,
        "maxrss_kb": ru.ru_maxrss,
        "stdout": stdout,
        "stderr": stderr,
    }


def append(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_sla_cache():
    for d in [ROOT / ".sa_cache", ROOT / ".sla-cache"]:
        if d.exists():
            shutil.rmtree(d)


def touch_warm_sources(bench):
    os.utime(SLA_SRC / f"{bench}.sla", None)
    os.utime(RUST_DIR / "src/bin" / f"{bench}.rs", None)


def compile_sla(bench, target, cold):
    out_dir = ART / f"sla-{target}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (f"{bench}.wasm" if target == "wasm" else bench)
    if out.exists():
        out.unlink()
    cmd = [SLA, "build-wasm" if target == "wasm" else "build-exe", str(SLA_SRC / f"{bench}.sla"), "-o", str(out), "--release-fast"]
    if cold:
        clean_sla_cache()
        cmd.append("--no-incremental")
    r = run_measured(cmd)
    return {
        "bench": bench,
        "lang": "sla",
        "target": target,
        "cold": cold,
        "ms": r["ms"],
        "maxrss_kb": r["maxrss_kb"],
        "bytes": out.stat().st_size if out.exists() else 0,
    }


def compile_rust(bench, target, cold, target_cpu_native=False):
    if cold:
        tmp = Path(tempfile.gettempdir()) / f"slarust-target-{uuid.uuid4().hex[:12]}"
    else:
        tmp = Path(tempfile.gettempdir()) / f"slarust-warm-{target}"
    tmp.mkdir(parents=True, exist_ok=True)
    env = base_env()
    env["CARGO_TARGET_DIR"] = str(tmp)
    rustflags = []
    if target_cpu_native:
        rustflags.append("-Ctarget-cpu=native")
    env["RUSTFLAGS"] = " ".join(rustflags)
    cmd = ["cargo", "build", "--release", "--bin", bench]
    if target == "wasm":
        cmd += ["--target", "wasm32-wasip1"]
    r = run_measured(cmd, cwd=RUST_DIR, env=env)
    if target == "wasm":
        out = tmp / "wasm32-wasip1/release" / f"{bench}.wasm"
    else:
        out = tmp / "release" / bench
    row = {
        "bench": bench,
        "lang": "rust",
        "target": target,
        "cold": cold,
        "ms": r["ms"],
        "maxrss_kb": r["maxrss_kb"],
        "bytes": out.stat().st_size if out.exists() else 0,
        "native_cpu": target_cpu_native,
    }
    if cold:
        shutil.rmtree(tmp, ignore_errors=True)
    return row


def do_compile(runs, phase="both"):
    rows = []
    for bench in BENCHES:
        for target in ["native", "wasm"]:
            for cold in [True, False]:
                if phase == "cold" and not cold:
                    continue
                if phase == "warm" and cold:
                    continue
                if not cold:
                    compile_sla(bench, target, False)
                    compile_rust(bench, target, False)
                for _ in range(runs):
                    if not cold:
                        touch_warm_sources(bench)
                    rows.append(compile_sla(bench, target, cold))
                    rows.append(compile_rust(bench, target, cold))
                    print(
                        f"[compile] {bench:10s} {target:6s} cold={cold} "
                        f"sla={rows[-2]['ms']:.0f}ms rust={rows[-1]['ms']:.0f}ms",
                        flush=True,
                    )
    append("compile.jsonl", rows)


def do_native(runs):
    rows = []
    for bench in BENCHES:
        # ensure artifacts exist (release-fast build without timing noise)
        if not (ART / "sla-native" / bench).exists():
            compile_sla(bench, "native", cold=False)
        rust_bin = RUST_DIR / "target/release" / bench
        for lang, cmd in [
            ("sla", [str(ART / "sla-native" / bench)]),
            ("rust", [str(rust_bin)]),
        ]:
            for i in range(runs + 1):
                r = run_measured(cmd)
                if i == 0:
                    continue
                row = {
                    "bench": bench,
                    "lang": lang,
                    "target": "native",
                    "run": i,
                    "ms": r["ms"],
                    "maxrss_kb": r["maxrss_kb"],
                    "checksum": r["stdout"].strip(),
                }
                rows.append(row)
                print(f"[native] {bench:10s} {lang:4s} {r['ms']:8.1f}ms rss={r['maxrss_kb']}KB", flush=True)
    append("native.jsonl", rows)


def do_wasm(runs):
    if not Path(WASMTIME).exists():
        raise SystemExit(f"wasmtime not found at {WASMTIME}; set WASMTIME env var")
    rows = []
    for bench in BENCHES:
        if not (ART / "sla-wasm" / f"{bench}.wasm").exists():
            compile_sla(bench, "wasm", cold=False)
        rust_wasm = RUST_DIR / "target/wasm32-wasip1/release" / f"{bench}.wasm"
        for lang, path in [
            ("sla", ART / "sla-wasm" / f"{bench}.wasm"),
            ("rust", rust_wasm),
        ]:
            for i in range(runs + 1):
                r = run_measured([WASMTIME, str(path)])
                if i == 0:
                    continue
                row = {
                    "bench": bench,
                    "lang": lang,
                    "target": "wasm",
                    "run": i,
                    "ms": r["ms"],
                    "maxrss_kb": r["maxrss_kb"],
                    "checksum": r["stdout"].strip(),
                }
                rows.append(row)
                print(f"[wasm]   {bench:10s} {lang:4s} {r['ms']:8.1f}ms rss={r['maxrss_kb']}KB", flush=True)
    append("wasm.jsonl", rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["compile", "native", "wasm", "all"], default="all")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--phase", choices=["cold", "warm", "both"], default="both")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.mode in ("compile", "all"):
        do_compile(3 if args.runs >= 3 else args.runs, args.phase)
    if args.mode in ("native", "all"):
        do_native(args.runs)
    if args.mode in ("wasm", "all"):
        do_wasm(max(3, args.runs - 2))


if __name__ == "__main__":
    main()
