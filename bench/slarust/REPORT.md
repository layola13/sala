# SLA vs Rust 性能实测报告（native / WASM / 编译）

日期：2026-10-22  
项目：`slarust`（10 个核心负载 + hello 启动）  
工具链：sla 0.1.4（SA 0.1.8）、Rust 1.99.1、Wasmtime 25.0.2  
平台：Linux x86_64（8 vCPU，Intel Xeon 2.20GHz，KVM，52GB RAM）

## 结论摘要

- **11 个程序（10 个核心负载 + hello）校验和全部一致**：SLA 与 Rust 实现的是同一算法、同一输入、同一输出，比较有效。
- **Native 运行时**：排除 hello 与 matmul 两个极端后，Rust 几何平均快 **1.47×**；算上 matmul
  则快 **2.02×**（matmul Rust 快 34.7×）。SLA 在
  sort 上快 1.35×、hashmap 上快 1.14×。
- **WASM 运行时**：排除 hello 与 matmul 后 Rust 几何平均快 **1.44×**；算上 matmul 则快
  **1.94×**。SLA 的 mandelbrot 反而快 **1.87×**，
  matmul Rust 快 28.3×。
- **编译时间**：常规源码 Rust 冷编译更快（native SLA 是 Rust 的 3.09×，WASM 是 2.48×）；
  热编译 Rust 约 30ms，SLA 130–1432ms。唯一例外是 **matmul native**：SLA `--release-fast` 冷编译
  70.1s，Rust 0.19s，慢约 379×；
  同一份源码 WASM 目标只要 0.86s。
- **产物体积**：SLA native 约 9.1MB，Rust 约 0.44MB（约 21×）；SLA WASM 约 650–705KB，Rust 约 61–64KB（约 10.7×）。
  这和“WASM 体积约 5× 小”的旧口径相反，旧口径需要按实测更新。
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
- 热编译：保留缓存/目标目录，取 3 次中位数。
- 运行时：native 7 次、WASM 5 次，去掉 1 次预热，取中位数；用 `wait4` 读取子进程 `ru_maxrss`。
- WASM 运行器：Wasmtime 25.0.2（WASI preview1），计时包含实例化与进程启动（hello 约 11–13ms）。

### 1.3 限制

- 单线程；没有测试 async / 多线程 / FFI / 网络 / 数据库。
- SLA 的 `Vec<f64>` 在当前版本 push 后读到 0，因此 matmul 使用固定长度 `[f64; 4096]` 数组；
  Rust 使用同样的固定数组，算法仍一致。
- SLA 没有导出 WASM 函数的 `.sla` 语法，WASM 只能以 `_start` 命令方式运行；两边都用 WASI 进程计时。
- 结果受 KVM 共享 CPU 影响；比值比绝对毫秒更可靠。

## 2. Native 运行时

| bench | SLA ms | Rust ms | Rust/SLA | SLA RSS KB | Rust RSS KB |
|---|---|---|---|---|---|
| hello | 2.0 | 1.9 | 0.95× | 14336 | 14336 |
| fib | 460.5 | 383.4 | 0.83× | 14336 | 14336 |
| loopsum | 798.3 | 531.1 | 0.67× | 14336 | 14336 |
| sieve | 907.2 | 346.0 | 0.38× | 422144 | 21632 |
| matmul | 1038.3 | 29.9 | 0.03× | 14336 | 14336 |
| sort | 371.5 | 502.3 | 1.35× | 19712 | 14336 |
| hashmap | 391.9 | 446.6 | 1.14× | 134784 | 67712 |
| nbody | 1070.9 | 1013.5 | 0.95× | 14336 | 14336 |
| mandelbrot | 616.7 | 608.4 | 0.99× | 14336 | 14336 |
| vecpush | 548.8 | 349.6 | 0.64× | 515968 | 252160 |
| bytes | 468.1 | 74.0 | 0.16× | 528000 | 34944 |

Rust 几何平均（不含 hello/matmul）：**1.47× 更快**；含 matmul：**2.02× 更快**。  
SLA 胜出的项目：sort 快 1.35×、hashmap 快 1.14×。
matmul 是最大差距（34.7×），从差距形态看，
很可能与 Rust/LLVM 对固定数组三重循环的向量化程度有关；SLA 生成的循环可能没有达到同等优化，
需要进一步看汇编确认。

## 3. WASM 运行时

