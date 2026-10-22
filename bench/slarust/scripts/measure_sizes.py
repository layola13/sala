#!/usr/bin/env python3
"""Measure raw vs deployable artifact sizes (strip native symbols / wasm custom debug+name)."""
import json
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
NATIVE = {"sla": ROOT / "artifacts/sla-native", "rust": ROOT / "benchmarks/rust/target/release"}
WASM = {"sla": ROOT / "artifacts/sla-wasm", "rust": ROOT / "benchmarks/rust/target/wasm32-wasip1/release"}


def native_rows():
    rows = []
    for bench in BENCHES:
        for lang, base in NATIVE.items():
            src = base / bench
            with tempfile.TemporaryDirectory() as tmp:
                dst = Path(tmp) / bench
                shutil.copy2(src, dst)
                subprocess.run(["strip", str(dst)], check=True)
                rows.append({"bench": bench, "lang": lang, "raw_bytes": src.stat().st_size,
                             "stripped_bytes": dst.stat().st_size})
    return rows


def wasm_rows():
    rows = []
    for bench in BENCHES:
        for lang, base in WASM.items():
            src = base / f"{bench}.wasm"
            data = strip(src.read_bytes())
            rows.append({"bench": bench, "lang": lang, "raw_bytes": src.stat().st_size,
                         "stripped_bytes": len(data)})
    return rows


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "native_stripped_sizes.json").write_text(
        json.dumps(native_rows(), indent=2) + "\n")
    (RESULTS / "stripped_sizes.json").write_text(
        json.dumps(wasm_rows(), indent=2) + "\n")
    print("wrote results/native_stripped_sizes.json and results/stripped_sizes.json")
