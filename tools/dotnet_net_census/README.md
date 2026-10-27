# .NET net 表面 × sa_std 缺口普查（Agent AS，2026-10-27）

跨语言 std 普查批之一（同批：Rust 全 std / Go net / Python net / Java net / Android net / iOS net）。
成果页：`content/06_stdlib/24_dotnet_net_census.html`。

## 来源

- .NET 侧：`dotnet/runtime` tag **v10.0.14**（commit `6aa72daa24f66c01c3d7b6a32519e9d21396deec`，.NET 10 最新 GA  servicing），
  稀疏克隆 `src/libraries/System.Net.*` 共 19 个程序集，解析其 `ref/*.cs` 参考源码（公共 API 契约面）。
- SA 侧：sci main `8a943911` 的 `sa_std` 网络面（net/netx/http/http2/ws/tls/quic/ssh 门面文件组）。

## 复跑

```bash
# 1) 稀疏克隆（在 /content 下）
git clone --filter=blob:none --no-checkout --depth 1 --branch v10.0.14 \
  https://github.com/dotnet/runtime.git dotnet-src
cd dotnet-src && git sparse-checkout init --cone
git sparse-checkout set src/libraries/System.Net.Http src/libraries/System.Net.Sockets \
  ...（全部 19 个 System.Net.* 目录，清单见 extract_dotnet.py 的运行输出）
git checkout
# 注意：部分克隆下 `git ls-tree HEAD src/libraries/`（斜杠路径形式）会静默返回空，
# 枚举目录请用 `git ls-tree HEAD:src/libraries`。

# 2) 双边抽取（ROOT 常量在 extract_dotnet.py 顶部；SA 路径在 extract_sa_net.py 顶部）
python3 extract_dotnet.py > dotnet_surface.tsv
python3 extract_sa_net.py > sa_net_surface.tsv

# 3) 分类（断言 334 个 distinct 类型全覆盖，缺一即失败）
python3 classify.py   # 读取同目录 classify_map.py / classify_map2.py
```

## 产物

| 文件 | 内容 |
|---|---|
| `extract_dotnet.py` | .NET ref 源码公共面抽取器（类型/成员/Obsolete 标记） |
| `extract_sa_net.py` | sa_std 网络面抽取器（.sai extern / .sal #def / .sa 宏与 fn / sa_std.h） |
| `classify_map.py` / `classify_map2.py` | 逐类型四分类映射（类、sa 证据符号、注记） |
| `classify.py` | 分类运行器（全覆盖断言 + 按命名空间计数） |
| `dotnet_surface.tsv` | .NET 表面：337 类型记录 / 4,194 成员 |
| `sa_net_surface.tsv` | sa_std 网络表面：1,491 行（extern 475、宏 583、常量 225、头文件声明 208） |
| `gap_classification.tsv` | 334 个 distinct 类型的分类结果 |
| `summary.json` | 关键数字汇总 |

## 覆盖边界

- 以 ref 源码为公共面权威来源；仅存在于 src 实现、未进 ref 的表面不在内。
- 嵌套类型按（命名空间，类型名）归并：337 条记录 → 334 个 distinct 类型（Enumerator、JsonContent、SseParser 各有一组同名重复）。
- 泛型委托的抽取伪影（`T`、`TContext` 两个「类型」）已在分类表中按伪影登记。
- 分类粒度为类型级；头部类型（Socket/HttpClient/SslStream 等）的成员级差异写在注记中。
