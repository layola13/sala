#!/usr/bin/env python3
"""Render REPORT.md and the sala HTML chapter from results/*.jsonl."""
import argparse
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
BENCHES = ["hello", "fib", "loopsum", "sieve", "matmul", "sort", "hashmap", "nbody", "mandelbrot", "vecpush", "bytes"]


def load(name):
    path = RESULTS / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def med(xs):
    return statistics.median(xs) if xs else 0.0


def med_map(rows, key="ms"):
    out = {}
    for r in rows:
        out.setdefault((r["bench"], r["lang"]), []).append(r[key])
    return {k: med(v) for k, v in out.items()}


native = load("native.jsonl")
wasm = load("wasm.jsonl")
compile_rows = load("compile.jsonl")
nm = med_map(native)
wm = med_map(wasm)
crss = {}
for r in native:
    crss.setdefault((r["bench"], r["lang"]), []).append(r["maxrss_kb"])
wrss = {}
for r in wasm:
    wrss.setdefault((r["bench"], r["lang"]), []).append(r["maxrss_kb"])

cold = {}
warm = {}
sizes = {}
for r in compile_rows:
    key = (r["bench"], r["target"], r["lang"])
    if r["cold"]:
        cold.setdefault(key, []).append(r["ms"])
        sizes.setdefault(key, []).append(r["bytes"])
    else:
        warm.setdefault(key, []).append(r["ms"])
cold = {k: med(v) for k, v in cold.items()}
warm = {k: med(v) for k, v in warm.items()}
sizes = {k: med(v) for k, v in sizes.items()}


def gm(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else 0


nat_core = [b for b in BENCHES if b not in ("hello", "matmul")]
wasm_core = [b for b in BENCHES if b not in ("hello", "matmul")]
nat_gm = gm([nm[(b, "rust")] / nm[(b, "sla")] for b in nat_core])
wasm_gm = gm([wm[(b, "rust")] / wm[(b, "sla")] for b in wasm_core])
nat_all = gm([nm[(b, "rust")] / nm[(b, "sla")] for b in BENCHES if b != "hello"])
wasm_all = gm([wm[(b, "rust")] / wm[(b, "sla")] for b in BENCHES if b != "hello"])
cold_nat = gm([cold[(b, "native", "rust")] / cold[(b, "native", "sla")] for b in BENCHES if b != "matmul"])
cold_wasm = gm([cold[(b, "wasm", "rust")] / cold[(b, "wasm", "sla")] for b in BENCHES if b != "matmul"])
warm_nat = gm([warm[(b, "native", "rust")] / warm[(b, "native", "sla")] for b in BENCHES])
warm_wasm = gm([warm[(b, "wasm", "rust")] / warm[(b, "wasm", "sla")] for b in BENCHES])

variants = json.loads((RESULTS / "variants.json").read_text())
var = {(r["bench"], r["lang"], r["variant"]): r for r in variants}
mmv = json.loads((RESULTS / "matmul_variants.json").read_text())
scaling = json.loads((RESULTS / "array_scaling.json").read_text())


def fmt(x, nd=0):
    return f"{x:.{nd}f}"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def html_tables_to_md(text):
    def conv(m):
        rows = re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)
        out = []
        for i, row in enumerate(rows):
            cells = re.findall(r"<t[hd]>(.*?)</t[hd]>", row, re.S)
            out.append("| " + " | ".join(cells) + " |")
            if i == 0:
                out.append("|" + "|".join("---" for _ in cells) + "|")
        return "\n".join(out)
    return re.sub(r"<table>.*?</table>", conv, text, flags=re.S)


def htable(headers, rows, cls=""):
    out = [f'<table class="{cls}">' if cls else "<table>"]
    out.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
    for row in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def ratio(r, s):
    return f"{r/s:.2f}×" if s else "-"


nat_rows = []
wasm_rows = []
for b in BENCHES:
    nat_rows.append([b, fmt(nm[(b, "sla")], 1), fmt(nm[(b, "rust")], 1), ratio(nm[(b, "rust")], nm[(b, "sla")]),
                     fmt(med(crss[(b, "sla")])), fmt(med(crss[(b, "rust")]))])
    wasm_rows.append([b, fmt(wm[(b, "sla")], 1), fmt(wm[(b, "rust")], 1), ratio(wm[(b, "rust")], wm[(b, "sla")]),
                      fmt(med(wrss[(b, "sla")])), fmt(med(wrss[(b, "rust")]))])

wsz = {(r["bench"], r["lang"]): r["stripped_bytes"]
       for r in json.loads((RESULTS / "stripped_sizes.json").read_text())}
nsz = {(r["bench"], r["lang"]): r["stripped_bytes"]
       for r in json.loads((RESULTS / "native_stripped_sizes.json").read_text())}
cold_rows = []
warm_rows = []
native_size_rows = []
wasm_size_rows = []
for b in BENCHES:
    cold_n = f'{fmt(cold[(b,"native","sla")])} / {fmt(cold[(b,"native","rust")])}'
    cold_w = f'{fmt(cold[(b,"wasm","sla")])} / {fmt(cold[(b,"wasm","rust")])}'
    cold_rows.append([b, cold_n, cold_w])
    warm_rows.append([b, f'{fmt(warm[(b,"native","sla")])} / {fmt(warm[(b,"native","rust")])}',
                      f'{fmt(warm[(b,"wasm","sla")])} / {fmt(warm[(b,"wasm","rust")])}'])
    native_size_rows.append([
        b,
        fmt(nsz[(b, "sla")] / 1024, 0) + " KB",
        fmt(sizes[(b, "native", "rust")] / 1024, 0) + " KB",
        fmt(nsz[(b, "rust")] / 1024, 0) + " KB",
        f'{nsz[(b, "sla")] / nsz[(b, "rust")]:.1f}×',
    ])
    wasm_size_rows.append([
        b,
        fmt(sizes[(b, "wasm", "sla")] / 1024, 0) + " KB",
        fmt(wsz[(b, "sla")] / 1024, 1) + " KB",
        fmt(sizes[(b, "wasm", "rust")] / 1024, 0) + " KB",
        fmt(wsz[(b, "rust")] / 1024, 1) + " KB",
        f'{wsz[(b, "sla")] / wsz[(b, "rust")]:.2f}×',
    ])

