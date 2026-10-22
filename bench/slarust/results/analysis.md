## Native runtime (median ms)

| bench | SLA | Rust | Rust/SLA | SLA checksum | Rust checksum |
|---|---:|---:|---:|---:|---:|
| bytes | 468.1 | 74.0 | 0.158 | 863801334 | 863801334 |
| fib | 460.5 | 383.4 | 0.833 | 102334155 | 102334155 |
| hashmap | 391.9 | 446.6 | 1.140 | 998405507 | 998405507 |
| hello | 2.0 | 1.9 | 0.954 | hello, slarust | hello, slarust |
| loopsum | 798.3 | 531.1 | 0.665 | 4499999927 | 4499999927 |
| mandelbrot | 616.7 | 608.4 | 0.987 | 123026899 | 123026899 |
| matmul | 1038.3 | 29.9 | 0.029 | 3145728000 | 3145728000 |
| nbody | 1070.9 | 1013.5 | 0.946 | 2611733 | 2611733 |
| sieve | 907.2 | 346.0 | 0.381 | 1270607 | 1270607 |
| sort | 371.5 | 502.3 | 1.352 | 852488716 | 852488716 |
| vecpush | 548.8 | 349.6 | 0.637 | 973248007 | 973248007 |

## WASM runtime (median ms, Wasmtime 25.0.2 WASI)

| bench | SLA | Rust | Rust/SLA | SLA checksum | Rust checksum |
|---|---:|---:|---:|---:|---:|
| bytes | 990.0 | 247.3 | 0.250 | 863801334 | 863801334 |
| fib | 670.6 | 633.3 | 0.944 | 102334155 | 102334155 |
| hashmap | 674.8 | 596.6 | 0.884 | 998405507 | 998405507 |
| hello | 13.0 | 11.5 | 0.881 | hello, slarust | hello, slarust |
| loopsum | 5249.9 | 1623.7 | 0.309 | 4499999927 | 4499999927 |
| mandelbrot | 654.4 | 1226.2 | 1.874 | 123026899 | 123026899 |
| matmul | 1251.3 | 44.3 | 0.035 | 3145728000 | 3145728000 |
| nbody | 1107.7 | 1063.3 | 0.960 | 2611733 | 2611733 |
| sieve | 994.8 | 395.7 | 0.398 | 1270607 | 1270607 |
| sort | 656.7 | 610.7 | 0.930 | 852488716 | 852488716 |
| vecpush | 1255.8 | 1119.2 | 0.891 | 973248007 | 973248007 |

## Cold compile time (median ms)

| bench | target | SLA | Rust | Rust/SLA |
|---|---|---:|---:|---:|
| bytes | native | 840 | 181 | 0.215 |
| bytes | wasm | 760 | 222 | 0.292 |
| fib | native | 281 | 166 | 0.593 |
| fib | wasm | 274 | 200 | 0.730 |
| hashmap | native | 1180 | 229 | 0.194 |
| hashmap | wasm | 1150 | 244 | 0.212 |
| hello | native | 306 | 188 | 0.616 |
| hello | wasm | 326 | 238 | 0.731 |
| loopsum | native | 274 | 158 | 0.577 |
| loopsum | wasm | 282 | 202 | 0.717 |
| mandelbrot | native | 294 | 173 | 0.589 |
| mandelbrot | wasm | 287 | 210 | 0.733 |
| matmul | native | 70107 | 185 | 0.003 |
| matmul | wasm | 860 | 257 | 0.299 |
| nbody | native | 400 | 228 | 0.570 |
| nbody | wasm | 306 | 246 | 0.803 |
| sieve | native | 1289 | 196 | 0.152 |
| sieve | wasm | 1142 | 223 | 0.196 |
| sort | native | 1806 | 228 | 0.126 |
| sort | wasm | 1713 | 242 | 0.141 |
| vecpush | native | 812 | 183 | 0.225 |
| vecpush | wasm | 752 | 221 | 0.294 |

