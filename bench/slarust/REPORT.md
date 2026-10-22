# SLA vs Rust vs Go 性能实测报告（native / WASM / 编译 / 网络）

日期：2026-10-22  
项目：`slarust`（10 个核心负载 + hello 启动 + HTTP 并发）  
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
- **编译时间**：常规源码 Rust 冷编译更快（native SLA 是 Rust 的 3.09×，WASM 是 2.48×）。
  热编译在两边都 touch 源文件、实际重建后，差距远小于旧稿：native SLA 慢 1.2–8.7×
  （几何 3.1×），WASM SLA/Rust 0.77–7.4×（几何 2.2×），
  小 WASM 项目 SLA 甚至略快。唯一例外是 **matmul native**：SLA `--release-fast` 冷编译
  70.1s，Rust 0.19s，慢约 379×；
  同一份源码 WASM 目标只要 0.86s。
- **体积最优对比**：双方各取最小配置（SLA `--release-fast`+strip；Rust `profile=size`
  +strip+`wasm-opt -Oz`）。native 仍是 SLA 明显更大（9.1MB vs 274–278KB，约 **32.8×**）。
  WASM 典型负载（不含 hello/matmul）SLA 5.6–7.9KB vs Rust 32.7–34.3KB，SLA 约小 **5.2×**，基本符合旧口径
  “约 5× 小”；matmul 是例外（58.0KB vs 33.0KB，SLA 大约 1.76×）。默认 release 的 raw/strip 对比见 5.1–5.2。
- **峰值内存**：SLA 的大数组场景 RSS 高 2×（vecpush）、19×（sieve）、15×（bytes），与增长/保留策略和分配器回收差异一致。
- **默认优化等级**：SLA 默认构建大致是 Rust debug 量级（fib 2.5s vs 1.35s，loopsum 8.05s vs 7.95s；
  sieve/bytes 则慢 3–9×）；`--release-fast` 是必要选项，但会让 matmul 编译从 1.6s 膨胀到 60–70s。
- **环境观察**：Node 20.19 的 WASI 在若干大内存模块退出时触发 V8 trap（SLA/Rust 都复现），
  本文 WASM 数据统一改用 Wasmtime 25.0.2。
- **网络并发（HTTP/1.1 keep-alive）**：4 个独立进程、每进程 1 个监听器时，SLA 约
  35.7–43.9k rps；Rust 222–249k（约 5.7–6.2×），Go 66–82k（约 1.6–2.0×）。
  SLA 每请求约 56KB RSS 增长，20k 请求后 1.1–3.6GB；同一插件由 C 驱动无增长，
  属 SLA 运行时/FFI 侧问题，长跑会拖慢吞吐。

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

- 数值/WASM 部分为单线程，未测试 async、FFI、数据库；网络部分只测 HTTP/1.1
  keep-alive（第 8 节），不含 TLS、路由、日志与真实业务逻辑。
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
| hello | 184 / 112 | 126 / 132 |
| fib | 176 / 113 | 136 / 148 |
| loopsum | 175 / 118 | 127 / 132 |
| sieve | 944 / 141 | 883 / 160 |
| matmul | 191 / 128 | 146 / 159 |
| sort | 1328 / 153 | 1302 / 177 |
| hashmap | 790 / 133 | 741 / 163 |
| nbody | 179 / 151 | 136 / 177 |
| mandelbrot | 186 / 120 | 134 / 144 |
| vecpush | 569 / 141 | 501 / 161 |
| bytes | 546 / 132 | 492 / 150 |

热编译测量前会 touch 两边源文件，保留各自缓存/目标目录，因此两边都实际重建。Rust release 默认不开 incremental，
是整 crate 重编；SLA 缓存则省掉部分阶段。修正后 native SLA 慢 1.2–8.7×
（几何 3.1×），WASM SLA/Rust 0.77–7.4×（几何 2.2×）。
旧稿的“Rust 约 30ms”是 Cargo 无改动时的 no-op，与 SLA 的实际重建不可比，已废弃。
补充：`.sla-cache` 中可见 `reachable/*.plan` 与 `sab/*.sab`，但即使输出已存在，`build-exe` 仍会重新写出可执行文件（实测 inode 改变）；
SLA 没有 Cargo 那种“目标已最新则直接返回”的短路，缓存只省掉部分前端/中间产物阶段。