| bench | SLA ms | Rust ms | Rust/SLA | SLA RSS KB | Rust RSS KB |
|---|---|---|---|---|---|
| hello | 13.0 | 11.5 | 0.88× | 16584 | 17056 |
| fib | 670.6 | 633.3 | 0.94× | 16648 | 17056 |
| loopsum | 5249.9 | 1623.7 | 0.31× | 16516 | 17060 |
| sieve | 994.8 | 395.7 | 0.40× | 435004 | 69412 |
| matmul | 1251.3 | 44.3 | 0.04× | 17160 | 16932 |
| sort | 656.7 | 610.7 | 0.93× | 32752 | 33200 |
| hashmap | 674.8 | 596.6 | 0.88× | 147808 | 82852 |
| nbody | 1107.7 | 1063.3 | 0.96× | 16772 | 17200 |
| mandelbrot | 654.4 | 1226.2 | 1.87× | 16604 | 17056 |
| vecpush | 1255.8 | 1119.2 | 0.89× | 528644 | 529024 |
| bytes | 990.0 | 247.3 | 0.25× | 540892 | 82720 |

Rust 几何平均（不含 hello/matmul）：**1.44× 更快**；含 matmul：**1.94× 更快**。  
WASM 上 SLA 唯一明显胜出的是 mandelbrot（1.87×）；
loopsum 上 Rust 快 3.2×，是除 matmul 外 WASM 侧最大差距。

## 4. 编译时间

表中每格为 **SLA / Rust**，单位 ms。

### 4.1 冷编译

| bench | native SLA / Rust | wasm SLA / Rust |
|---|---|---|
| hello | 306 / 188 | 326 / 238 |
| fib | 281 / 166 | 274 / 200 |
| loopsum | 274 / 158 | 282 / 202 |
| sieve | 1289 / 196 | 1142 / 223 |
| matmul | 70107 / 185 | 860 / 257 |
| sort | 1806 / 228 | 1713 / 242 |
| hashmap | 1180 / 229 | 1150 / 244 |
| nbody | 400 / 228 | 306 / 246 |
| mandelbrot | 294 / 173 | 287 / 210 |
| vecpush | 812 / 183 | 752 / 221 |
| bytes | 840 / 181 | 760 / 222 |

常规大小源码上 Rust 冷编译更快：native 几何平均 Rust 是 SLA 的 0.32× 用时，WASM 是 0.40×。
matmul native 是异常点：SLA 冷编译 70.1s，Rust 185ms；
同一源码的 SLA WASM 冷编译只要 860ms，说明瓶颈在 native LLVM 优化/代码生成，而不是前端。

### 4.2 热编译

| bench | native SLA / Rust | wasm SLA / Rust |
|---|---|---|
| hello | 206 / 30 | 130 / 28 |
| fib | 188 / 30 | 139 / 32 |
| loopsum | 198 / 31 | 139 / 28 |
| sieve | 956 / 29 | 933 / 30 |
| matmul | 208 / 31 | 167 / 31 |
| sort | 1432 / 27 | 1355 / 33 |
| hashmap | 831 / 30 | 781 / 29 |
| nbody | 199 / 28 | 138 / 29 |
| mandelbrot | 187 / 28 | 153 / 33 |
| vecpush | 618 / 32 | 501 / 27 |
| bytes | 564 / 28 | 503 / 28 |

Rust 热编译稳定在约 30ms（Cargo 无改动时只做新鲜度检查）；SLA 热编译 130–1432ms，源文件越大越慢，
说明 SLA 的缓存只省掉了部分阶段，前端/校验仍在重复执行。

## 5. 产物体积与内存

### 5.1 体积（冷构建产物，含运行时）

| bench | SLA native | Rust native | SLA wasm | Rust wasm |
|---|---|---|---|---|
| hello | 9080 KB | 433 KB | 652 KB | 61 KB |
| fib | 9081 KB | 433 KB | 654 KB | 62 KB |
| loopsum | 9081 KB | 433 KB | 654 KB | 62 KB |
| sieve | 9085 KB | 434 KB | 655 KB | 62 KB |
| matmul | 9097 KB | 434 KB | 705 KB | 63 KB |
| sort | 9083 KB | 436 KB | 656 KB | 64 KB |
| hashmap | 9083 KB | 435 KB | 655 KB | 63 KB |
| nbody | 9082 KB | 436 KB | 656 KB | 64 KB |
| mandelbrot | 9081 KB | 434 KB | 654 KB | 62 KB |
| vecpush | 9083 KB | 434 KB | 655 KB | 62 KB |
| bytes | 9083 KB | 434 KB | 655 KB | 62 KB |

SLA native 基本恒定在 9,080–9,097KB（约 9.1MB，静态运行时占主导），Rust 约 433–436KB；
SLA WASM 约 650–705KB，Rust 约 61–64KB。**WASM 体积约为 Rust 的 10.7×，而不是更小**。若部署场景对体积敏感，当前 SLA 0.1.4 不占优。

### 5.2 峰值 RSS

