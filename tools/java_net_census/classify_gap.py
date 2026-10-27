#!/usr/bin/env python3
"""Gap classification for the Java net census (JDK 27 GA x sa_std @ sci 8a943911).

Every API type extracted from the OpenJDK sources gets exactly one verdict:
  equiv  = 已有等价 (sa_std already covers the capability; note names the surface)
  direct = 可直接对应 (semantics land directly on the SA model; not yet present)
  model  = 需建模 (needs a modeled layer: state/config/callback/integration)
  unfit  = 模型不合 (presumes Java/JVM architecture SA does not adopt)
The script asserts full coverage of the refined API set and emits gap_table.tsv.
API visibility (refined): public, or a member type of an interface (implicitly
public) without `private`; other nested/package types count as internal.
"""
import csv, sys
from collections import Counter, defaultdict

EQ, DI, MO, UN = "已有等价", "可直接对应", "需建模", "模型不合"
ERR = "SA 错误码模型：SA_NET_ERROR_CODE_*（29 个）+ sa_std_net_error_code_name；SA 无异常类型，状态码即对应面"
PROV = "Java 可插拔 provider/SPI 架构（ServiceLoader/工厂注册），SA 为直达 extern 面，不迁移"

V = {}


def put(cls, note, *fqns):
    for f in fqns:
        assert f not in V, f
        V[f] = (cls, note)


# ---------------- java.net ----------------
put(EQ, "sa_std_net_tcp_stream_*/sa_net_tcp_* 全族（连接/读写/vectored/选项/shutdown）；子缺口：OOB 紧急数据、traffic class",
    "java.net.Socket")
put(EQ, "sa_std_net_tcp_listen/accept 族（backlog/reuseaddr/reuseport/only_v6/nonblocking）",
    "java.net.ServerSocket")
put(EQ, "sa_std_net_udp_* 全族（bind/connect/send_to/recv_from/peek/broadcast/超时/缓冲）",
    "java.net.DatagramSocket")
put(EQ, "udp send_to/recv_from + 地址句柄 + 缓冲三件套（包对象为值语义）",
    "java.net.DatagramPacket")
put(EQ, "sa_net_udp_join/leave_multicast_v4/v6 + multicast_if/ttl/hops/loop 全套",
    "java.net.MulticastSocket")
put(EQ, "sa_std_net_to_socket_addr_list/_first（解析为地址列表）+ addr_format + reverse_lookup + scope_id；子缺口：isReachable（ICMP/echo 探测）无符号",
    "java.net.InetAddress", "java.net.Inet4Address", "java.net.Inet6Address")
put(EQ, "socket_addr v4/v6 parse/format + port（createUnresolved ≈ parse_ascii 不解析路径）",
    "java.net.InetSocketAddress")
put(EQ, "NetAddr 不透明句柄（sa_net_addr_*）", "java.net.SocketAddress")
put(EQ, "sa_std_net_unix_addr_from_pathname/_abstract_name + unix 流/数据报全族",
    "java.net.UnixDomainSocketAddress")
put(EQ, "选项常量 ↔ sa_std_net_*_set_* 选项族（nodelay/keepalive/linger/ttl/缓冲/quickack/deferaccept）+ SA_NET_SOCKET_OPTION_*",
    "java.net.StandardSocketOptions", "java.net.SocketOptions", "java.net.SocketOption")
put(EQ, "地址族值（sa_net_addr_family）；注意 AJ 普查登记的 SA_NET_AF 双定义陷阱（.sal 内编号 vs OS 值）",
    "java.net.StandardProtocolFamily", "java.net.ProtocolFamily")
put(EQ, ERR,
    "java.net.BindException", "java.net.ConnectException", "java.net.HttpRetryException",
    "java.net.MalformedURLException", "java.net.NoRouteToHostException",
    "java.net.PortUnreachableException", "java.net.ProtocolException",
    "java.net.SocketException", "java.net.SocketTimeoutException",
    "java.net.UnknownHostException", "java.net.UnknownServiceException",
    "java.net.URISyntaxException")
put(DI, "punycode/IDNA 双向转换：std 全域无符号（纯函数，可直接落 sa_std）",
    "java.net.IDN")