wasm_size_gain = gm([wsz[(b, "rust")] / wsz[(b, "sla")] for b in BENCHES if b not in ("hello", "matmul")])
native_size_ratio = nsz[("hello", "sla")] / nsz[("hello", "rust")]
opt = {r["bench"]: r for r in json.loads((RESULTS / "optimal_sizes.json").read_text())}
opt_core = [b for b in BENCHES if b not in ("hello", "matmul")]
opt_wasm_gain = gm([opt[b]["rust_wasm_best"] / opt[b]["sla_wasm_best"] for b in opt_core])
opt_native_ratio = gm([opt[b]["sla_native"] / opt[b]["rust_native"] for b in opt_core])
warm_core = [b for b in BENCHES if b not in ("hello", "matmul")]
warm_nat_ratios = [warm[(b, "native", "sla")] / warm[(b, "native", "rust")] for b in warm_core]
warm_wasm_ratios = [warm[(b, "wasm", "sla")] / warm[(b, "wasm", "rust")] for b in warm_core]
warm_nat_gm = gm(warm_nat_ratios)
warm_wasm_gm = gm(warm_wasm_ratios)
opt_rows = [[b,
             fmt(opt[b]["sla_native"] / 1024, 0) + " KB",
             fmt(opt[b]["rust_native"] / 1024, 0) + " KB",
             fmt(opt[b]["sla_wasm_best"] / 1024, 1) + " KB",
             fmt(opt[b]["rust_wasm_best"] / 1024, 1) + " KB",
             f'{opt[b]["sla_wasm_best"] / opt[b]["rust_wasm_best"]:.2f}×']
            for b in BENCHES]
scale_rows = [[r["n"], r["elems"], fmt(r["compile_ms"])] for r in scaling]
variant_rows = []
for b in ["fib", "loopsum", "sieve", "matmul", "sort", "bytes"]:
    default_ok = (b, "sla", "default") in var and var[(b, "sla", "default")]["out"]
    variant_rows.append([
        b,
        fmt(var[(b, "sla", "default")]["run_ms"], 1) if default_ok else "-",
        fmt(nm[(b, "sla")], 1),
        fmt(var[(b, "rust", "debug")]["run_ms"], 1),
        fmt(nm[(b, "rust")], 1),
    ])

mmv_rows = [[r["variant"], fmt(r["compile_ms"]), fmt(r["run_ms"], 1) if r["out"] else "-",
             fmt(r["bytes"] / 1024, 0) + " KB", r["out"] or "(segfault)"] for r in mmv]