## 5. 产物体积与内存

### 5.1 Native 体积（strip 后）

| bench | SLA stripped | Rust raw | Rust stripped | SLA/Rust |
|---|---|---|---|---|
| hello | 9080 KB | 433 KB | 328 KB | 27.7× |
| fib | 9081 KB | 433 KB | 328 KB | 27.7× |
| loopsum | 9081 KB | 433 KB | 328 KB | 27.7× |
| sieve | 9085 KB | 434 KB | 329 KB | 27.6× |
| matmul | 9097 KB | 434 KB | 329 KB | 27.7× |
| sort | 9083 KB | 436 KB | 330 KB | 27.5× |
| hashmap | 9083 KB | 435 KB | 329 KB | 27.6× |
| nbody | 9082 KB | 436 KB | 330 KB | 27.5× |
| mandelbrot | 9081 KB | 434 KB | 328 KB | 27.6× |
| vecpush | 9083 KB | 434 KB | 329 KB | 27.6× |
| bytes | 9083 KB | 434 KB | 329 KB | 27.6× |

SLA native 基本恒定在 9,080–9,097KB（静态运行时占主导），且本身已 stripped；
Rust raw 约 433–436KB，strip 后约 328–330KB。默认 release 口径下可部署体积 SLA 约为 Rust 的 **27.7×**，
native 侧“SLA 更小”不成立；双方体积最优口径见下。

### 5.2 WASM 体积（raw vs 可部署）

| bench | SLA raw | SLA stripped | Rust raw | Rust stripped | SLA/Rust |
|---|---|---|---|---|---|
| hello | 652 KB | 5.2 KB | 61 KB | 46.5 KB | 0.11× |
| fib | 654 KB | 6.7 KB | 62 KB | 46.9 KB | 0.14× |
| loopsum | 654 KB | 6.7 KB | 62 KB | 46.9 KB | 0.14× |
| sieve | 655 KB | 8.0 KB | 62 KB | 47.8 KB | 0.17× |
| matmul | 705 KB | 58.0 KB | 63 KB | 48.2 KB | 1.20× |
| sort | 656 KB | 8.7 KB | 64 KB | 48.8 KB | 0.18× |
| hashmap | 655 KB | 8.0 KB | 63 KB | 48.1 KB | 0.17× |
| nbody | 656 KB | 8.9 KB | 64 KB | 49.4 KB | 0.18× |
| mandelbrot | 654 KB | 6.9 KB | 62 KB | 47.1 KB | 0.15× |
| vecpush | 655 KB | 7.8 KB | 62 KB | 47.4 KB | 0.16× |
| bytes | 655 KB | 7.8 KB | 62 KB | 47.2 KB | 0.16× |

SLA 的 WASM 原始产物大部分是 `.debug_*` 自定义段（hello：667,795 字节中 659,470 字节是调试段；
典型约 99%，matmul 约 92%），直接比较 raw 会严重高估体积。剥离 `.debug*` 和 `name` 后，典型 SLA 负载为 5.2–8.9KB，
Rust 为 46.5–49.4KB，SLA 几何平均小 **6.2×**；matmul 例外（58.0KB vs 48.2KB，SLA 大约 1.2×）。
因此默认 release 对比下，旧口径“WASM 体积约 5× 小”在典型负载上基本成立，但必须说明是 strip 后，且 matmul 不成立；
双方各取体积最优配置的结果见 5.3。

### 5.3 体积最优对比（双方各自最小配置）

SLA 侧：`build-wasm --release-fast`（`--release-small` 产物与 fast 完全相同），移除 `.debug*`/`name`。
Rust 侧：新增 `profile.size`（`opt-level="z"`、LTO、`codegen-units=1`、`panic="abort"`、`strip="symbols"`），
再移除 WASM 自定义调试段。两边都额外尝试 `wasm-opt 132 -Oz`，每项取 strip 与 strip+wasm-opt 的较小值。