put(DI, "URI 语法操作：仅 sa_std_url_parse（scheme/host/port/path）存在；resolve/relativize/normalize/引号编解码等纯语法面未覆盖",
    "java.net.URI")
put(DI, "application/x-www-form-urlencoded 百分号编解码：std 无符号（纯函数）",
    "java.net.URLEncoder", "java.net.URLDecoder")
put(DI, "单个 cookie 的解析/序列化/域路径匹配（纯函数）；jar 与存储见 CookieStore 簇",
    "java.net.HttpCookie")
put(DI, "扩展名→MIME 类型表（小型纯函数面），std 无符号", "java.net.FileNameMap")
put(DI, "网卡枚举面（getifaddrs 类）：地址/广播/前缀长度/MTU/硬件地址/up/回环标志；std 仅有主机名与单地址解析，无枚举符号",
    "java.net.NetworkInterface", "java.net.InterfaceAddress")
put(MO, "HTTP cookie jar + 接受策略 + 存储，并与 HTTP 客户端集成；std cookie 符号为零",
    "java.net.CookieHandler", "java.net.CookieManager", "java.net.CookiePolicy",
    "java.net.CookieStore")
put(MO, "HTTP 凭据回调（Authenticator 模型）；sa_http_client 仅有 req_add_openai_auth 硬编码面，无通用凭据回调",
    "java.net.Authenticator", "java.net.Authenticator.RequestorType",
    "java.net.PasswordAuthentication")
put(MO, "代理配置与选择（HTTP/SOCKS）；std 代理符号为零，客户端与套接字均无代理参数面",
    "java.net.Proxy", "java.net.Proxy.Type", "java.net.ProxySelector")
put(MO, "URLConnection 对象模型（legacy 客户端）；能力大部由 sa_http_client_* 覆盖，缺重定向/认证/缓存集成与流式请求体",
    "java.net.HttpURLConnection", "java.net.URLConnection")
put(MO, "URL 值对象绑定 openStream/openConnection（URLConnection 栈）；解析部分由 sa_std_url_parse 覆盖",
    "java.net.URL")
put(MO, "HTTP 响应缓存 SPI + 客户端集成点；std 无缓存面",
    "java.net.CacheRequest", "java.net.CacheResponse", "java.net.ResponseCache",
    "java.net.SecureCacheResponse")
put(UN, "URLConnection 内容处理器可插拔架构，随 URLConnection 模型不迁移",
    "java.net.ContentHandler", "java.net.ContentHandlerFactory")
put(UN, "SocketImpl 实现继承/工厂架构（JVM 可插拔实现层）；SA 为直达 extern 面",
    "java.net.DatagramSocketImpl", "java.net.DatagramSocketImplFactory",
    "java.net.SocketImpl", "java.net.SocketImplFactory")
put(UN, "协议处理器可插拔架构（URLStreamHandler 族）",
    "java.net.URLStreamHandler", "java.net.URLStreamHandlerFactory")
put(UN, "网络类加载（JVM 类加载体系），非网络能力面", "java.net.URLClassLoader")
put(UN, "jar: 协议 URL 语义（Java 归档协议），SA 无对应协议栈", "java.net.JarURLConnection")
put(UN, "Java 权限/SecurityManager 模型；SA 侧由 policy 体系（sala 16_policy）承担，不迁移权限类",
    "java.net.NetPermission", "java.net.SocketPermission", "java.net.URLPermission")
# java.net.spi
put(MO, "可插拔 DNS 解析器钩子（InetAddress 解析策略点）；std 解析为内置实现、无策略注入面",
    "java.net.spi.InetAddressResolver", "java.net.spi.InetAddressResolver.LookupPolicy")
put(UN, PROV,
    "java.net.spi.InetAddressResolverProvider",
    "java.net.spi.InetAddressResolverProvider.Configuration",
    "java.net.spi.URLStreamHandlerProvider")

# ---------------- javax.net ----------------
put(MO, "工厂间接层；底层 connect/listen 能力已有（sa_std_net_tcp_*），SA 惯例为直达函数，工厂层属建模选择",
    "javax.net.SocketFactory", "javax.net.ServerSocketFactory")

# ---------------- javax.net.ssl ----------------
put(EQ, "sa_std_tls_client_*（connect/read/write/close/add_ca_file）+ tls_shaped 指纹客户端（JA3/JA4 整形）；会话信息经 status_json 部分对应",
    "javax.net.ssl.SSLSocket")
