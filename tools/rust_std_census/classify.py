#!/usr/bin/env python3
"""Classify the Rust library surface against the sa_std inventory.

Inputs: rust_surface.tsv (extract_rust.py), sa_surface.tsv (extract_sa.py).
Output: rust_classified.tsv + summary printed to stdout.

Every row gets exactly one category:
  equiv   已有等价  (auto name-match or curated type map, evidence recorded)
  direct  可直接对应 (semantics land directly in sa_std, just not done)
  model   需建模    (needs a modeling layer: handles/state machines/traits)
  nomodel 模型不合  (depends on machinery outside SA's model; reason recorded)
  internal 非公共面 (std::sys etc. — not public API, excluded from gap stats)

Classification order: internal -> auto-match -> type map -> trait rules ->
domain name-pattern subrules -> domain defaults. The rule id that decided
each row is recorded so the census is auditable and re-runnable.
"""
import csv, json, re, sys
from collections import defaultdict

RUST_TSV, SA_TSV, OUT_TSV = sys.argv[1], sys.argv[2], sys.argv[3]

# ---------- SA inventory ----------
sa_names = set()          # exact names, all layers
sa_lower = {}             # lowercase name -> example original
sa_files = set()          # file stems, e.g. vec, string, btree_map
with open(SA_TSV, encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter="\t"):
        sa_names.add(row["name"])
        sa_lower.setdefault(row["name"].lower(), row["name"])
        stem = row["file"].replace("\\", "/").split("/")[-1]
        sa_files.add(stem.rsplit(".", 1)[0])

def sa_has(name):
    return name in sa_names or name.lower() in sa_lower

def sa_family(prefix):
    """True if any SA symbol starts with prefix (a live surface family)."""
    p = prefix.lower()
    return any(k.startswith(p) for k in sa_lower)

# ---------- name helpers ----------
def snake(name):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", s)
    return s.lower()

OWNER_ALIASES = {
    "Vec": ["vec"], "VecDeque": ["vec_deque", "deque"], "String": ["string", "str"],
    "str": ["str", "string"], "slice": ["slice", "arr"], "HashMap": ["hash_map", "map"],
    "HashSet": ["hash_set", "set"], "BTreeMap": ["btree_map"], "BTreeSet": ["btree_set"],
    "BinaryHeap": ["binary_heap"], "LinkedList": ["linked_list"],
    "Duration": ["duration"], "PathBuf": ["path"], "Path": ["path"],
    "TcpStream": ["tcp"], "UdpSocket": ["udp"], "TcpListener": ["tcp"],
    "Cow": ["cow"], "CString": ["cstring"], "CStr": ["cstring"],
    "OsString": ["os_str", "os_string"], "OsStr": ["os_str"],
    "Rc": ["rc"], "Arc": ["arc"], "Box": ["box"],
    "Cell": ["cell"], "RefCell": ["refcell", "cell"],
    "Mutex": ["mutex"], "RwLock": ["rwlock"],
    "Option": ["option"], "Result": ["result"],
    "Wtf8": ["wtf8"], "Wtf8Buf": ["wtf8"],
    "Char": ["char"], "char": ["char"], "bool": ["bool"],
    "Range": ["range"], "RangeInclusive": ["range"], "RangeFull": ["range"],
    "RangeFrom": ["range"], "RangeTo": ["range"], "RangeToInclusive": ["range"],
    "Ordering": ["ordering", "cmp"],
    "SystemTime": ["time", "system_time"], "Instant": ["time", "instant"],
    "File": ["file", "fs"], "DirEntry": ["fs"], "Metadata": ["fs", "metadata"],
    "Error": ["error"], "Formatter": ["fmt", "format"],
}