| bench | SLA native | Rust native | SLA wasm best | Rust wasm best | wasm SLA/Rust |
|---|---|---|---|---|---|
| hello | 9080 KB | 275 KB | 4.4 KB | 31.8 KB | 0.14× |
| fib | 9081 KB | 276 KB | 5.6 KB | 32.7 KB | 0.17× |
| loopsum | 9081 KB | 276 KB | 5.6 KB | 32.7 KB | 0.17× |
| sieve | 9085 KB | 277 KB | 6.7 KB | 33.4 KB | 0.20× |
| matmul | 9097 KB | 276 KB | 58.0 KB | 33.0 KB | 1.76× |
| sort | 9083 KB | 277 KB | 7.3 KB | 34.3 KB | 0.21× |
| hashmap | 9083 KB | 277 KB | 6.7 KB | 34.1 KB | 0.20× |
| nbody | 9082 KB | 277 KB | 7.9 KB | 34.2 KB | 0.23× |
| mandelbrot | 9081 KB | 276 KB | 5.8 KB | 32.9 KB | 0.18× |
| vecpush | 9083 KB | 276 KB | 6.5 KB | 33.4 KB | 0.19× |
| bytes | 9083 KB | 276 KB | 6.5 KB | 33.0 KB | 0.20× |

- Native：SLA 9,080–9,097KB vs Rust 274–278KB，几何平均 SLA 大约 **32.8×**。
- WASM 典型负载（不含 hello/matmul）：SLA 5.6–7.9KB vs Rust 32.7–34.3KB，SLA 小 **5.2×**。
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

## 8. 网络并发（HTTP/1.1 keep-alive）

### 8.1 口径

- 响应统一为 `200 OK`、`Content-Type: text/plain`、body `ok`，HTTP/1.1 keep-alive。
- SLA：`http-server` 插件，4 个独立进程（18092–18095），每进程 1 个监听器 + 1 个
  SLA `accept` worker；accept 后设置 `TCP_NODELAY`。客户端按连接轮询 4 个端口。
  未用 `sa_std/net` 直接实现（原因见 8.3）。
- Rust：4 个进程，每进程 `TcpListener` + thread-per-connection，最小 HTTP 头解析。
- Go：4 个进程，`net/http` 默认 `ServeMux`，无日志/中间件。
- 客户端：Rust 阻塞式 keep-alive，每条连接先预热 200 次，再计时；并发 1/16/64/256，
  每档 20,000 请求，2 次重复取中位数；每档重启服务器，避免上一档内存影响吞吐。
- 指标：rps、P50/P95/P99、进程 `VmHWM` 之和、线程数。平台同第 1 节（8 vCPU KVM）。

### 8.2 结果

| 并发 | SLA rps | Rust rps | Go rps | SLA P50/P95/P99 ms | Rust P50/P95/P99 ms | Go P50/P95/P99 ms | SLA RSS MB | Rust RSS MB | Go RSS MB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9,691 | 22,456 | 6,613 | 0.08/0.27/0.40 | 0.04/0.10/0.24 | 0.11/0.38/0.63 | 1,119 | 9 | 34 |
| 16 | 41,802 | 245,006 | 66,356 | 0.33/0.62/1.21 | 0.04/0.09/0.19 | 0.09/0.69/2.17 | 1,201 | 9 | 56 |
| 64 | 43,890 | 248,965 | 81,997 | 1.32/2.00/2.48 | 0.19/0.45/0.81 | 0.16/3.09/8.46 | 1,688 | 10 | 57 |
| 256 | 35,688 | 222,339 | 72,496 | 6.57/8.67/9.55 | 0.65/2.00/3.52 | 0.37/11.32/28.95 | 3,640 | 12 | 60 |

- 相对 SLA：Rust 在 16/64/256 并发分别快 **5.9× / 5.7× / 6.2×**，
  Go 分别快 **1.6× / 1.9× / 2.0×**。1 并发时 Rust 快 2.3×，Go 反而慢约 0.7×
  （单连接下 Go `net/http` 的固定开销高于 SLA 的最小响应路径）。
- SLA 在 16/64 并发达到 41.8–43.9k，256 并发回落到 35.7k，P50 从 0.08ms 升到 6.57ms。
  Rust 随并发上升基本保持 222–249k，P50 仅 0.04–0.65ms；Go 在 64 并发约 82k，
  256 并发回落到约 72k，P99 达 29ms。