put(EQ, "tls_client connect 入口（工厂形态不同、能力对应）", "javax.net.ssl.SSLSocketFactory")
put(EQ, "sa_std_tls_server_ctx_create（cert/key 文件路径）+ accept/read/write",
    "javax.net.ssl.SSLServerSocket", "javax.net.ssl.SSLServerSocketFactory")
put(EQ, ERR,
    "javax.net.ssl.SSLException", "javax.net.ssl.SSLHandshakeException",
    "javax.net.ssl.SSLKeyException", "javax.net.ssl.SSLPeerUnverifiedException",
    "javax.net.ssl.SSLProtocolException")
put(MO, "TLS 上下文聚合（key/trust/session/参数）；SA 仅 tls_server ctx（证书路径）与客户端直连，无统一上下文对象",
    "javax.net.ssl.SSLContext")
put(MO, "TLS 配置面：密码套件/协议版本/ALPN/SNI 匹配/端点识别/客户端认证模式；SA 符号面无对应（shaped 客户端的指纹整形是另一条轴）",
    "javax.net.ssl.SSLParameters")
put(MO, "SNI 名称与匹配（SSLParameters 簇）；tls connect 以 host 隐含 SNI，无显式多名/匹配器面",
    "javax.net.ssl.SNIServerName", "javax.net.ssl.SNIHostName",
    "javax.net.ssl.SNIMatcher", "javax.net.ssl.StandardConstants")
put(MO, "非阻塞 TLS 引擎（wrap/unwrap 字节缓冲状态机），可嵌入自有反应器（如 netx）；SA 的 TLS 绑定套接字、无引擎形态",
    "javax.net.ssl.SSLEngine", "javax.net.ssl.SSLEngineResult",
    "javax.net.ssl.SSLEngineResult.HandshakeStatus", "javax.net.ssl.SSLEngineResult.Status")
put(MO, "TLS 会话内省/恢复/绑定事件；SA 仅 status_json/negotiated_json 部分内省，无会话缓存与恢复面",
    "javax.net.ssl.SSLSession", "javax.net.ssl.ExtendedSSLSession",
    "javax.net.ssl.SSLSessionContext", "javax.net.ssl.SSLSessionBindingEvent",
    "javax.net.ssl.SSLSessionBindingListener")
put(MO, "密钥材料管理（内存证书、别名选择回调）；SA 仅文件路径装载（ctx_create/add_ca_file）",
    "javax.net.ssl.KeyManager", "javax.net.ssl.X509KeyManager",
    "javax.net.ssl.X509ExtendedKeyManager", "javax.net.ssl.KeyManagerFactory",
    "javax.net.ssl.KeyStoreBuilderParameters")
put(MO, "信任决策面（自定义校验回调、证书链内省）；SA 仅 add_ca_file，无 X.509 解析符号与校验回调",
    "javax.net.ssl.TrustManager", "javax.net.ssl.X509TrustManager",
    "javax.net.ssl.X509ExtendedTrustManager", "javax.net.ssl.TrustManagerFactory",
    "javax.net.ssl.CertPathTrustManagerParameters",
    "javax.net.ssl.ManagerFactoryParameters")
put(MO, "主机名校验回调；SA 客户端校验策略未在符号面暴露", "javax.net.ssl.HostnameVerifier")
put(MO, "握手完成事件/回调（SSLSocket/SSLEngine 事件面）",
    "javax.net.ssl.HandshakeCompletedEvent", "javax.net.ssl.HandshakeCompletedListener")
put(MO, "URLConnection×TLS 复合类；底层能力由 http_client(use_tls)+tls 覆盖，对象模型见 URLConnection 簇",
    "javax.net.ssl.HttpsURLConnection")
put(UN, PROV,
    "javax.net.ssl.SSLContextSpi", "javax.net.ssl.KeyManagerFactorySpi",
    "javax.net.ssl.TrustManagerFactorySpi")
put(UN, "Java 权限模型（见 NetPermission 行）", "javax.net.ssl.SSLPermission")

# ---------------- java.net.http ----------------
put(EQ, "sa_http_client_req_new/add_header/set_body/set_timeout/send(+async/poll)；method 以 u8 传入（AJ 登记：method 命名常量面仅四种）",
    "java.net.http.HttpRequest", "java.net.http.HttpRequest.Builder")
