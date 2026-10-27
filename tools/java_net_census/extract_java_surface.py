#!/usr/bin/env python3
"""Extract the public/protected surface of OpenJDK network packages.

Mechanical, heuristic source extraction (no javac). Coverage boundary:
- Only declarations physically present in the given source roots are seen;
  inherited members are NOT expanded.
- Comments and string/char literals are stripped before parsing.
- Generic signatures are kept verbatim (whitespace-normalized).
- Enum constants are collected from the enum body header.
Outputs: java_types.tsv, java_members.tsv in the output directory.
"""
import os, re, sys

ROOTS = [
    ("java.base", "src/java.base/share/classes/java/net"),
    ("java.base", "src/java.base/share/classes/javax/net"),
    ("java.base", "src/java.base/share/classes/java/nio/channels"),
    ("java.net.http", "src/java.net.http/share/classes/java/net/http"),
    ("jdk.httpserver", "src/jdk.httpserver/share/classes/com/sun/net/httpserver"),
    ("jdk.net", "src/jdk.net/share/classes/jdk/net"),
]

TYPE_RE = re.compile(
    r"(public\s+|protected\s+|private\s+)?((?:(?:final|abstract|sealed|non-sealed|static|strictfp)\s+)*)"
    r"(class|interface|enum|record|@interface)\s+([A-Za-z_$][\w$]*)")
ANN_RE = re.compile(r"@\w+(?:\s*\([^)]*\))?\s*")
VIS_RE = re.compile(r"^(public|protected)\b")


def strip_noise(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            i = n if j < 0 else j
        elif c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            out.append(' ')
        elif c == '"' and src.startswith('"""', i):
            j = src.find('"""', i + 3)
            i = n if j < 0 else j + 3
            out.append('""')
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == '\\' else 1
            i = j + 1
            out.append('""')
        elif c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == '\\' else 1
            i = j + 1
            out.append("'x'")
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def norm(s):
    return re.sub(r"\s+", " ", s).strip()[:240]


def enum_constants(body_text):
    """body_text: raw text right after the enum's opening brace."""
    # constants run until the first ';' or a visibility/type keyword at depth 0
    depth = 0
    cut = len(body_text)
    i = 0
    while i < len(body_text):
        ch = body_text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif depth == 0 and ch == ';':
            cut = i
            break
        elif depth == 0 and ch == '{':
            # a constant-specific class body: skip it, keep scanning after its match
            d = 1
            i += 1
            while i < len(body_text) and d:
                if body_text[i] == '{':
                    d += 1
                elif body_text[i] == '}':
                    d -= 1
                i += 1
            continue
        i += 1
    head = body_text[:cut]
    parts, depth, cur = [], 0, ''
    for ch in head:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    names = []
    for p in parts:
        p = ANN_RE.sub('', p).strip()
        m = re.match(r"^([A-Za-z_$][\w$]*)", p)
        if m and not VIS_RE.match(p):
            names.append(m.group(1))
    return names


def parse_file(path, module, types, members):
    src = strip_noise(open(path, encoding='utf-8', errors='replace').read())
    pm = re.search(r"package\s+([\w\.]+)\s*;", src)
    package = pm.group(1) if pm else ""
    # token stream of segments separated by { } ;
    tokens = re.split(r"([{};])", src)
    stack = []  # each: dict(kind='type'|'block', ...)
    seg = ""
    pending_enum = None  # (fqn) whose body just opened, for constant scan
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == '{':
            s = seg.strip()
            tm = None
            for m in TYPE_RE.finditer(s):
                tm = m
            if tm:
                vis, mods, kind, name = tm.group(1), tm.group(2), tm.group(3), tm.group(4)
                parent = next((c for c in reversed(stack) if c['kind'] == 'type'), None)
                fqn = (parent['fqn'] + '.' + name) if parent else (package + '.' + name if package else name)
                types.append((module, package, fqn, kind,
                              norm((vis or '') + mods), os.path.basename(path)))
                ctx = {'kind': 'type', 'fqn': fqn, 'name': name, 'tkind': kind}
                stack.append(ctx)
                if kind == 'enum':
                    # look ahead: raw text until matching close is hard from tokens;
                    # collect following segments until first ';'-terminated segment
                    pending_enum = ctx
            else:
                # method body / block / array init / constant class body
                ctx_top = next((c for c in reversed(stack) if c['kind'] == 'type'), None)
                if ctx_top is not None and stack and stack[-1] is ctx_top:
                    record_member(seg, '{', ctx_top, members)
                stack.append({'kind': 'block'})
            seg = ""
        elif tok == '}':
            if stack:
                stack.pop()
            seg = ""
        elif tok == ';':
            if stack and stack[-1]['kind'] == 'type':
                record_member(seg, ';', stack[-1], members)
            seg = ""
        else:
            seg += tok
            if pending_enum is not None:
                # enum body header text is in this segment (constants ended by ';'
                # handled next round); if the segment itself holds them, grab now
                names = enum_constants(seg)
                for nm in names:
                    members.append((pending_enum['fqn'], 'enum_const', nm))
                pending_enum = None
        i += 1


def record_member(seg, term, ctx, members):
    s = seg.strip()
    if not s:
        return
    s2 = ANN_RE.sub('', s).strip()
    if not VIS_RE.match(s2):
        # Interface members without an explicit modifier are implicitly
        # public in Java; accept them (except private helpers).
        if ctx['tkind'] not in ('interface', '@interface'):
            return
        if s2.startswith('private'):
            return
    if TYPE_RE.search(s2):
        return  # nested type; recorded when its '{' opened (or abstract decl)
    has_paren = '(' in s2
    eq = s2.find('=')
    paren = s2.find('(')
    if term == ';':
        if has_paren and (eq < 0 or paren < eq) and re.search(r"\)\s*(throws\s+[\w\s,\.]+)?$", s2):
            kind = 'method'
        elif 'static' in s2.split('(')[0] and 'final' in s2.split('(')[0]:
            kind = 'const'
        else:
            kind = 'field'
    else:  # '{'
        if has_paren and (eq < 0 or paren < eq):
            kind = 'method'
        else:
            return  # initializer block or array-init field: field header without vis-paren is rare; skip
    # constructor?
    if kind == 'method':
        head = s2[:paren].split()
        if head and head[-1] == ctx['name'] and len(head) <= 3:
            kind = 'ctor'
    members.append((ctx['fqn'], kind, norm(s2)))


def main():
    src_root, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    types, members = [], []
    files = 0
    for module, rel in ROOTS:
        base = os.path.join(src_root, rel)
        for dirpath, _dirs, fnames in os.walk(base):
            for fn in sorted(fnames):
                if fn.endswith('.java') and fn != 'module-info.java':
                    parse_file(os.path.join(dirpath, fn), module, types, members)
                    files += 1
    with open(os.path.join(out_dir, 'java_types.tsv'), 'w') as f:
        f.write("module\tpackage\tfqn\tkind\tmodifiers\tfile\n")
        for t in types:
            f.write("\t".join(t) + "\n")
    with open(os.path.join(out_dir, 'java_members.tsv'), 'w') as f:
        f.write("fqn\tmember_kind\tsignature\n")
        for m in members:
            f.write("\t".join(m) + "\n")
    from collections import Counter
    print("files:", files)
    print("types:", len(types), Counter(t[3] for t in types))
    print("types by package:", Counter(t[1] for t in types))
    print("members:", len(members), Counter(m[1] for m in members))


if __name__ == '__main__':
    main()