# type-level equivalence: rust type -> SA evidence substrings (names or files)
TYPE_MAP = {
    "Vec": ["vec"], "VecDeque": ["vec_deque", "deque"], "String": ["string"],
    "str": ["str"], "BTreeMap": ["btree_map"], "BTreeSet": ["btree_set"],
    "HashMap": ["hash_map"], "HashSet": ["hash_set"], "BinaryHeap": ["binary_heap"],
    "LinkedList": ["linked_list"], "Duration": ["duration"],
    "Cow": ["cow"], "CString": ["cstring"], "CStr": ["cstring"],
    "Rc": ["rc"], "Arc": ["arc"], "Cell": ["cell"], "RefCell": ["cell"],
    "Path": ["path"], "PathBuf": ["path"], "Ordering": ["cmp"],
    "Range": ["range"], "RangeInclusive": ["range"],
    "SystemTime": ["time"], "Instant": ["time"],
    "TcpStream": ["tcp"], "TcpListener": ["tcp"], "UdpSocket": ["udp"],
    "File": ["fs"], "Mutex": ["mutex"], "RwLock": ["rwlock"],
    "Condvar": ["condvar"], "Barrier": ["barrier"],
    "Error": ["error"], "Formatter": ["fmt"],
    "AtomicBool": ["atomic"], "AtomicU64": ["atomic"], "AtomicUsize": ["atomic"],
    "AtomicI32": ["atomic"], "AtomicPtr": ["atomic"],
    "Layout": ["alloc", "layout"], "ManuallyDrop": ["manually_drop"],
    "MaybeUninit": ["maybe_uninit"], "PhantomData": [],
    "Once": ["once"], "OnceLock": ["once"], "LazyLock": ["once", "lazy"],
    "Thread": ["thread"], "JoinHandle": ["thread"],
    "Command": ["process"], "Child": ["process"],
    "ExitStatus": ["process"], "Output": ["process"], "Stdio": ["process"],
    "IpAddr": ["net", "ip"], "Ipv4Addr": ["ipv4"], "Ipv6Addr": ["ipv6"],
    "SocketAddr": ["net", "socket"], "SocketAddrV4": ["net"], "SocketAddrV6": ["net"],
    "Read": [], "Write": [], "Seek": [], "Iterator": [],
}

INT_OWNERS = {f"{p}{b}" for p in "iu" for b in (8, 16, 32, 64, 128)} | {
    "usize", "isize", "f16", "f32", "f64", "f128", "bool",
    "NonZeroI8", "NonZeroI16", "NonZeroI32", "NonZeroI64", "NonZeroI128",
    "NonZeroIsize", "NonZeroU8", "NonZeroU16", "NonZeroU32", "NonZeroU64",
    "NonZeroU128", "NonZeroUsize", "Wrapping", "Saturating",
}

