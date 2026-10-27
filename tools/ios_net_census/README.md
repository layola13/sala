# iOS net × sa_std 缺口普查（Agent AU，2026-10-27）

同批普查之一（AO=Rust 全 std、AP=Go net、AQ=Python net、AR=Java net、
AS=.NET net、AT=Android net）。成果页：`content/06_stdlib/22_ios_net_census.html`。

## 数据来源（版本、出处与等级）

iOS 的 Network.framework / CFNetwork **没有完整开源发布**，本线按可靠度
分级取用，每条表面都在清单里标注等级：

- **grade=oss（Apple 开源发布）**：apple-oss-distributions 的 Libinfo
  （lookup.subproj/netdb.h、netdb_async.h）与 xnu（bsd/sys/socket.h、
  bsd/netinet/in.h 原文抓取），仓主分支快照，下载于 2026-10-27。
- **grade=oss-swift（开源对应物）**：swift-corelibs-foundation
  **swift-6.4.1-RELEASE**（该仓最新发行标签）的 Sources/FoundationNetworking
  全部 .swift + Sources/Foundation 的 URL 值类型三件。它是 Swift
  Foundation 层的开源实现，不是 Darwin 二进制的源码——与 Darwin
  URLSession 的已知差异写在成果页「覆盖边界」。
- **grade=doc（文档面、非源码面）**：Network.framework 无开源源码，
  表面取自 Apple 开发者文档站的官方 DocC 数据端点
  （developer.apple.com/tutorials/data/documentation/network/…），
  自框架根页 BFS 爬取符号引用闭包：1,712 页、抓取错误 0、符号 1,711；
  文档面中出现的最高 iOS 引入版本为 **27.0**，故本普查以 iOS 27
  世代文档面为准。
- **不可核登记**：CFNetwork 的 C 面（CFHTTPMessage 等）不在任何
  Apple 开源发布内，本线不取、不写。

- SA 侧基线：sci main `8a943911` 的 `sa_std`（盒上 `/content/sa_all/sci`），
  网络契约文件集：net.sai、netx.sai、http_client.sai、http_server.sai、
  http2.sai、ws_client.sai、tls_client.sai、tls_server.sai、dtls.sai、
  quic.sai、ssh.sai、multipart.sai 的 @extern（475）+ net.sal 的 #def
  常量（142），共 617 个符号。

盒上源码位置（运行时易失，勿依赖）：`/content/ioscensus-work/`
（corelibs 发行包、libinfo 克隆、xnu 头文件、DocC 爬取产物）。

## 脚本与复跑

```sh
python3 extract_sa_net.py <sa_std_dir> out/sa_net_surface.tsv
python3 crawl_network_docc.py out/network_symbols.tsv out/network_crawl_stats.json
python3 extract_corelibs.py <corelibs-release-root> out/corelibs_surface.tsv
python3 extract_apple_oss.py <workdir-with-libinfo-and-xnu-headers> out/apple_oss_surface.tsv
```

- `out/network_symbols.tsv`：Network.framework 文档面符号（1,711）
- `out/corelibs_surface.tsv`：URLSession 家族开源面声明（454）
- `out/apple_oss_surface.tsv`：POSIX/解析器开源面函数（76）
- `out/sa_net_surface.tsv`：sa_std 网络面符号（617）
- `out/network_crawl_stats.json`：DocC 爬取统计（页数/错误/分 kind 计数）
- `gap_classification.tsv`：35 个能力域的四分类裁定（人工裁定、证据列
  引用两侧清单；分类口径与同批一致）