### 8.3 问题与阻塞

1. **SLA 每请求约 56KB RSS 增长**。20k 请求后 c=1 已约 1.1GB，c=256 约 3.6GB；
   同一 `http-server` 插件由 C 驱动执行 20k 请求，RSS 仅从约 2.0MB 增到 2.0MB。
   因此泄漏在 SLA 运行时/FFI 侧，不在插件。旧拓扑长跑 80k 请求后吞吐会降到
   3.7–7.5k；新拓扑未做长跑，但泄漏仍会限制持续服务时间。这是当前 SLA 网络
   服务最大的阻塞项。
2. **`serve_threaded` 从 SLA 调用会立即返回**。根因是 SA 主机导出了
   `pthread_join(int32_t, uint8_t*)`，动态链接时覆盖了 libc 的 `pthread_join`，
   插件里的 `std.Thread.join` 实际 join 了错误的句柄，`serve_threaded` 随即返回并
   释放线程池。已把插件改为 `detach` + 原子完成计数等待；`zig build test` 通过。
3. **函数指针不能直接传 SLA 闭包**。`PTR_BYTE_ADD(handle, 0)` 传的是闭包 vtable
   地址；正确做法是从 `handle+8` 取 vtable，再取 vtable+0 的 code 指针
   （见 `benchmarks/net/sla/fnptr2.sa`）。
4. **部署拓扑决定吞吐，插件 accept 路径仍是上限**。同一 `http-server` 插件由 C
   驱动、单监听器 + 1 个 accept worker 原本约 3.1k rps，accept 后补
   `TCP_NODELAY` 提升到约 7.4k；4 线程 `serve_threaded` 约 4.1k，4 监听器 ×
   4 线程反而降到 2.3–2.7k（recycled pool 锁争用）。把 4 个监听器放在同一
   SLA 进程只有 8–12k，而 4 个独立进程、每进程 1 个监听器可达 35–44k。
   因此最终口径改为 **1 进程 1 监听器**；剩余开销仍在每请求 poll/池扫描/
   `std.http` head 解析/`setsockopt`，以及 SLA 侧每请求 ~56KB 增长。
5. **为何不用 `sa_std/net` 直接写**：高层 `net` 的 bind/accept 可用，但 4KB 读缓冲
   会触发 `MemoryLeak ... Composite`；在 `.sla` 里也无法直接声明 `malloc`/低层
   `NET_TCP_STREAM_READ` 宏。按用户允许的方案改用 `http-server` 插件。

### 8.4 编译与产物体积

| 实现 | 构建 | 时间（中位数） | stripped 体积 |
|---|---|---:|---:|
| SLA | `sla build` + `sa build-exe --release-fast` | 1.51s/个（4 个进程） | 9.31MB |
| Rust | `rustc -O` | 0.42s | 382KB |
| Go | `go build -trimpath -ldflags '-s -w'` | 0.16s（冷构建 15.6s） | 5.88MB |

SLA 的 native 体积仍由静态运行时主导（约 9.3MB），Rust 最小（约 0.38MB），
Go 居中（约 5.9MB）。网络基准的 SLA 源码需两步构建，因为该程序使用线程闭包，
`sla build-exe` 的 SAB 直降会报 `UnsupportedSabDirectFeature`。

## 9. 结论与建议

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
7. **公平性**：数值/WASM 部分只覆盖单线程负载；网络部分只覆盖 HTTP/1.1 keep-alive。
   SLA 的 async、FFI、包管理等未纳入，需要单独基准与安全检查。
8. **网络结论**：SLA 用 4 个独立进程、每进程 1 个监听器时可达 35–44k rps，
   P50 0.08ms（c=1）到 6.6ms（c=256），但与 Rust 的 222–249k、Go 的 66–82k
   仍有 5.7–6.2× / 1.6–2.0× 差距。上线前应优先修复每请求约 56KB 的运行时泄漏；
   当前不建议在同一进程内堆多个监听器或多 accept worker。

## 10. 复现

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
# 网络并发（需先安装 http-server 插件与 Zig 0.17）
cd benchmarks/net
python3 run_bench.py --servers sla,rust,go --concurrency 1,16,64,256 --requests 20000
python3 summarize.py
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