MODULE_DOMAIN = [
    ("std::sys", "internal"), ("std::sys_common", "internal"), ("std::rt", "internal"),
    ("core::intrinsics", "internal"), ("alloc::raw_vec", "internal"),
    ("core::io", "io"), ("alloc::io", "io"),
    ("core::ops", "num"), ("core::ascii", "string_str"), ("core::unicode", "string_str"),
    ("core::hint", "mem"), ("core::future", "async"), ("core::task", "async"),
    ("core::wtf8", "string_str"), ("std::ascii", "string_str"),
    ("core::range", "slice"), ("core::clone", "convert"),
    ("core::async_iter", "async"), ("core::asserting", "internal"),
    ("alloc::ffi", "ffi_os"), ("core::net", "net"),
    ("core::iter", "iter"), ("core::fmt", "fmt"), ("alloc::fmt", "fmt"),
    ("core::str", "string_str"), ("alloc::str", "string_str"),
    ("alloc::string", "string_str"), ("core::char", "string_str"),
    ("alloc::collections", "collections"), ("std::collections", "collections"),
    ("alloc::vec", "collections"), ("alloc::boxed", "collections"),
    ("alloc::rc", "collections"), ("alloc::sync", "sync"),
    ("core::slice", "slice"), ("alloc::slice", "slice"), ("core::array", "slice"),
    ("core::option", "option_result"), ("core::result", "option_result"),
    ("core::num", "num"), ("core::mem", "mem"), ("core::ptr", "mem"),
    ("core::alloc", "mem"), ("alloc::alloc", "mem"), ("core::pin", "mem"),
    ("core::cmp", "cmp"), ("core::convert", "convert"),
    ("core::error", "error"), ("std::error", "error"),
    ("core::panic", "panic"), ("std::panic", "panic"),
    ("core::panicking", "panic"), ("std::panicking", "panic"),
    ("std::backtrace", "panic"),
    ("core::marker", "marker_meta"), ("core::any", "marker_meta"),
    ("core::cell", "cell"), ("core::sync", "sync"), ("std::sync", "sync"),
    ("core::time", "time"), ("std::time", "time"),
    ("core::hash", "collections"), ("core::borrow", "convert"),
    ("alloc::borrow", "string_str"),
    ("std::io", "io"), ("std::fs", "fs"), ("std::path", "fs"),
    ("std::net", "net"), ("std::process", "process_env"), ("std::env", "process_env"),
    ("std::thread", "thread"), ("std::ffi", "ffi_os"), ("std::os", "ffi_os"),
    ("alloc::task", "other"), ("core::future", "other"), ("core::task", "other"),
]
OWNER_DOMAIN = {
    "Option": "option_result", "Result": "option_result",
    "String": "string_str", "str": "string_str", "char": "string_str",
    "Wtf8": "string_str", "Wtf8Buf": "string_str", "Cow": "string_str",
    "Vec": "collections", "VecDeque": "collections", "BTreeMap": "collections",
    "BTreeSet": "collections", "HashMap": "collections", "HashSet": "collections",
    "BinaryHeap": "collections", "LinkedList": "collections", "Rc": "collections",
    "Box": "collections", "Arc": "sync", "Weak": "sync",
    "slice": "slice", "Ordering": "cmp",
    "Duration": "time", "Instant": "time", "SystemTime": "time",
    "File": "fs", "Path": "fs", "PathBuf": "fs", "DirEntry": "fs",
    "OpenOptions": "fs", "Metadata": "fs",
    "TcpStream": "net", "TcpListener": "net", "UdpSocket": "net",
    "IpAddr": "net", "Ipv4Addr": "net", "Ipv6Addr": "net",
    "SocketAddr": "net", "SocketAddrV4": "net", "SocketAddrV6": "net",
    "Mutex": "sync", "RwLock": "sync", "Condvar": "sync", "Barrier": "sync",
    "Once": "sync", "OnceLock": "sync", "LazyLock": "sync",
    "Cell": "cell", "RefCell": "cell", "UnsafeCell": "cell",
    "Layout": "mem", "ManuallyDrop": "mem", "MaybeUninit": "mem",
    "Error": "error", "CString": "ffi_os", "CStr": "ffi_os",
    "OsString": "ffi_os", "OsStr": "ffi_os",
    "Command": "process_env", "Child": "process_env",
    "ExitStatus": "process_env", "Output": "process_env", "Stdio": "process_env",
    "Thread": "thread", "JoinHandle": "thread",
    "Formatter": "fmt",
    "Waker": "async", "RawWaker": "async", "Context": "async", "Poll": "async",
}

def domain_of(module, owner):
    for prefix, dom in MODULE_DOMAIN:
        if module == prefix or module.startswith(prefix + "::"):
            return dom
    if owner in OWNER_DOMAIN:
        return OWNER_DOMAIN[owner]
    if owner in INT_OWNERS:
        return "num"
    return "other"

# ---------- auto equivalence ----------
def auto_match(kind, owner, name):
    """Return matched SA symbol or None."""
    if kind in ("fn",):
        for cand in (name, "sa_" + name, name.upper(), "sa_std_" + name):
            if sa_has(cand):
                return sa_lower.get(cand.lower(), cand)
        return None
    if kind in ("method", "trait_method") and owner:
        aliases = OWNER_ALIASES.get(owner, [snake(owner)])
        for a in aliases:
            for cand in (f"sa_{a}_{name}", f"{a}_{name}", f"{a.upper()}_{name.upper()}",
                         f"sa_std_{a}_{name}", f"ts_{a}_{name}"):
                if sa_has(cand):
                    return sa_lower.get(cand.lower(), cand)
        return None
    if kind == "const":
        for cand in (name, f"SA_{name}", name.upper()):
            if sa_has(cand):
                return sa_lower.get(cand.lower(), cand)
        return None
    return None