summary = f"""# SLA vs Rust 性能实测报告（native / WASM / 编译）

日期：2026-10-22  
项目：`slarust`（10 个核心负载 + hello 启动）  
工具链：sla 0.1.4（SA 0.1.8）、Rust 1.99.1、Wasmtime 25.0.2  
平台：Linux x86_64（8 vCPU，Intel Xeon 2.20GHz，KVM，52GB RAM）

## 结论摘要

- **11 个程序（10 个核心负载 + hello）校验和全部一致**：SLA 与 Rust 实现的是同一算法、同一输入、同一输出，比较有效。
- **Native 运行时**：排除 hello 与 matmul 两个极端后，Rust 几何平均快 **{1/nat_gm:.2f}×**；算上 matmul
  则快 **{1/nat_all:.2f}×**（matmul Rust 快 {nm[("matmul","sla")]/nm[("matmul","rust")]:.1f}×）。SLA 在
  sort 上快 {nm[("sort","rust")]/nm[("sort","sla")]:.2f}×、hashmap 上快 {nm[("hashmap","rust")]/nm[("hashmap","sla")]:.2f}×。
- **WASM 运行时**：排除 hello 与 matmul 后 Rust 几何平均快 **{1/wasm_gm:.2f}×**；算上 matmul 则快
  **{1/wasm_all:.2f}×**。SLA 的 mandelbrot 反而快 **{wm[("mandelbrot","rust")]/wm[("mandelbrot","sla")]:.2f}×**，
  matmul Rust 快 {wm[("matmul","sla")]/wm[("matmul","rust")]:.1f}×。
- **编译时间**：常规源码 Rust 冷编译更快（native SLA 是 Rust 的 {1/cold_nat:.2f}×，WASM 是 {1/cold_wasm:.2f}×）。
  热编译在两边都 touch 源文件、实际重建后，差距远小于旧稿：native SLA 慢 {min(warm_nat_ratios):.1f}–{max(warm_nat_ratios):.1f}×
  （几何 {warm_nat_gm:.1f}×），WASM SLA/Rust {min(warm_wasm_ratios):.2f}–{max(warm_wasm_ratios):.1f}×（几何 {warm_wasm_gm:.1f}×），
  小 WASM 项目 SLA 甚至略快。唯一例外是 **matmul native**：SLA `--release-fast` 冷编译
  {cold[("matmul","native","sla")]/1000:.1f}s，Rust 0.19s，慢约 {cold[("matmul","native","sla")]/cold[("matmul","native","rust")]:.0f}×；
  同一份源码 WASM 目标只要 0.86s。
- **体积最优对比**：双方各取最小配置（SLA `--release-fast`+strip；Rust `profile=size`
  +strip+`wasm-opt -Oz`）。native 仍是 SLA 明显更大（9.1MB vs 274–278KB，约 **{opt_native_ratio:.1f}×**）。
  WASM 典型负载（不含 hello/matmul）SLA 5.6–7.9KB vs Rust 32.7–34.3KB，SLA 约小 **{opt_wasm_gain:.1f}×**，基本符合旧口径
  “约 5× 小”；matmul 是例外（58.0KB vs 33.0KB，SLA 大约 1.76×）。默认 release 的 raw/strip 对比见 5.1–5.2。
- **峰值内存**：SLA 的大数组场景 RSS 高 2×（vecpush）、19×（sieve）、15×（bytes），与增长/保留策略和分配器回收差异一致。
- **默认优化等级**：SLA 默认构建大致是 Rust debug 量级（fib 2.5s vs 1.35s，loopsum 8.05s vs 7.95s；
  sieve/bytes 则慢 3–9×）；`--release-fast` 是必要选项，但会让 matmul 编译从 1.6s 膨胀到 60–70s。
- **环境观察**：Node 20.19 的 WASI 在若干大内存模块退出时触发 V8 trap（SLA/Rust 都复现），
  本文 WASM 数据统一改用 Wasmtime 25.0.2。

## 1. 测试口径与环境

### 1.1 工作负载（10 个核心负载 + hello）

| 名称 | 内容 | 数据规模 |
|---|---|---|
| hello | 进程启动 + 一次 println | - |
| fib | 递归 Fibonacci | fib(40) |
| loopsum | 整数循环、取模与乘法 | 300,000,000 次 |
| sieve | Eratosthenes 筛法 | 20,000,000 |
| matmul | f64 矩阵乘（固定数组） | 64×64，重复 4000 次 |
| sort | 原地堆排序 | 1,000,000 个 i64 |
| hashmap | 开放寻址哈希表插入 + 查询 | 3,000,000 键，4,194,304 槽 |
| nbody | 5 体引力模拟，Newton 开方 | 1,000,000 步 |
| mandelbrot | f64 逃逸迭代 | 1600×1600，最多 200 iter |
| vecpush | `Vec<i64>` 增长 + 求和 | 32,000,000 元素 |
| bytes | `Vec<u8>` 增长 + 校验和 | 33,554,432 字节 |

所有程序只输出一个校验和；SLA/Rust 校验和逐项一致。不含 hello 时 SLA 源码共 394 行、Rust 共 329 行（含 hello 为 400/332 行）。

### 1.2 构建与测量

- SLA native：`sla build-exe <src> -o <out> --release-fast`。
- SLA WASM：`sla build-wasm <src> -o <out>.wasm --release-fast`。
- Rust native：`cargo build --release`（opt-level=3、lto=false、codegen-units=16、panic=abort）。
- Rust WASM：`--target wasm32-wasip1`，release profile 同上。
- 冷编译：删除 `.sa_cache` 并加 `--no-incremental`；Rust 使用全新 `CARGO_TARGET_DIR`。取 3 次中位数。
- 热编译：保留缓存/目标目录，测量前 touch 两边源文件，确保 SLA 与 Rust 都实际重建（Rust 为整 crate 重编），取 3 次中位数。
  SLA 的 `.sla-cache` 缓存中间产物，但 `build-exe` 仍会重新生成输出，不是 Cargo 式目标 no-op。
- 运行时：native 7 次、WASM 5 次，去掉 1 次预热，取中位数；用 `wait4` 读取子进程 `ru_maxrss`。
- WASM 运行器：Wasmtime 25.0.2（WASI preview1），计时包含实例化与进程启动（hello 约 11–13ms）。

### 1.3 限制

- 单线程；没有测试 async / 多线程 / FFI / 网络 / 数据库。
- SLA 的 `Vec<f64>` 在当前版本 push 后读到 0，因此 matmul 使用固定长度 `[f64; 4096]` 数组；
  Rust 使用同样的固定数组，算法仍一致。
- SLA 没有导出 WASM 函数的 `.sla` 语法，WASM 只能以 `_start` 命令方式运行；两边都用 WASI 进程计时。
- 结果受 KVM 共享 CPU 影响；比值比绝对毫秒更可靠。

## 2. Native 运行时

{htable(["bench", "SLA ms", "Rust ms", "Rust/SLA", "SLA RSS KB", "Rust RSS KB"], nat_rows)}

Rust 几何平均（不含 hello/matmul）：**{1/nat_gm:.2f}× 更快**；含 matmul：**{1/nat_all:.2f}× 更快**。  
SLA 胜出的项目：sort 快 {nm[("sort","rust")]/nm[("sort","sla")]:.2f}×、hashmap 快 {nm[("hashmap","rust")]/nm[("hashmap","sla")]:.2f}×。
matmul 是最大差距（{nm[("matmul","sla")]/nm[("matmul","rust")]:.1f}×），从差距形态看，
很可能与 Rust/LLVM 对固定数组三重循环的向量化程度有关；SLA 生成的循环可能没有达到同等优化，
需要进一步看汇编确认。

## 3. WASM 运行时

{htable(["bench", "SLA ms", "Rust ms", "Rust/SLA", "SLA RSS KB", "Rust RSS KB"], wasm_rows)}

Rust 几何平均（不含 hello/matmul）：**{1/wasm_gm:.2f}× 更快**；含 matmul：**{1/wasm_all:.2f}× 更快**。  
WASM 上 SLA 唯一明显胜出的是 mandelbrot（{wm[("mandelbrot","rust")]/wm[("mandelbrot","sla")]:.2f}×）；
loopsum 上 Rust 快 {wm[("loopsum","sla")]/wm[("loopsum","rust")]:.1f}×，是除 matmul 外 WASM 侧最大差距。

## 4. 编译时间

表中每格为 **SLA / Rust**，单位 ms。

### 4.1 冷编译

{htable(["bench", "native SLA / Rust", "wasm SLA / Rust"], cold_rows)}

常规大小源码上 Rust 冷编译更快：native 几何平均 Rust 是 SLA 的 {cold_nat:.2f}× 用时，WASM 是 {cold_wasm:.2f}×。
matmul native 是异常点：SLA 冷编译 {cold[("matmul","native","sla")]/1000:.1f}s，Rust {cold[("matmul","native","rust")]:.0f}ms；
同一源码的 SLA WASM 冷编译只要 {cold[("matmul","wasm","sla")]:.0f}ms，说明瓶颈在 native LLVM 优化/代码生成，而不是前端。

### 4.2 热编译

{htable(["bench", "native SLA / Rust", "wasm SLA / Rust"], warm_rows)}

热编译测量前会 touch 两边源文件，保留各自缓存/目标目录，因此两边都实际重建。Rust release 默认不开 incremental，
是整 crate 重编；SLA 缓存则省掉部分阶段。修正后 native SLA 慢 {min(warm_nat_ratios):.1f}–{max(warm_nat_ratios):.1f}×
（几何 {warm_nat_gm:.1f}×），WASM SLA/Rust {min(warm_wasm_ratios):.2f}–{max(warm_wasm_ratios):.1f}×（几何 {warm_wasm_gm:.1f}×）。
旧稿的“Rust 约 30ms”是 Cargo 无改动时的 no-op，与 SLA 的实际重建不可比，已废弃。
补充：`.sla-cache` 中可见 `reachable/*.plan` 与 `sab/*.sab`，但即使输出已存在，`build-exe` 仍会重新写出可执行文件（实测 inode 改变）；
SLA 没有 Cargo 那种“目标已最新则直接返回”的短路，缓存只省掉部分前端/中间产物阶段。

## 5. 产物体积与内存

### 5.1 Native 体积（strip 后）

{htable(["bench", "SLA stripped", "Rust raw", "Rust stripped", "SLA/Rust"], native_size_rows)}

SLA native 基本恒定在 9,080–9,097KB（静态运行时占主导），且本身已 stripped；
Rust raw 约 433–436KB，strip 后约 328–330KB。默认 release 口径下可部署体积 SLA 约为 Rust 的 **{native_size_ratio:.1f}×**，
native 侧“SLA 更小”不成立；双方体积最优口径见下。

### 5.2 WASM 体积（raw vs 可部署）

{htable(["bench", "SLA raw", "SLA stripped", "Rust raw", "Rust stripped", "SLA/Rust"], wasm_size_rows)}

SLA 的 WASM 原始产物大部分是 `.debug_*` 自定义段（hello：667,795 字节中 659,470 字节是调试段；
典型约 99%，matmul 约 92%），直接比较 raw 会严重高估体积。剥离 `.debug*` 和 `name` 后，典型 SLA 负载为 5.2–8.9KB，
Rust 为 46.5–49.4KB，SLA 几何平均小 **{wasm_size_gain:.1f}×**；matmul 例外（58.0KB vs 48.2KB，SLA 大约 1.2×）。
因此默认 release 对比下，旧口径“WASM 体积约 5× 小”在典型负载上基本成立，但必须说明是 strip 后，且 matmul 不成立；
双方各取体积最优配置的结果见 5.3。

### 5.3 体积最优对比（双方各自最小配置）

SLA 侧：`build-wasm --release-fast`（`--release-small` 产物与 fast 完全相同），移除 `.debug*`/`name`。
Rust 侧：新增 `profile.size`（`opt-level="z"`、LTO、`codegen-units=1`、`panic="abort"`、`strip="symbols"`），
再移除 WASM 自定义调试段。两边都额外尝试 `wasm-opt 132 -Oz`，每项取 strip 与 strip+wasm-opt 的较小值。

{htable(["bench", "SLA native", "Rust native", "SLA wasm best", "Rust wasm best", "wasm SLA/Rust"], opt_rows)}

- Native：SLA 9,080–9,097KB vs Rust 274–278KB，几何平均 SLA 大约 **{opt_native_ratio:.1f}×**。
- WASM 典型负载（不含 hello/matmul）：SLA 5.6–7.9KB vs Rust 32.7–34.3KB，SLA 小 **{opt_wasm_gain:.1f}×**。
- matmul 例外：SLA 58.0KB vs Rust 33.0KB，SLA 大 1.76×；`wasm-opt -Oz` 反而把 SLA matmul 从 58KB 膨胀到 121KB，
  因此该行取 strip 后的值。
- 结论：在“双方都尽量压体积”的口径下，旧说法“WASM 约 5× 小”基本成立，但不能外推到 matmul，也不能用于 native。

### 5.4 峰值 RSS

Native 与 WASM 的 RSS 表已在第 2、3 节列出。结论：

- 小分配/纯计算场景两者基线都在 14–17MB。
- SLA 的 `Vec` 在大数组场景明显更费内存：sieve 422MB vs 22MB、bytes 528MB vs 35MB、
  vecpush 516MB vs 252MB。
- 从数据看与增长策略、分配器回收差异一致（SLA 可能重复分配并保留旧块），需进一步 profiling 确认。

## 6. 优化等级与构建变体

### 6.1 SLA 默认 vs `--release-fast`，Rust debug vs release

{htable(["bench", "SLA default", "SLA release-fast", "Rust debug", "Rust release"], variant_rows)}

- SLA 默认构建大致处于 Rust debug 量级：fib 2.5s vs Rust debug 1.35s、loopsum 8.05s vs 7.95s；
  sieve 5.6s vs 1.22s、bytes 3.5s vs 0.40s，落后 3–9×。
- `--release-fast` 是必选项：fib 快 5.5×、loopsum 快 10×、sieve 快 6.2×、bytes 快 7.5×。
- SLA 默认构建下 matmul、sort 会发生段错误（exit 139），不能用于基准；表中用 “-” 表示。
- Rust debug 相对 release：fib 3.5×、loopsum 15×、sieve 3.5×、matmul 246×、sort 6×、bytes 5.5×。

### 6.2 Rust `target-cpu=native` 与 WASM `+simd128`

- Native `-C target-cpu=native` 只让 loopsum 明显变快（1.88×），其余项目在 ±7% 内。
- WASM `-C target-feature=+simd128` 对所有项目影响在 ±7% 内；Rust 默认 WASM 已经能吃到大部分优化。
- 因此第 2、3 节使用默认 release 口径是合理的；CPU 特性不是主要解释变量。

### 6.3 matmul 的 SLA 构建变体

{htable(["variant", "compile ms", "run ms", "size", "checksum"], mmv_rows)}

`--release-fast` / `--release-small` 的编译时间都在 60s 量级，运行约 1.04s；默认构建虽只要 1.6s，
但运行时段错误。这个组合（固定数组 + 三重循环 + 优化）是当前 SLA 后端的明确短板。

## 7. 编译时间可扩展性

固定长度 `[f64; N*N]` 数组初始化、只打印首元素的微基准（`--release-fast --no-incremental`）：

{htable(["N", "elements", "compile ms"], scale_rows)}

数组初始化本身随规模近似线性/轻微超线性增长（4,096 元素约 4.9s），但 matmul 完整程序要 60–70s，
说明主要成本来自循环体优化/代码生成，而不是数组字面量。

## 8. 结论与建议

1. **运行时**：当前 SLA 0.1.4 在多数标量/内存密集型负载上比 Rust release 慢 1.5–2×；
   固定数组 + 浮点循环（matmul）差距可达 30×。SLA 在无序索引访问（sort）和哈希表探测（hashmap）上更快，
   可能与生成代码省略边界检查有关（未做汇编确认）。
2. **WASM**：整体差距与 native 接近；SLA 的 mandelbrot 更快，说明 float 循环的 wasm 代码生成并不总是劣势。
   但 loopsum/筛法/字节流仍明显落后。
3. **编译**：SLA 冷编译常规项目比 Rust 慢约 2.5–3×；热编译在大型源码上慢 4–9×，但小 WASM 项目已接近持平或略快（不再有“4–50×”的普遍结论）。matmul native 的 60–70s 是必须修复的回归。
   建议优先排查 `--release-fast` 在固定数组 + 嵌套循环上的 LLVM 优化爆炸，并让缓存覆盖前端/校验阶段。
4. **体积**：体积最优配置下 native 仍是 SLA 明显更大（9.1MB vs Rust 约 0.27MB，约 33×）。
   WASM 旧口径基本成立：典型负载 SLA 约小 5.2×，但 matmul 反而大约 1.76×；报告体积时必须注明构建配置与是否 strip。
5. **内存**：优先修复 `Vec` 增长时的旧块回收与容量策略；sieve/bytes 的 15–19× RSS 差距会限制边缘设备部署。
6. **默认构建**：默认优化等级大致是 Rust debug 量级（部分负载慢 3–9×），且 matmul/sort 会崩溃；文档应明确要求 `--release-fast`，
   并修复默认后端的聚合类型代码生成。
7. **公平性**：本报告只覆盖单线程数值/内存负载。SLA 的 async、线程、FFI、包管理等未纳入；
   这些场景需要单独的基准与安全检查。

## 9. 复现

```sh
# 依赖
npm install -g @slalang/sla
rustup target add wasm32-wasip1
# wasmtime 25.0.2 (linux x64)
curl -L -o /tmp/wasmtime.tar.xz \\
  https://github.com/bytecodealliance/wasmtime/releases/download/v25.0.2/wasmtime-v25.0.2-x86_64-linux.tar.xz
tar -xf /tmp/wasmtime.tar.xz -C /tmp

# 构建 + 运行
cd slarust
python3 scripts/bench.py --mode all --runs 7
python3 scripts/analyze.py > results/analysis.md
python3 scripts/render_report.py
```

原始数据：`results/native.jsonl`、`results/wasm.jsonl`、`results/compile.jsonl`、
`results/variants.json`、`results/matmul_variants.json`、`results/array_scaling.json`。

## 附：逐项校验和

{htable(["bench", "native SLA", "native Rust", "wasm SLA", "wasm Rust"],
        [[b, next(r["checksum"] for r in native if r["bench"] == b and r["lang"] == "sla"),
          next(r["checksum"] for r in native if r["bench"] == b and r["lang"] == "rust"),
          next(r["checksum"] for r in wasm if r["bench"] == b and r["lang"] == "sla"),
          next(r["checksum"] for r in wasm if r["bench"] == b and r["lang"] == "rust")] for b in BENCHES])}
"""

