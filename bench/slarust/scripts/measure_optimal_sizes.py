#!/usr/bin/env python3
"""Compare minimum deployable sizes: SLA release-fast + strip vs Rust profile=size + strip + wasm-opt -Oz."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "scripts"))
from strip_wasm import strip  # noqa: E402

BENCHES = ["hello", "fib", "loopsum", "sieve", "matmul", "sort", "hashmap",
           "nbody", "mandelbrot", "vecpush", "bytes"]
RUST = ROOT / "benchmarks/rust"
SLA_NATIVE = ROOT / "artifacts/sla-native"
SLA_WASM = ROOT / "artifacts/sla-wasm"
RUST_NATIVE = ROOT / "artifacts/rust-size-native/size"
RUST_WASM = ROOT / "artifacts/rust-size-wasm/wasm32-wasip1/size"
WASM_OPT_FLAGS = ["--enable-bulk-memory", "--enable-sign-ext", "--enable-mutable-globals",
                  "--enable-reference-types", "--enable-multivalue",
                  "--enable-nontrapping-float-to-int"]


def find_wasm_opt():
    for cand in (os.environ.get("WASM_OPT"), shutil.which("wasm-opt"),
                 "/tmp/binaryen/node_modules/.bin/wasm-opt"):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("wasm-opt not found; install binaryen or set WASM_OPT")


def build_rust():
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".cargo/bin") + ":" + env.get("PATH", "")
    for target_dir, extra in [
        (ROOT / "artifacts/rust-size-native", []),
        (ROOT / "artifacts/rust-size-wasm", ["--target", "wasm32-wasip1"]),
    ]:
        env["CARGO_TARGET_DIR"] = str(target_dir)
        subprocess.run(["cargo", "build", "--profile", "size", *extra], cwd=RUST,
                       env=env, check=True)


def strip_native(src):
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / src.name
        shutil.copy2(src, dst)
        subprocess.run(["strip", str(dst)], check=True)
        return dst.stat().st_size


def main():
    build_rust()
    wasm_opt = find_wasm_opt()
    rows = []
    for bench in BENCHES:
        sla_native = SLA_NATIVE / bench
        rust_native = RUST_NATIVE / bench
        sla_wasm = SLA_WASM / f"{bench}.wasm"
        rust_wasm = RUST_WASM / f"{bench}.wasm"
        for p in (sla_native, rust_native, sla_wasm, rust_wasm):
            if not p.exists():
                raise SystemExit(f"missing {p}; run scripts/bench.py first")

        sla_native_stripped = strip_native(sla_native)
        rust_native_stripped = strip_native(rust_native)

        sla_raw = sla_wasm.read_bytes()
        rust_raw = rust_wasm.read_bytes()
        sla_stripped = strip(sla_raw)
        rust_stripped = strip(rust_raw)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "sla.wasm").write_bytes(sla_stripped)
            (tmp / "rust.wasm").write_bytes(rust_stripped)
            subprocess.run([wasm_opt, str(tmp / "sla.wasm"), *WASM_OPT_FLAGS, "-Oz", "-o", str(tmp / "sla.opt.wasm")], check=True)
            subprocess.run([wasm_opt, str(tmp / "rust.wasm"), *WASM_OPT_FLAGS, "-Oz", "-o", str(tmp / "rust.opt.wasm")], check=True)
            sla_opt = (tmp / "sla.opt.wasm").stat().st_size
            rust_opt = (tmp / "rust.opt.wasm").stat().st_size

        rows.append({
            "bench": bench,
            "sla_native": sla_native_stripped,
            "rust_native": rust_native_stripped,
            "sla_wasm_raw": len(sla_raw),
            "sla_wasm_stripped": len(sla_stripped),
            "sla_wasm_opt": sla_opt,
            "rust_wasm_raw": len(rust_raw),
            "rust_wasm_stripped": len(rust_stripped),
            "rust_wasm_opt": rust_opt,
            "sla_wasm_best": min(len(sla_stripped), sla_opt),
            "rust_wasm_best": min(len(rust_stripped), rust_opt),
        })
    (RESULTS / "optimal_sizes.json").write_text(json.dumps(rows, indent=2) + "\n")
    print("wrote results/optimal_sizes.json")


if __name__ == "__main__":
    main()