def type_map_match(name):
    for key in TYPE_MAP.get(name, []):
        if sa_family(key) or key in sa_files or sa_has(key):
            return key
    return None

ITER_NAMES = re.compile(r"^(iter|iter_mut|into_iter|keys|values|values_mut|drain|range|range_mut|"
                        r"extract_if|chars|char_indices|bytes|lines|split|split_|rsplit|matches|"
                        r"match_indices|windows|chunks|chunks_mut|chunks_exact|rchunks|splitn|"
                        r"rsplitn|split_inclusive|split_ascii_whitespace|split_whitespace|"
                        r"split_terminator|rsplit_terminator|graphemes|utf16|encode_utf16|ancestors)$")
TRAIT_NOMODEL = {"Drop", "Any"}
TRAIT_NOMODEL_REASON = {
    "Drop": "用户 Drop 靠编译器在作用域退出时自动调用析构，SA/SLA 无此钩子面（只有内建资源释放）",
    "Any": "Any/downcast 依赖 RTTI 类型标识，SA 无运行时类型信息面",
}

def classify(row):
    crate, module, kind, owner, name = row["crate"], row["module"], row["kind"], row["owner"], row["name"]
    dom = domain_of(module, owner)
    if dom == "internal":
        return dom, "internal", "", "R-internal", "std::sys 等是 std 内部实现模块，非公共 API"
    if kind in ("struct", "enum", "trait", "type", "union") and name in TYPE_MAP:
        hit = type_map_match(name)
        if hit:
            return dom, "equiv", hit, "R-typemap", f"sa_std 已有对应表面（证据符号/文件含 '{hit}'）"
    m = auto_match(kind, owner, name)
    if m:
        return dom, "equiv", m, "R-automatch", f"sa_std 已有同名/同族符号 {m}"
    # trait bodies
    if kind == "trait":
        if name in TRAIT_NOMODEL:
            return dom, "nomodel", "", "R-trait-nomodel", TRAIT_NOMODEL_REASON[name]
        if name in ("Send", "Sync", "Copy", "Sized", "Unpin"):
            return dom, "nomodel", "", "R-trait-marker", "标记 trait 是类型系统层声明，SA 模型中被擦除、无可实现实体"
        return dom, "model", "", "R-trait", "trait 本体需以单态化展开或函数表建模，sa_std 无通用 trait 面"
    # iterator-returning methods across collection/string/slice domains
    if kind in ("method", "trait_method") and ITER_NAMES.match(name) and dom in ("collections", "string_str", "slice", "fs"):
        return dom, "model", "", "R-iter-return", "返回惰性迭代器，需迭代器建模（状态机/适配器面），急切数组函数不等价"
    # domain subrules + defaults: (category, rule, reason)
    D = {
        "iter":      ("model", "R-dom-iter", "Iterator 适配器链/源需惰性迭代器建模（状态机 + 适配器组合）"),
        "fmt":       ("model", "R-dom-fmt", "格式化体系（Display/Debug/format_args）需格式化建模层"),
        "io":        ("model", "R-dom-io", "io trait 体系（Read/Write/Seek/BufRead 对象面）需句柄化 io 建模"),
        "fs":        ("direct", "R-dom-fs", "文件/路径操作是直接 syscall 面，sa_std fs 已有大面、余为补齐包装"),
        "net":       ("direct", "R-dom-net", "socket 操作是直接 syscall 面，sa_std net 已有大面、余为补齐包装"),
        "time":      ("direct", "R-dom-time", "时间/时长是数值 + 时钟 syscall 面，可直接落 sa_std"),
        "num":       ("direct", "R-dom-num", "基本数值运算是原语面，可直接落 sa_std（或已由编译器内建覆盖）"),
        "mem":       ("direct", "R-dom-mem", "内存/指针原语是 SA 的原生面，可直接对应"),
        "slice":     ("direct", "R-dom-slice", "切片算法是直接内存算法面，可直接落 sa_std"),
        "string_str": ("direct", "R-dom-string", "字符串操作是直接字节/UTF-8 算法面，可直接落 sa_std"),
        "collections": ("direct", "R-dom-collections", "集合操作是直接数据结构面，可直接落 sa_std"),
        "option_result": ("direct", "R-dom-option", "Option/Result 组合子是带标签值上的直接函数，可直接落 sa_std"),
        "cmp":       ("direct", "R-dom-cmp", "比较运算是原语面，可直接对应"),
        "cell":      ("direct", "R-dom-cell", "单线程内部可变性在 SA 模型中是普通内存状态，可直接对应"),
        "ffi_os":    ("direct", "R-dom-ffi", "FFI/OS 字符串与句柄访问是直接字节/syscall 面，可直接落 sa_std"),
        "convert":   ("model", "R-dom-convert", "转换 trait 需按具体类型对展开为显式转换函数（生成面建模）"),
        "error":     ("model", "R-dom-error", "Error trait 体系需错误类型建模（sa_std 现以状态码为错误面）"),
        "sync":      ("model", "R-dom-sync", "阻塞同步原语需与线程模型整合建模（等待/唤醒/锁状态）"),
        "thread":    ("model", "R-dom-thread", "线程句柄/join/TLS 需线程模型面，sa_std 现有 thread 面只覆盖一部分"),
        "process_env": ("direct", "R-dom-process", "env 是直接 syscall 面；process 句柄面 sa_std 已有 spawn 家族"),
        "panic":     ("nomodel", "R-dom-panic", "panic 展开/钩子/回溯依赖展开机制与符号回溯，SA 无 panic 展开模型"),
        "marker_meta": ("nomodel", "R-dom-marker", "标记/元类型是类型系统层实体，SA 模型中不存在对应物"),
        "async":     ("model", "R-dom-async", "Future/Waker/Poll 需与 SLA async 运行时（task poll 模型）对齐建模"),
        "other":     ("direct", "R-dom-other", "未归域条目：以基本函数面为主，可直接对应（详原始清单复核）"),
    }
    if dom == "process_env" and module.startswith("std::process"):
        return dom, "model", "", "R-process-builder", "Command 构建器 + 子进程管道/wait 模型需进程句柄建模"
    if dom == "sync" and (owner.startswith("Atomic") or owner in ("Arc", "Weak", "Rc")):
        return dom, "direct", "", "R-sync-atomic", "原子操作/引用计数是原语面，可直接对应"
    if dom == "error" and kind in ("struct", "enum"):
        return dom, "direct", "", "R-error-data", "具体错误类型是数据结构，可直接对应"
    if dom == "panic" and name in ("Location",):
        return dom, "direct", "", "R-panic-location", "调用点位置是编译期信息，可直接对应"
    if kind == "macro":
        if name in ("panic", "unreachable", "todo", "unimplemented"):
            return dom, "nomodel", "", "R-macro-panic", "panic 系宏依赖 panic 机制（见 panic 域）"
        if name in ("assert", "assert_eq", "assert_ne", "debug_assert", "debug_assert_eq", "debug_assert_ne"):
            return dom, "direct", "", "R-macro-assert", "断言宏可直接以 SLA 宏/内建对应"
        return dom, "model", "", "R-macro", "宏面需逐个以 SLA 宏或编译器内建糖对应"
    cat, rule, reason = D[dom]
    return dom, cat, "", rule, reason

def main():
    rows = []
    with open(RUST_TSV, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            dom, cat, matched, rule, reason = classify(row)
            rows.append({**row, "domain": dom, "category": cat,
                         "matched_sa": matched, "rule": rule, "reason": reason})
    with open(OUT_TSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=[
            "crate", "module", "kind", "owner", "name", "file",
            "domain", "category", "matched_sa", "rule", "reason"])
        w.writeheader()
        w.writerows(rows)
    table = defaultdict(lambda: defaultdict(int))
    for r in rows:
        table[r["domain"]][r["category"]] += 1
        table[r["domain"]]["TOTAL"] += 1
        table["ALL"][r["category"]] += 1
        table["ALL"]["TOTAL"] += 1
    print(json.dumps({d: dict(c) for d, c in sorted(table.items())},
                     ensure_ascii=False, indent=1, sort_keys=True))

if __name__ == "__main__":
    main()