## Warm/incremental compile time (median ms)

| bench | target | SLA | Rust | Rust/SLA |
|---|---|---:|---:|---:|
| bytes | native | 564 | 28 | 0.050 |
| bytes | wasm | 503 | 28 | 0.056 |
| fib | native | 188 | 30 | 0.158 |
| fib | wasm | 139 | 32 | 0.227 |
| hashmap | native | 831 | 30 | 0.036 |
| hashmap | wasm | 781 | 29 | 0.037 |
| hello | native | 206 | 30 | 0.148 |
| hello | wasm | 130 | 28 | 0.220 |
| loopsum | native | 198 | 31 | 0.158 |
| loopsum | wasm | 139 | 28 | 0.204 |
| mandelbrot | native | 187 | 28 | 0.151 |
| mandelbrot | wasm | 153 | 33 | 0.217 |
| matmul | native | 208 | 31 | 0.148 |
| matmul | wasm | 167 | 31 | 0.184 |
| nbody | native | 199 | 28 | 0.143 |
| nbody | wasm | 138 | 29 | 0.213 |
| sieve | native | 956 | 29 | 0.031 |
| sieve | wasm | 933 | 30 | 0.032 |
| sort | native | 1432 | 27 | 0.019 |
| sort | wasm | 1355 | 33 | 0.024 |
| vecpush | native | 618 | 32 | 0.052 |
| vecpush | wasm | 501 | 27 | 0.054 |

## Artifact size (bytes, cold build)

| bench | SLA native | Rust native | SLA wasm | Rust wasm |
|---|---:|---:|---:|---:|
| bytes | 9301304 | 444328 | 670623 | 63322 |
| fib | 9298552 | 443768 | 669429 | 62991 |
| hashmap | 9300984 | 445376 | 670854 | 64536 |
| hello | 9298328 | 443032 | 667795 | 62448 |
| loopsum | 9299128 | 443784 | 669440 | 62990 |
| mandelbrot | 9299192 | 444008 | 669655 | 63225 |
| matmul | 9315128 | 444128 | 721991 | 64336 |
| nbody | 9300216 | 446064 | 671763 | 65553 |
| sieve | 9302712 | 444824 | 670817 | 63975 |
| sort | 9301112 | 446144 | 671513 | 65194 |
| vecpush | 9301112 | 444832 | 670601 | 63803 |

## Native peak RSS (median KB)

| bench | SLA | Rust | Rust/SLA |
|---|---:|---:|---:|
| bytes | 528000 | 34944 | 0.066 |
| fib | 14336 | 14336 | 1.000 |
| hashmap | 134784 | 67712 | 0.502 |
| hello | 14336 | 14336 | 1.000 |
| loopsum | 14336 | 14336 | 1.000 |
| mandelbrot | 14336 | 14336 | 1.000 |
| matmul | 14336 | 14336 | 1.000 |
| nbody | 14336 | 14336 | 1.000 |
| sieve | 422144 | 21632 | 0.051 |
| sort | 19712 | 14336 | 0.727 |
| vecpush | 515968 | 252160 | 0.489 |

## WASM peak RSS (median KB)

| bench | SLA | Rust | Rust/SLA |
|---|---:|---:|---:|
| bytes | 540892 | 82720 | 0.153 |
| fib | 16648 | 17056 | 1.025 |
| hashmap | 147808 | 82852 | 0.561 |
| hello | 16584 | 17056 | 1.028 |
| loopsum | 16516 | 17060 | 1.033 |
| mandelbrot | 16604 | 17056 | 1.027 |
| matmul | 17160 | 16932 | 0.987 |
| nbody | 16772 | 17200 | 1.026 |
| sieve | 435004 | 69412 | 0.160 |
| sort | 32752 | 33200 | 1.014 |
| vecpush | 528644 | 529024 | 1.001 |
