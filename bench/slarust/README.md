# slarust：SLA vs Rust 性能基准

2026-10-22 的 10 个工作负载对比，覆盖 native、WASM、冷/热编译、产物体积、峰值 RSS 与优化等级。
完整报告见 [REPORT.md](REPORT.md)；sala 章节版本是仓库中的
`content/09_rust_compare/09_performance.html`（本基准项目也复制在 `bench/slarust/`）。

## 结论速览

- 校验和全部一致；SLA 与 Rust 实现的是同一算法、同一输入。
- Native 运行时：Rust release 几何平均快约 1.47×（不含 matmul；含 matmul 约 2.02×）。
- WASM 运行时：Rust release 几何平均快约 1.44×（不含 matmul；含 matmul 约 1.94×）。
- SLA 领先：native sort 1.35×、hashmap 1.14×；WASM mandelbrot 1.87×。
- 编译：常规源码 Rust 冷编译约为 SLA 的 0.32×（native）/0.40×（WASM）用时；热编译约 30ms vs 130–1432ms。
- 体积：SLA native 约 9.1MB vs Rust 0.43MB；SLA WASM 约 650–705KB vs Rust 61–64KB。
- 异常点：SLA `--release-fast` 编译 matmul native 需要约 70s；默认构建下 matmul/sort 段错误。

## 目录

```
benchmarks/sla/           SLA 源码（11 个，含 hello）
benchmarks/rust/          Rust Cargo 项目（src/bin/ 下 11 个）
benchmarks/micro/         固定数组初始化编译扩展性微基准
scripts/bench.py          冷/热编译 + native/wasm 运行时测量
scripts/analyze.py        生成 results/analysis.md
scripts/render_report.py  生成 REPORT.md（可选 --html 输出 sala 页面）
scripts/wasm_runner.mjs   Node WASI runner（最终数据用 Wasmtime）
results/                  原始 jsonl/json 与汇总
```

## 环境

- Linux x86_64，8 vCPU，Intel Xeon 2.20GHz，52GB RAM
- `sla 0.1.4`（`SA 0.1.8`）
- `rustc 1.99.1` / `cargo 1.99.1`
- Wasmtime 25.0.2
- Node 20.19（仅用于早期尝试；其 WASI 在大内存模块退出时会 trap，最终 WASM 数据全部用 Wasmtime）

SLA 安装后可能需要：

```sh
chmod +x /tools/node/lib/node_modules/@slalang/sla/node_modules/@salang/sa-linux-x64/bin/sa
export LD_LIBRARY_PATH=/tools/node/lib/node_modules/@slalang/sla/node_modules/@salang/sa-linux-x64/bin:$LD_LIBRARY_PATH
```

## 复现

```sh
npm install -g @slalang/sla
rustup target add wasm32-wasip1

curl -L -o /tmp/wasmtime.tar.xz \
  https://github.com/bytecodealliance/wasmtime/releases/download/v25.0.2/wasmtime-v25.0.2-x86_64-linux.tar.xz
tar -xf /tmp/wasmtime.tar.xz -C /tmp

python3 scripts/bench.py --mode all --runs 7
python3 scripts/analyze.py > results/analysis.md
python3 scripts/render_report.py
# 可选：重新生成 sala 章节 HTML
python3 scripts/render_report.py --html <sala>/content/09_rust_compare/09_performance.html
```

`bench.py` 可用环境变量覆盖 `WASMTIME`、`SLA` 和 `SA_LIB`；`WASMTIME` 默认取
`/tmp/wasmtime-v25.0.2-x86_64-linux/wasmtime`。

## 口径与限制

- SLA 使用 `build-exe/build-wasm --release-fast`；Rust 使用 `cargo build --release`
  （opt-level=3、lto=false、codegen-units=16、panic=abort）与 `wasm32-wasip1`。
- 冷编译删除 `.sa_cache` 并加 `--no-incremental`；Rust 使用全新 `CARGO_TARGET_DIR`。
- 运行时取 native 7 次、WASM 5 次中位数，去掉 1 次预热；RSS 取 `wait4` 的 `ru_maxrss`。
- 单线程；未覆盖 async、线程、FFI、网络与数据库。
- SLA 当前 `Vec<f64>` push 后读到 0，因此 matmul 两边都使用固定 `[f64; 4096]` 数组。
- SLA 没有导出 WASM 函数的语法，WASM 只能以 `_start` 命令方式运行。
- `results/variants.json` 中 SLA `release-small` 行与 default 实际产物相同（SLA 缓存键可能忽略 flags），
  报告未使用该列。
