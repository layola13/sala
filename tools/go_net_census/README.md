# Go net × sa_std 普查工具

机械抽取 + 规则分类，可复跑。数据基线：

- Go：golang/go tag `go1.27.3`（commit `2aae1000ea1d4b28923b96db28acf4e3b99d6aff`），
  sparse checkout 只取 `src/net` + `src/crypto/tls`。
- SA：sci main `8a943911` 的 `sa_std/` + `src/runtime/sa_std.h`。

## 复跑

```sh
# 1) 取 Go 源码（盒上 /content/go-net-src 即如此得到）
git clone --depth 1 --branch go1.27.3 --filter=blob:none --sparse https://github.com/golang/go go-net-src
cd go-net-src && git sparse-checkout set src/net src/crypto/tls

# 2) 双边抽取
python3 extract_go_net.py <go>/src go_net_api.json
python3 extract_sa_net.py <sci>/sa_std <sci>/src/runtime/sa_std.h sa_net_api.json

# 3) 分类（规则在 rules.py，逐簇作者化；被引用的 SA 符号自动校验存在性）
python3 compare_go_net.py go_net_api.json sa_net_api.json rules.py gap_table.tsv
```

本目录内的 `go_net_api.json` / `sa_net_api.json` / `gap_table.tsv` 为
2026-10-27 的基线产物；以同版输入复跑应与入库产物 byte-identical
（已实证）。

## 口径

- Go 侧：导出 func/method/type/const/var + 结构体导出字段 + 接口方法集；
  未导出接收者上的方法不计（按名不可达）；嵌入提升的方法不重复计；
  平台变体取并集去重；Go 1.27 同名 const/var（密码套件 ID）去重 30 条。
- SA 侧：契约层符号——.sai 的 `@extern`、.sal 的 `#def`、.sa 的 `[MACRO]`、
  sa_std.h 原型，按网络 token 过滤。SA 文本层内部函数不做定义/调用区分，
  不入清单（消费者实际可绑定的就是契约层）。
- 分类：`equiv` 已有等价 / `direct` 可直接对应 / `model` 需建模 /
  `mismatch` 模型不合。规则逐簇写在 `rules.py`，结论只来自抽取清单。