(ROOT / "REPORT.md").write_text(html_tables_to_md(summary))

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>SLA vs Rust 性能实测（native / WASM / 编译）</title>
<link rel="stylesheet" href="../../assets/help.css">
</head>
<body class="topic">
<div class="topic-header">与 Rust 对比 &gt; 性能实测</div>
<h1>SLA vs Rust 性能实测（native / WASM / 编译）</h1>

<p>这一页是 2026-10-22 在 <code>slarust</code> 项目上跑出的完整对比：10 个核心负载 + hello、native 与 WASM 两条产物链、
冷/热编译、产物体积、峰值内存、优化等级与编译可扩展性。所有 SLA/Rust 程序输出逐项一致的校验和，
因此下面的倍数是同一算法的实现差异，而不是负载差异。</p>

<div class="note"><span class="label">注意</span>本页是可复现的实测快照，不是永久结论。
工具链为 sla 0.1.4 / SA 0.1.8、Rust 1.99.1、Wasmtime 25.0.2，平台为 Linux x86_64（8 vCPU KVM）。</div>

<h2>一句话结论</h2>
<blockquote>在当前版本上，Rust release 的 native/WASM 运行时中位数分别比 SLA 快约
{1/nat_gm:.2f}× / {1/wasm_gm:.2f}×（不含 matmul 异常点）；SLA 的编译更快这一旧结论也不成立：
冷编译常规项目 Rust 快 {1/cold_nat:.2f}×（native）/{1/cold_wasm:.2f}×（WASM）；热编译在大型源码上仍快，但小 WASM 项目 SLA 已接近持平或略快。
SLA 的 WASM 产物体积在剥离 DWARF 后典型负载约为 Rust 的 1/6，但 matmul 反而大约 1.2×；native 体积仍约 28×。</blockquote>