put(EQ, "sa_http_client_resp_status/get_header/body_len/body_ptr/body_reader/read_chunk",
    "java.net.http.HttpResponse", "java.net.http.HttpResponse.ResponseInfo")
put(EQ, "req/resp 头函数面（get/add）；无独立多值映射容器类型，能力对应",
    "java.net.http.HttpHeaders")
put(EQ, "sa_std_ws_client_*（connect/send_text/send_binary/ping/recv/close）+ sa_http_client_websocket_*；Listener 回调 ↔ SA 轮询读（poll/read）模型差异已注",
    "java.net.http.WebSocket", "java.net.http.WebSocket.Builder",
    "java.net.http.WebSocket.Listener")
put(EQ, ERR,
    "java.net.http.HttpConnectTimeoutException", "java.net.http.HttpTimeoutException",
    "java.net.http.WebSocketHandshakeException", "java.net.http.StreamLimitException",
    "java.net.http.UnsupportedProtocolVersionException")
put(MO, "客户端聚合配置（版本偏好/重定向/cookie/proxy/auth/连接超时/executor）；SA 为分立函数面，多项子面缺失（见各簇）",
    "java.net.http.HttpClient", "java.net.http.HttpClient.Builder")
put(MO, "协议版本偏好；SA 以 http_client / http2 client_request / http3 session 三个显式入口分立",
    "java.net.http.HttpClient.Version")
put(DI, "重定向跟随策略与客户端重定向循环：SA 客户端符号面未见重定向处理（小面策略 + 既有 send 循环）",
    "java.net.http.HttpClient.Redirect")
put(MO, "请求体发布者：字符串/字节 ≈ req_set_body；文件/输入流/迭代器发布者无对应（请求体为整缓冲模型）",
    "java.net.http.HttpRequest.BodyPublisher", "java.net.http.HttpRequest.BodyPublishers")
put(MO, "响应体处理器：ofString/ofBytes ≈ 体缓冲；ofFile/ofLines 流式 ≈ body_reader/read_chunk 部分对应，处理器注册模型无",
    "java.net.http.HttpResponse.BodyHandler", "java.net.http.HttpResponse.BodyHandlers")
put(MO, "响应式流订阅模型（Flow.Subscription 背压）；SA 为拉取式 body_reader，模型不同",
    "java.net.http.HttpResponse.BodySubscriber", "java.net.http.HttpResponse.BodySubscribers")
put(MO, "h2/h3 服务器推送处理；SA http2 有 HTTP2_SETTINGS_ENABLE_PUSH、http3 有 session，无推送承诺处理面",
    "java.net.http.HttpResponse.PushPromiseHandler",
    "java.net.http.HttpResponse.PushPromiseHandler.PushId",
    "java.net.http.HttpResponse.PushPromiseHandler.PushId.Http3PushId")
put(MO, "HttpClient 的 HTTP/3 发现模式配置（Alt-Svc/HTTPS RR 发现与回退）；SA http3 为显式 session API，无发现语义",
    "java.net.http.HttpOption", "java.net.http.HttpOption.Http3DiscoveryMode")

# ---------------- com.sun.net.httpserver ----------------
put(EQ, "sa_http_server_new/start/accept(_v2) + req method/path/header/body + resp/stream 面 + serve_threaded",
    "com.sun.net.httpserver.HttpServer")
put(EQ, "http_server req/resp 头函数面（见 HttpHeaders 行）", "com.sun.net.httpserver.Headers")
put(MO, "HTTP×TLS 组合服务器 + 服务器 TLS 参数；SA 有 tls_server 分立面，无组合 https server 与参数面",
    "com.sun.net.httpserver.HttpsServer", "com.sun.net.httpserver.HttpsConfigurator",
    "com.sun.net.httpserver.HttpsParameters")
put(MO, "路径上下文 + handler 对象（框架层）；SA std 为 accept 循环层，框架形态属 plugin 门面层",
    "com.sun.net.httpserver.HttpContext", "com.sun.net.httpserver.HttpHandler",
    "com.sun.net.httpserver.HttpHandlers", "com.sun.net.httpserver.Request")
