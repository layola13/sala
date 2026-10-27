#!/usr/bin/env python3
"""Extract the public surface of CPython's network-related stdlib modules.

Method: AST walk over the Lib-layer .py files (the C-implemented modules
_socket/_ssl are represented by their Lib-layer modules socket.py/ssl.py,
per the census rule), plus a clearly-labelled supplementary scan of the C
sources (Modules/socketmodule.c, Modules/_ssl/*.c) for registered method
names and constant names.

Usage: extract_python_surface.py <cpython_root> <out_tsv> <out_summary_json>
"""
import ast
import json
import re
import sys
from pathlib import Path

# module dotted name -> path relative to Lib/
MODULES = {
    # core face
    "socket": "socket.py",
    "ssl": "ssl.py",
    "ipaddress": "ipaddress.py",
    "http": "http/__init__.py",
    "http.client": "http/client.py",
    "http.server": "http/server.py",
    "http.cookies": "http/cookies.py",
    "http.cookiejar": "http/cookiejar.py",
    "urllib.parse": "urllib/parse.py",
    "urllib.request": "urllib/request.py",
    "urllib.error": "urllib/error.py",
    "urllib.response": "urllib/response.py",
    "urllib.robotparser": "urllib/robotparser.py",
    "socketserver": "socketserver.py",
    "selectors": "selectors.py",
    # asyncio network face (single section in the report)
    "asyncio.streams": "asyncio/streams.py",
    "asyncio.transports": "asyncio/transports.py",
    "asyncio.protocols": "asyncio/protocols.py",
    "asyncio.selector_events": "asyncio/selector_events.py",
    "asyncio.base_events": "asyncio/base_events.py",
    "asyncio.proactor_events": "asyncio/proactor_events.py",
    "asyncio.unix_events": "asyncio/unix_events.py",
    "asyncio.windows_events": "asyncio/windows_events.py",
    "asyncio.sslproto": "asyncio/sslproto.py",
    "asyncio.trsock": "asyncio/trsock.py",
    # protocol clients (registration-style coverage)
    "smtplib": "smtplib.py",
    "ftplib": "ftplib.py",
    "imaplib": "imaplib.py",
    "poplib": "poplib.py",
}

ENUM_BASES = {"Enum", "IntEnum", "IntFlag", "StrEnum", "Flag"}


def is_public(name: str) -> bool:
    return not name.startswith("_")


def base_names(cls: ast.ClassDef):
    out = []
    for b in cls.bases:
        if isinstance(b, ast.Name):
            out.append(b.id)
        elif isinstance(b, ast.Attribute):
            out.append(b.attr)
    return out


def extract_module_tokens(modname: str, text: str):
    """Fallback extractor for sources the host interpreter cannot parse
    (e.g. CPython 3.15 grammar parsed by a 3.13 host). Token-stream walk:
    scope is tracked by indentation; module-level defs/classes/consts and
    direct class-body methods/enum members are recovered."""
    import io
    import keyword
    import tokenize

    rows = []
    toks = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            toks.append(tok)
    except Exception:
        return rows
    # group into logical lines: list of (indent_col, [token strings], [token types])
    lines = []
    cur, cur_types = [], []
    for tok in toks:
        if tok.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
            continue
        if tok.type == tokenize.NEWLINE:
            if cur:
                lines.append(cur)
                cur = []
            continue
        if tok.type in (tokenize.NL, tokenize.COMMENT):
            continue
        cur.append(tok)
    # scope stack entries: (indent_col, kind, name, is_enum)
    stack = [(-1, "module", modname, False)]
    i = 0
    while i < len(lines):
        line = lines[i]
        first = line[0]
        indent = first.start[1]
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        scope_kind, scope_name, _sc, scope_enum = stack[-1][1], stack[-1][2], stack[-1], stack[-1][3]
        words = [t.string for t in line]
        types = [t.type for t in line]
        import token as _t

        def is_kw(w, kw):
            return w == kw

        if words[0] == "class" and len(words) > 1:
            cname = words[1].split("(")[0]
            header = " ".join(words)
            bases = []
            if "(" in header and ")" in header:
                bases = [b.strip() for b in header.split("(", 1)[1].split(")")[0].split(",")]
            is_enum = bool(ENUM_BASES & set(bases))
            if scope_kind == "module" and is_public(cname):
                rows.append((modname, "class", cname, "bases=" + ",".join(bases)))
                stack.append((indent, "class", cname, is_enum))
            else:
                stack.append((indent, "other", cname, False))
            i += 1
            continue
        if words[0] in ("def",) or (words[0] == "async" and len(words) > 1 and words[1] == "def"):
            fname = words[2] if words[0] == "async" else words[1]
            fname = fname.split("(")[0]
            kind = "async_" if words[0] == "async" else ""
            if scope_kind == "module" and is_public(fname):
                rows.append((modname, kind + "func", fname, ""))
            elif scope_kind == "class" and (is_public(fname) or fname == "__init__"):
                rows.append((modname, kind + "method", f"{scope_name}.{fname}", ""))
            stack.append((indent, "other", fname, False))
            i += 1
            continue
        if scope_kind == "module" and types[0] == _t.NAME and words[0].isupper() and len(words[0]) > 1:
            if len(words) > 1 and words[1] in ("=", ":"):
                rows.append((modname, "const", words[0], ""))
        if scope_kind == "class" and scope_enum and types[0] == _t.NAME and is_public(words[0]):
            if len(words) > 1 and words[1] in ("=", ":"):
                rows.append((modname, "enum_member", f"{scope_name}.{words[0]}", ""))
        i += 1
    return rows