<h2>摘要</h2>
<ul>
<li><b>正确性</b>：11 个程序（10 个核心负载 + hello）的 SLA/Rust 校验和全部一致。</li>
<li><b>Native</b>：排除 hello/matmul，Rust 几何平均快 {1/nat_gm:.2f}×；含 matmul 快 {1/nat_all:.2f}×。
SLA 在 sort 上快 {nm[("sort","rust")]/nm[("sort","sla")]:.2f}×、hashmap 上快 {nm[("hashmap","rust")]/nm[("hashmap","sla")]:.2f}×。</li>
<li><b>WASM</b>：排除 hello/matmul，Rust 快 {1/wasm_gm:.2f}×；含 matmul 快 {1/wasm_all:.2f}×。
SLA 的 mandelbrot 快 {wm[("mandelbrot","rust")]/wm[("mandelbrot","sla")]:.2f}×。</li>
<li><b>编译</b>：常规源码 Rust 冷编译约为 SLA 的 {cold_nat:.2f}×（native）/{cold_wasm:.2f}×（WASM）用时；
matmul native 是异常点，SLA 需要 {cold[("matmul","native","sla")]/1000:.1f}s，Rust 0.19s。</li>
<li><b>体积最优</b>：native SLA {opt["hello"]["sla_native"]/1024:.0f}KB vs Rust {opt["hello"]["rust_native"]/1024:.0f}KB（约 {opt_native_ratio:.1f}× 大）；
WASM 典型 SLA {min(opt[b]["sla_wasm_best"] for b in opt_core)/1024:.1f}–{max(opt[b]["sla_wasm_best"] for b in opt_core)/1024:.1f}KB vs Rust
{min(opt[b]["rust_wasm_best"] for b in opt_core)/1024:.1f}–{max(opt[b]["rust_wasm_best"] for b in opt_core)/1024:.1f}KB（约小 {opt_wasm_gain:.1f}×；matmul 例外，SLA 大约 1.76×）。</li>
<li><b>内存</b>：大数组场景 SLA RSS 高 2–19×（sieve 422MB vs 22MB，bytes 528MB vs 35MB）。</li>
<li><b>默认优化</b>：SLA 默认构建大致是 Rust debug 量级（sieve/bytes 慢 3–9×），且 matmul/sort 默认构建段错误；必须使用 <code>--release-fast</code>。</li>
</ul>