put(MO, "单次交换对象（请求/响应流 + 属性表）；能力由 accept_v2 的 req/resp 句柄覆盖，对象模型属框架层",
    "com.sun.net.httpserver.HttpExchange", "com.sun.net.httpserver.HttpsExchange")
put(MO, "中间件过滤链（框架层）",
    "com.sun.net.httpserver.Filter", "com.sun.net.httpserver.Filter.Chain")
put(MO, "服务器侧 HTTP Basic 认证 + 主体；SA std 无 auth 符号面",
    "com.sun.net.httpserver.Authenticator", "com.sun.net.httpserver.Authenticator.Result",
    "com.sun.net.httpserver.Authenticator.Success",
    "com.sun.net.httpserver.Authenticator.Failure",
    "com.sun.net.httpserver.Authenticator.Retry",
    "com.sun.net.httpserver.BasicAuthenticator", "com.sun.net.httpserver.HttpPrincipal")
put(DI, "静态文件服务助手（http_server 之上的小型固化实现）；std 无现成符号",
    "com.sun.net.httpserver.SimpleFileServer", "com.sun.net.httpserver.SimpleFileServer.OutputLevel")
put(UN, PROV, "com.sun.net.httpserver.spi.HttpServerProvider")

# ---------------- java.nio.channels (NIO, single-listed) ----------------
put(EQ, "sa_std_net_tcp_stream_* + set_nonblocking + read/write_vectored（通道阻塞/非阻塞双模 ↔ nonblocking 开关）",
    "java.nio.channels.SocketChannel")
put(EQ, "tcp_listener 族（bind/accept/nonblocking）", "java.nio.channels.ServerSocketChannel")
put(EQ, "udp 族（bind/connect/send/recv + 组播）", "java.nio.channels.DatagramChannel")
put(EQ, "udp join_multicast 对应；源特定组播（SSM）过滤 block/unblock 未见符号（子缺口）",
    "java.nio.channels.MembershipKey", "java.nio.channels.MulticastChannel")
put(EQ, "sa_net_unix_pair（socketpair）", "java.nio.channels.Pipe",
    "java.nio.channels.Pipe.SinkChannel", "java.nio.channels.Pipe.SourceChannel")
put(EQ, ERR,
    "java.nio.channels.AcceptPendingException", "java.nio.channels.AlreadyBoundException",
    "java.nio.channels.AlreadyConnectedException", "java.nio.channels.AsynchronousCloseException",
    "java.nio.channels.CancelledKeyException", "java.nio.channels.ClosedByInterruptException",
    "java.nio.channels.ClosedChannelException", "java.nio.channels.ClosedSelectorException",
    "java.nio.channels.ConnectionPendingException", "java.nio.channels.IllegalBlockingModeException",
    "java.nio.channels.IllegalChannelGroupException", "java.nio.channels.IllegalSelectorException",
    "java.nio.channels.NoConnectionPendingException",
    "java.nio.channels.InterruptedByTimeoutException", "java.nio.channels.NonReadableChannelException",
    "java.nio.channels.NonWritableChannelException", "java.nio.channels.NotYetBoundException",
    "java.nio.channels.NotYetConnectedException", "java.nio.channels.ReadPendingException",
    "java.nio.channels.ShutdownChannelGroupException", "java.nio.channels.UnresolvedAddressException",
    "java.nio.channels.UnsupportedAddressTypeException", "java.nio.channels.WritePendingException")
put(MO, "就绪选择模型（interestOps/selectedKeys/wakeup）；SA 的对应物是 netx io_uring 完成式反应器（票据模型）+ 非阻塞句柄，无 Selector 形态",
    "java.nio.channels.Selector", "java.nio.channels.SelectionKey",
    "java.nio.channels.SelectableChannel", "java.nio.channels.NetworkChannel")
put(MO, "完成式 AIO（CompletionHandler/Future 回调）；与 netx 票据模型相近但形态不同（netx 无 per-op handler 对象）",
    "java.nio.channels.AsynchronousSocketChannel",
    "java.nio.channels.AsynchronousServerSocketChannel",
    "java.nio.channels.AsynchronousByteChannel", "java.nio.channels.AsynchronousChannel",
    "java.nio.channels.CompletionHandler")