def extract_module(modname: str, path: Path, fallback_flag=None):
    rows = []  # (module, kind, name, detail)
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        if fallback_flag is not None:
            fallback_flag.append(modname)
        return extract_module_tokens(modname, text)
    all_names = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            try:
                all_names = set(ast.literal_eval(node.value))
            except Exception:
                all_names = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_public(node.name) or (all_names and node.name in all_names):
                kind = "async_func" if isinstance(node, ast.AsyncFunctionDef) else "func"
                args = [a.arg for a in node.args.args]
                rows.append((modname, kind, node.name, "args=" + ",".join(args)))
        elif isinstance(node, ast.ClassDef):
            if not is_public(node.name) and not (all_names and node.name in all_names):
                continue
            bases = base_names(node)
            rows.append((modname, "class", node.name, "bases=" + ",".join(bases)))
            is_enum = bool(ENUM_BASES & set(bases))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if is_public(item.name) or item.name == "__init__":
                        kind = (
                            "async_method"
                            if isinstance(item, ast.AsyncFunctionDef)
                            else "method"
                        )
                        rows.append(
                            (modname, kind, f"{node.name}.{item.name}", "")
                        )
                elif isinstance(item, ast.Assign) and is_enum:
                    for t in item.targets:
                        if isinstance(t, ast.Name) and is_public(t.id):
                            rows.append(
                                (modname, "enum_member", f"{node.name}.{t.id}", "")
                            )
                elif isinstance(item, ast.AnnAssign) and is_enum:
                    if isinstance(item.target, ast.Name) and is_public(item.target.id):
                        rows.append(
                            (modname, "enum_member", f"{node.name}.{item.target.id}", "")
                        )
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper() and len(t.id) > 1:
                    rows.append((modname, "const", t.id, ""))
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id.isupper()
                and len(node.target.id) > 1
            ):
                rows.append((modname, "const", node.target.id, ""))
    return rows


C_METHOD_TABLE_RE = re.compile(r"PyMethodDef\s+\w+\[\]\s*=\s*\{")
C_METHOD_NAME_RE = re.compile(r'\{"([A-Za-z_][A-Za-z0-9_]*)"\s*,')
C_CONST_RE = re.compile(
    r'"((?:AF|PF|SOCK|SO|SOL|IPPROTO|IP_|IPV6_|TCP_|UDP_|MSG_|SHUT_|AI_|NI_|EAI_|'
    r"CMSG_|SCM_|INADDR_|MCAST_|SSL|TLS|CERT_|OP_|VERIFY_|PROTOCOL_|HAS_|ALERT_|"
    r'CHANNEL_|X509_|SSLEOF|SSL_ERROR|PEM_|DER_|ASN1_|SSLKEYLOG)[A-Z0-9_]*?)["]'
)
C_ADD_MACRO_RE = re.compile(r"ADD_INT_MACRO\(\s*\w+\s*,\s*([A-Z][A-Z0-9_]*)")
C_ADD_NAMED_RE = re.compile(
    r'ADD_(?:INT|STR)_CONST\(\s*\w+\s*,\s*"([^"]+)"'
    r'|PyModule_Add(?:Int|String)Constant\(\s*\w+\s*,\s*"([^"]+)"'
)


def extract_c(modname: str, files):
    rows = []
    methods, consts = set(), set()
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        # method names: only inside PyMethodDef tables (up to closing "};")
        for m in C_METHOD_TABLE_RE.finditer(text):
            seg = text[m.end(): m.end() + 30000]
            end = seg.find("\n};")
            if end != -1:
                seg = seg[:end]
            methods |= set(C_METHOD_NAME_RE.findall(seg))
        consts |= set(C_CONST_RE.findall(text))
        consts |= set(C_ADD_MACRO_RE.findall(text))
        for pair in C_ADD_NAMED_RE.findall(text):
            consts |= {x for x in pair if x}
    # drop ALL-CAPS type/macro noise that is not a module constant:
    methods = {m for m in methods if not m.startswith("__")}
    for m in sorted(methods):
        rows.append((modname, "c_method", m, "source=C PyMethodDef scan"))
    for c in sorted(consts):
        rows.append((modname, "c_const", c, "source=C constant-name scan"))
    return rows


def main():
    root = Path(sys.argv[1])
    lib = root / "Lib"
    out_tsv, out_json = Path(sys.argv[2]), Path(sys.argv[3])
    rows = []
    missing = []
    fallback_files = []
    for modname, rel in MODULES.items():
        p = lib / rel
        if not p.exists():
            missing.append(modname)
            continue
        rows.extend(extract_module(modname, p, fallback_files))
    rows.extend(extract_c("_socket(C)", [root / "Modules/socketmodule.c"]))
    ssl_c = []
    if (root / "Modules/_ssl.c").exists():
        ssl_c.append(root / "Modules/_ssl.c")
    if (root / "Modules/_ssl").exists():
        ssl_c += sorted((root / "Modules/_ssl").glob("*.c"))
    if ssl_c:
        rows.extend(extract_c("_ssl(C)", ssl_c))
    with out_tsv.open("w", encoding="utf-8") as fh:
        fh.write("module\tkind\tname\tdetail\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    summary = {}
    for mod, kind, _name, _d in rows:
        summary.setdefault(mod, {}).setdefault(kind, 0)
        summary[mod][kind] += 1
    summary["_missing_modules"] = missing
    summary["_token_fallback_modules"] = fallback_files
    summary["_total_rows"] = len(rows)
    out_json.write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"rows={len(rows)} missing={missing}")


if __name__ == "__main__":
    main()