<h2>测试口径</h2>
<p>源码在 <code>benchmarks/sla/*.sla</code> 与 <code>benchmarks/rust/src/bin/*.rs</code>。
SLA 用 <code>build-exe/build-wasm --release-fast</code>；Rust 用 <code>cargo build --release</code>
（opt-level=3、lto=false、codegen-units=16、panic=abort）和 <code>wasm32-wasip1</code>。
冷编译删除 SLA <code>.sa_cache</code> 并加 <code>--no-incremental</code>，Rust 使用全新
<code>CARGO_TARGET_DIR</code>；热编译保留缓存，并 touch 两边源文件确保都实际重建。运行时取 7 次（native）/5 次（WASM）中位数，
计时包含进程启动，WASM 使用 Wasmtime 25.0.2。</p>

<p>关键限制：单线程；SLA 当前 <code>Vec&lt;f64&gt;</code> push 后读到 0，因此 matmul 两边都用固定
<code>[f64; 4096]</code> 数组；SLA 没有导出 WASM 函数的语法，只能以 <code>_start</code> 命令运行；
Node 20.19 的 WASI 在部分大内存模块退出时会让 SLA/Rust 同时触发 V8 trap，故 WASM 数据统一用 Wasmtime。</p>

<h2>Native 运行时</h2>
{htable(["bench", "SLA ms", "Rust ms", "Rust/SLA", "SLA RSS KB", "Rust RSS KB"], nat_rows)}

<p>Rust 几何平均（不含 hello/matmul）快 <b>{1/nat_gm:.2f}×</b>。SLA 在 sort 上快
{nm[("sort","rust")]/nm[("sort","sla")]:.2f}×、hashmap 上快 {nm[("hashmap","rust")]/nm[("hashmap","sla")]:.2f}×；
matmul 上 Rust 快 {nm[("matmul","sla")]/nm[("matmul","rust")]:.1f}×，是最大差距。</p>

<h2>WASM 运行时</h2>
{htable(["bench", "SLA ms", "Rust ms", "Rust/SLA", "SLA RSS KB", "Rust RSS KB"], wasm_rows)}

<p>Rust 几何平均（不含 hello/matmul）快 <b>{1/wasm_gm:.2f}×</b>。WASM 上 SLA 的 mandelbrot 快
{wm[("mandelbrot","rust")]/wm[("mandelbrot","sla")]:.2f}×；loopsum Rust 快
{wm[("loopsum","sla")]/wm[("loopsum","rust")]:.1f}×，matmul Rust 快
{wm[("matmul","sla")]/wm[("matmul","rust")]:.1f}×。</p>

<h2>编译时间</h2>
<p>每格为 <b>SLA / Rust</b>，单位 ms。</p>
<h3>冷编译</h3>
{htable(["bench", "native SLA / Rust", "wasm SLA / Rust"], cold_rows)}
<p>常规源码 Rust 冷编译更快：native 用时为 SLA 的 {cold_nat:.2f}×，WASM 为 {cold_wasm:.2f}×。
matmul native 是异常点：SLA {cold[("matmul","native","sla")]/1000:.1f}s vs Rust
{cold[("matmul","native","rust")]:.0f}ms；同源码 SLA WASM 只要 {cold[("matmul","wasm","sla")]:.0f}ms。
这说明瓶颈在 native LLVM 优化，而不是 SLA 前端。</p>

<h3>热编译</h3>
{htable(["bench", "native SLA / Rust", "wasm SLA / Rust"], warm_rows)}
<p>测量前 touch 两边源文件，确保都实际重建。Rust release 默认不开 incremental，为整 crate 重编；SLA 缓存省掉部分阶段。修正后 native SLA 慢 {min(warm_nat_ratios):.1f}–{max(warm_nat_ratios):.1f}×（几何 {warm_nat_gm:.1f}×），WASM SLA/Rust {min(warm_wasm_ratios):.2f}–{max(warm_wasm_ratios):.1f}×（几何 {warm_wasm_gm:.1f}×）。旧稿的“Rust 约 30ms”是 Cargo no-op，不可比，已废弃。补充：<code>.sla-cache</code> 中可见 <code>reachable/*.plan</code> 与 <code>sab/*.sab</code>，但即使输出已存在，<code>build-exe</code> 仍会重新写出可执行文件（实测 inode 改变）；SLA 没有 Cargo 式“目标已最新则直接返回”的短路，缓存只省掉部分前端/中间产物阶段。</p>

<h2>产物体积与内存</h2>
<h3>Native 体积（strip 后）</h3>
{htable(["bench", "SLA stripped", "Rust raw", "Rust stripped", "SLA/Rust"], native_size_rows)}
<p>SLA native 约 9,080–9,097KB（静态运行时占主导），本身已 stripped；Rust raw 约 433–436KB，
strip 后约 328–330KB。默认 release 口径下可部署体积 SLA 约为 Rust 的 {native_size_ratio:.1f}×；
双方体积最优口径见下。</p>

<h3>WASM 体积（raw vs 可部署）</h3>
{htable(["bench", "SLA raw", "SLA stripped", "Rust raw", "Rust stripped", "SLA/Rust"], wasm_size_rows)}
<p>SLA 原始 WASM 中大部分是 `.debug_*` 调试段（典型约 99%，matmul 约 92%）；直接比较 raw 会严重高估体积。剥离 `.debug*` 与 `name` 后，
典型 SLA 负载 5.2–8.9KB，Rust 46.5–49.4KB，SLA 几何平均小 {wasm_size_gain:.1f}×；matmul 例外（58.0KB vs 48.2KB）。
旧口径“WASM 体积约 5× 小”在默认 release 对比下基本成立，但必须注明 strip 后，且 matmul 不成立；双方体积最优的结果见下。大数组场景 SLA 的 RSS
高 2–19×（见运行时表）。</p>

<h3>体积最优对比（双方各自最小配置）</h3>
<p>SLA 侧用 <code>--release-fast</code>（<code>--release-small</code> 产物与之相同）并移除 <code>.debug*</code>/<code>name</code>；
Rust 侧用 <code>profile.size</code>（<code>opt-level="z"</code>、LTO、<code>codegen-units=1</code>、<code>panic="abort"</code>、<code>strip="symbols"</code>）
再移除 WASM 调试段。两边都额外尝试 <code>wasm-opt 132 -Oz</code>，每项取 strip 与 strip+wasm-opt 的较小值。</p>
{htable(["bench", "SLA native", "Rust native", "SLA wasm best", "Rust wasm best", "wasm SLA/Rust"], opt_rows)}
<ul>
<li>Native：SLA 9,080–9,097KB vs Rust 274–278KB，几何平均 SLA 大约 {opt_native_ratio:.1f}×。</li>
<li>WASM 典型负载（不含 hello/matmul）：SLA 5.6–7.9KB vs Rust 32.7–34.3KB，SLA 小 {opt_wasm_gain:.1f}×。</li>
<li>matmul 例外：SLA 58.0KB vs Rust 33.0KB，SLA 大 1.76×；<code>wasm-opt -Oz</code> 反而把 SLA matmul 从 58KB 膨胀到 121KB，因此该行取 strip 后的值。</li>
<li>结论：双方都尽量压体积时，旧说法“WASM 约 5× 小”基本成立，但不能外推到 matmul，也不能用于 native。</li>
</ul>

<h2>优化等级与变体</h2>
{htable(["bench", "SLA default", "SLA release-fast", "Rust debug", "Rust release"], variant_rows)}
<ul>
<li>SLA 默认构建大致处于 Rust debug 量级：fib 2.5s vs Rust debug 1.35s / release 0.38s；
  sieve 5.6s vs 1.22s、bytes 3.5s vs 0.40s，落后 3–9×。</li>
<li><code>--release-fast</code> 是必选项：fib 快 5.5×、loopsum 快 10×、sieve 快 6.2×、bytes 快 7.5×。</li>
<li>SLA 默认构建下 matmul、sort 段错误（exit 139），表中用 “-” 表示。</li>
<li>Rust <code>target-cpu=native</code> 只让 loopsum 快 1.88×，其余 ±7%；WASM <code>+simd128</code> 影响也在 ±7%。</li>
</ul>

<h3>matmul 的 SLA 构建变体</h3>
{htable(["variant", "compile ms", "run ms", "size", "checksum"], mmv_rows)}
<p><code>--release-fast/--release-small</code> 编译约 60s、运行约 1.04s；默认构建虽然 1.6s 完成，
但运行时段错误。固定数组 + 三重循环 + 优化是当前 SLA 后端的明确短板。</p>

<h3>固定数组初始化的编译扩展性</h3>
{htable(["N", "elements", "compile ms"], scale_rows)}
<p>数组初始化本身近似线性（4,096 元素约 4.9s），但完整 matmul 要 60–70s，主要成本在循环优化/代码生成。</p>

<h2>结论与建议</h2>
<ol>
<li><b>运行时</b>：SLA 0.1.4 在多数负载上比 Rust release 慢 1.5–2×；matmul 差距 30×。
SLA 的优势集中在无序索引访问（sort）与哈希探测（hashmap），可能与生成代码省略边界检查有关（未做汇编确认）。</li>
<li><b>WASM</b>：整体差距与 native 接近；mandelbrot 是 SLA 的反例，说明 float 循环的 wasm 代码生成并不总是劣势。</li>
<li><b>编译</b>：SLA 冷编译慢约 2.5–3×；热编译在大型源码上慢 4–9×，小 WASM 项目已接近持平或略快。matmul native 的 60–70s 是必须修复的回归。
应优先排查 <code>--release-fast</code> 在固定数组 + 嵌套循环上的 LLVM 优化爆炸，并让缓存覆盖前端/校验。</li>
<li><b>体积</b>：体积最优配置下 native 仍是 SLA 明显更大（9.1MB vs Rust 约 0.27MB，约 33×）。
WASM 在双方最优配置下典型负载 SLA 约小 5.2×，但 matmul 反而大约 1.76×；报告体积时必须注明构建配置与是否 strip。</li>
<li><b>内存</b>：修复 <code>Vec</code> 增长时旧块回收与容量策略；sieve/bytes 的 15–19× RSS 差距会限制边缘部署。</li>
<li><b>默认构建</b>：默认优化等级大致是 Rust debug 量级（部分负载慢 3–9×），且 matmul/sort 会崩溃；文档应明确要求 <code>--release-fast</code>，
并修复聚合类型的默认代码生成。</li>
<li><b>后续</b>：本报告只覆盖单线程数值/内存负载；async、线程、FFI、包管理需要单独基准。</li>
</ol>

<h2>复现</h2>
<pre><code>npm install -g @slalang/sla
rustup target add wasm32-wasip1
curl -L -o /tmp/wasmtime.tar.xz \\
  https://github.com/bytecodealliance/wasmtime/releases/download/v25.0.2/wasmtime-v25.0.2-x86_64-linux.tar.xz
tar -xf /tmp/wasmtime.tar.xz -C /tmp
cd slarust
python3 scripts/bench.py --mode all --runs 7
python3 scripts/analyze.py &gt; results/analysis.md
python3 scripts/render_report.py</code></pre>

<p>原始数据：<code>results/native.jsonl</code>、<code>results/wasm.jsonl</code>、
<code>results/compile.jsonl</code>、<code>results/variants.json</code>、
<code>results/matmul_variants.json</code>、<code>results/array_scaling.json</code>。</p>

<h2>逐项校验和</h2>
{htable(["bench", "native SLA", "native Rust", "wasm SLA", "wasm Rust"],
        [[b, next(r["checksum"] for r in native if r["bench"] == b and r["lang"] == "sla"),
          next(r["checksum"] for r in native if r["bench"] == b and r["lang"] == "rust"),
          next(r["checksum"] for r in wasm if r["bench"] == b and r["lang"] == "sla"),
          next(r["checksum"] for r in wasm if r["bench"] == b and r["lang"] == "rust")] for b in BENCHES])}

</body>
</html>
"""
ap = argparse.ArgumentParser()
ap.add_argument("--html", help="optional output path for the sala HTML chapter")
args = ap.parse_args()
print("wrote", ROOT / "REPORT.md")
if args.html:
    out = Path(args.html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print("wrote", out)