put(UN, "通道组 = JVM 线程池/运行时架构（AIO 线程池生命周期）",
    "java.nio.channels.AsynchronousChannelGroup")
put(UN, "java.io 流 ↔ 通道适配（建立在 Java IO 类型体系上）", "java.nio.channels.Channels")
put(UN, "通道接口层级（类型体系抽象）；SA 句柄模型无对应的接口层级",
    "java.nio.channels.Channel", "java.nio.channels.ByteChannel",
    "java.nio.channels.ReadableByteChannel", "java.nio.channels.WritableByteChannel",
    "java.nio.channels.GatheringByteChannel", "java.nio.channels.ScatteringByteChannel",
    "java.nio.channels.SeekableByteChannel", "java.nio.channels.InterruptibleChannel")
put(UN, "范围外（文件域）：NIO 文件通道归 sa_std fs 契约，本普查登记但不计入网络缺口",
    "java.nio.channels.FileChannel", "java.nio.channels.FileChannel.MapMode",
    "java.nio.channels.FileLock", "java.nio.channels.AsynchronousFileChannel",
    "java.nio.channels.FileLockInterruptionException",
    "java.nio.channels.OverlappingFileLockException")
put(UN, PROV,
    "java.nio.channels.spi.AbstractInterruptibleChannel",
    "java.nio.channels.spi.AbstractSelectableChannel",
    "java.nio.channels.spi.AbstractSelectionKey",
    "java.nio.channels.spi.AbstractSelector",
    "java.nio.channels.spi.AsynchronousChannelProvider",
    "java.nio.channels.spi.SelectorProvider")

# ---------------- jdk.net ----------------
put(EQ, "扩展套接字选项 ↔ keepalive_params/quickack/deferaccept/ttl 等 set 族（个别平台项如 SO_FLOW_SLA 未见对应）",
    "jdk.net.ExtendedSocketOptions", "jdk.net.Sockets")
put(DI, "unix 套接字对端凭据（SO_PEERCRED 面）；SA unix addr 族有 kind/path/abstract，无 peer-cred 符号（小面）",
    "jdk.net.UnixDomainPrincipal")
put(UN, "Java 权限模型（见 NetPermission 行）", "jdk.net.NetworkPermission")


def main():
    types = list(csv.DictReader(open("out/java_types.tsv"), delimiter="\t"))
    mem = list(csv.DictReader(open("out/java_members.tsv"), delimiter="\t"))
    byfqn = {t["fqn"]: t for t in types}

    def is_api(t):
        mods = t["modifiers"]
        if "private" in mods:
            return False
        if "public" in mods:
            return True
        fqn = t["fqn"]
        rest = fqn[len(t["package"]) + 1:]
        if "." not in rest:
            return False
        parent = byfqn.get(fqn.rsplit(".", 1)[0])
        return bool(parent) and parent["kind"] in ("interface", "@interface") \
            and is_api(parent)

    api = [t for t in types if is_api(t)]
    mc = Counter(m["fqn"] for m in mem)
    apiset = {t["fqn"] for t in api}
    missing = apiset - set(V)
    extra = set(V) - apiset
    if missing:
        print("UNCLASSIFIED:", sorted(missing)); sys.exit(1)
    if extra:
        print("CLASSIFIED BUT NOT API:", sorted(extra)); sys.exit(1)
    with open("out/gap_table.tsv", "w") as f:
        f.write("package\tfqn\tkind\tmembers\tclass\tnote\n")
        for t in sorted(api, key=lambda x: (x["package"], x["fqn"])):
            cls, note = V[t["fqn"]]
            f.write("\t".join([t["package"], t["fqn"], t["kind"],
                               str(mc.get(t["fqn"], 0)), cls, note]) + "\n")
    print("API types classified:", len(api))
    bypkg = defaultdict(Counter)
    for t in api:
        bypkg[t["package"]][V[t["fqn"]][0]] += 1
    for pkg in sorted(bypkg):
        c = bypkg[pkg]
        print(pkg, dict(c), "total", sum(c.values()))
    tot = Counter(V[t["fqn"]][0] for t in api)
    print("TOTAL", dict(tot), "sum", sum(tot.values()))
    dropped = [t["fqn"] for t in types if t not in api]
    print("internal types:", len(dropped))


if __name__ == '__main__':
    main()
