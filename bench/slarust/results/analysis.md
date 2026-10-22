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
| bytes | native | 546 | 132 | 0.241 |
| bytes | wasm | 492 | 150 | 0.304 |
| fib | native | 176 | 113 | 0.643 |
| fib | wasm | 136 | 148 | 1.086 |
| hashmap | native | 790 | 133 | 0.168 |
| hashmap | wasm | 741 | 163 | 0.220 |
| hello | native | 184 | 112 | 0.609 |
| hello | wasm | 126 | 132 | 1.041 |
| loopsum | native | 175 | 118 | 0.676 |
| loopsum | wasm | 127 | 132 | 1.036 |
| mandelbrot | native | 186 | 120 | 0.644 |
| mandelbrot | wasm | 134 | 144 | 1.078 |
| matmul | native | 191 | 128 | 0.671 |
| matmul | wasm | 146 | 159 | 1.094 |
| nbody | native | 179 | 151 | 0.843 |
| nbody | wasm | 136 | 177 | 1.301 |
| sieve | native | 944 | 141 | 0.149 |
| sieve | wasm | 883 | 160 | 0.181 |
| sort | native | 1328 | 153 | 0.115 |
| sort | wasm | 1302 | 177 | 0.136 |
| vecpush | native | 569 | 141 | 0.248 |
| vecpush | wasm | 501 | 161 | 0.321 |

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

## Deployable size after strip (bytes)


### native

| bench | SLA raw | SLA stripped | Rust raw | Rust stripped | SLA/Rust |
|---|---:|---:|---:|---:|---:|
| bytes | 9301304 | 9301296 | 444328 | 336496 | 27.64 |
| fib | 9298552 | 9298544 | 443768 | 336088 | 27.67 |
| hashmap | 9300984 | 9300976 | 445376 | 337272 | 27.58 |
| hello | 9298328 | 9298320 | 443032 | 335568 | 27.71 |
| loopsum | 9299128 | 9299120 | 443784 | 336136 | 27.66 |
| mandelbrot | 9299192 | 9299184 | 444008 | 336328 | 27.65 |
| matmul | 9315128 | 9315120 | 444128 | 336488 | 27.68 |
| nbody | 9300216 | 9300208 | 446064 | 338424 | 27.48 |
| sieve | 9302712 | 9302704 | 444824 | 336992 | 27.61 |
| sort | 9301112 | 9301104 | 446144 | 338072 | 27.51 |
| vecpush | 9301112 | 9301104 | 444832 | 336728 | 27.62 |

### wasm

| bench | SLA raw | SLA stripped | Rust raw | Rust stripped | SLA/Rust |
|---|---:|---:|---:|---:|---:|
| bytes | 670623 | 7971 | 63322 | 48317 | 0.16 |
| fib | 669429 | 6821 | 62991 | 48033 | 0.14 |
| hashmap | 670854 | 8200 | 64536 | 49252 | 0.17 |
| hello | 667795 | 5292 | 62448 | 47578 | 0.11 |
| loopsum | 669440 | 6826 | 62990 | 48045 | 0.14 |
| mandelbrot | 669655 | 7038 | 63225 | 48257 | 0.15 |
| matmul | 721991 | 59378 | 64336 | 49394 | 1.20 |
| nbody | 671763 | 9151 | 65553 | 50616 | 0.18 |
| sieve | 670817 | 8165 | 63975 | 48915 | 0.17 |
| sort | 671513 | 8862 | 65194 | 49936 | 0.18 |
| vecpush | 670601 | 7947 | 63803 | 48578 | 0.16 |

## Size-optimal comparison (bytes)

SLA = release-fast + strip; Rust = profile.size + strip; wasm best = min(strip, strip+wasm-opt -Oz).

| bench | SLA native | Rust native | SLA wasm best | Rust wasm best | wasm SLA/Rust |
|---|---:|---:|---:|---:|---:|
| bytes | 9301296 | 282864 | 6647 | 33742 | 0.20 |
| fib | 9298544 | 282592 | 5747 | 33501 | 0.17 |
| hashmap | 9300976 | 283704 | 6891 | 34882 | 0.20 |
| hello | 9298320 | 281264 | 4526 | 32566 | 0.14 |
| loopsum | 9299120 | 282544 | 5760 | 33509 | 0.17 |
| mandelbrot | 9299184 | 282736 | 5957 | 33682 | 0.18 |
| matmul | 9315120 | 282720 | 59378 | 33745 | 1.76 |
| nbody | 9300208 | 283952 | 8114 | 35037 | 0.23 |
| sieve | 9302704 | 283400 | 6835 | 34191 | 0.20 |
| sort | 9301104 | 284112 | 7447 | 35150 | 0.21 |
| vecpush | 9301104 | 282752 | 6621 | 34214 | 0.19 |

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
