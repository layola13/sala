# Android net × sa_std 缺口普查（Agent AT，2026-10-27）

同批普查之一（AO=Rust 全 std、AP=Go net、AQ=Python net、AR=Java net、
AS=.NET net、AU=iOS net）。成果页：`content/06_stdlib/21_android_net_census.html`。

## 数据来源（版本与出处）

- Android 公共 API 签名面：AOSP `platform/prebuilts/sdk`，分支
  `android16-release`（HEAD `3b7daadc4e54d51439e5ae9b4dbd96cda8b6104e`，
  2025-04-18），文件 `36/public/api/android.txt`（签名格式 2.0，
  metalava 风格）——即 Android 16 / API level 36 的 SDK 公共 API 精确签名清单。
  注：新版 AOSP 的 frameworks/base 已不内嵌 current.txt，签名面以
  prebuilts/sdk 的 per-level android.txt 为权威来源。
- 辅证：`platform/frameworks/base` 同分支（HEAD
  `99b01a65cc4c104933788b3143285ab6bae65827`）的 `core/java/android/net` 源码。
- libcore 差异基线：盒上桌面 OpenJDK 源码树（AR 线的 jdk-src）中
  java.base 的 `java/net`、`javax/net`、`javax/net/ssl` 三包公共顶层类型。
- SA 侧基线：sci main `8a943911` 的 `sa_std`（盒上 `/content/sa_all/sci`）。

盒上源码位置（运行时易失，勿依赖）：`/content/android-sdk-src`、
`/content/android-fw-src`、`/content/jdk-src`。

## 复跑

```sh
cd tools/android_net_census
python3 extract_android_api.py <android.txt 路径> out
python3 extract_desktop_jdk_net.py <jdk-src 根> out
python3 extract_sa_std_net.py <sa_std 目录> out
```

产物（out/，随本目录入库）：

- `android_classes.tsv` / `android_members.tsv`：Android 侧类与成员清单
  （full = 全量分类范围；registration = wifi/telephony 仅登记）。
- `desktop_jdk_net_classes.tsv`：桌面 OpenJDK 三包公共顶层类型（107 个）。
- `sa_std_net_symbols.tsv`：sa_std 网络面符号（11 个 .sai 共 457 extern，
  另 .sa 层 487 个 fn/宏）。
- `gap_classification.tsv`：逐域四分类表（本目录下，与成果页内容一致）。

## 覆盖边界（如实注记）

- 类头带注解（`@Deprecated public class …`）的声明在抽取器初版被漏掉
  （595 类），修正后为 635 类 / 7,805 成员；rtp/sip 两包即此情形
  （整体 @Deprecated）。
- libcore 差异只做到**顶层类粒度**：桌面 107 个公共类型中 Android 仅缺
  `java.net.URLPermission` 与 `java.net.UnixDomainSocketAddress`，无
  Android 独有新增；方法级增减未逐项比对。
- WiFi / Telephony 只登记类/方法计数，不做逐项分类。
- `android.security.NetworkSecurityPolicy` 不在抽取包范围内，策略一节
  的存在性由签名文件直接查证。
- sa_std 侧比对以 .sai extern 契约（457）为准；.sa 层简化面
  （`sa_net_*`）与宏包装（487）只作注记、不逐项计入。