Native 与 WASM 的 RSS 表已在第 2、3 节列出。结论：

- 小分配/纯计算场景两者基线都在 14–17MB。
- SLA 的 `Vec` 在大数组场景明显更费内存：sieve 422MB vs 22MB、bytes 528MB vs 35MB、
  vecpush 516MB vs 252MB。
- 从数据看与增长策略、分配器回收差异一致（SLA 可能重复分配并保留旧块），需进一步 profiling 确认。

## 6. 优化等级与构建变体

### 6.1 SLA 默认 vs `--release-fast`，Rust debug vs release

| bench | SLA default | SLA release-fast | Rust debug | Rust release |
|---|---|---|---|---|
| fib | 2532.0 | 460.5 | 1350.6 | 383.4 |
| loopsum | 8052.0 | 798.3 | 7949.9 | 531.1 |
| sieve | 5626.0 | 907.2 | 1220.4 | 346.0 |
| matmul | - | 1038.3 | 7388.0 | 29.9 |
| sort | - | 371.5 | 3042.4 | 502.3 |
| bytes | 3507.9 | 468.1 | 404.2 | 74.0 |

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

| variant | compile ms | run ms | size | checksum |
|---|---|---|---|---|
| default | 1622 | - | 9360 KB | (segfault) |
| release-small | 58223 | 1045.5 | 9097 KB | 3145728000 |
| release-fast | 62891 | 1043.9 | 9097 KB | 3145728000 |

`--release-fast` / `--release-small` 的编译时间都在 60s 量级，运行约 1.04s；默认构建虽只要 1.6s，
但运行时段错误。这个组合（固定数组 + 三重循环 + 优化）是当前 SLA 后端的明确短板。

## 7. 编译时间可扩展性

固定长度 `[f64; N*N]` 数组初始化、只打印首元素的微基准（`--release-fast --no-incremental`）：

| N | elements | compile ms |
|---|---|---|
| 2 | 4 | 294 |
| 8 | 64 | 277 |
| 16 | 256 | 437 |
| 24 | 576 | 653 |
| 32 | 1024 | 1093 |
| 40 | 1600 | 1619 |
| 48 | 2304 | 2294 |
| 56 | 3136 | 3348 |
| 64 | 4096 | 4863 |

数组初始化本身随规模近似线性/轻微超线性增长（4,096 元素约 4.9s），但 matmul 完整程序要 60–70s，
说明主要成本来自循环体优化/代码生成，而不是数组字面量。

## 8. 结论与建议

1. **运行时**：当前 SLA 0.1.4 在多数标量/内存密集型负载上比 Rust release 慢 1.5–2×；
   固定数组 + 浮点循环（matmul）差距可达 30×。SLA 在无序索引访问（sort）和哈希表探测（hashmap）上更快，
   可能与生成代码省略边界检查有关（未做汇编确认）。
2. **WASM**：整体差距与 native 接近；SLA 的 mandelbrot 更快，说明 float 循环的 wasm 代码生成并不总是劣势。
   但 loopsum/筛法/字节流仍明显落后。
3. **编译**：SLA 冷编译常规项目比 Rust 慢约 2.5–3×，热编译慢 4–50×；matmul native 的 60–70s 是必须修复的回归。
   建议优先排查 `--release-fast` 在固定数组 + 嵌套循环上的 LLVM 优化爆炸，并让缓存覆盖前端/校验阶段。
4. **体积**：9.1MB native / 650–705KB WASM 显著大于 Rust（0.44MB / 61–64KB）。如果 SLA 的卖点是“WASM 体积小”，
   需要先做 DCE/运行时裁剪；当前数据不支持该结论。
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
curl -L -o /tmp/wasmtime.tar.xz \
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

| bench | native SLA | native Rust | wasm SLA | wasm Rust |
|---|---|---|---|---|
| hello | hello, slarust | hello, slarust | hello, slarust | hello, slarust |
| fib | 102334155 | 102334155 | 102334155 | 102334155 |
| loopsum | 4499999927 | 4499999927 | 4499999927 | 4499999927 |
| sieve | 1270607 | 1270607 | 1270607 | 1270607 |
| matmul | 3145728000 | 3145728000 | 3145728000 | 3145728000 |
| sort | 852488716 | 852488716 | 852488716 | 852488716 |
| hashmap | 998405507 | 998405507 | 998405507 | 998405507 |
| nbody | 2611733 | 2611733 | 2611733 | 2611733 |
| mandelbrot | 123026899 | 123026899 | 123026899 | 123026899 |
| vecpush | 973248007 | 973248007 | 973248007 | 973248007 |
| bytes | 863801334 | 863801334 | 863801334 | 863801334 |
