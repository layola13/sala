#!/usr/bin/env python3
"""extract_corelibs.py — mechanically extract the public Swift surface of the
URLSession family from swift-corelibs-foundation (source grade: oss-swift —
Apple's open-source Foundation; it is the Swift Foundation layer's open
counterpart, NOT the Darwin binary's source).

Scope: every .swift file under Sources/FoundationNetworking/ (the URLSession
module, incl. the URLSession/ subdirectory) plus the URL value types in
Sources/Foundation/ (URL.swift, URLComponents.swift, URLQueryItem.swift).

Method: line-based scan with a brace-depth context stack. A declaration is
counted when it carries an explicit `public`/`open` modifier, or when it sits
directly inside a `public extension` block. Type declarations
(class/struct/enum/protocol) and extensions push an owner context.
Known limits (stated, not hidden): members declared without a modifier inside
plain (non-public) extensions of public types are missed; declarations split
across lines with the modifier on its own line are missed.

Usage: extract_corelibs.py <corelibs_root> <out.tsv>
"""
import os
import re
import sys

TYPE_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(public\s+|open\s+)?(?:final\s+)?"
    r"(class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)")
EXT_RE = re.compile(
    r"^\s*(public\s+)?extension\s+([A-Za-z_]\w*)")
MEMBER_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(public\s+|open\s+)(?:final\s+|static\s+|class\s+|"
    r"override\s+|mutating\s+|nonmutating\s+|required\s+|convenience\s+|lazy\s+|weak\s+|"
    r"unowned\s+)*(func|var|let|init|subscript|typealias)\s*\(?\s*([A-Za-z_]\w*)?")
MEMBER_IN_PUBEXT_RE = re.compile(
    r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:final\s+|static\s+|class\s+|override\s+|"
    r"mutating\s+|nonmutating\s+|required\s+|convenience\s+|lazy\s+|weak\s+|unowned\s+)*"
    r"(func|var|let|init|subscript|typealias)\s*\(?\s*([A-Za-z_]\w*)?")


def scan_file(path, rel, rows):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    stack = []  # (owner_name, brace_depth_at_which_context_closes, public_ext)
    depth = 0
    pending = None  # (owner, is_public_ext) waiting for its opening brace
    for line in lines:
        code = line.split("//")[0]
        cur_owner = stack[-1][0] if stack else ""
        in_pub_ext = stack[-1][2] if stack else False
        tm = TYPE_RE.match(code)
        # `public class var shared` / `class func` are member declarations,
        # not type declarations — reject captures named like member keywords.
        if tm and tm.group(3) in ("var", "func", "let", "init", "subscript", "get", "set"):
            tm = None
        em = EXT_RE.match(code) if not tm else None
        if tm:
            kind, name = tm.group(2), tm.group(3)
            if tm.group(1):  # public/open type declaration counts itself
                rows.append((os.path.basename(path), kind, cur_owner, name, rel))
            pending = (name, False)
        elif em:
            pending = (em.group(2), bool(em.group(1)))
        else:
            mm = MEMBER_RE.match(code)
            if mm:
                kind = mm.group(2)
                name = mm.group(3) or ("init" if kind == "init" else kind)
                rows.append((os.path.basename(path), kind, cur_owner, name, rel))
            elif in_pub_ext:
                mm2 = MEMBER_IN_PUBEXT_RE.match(code)
                if mm2 and cur_owner:
                    kind = mm2.group(1)
                    name = mm2.group(2) or ("init" if kind == "init" else kind)
                    rows.append((os.path.basename(path), kind, cur_owner, name, rel))
        opens = code.count("{")
        closes = code.count("}")
        if pending and opens:
            stack.append((pending[0], depth + opens - closes, pending[1]))
            pending = None
        depth += opens - closes
        while stack and depth < stack[-1][1]:
            stack.pop()
    return rows


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    rows = []
    files = []
    netdir = os.path.join(root, "Sources", "FoundationNetworking")
    for dirpath, _dirs, names in os.walk(netdir):
        for n in sorted(names):
            if n.endswith(".swift"):
                files.append(os.path.join(dirpath, n))
    for extra in ("URL.swift", "URLComponents.swift", "URLQueryItem.swift"):
        p = os.path.join(root, "Sources", "Foundation", extra)
        if os.path.exists(p):
            files.append(p)
    for p in sorted(files):
        rel = os.path.relpath(p, root)
        scan_file(p, rel, rows)
    seen = set()
    uniq = []
    for r in rows:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    uniq.sort()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("framework\tmodule\tkind\towner\tname\tlang\tios_since\tgrade\tref\n")
        for mod, kind, owner, name, rel in uniq:
            f.write(f"Foundation-URLSession\t{mod}\t{kind}\t{owner}\t{name}\tswift\t\toss-swift\t{rel}\n")
    print("corelibs files scanned:", len(files))
    print("corelibs public decls:", len(uniq))
    by_owner = {}
    for _m, _k, o, _n, _r in uniq:
        by_owner[o] = by_owner.get(o, 0) + 1
    for o in sorted(by_owner, key=lambda x: -by_owner[x])[:18]:
        print(f"  owner {o or '(file scope)'}: {by_owner[o]}")


if __name__ == "__main__":
    main()
