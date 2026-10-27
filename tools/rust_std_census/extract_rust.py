#!/usr/bin/env python3
"""Extract the public surface of rustc's library/{core,alloc,std} sources.

Mechanical, regex/brace-tracking based over a sanitized code view (comments
removed, string/char/raw-string literal contents blanked) — rustfmt-formatted
sources make this reliable. Coverage boundaries (also in the census page):
- macro_rules definitions are counted separately, not expanded;
- `pub use` re-exports are not followed (items recorded at defining module);
- inherent + trait-decl + trait-impl methods captured by impl/trait context;
- items inside `mod tests` / tests.rs skipped; cfg-gated items counted
  regardless of cfg (platform-variant files in std therefore appear once
  per platform that defines them — the census also reports a deduplicated
  (crate,kind,owner,name) count).
Output TSV: crate, module, kind, owner, name, file
kind: fn | method | trait_method | struct | enum | trait | union | type |
      const | static | macro
"""
import os, re, sys

LIB = sys.argv[1]
OUT = sys.argv[2]
CRATES = ["core", "alloc", "std"]

QUAL = r"(?:(?:unsafe|async|const)\s+)*"
PUBQ = r"pub\s+" + QUAL
RE_ITEM = [
    ("fn",       re.compile(r"^\s*" + PUBQ + r"(?:extern\s+\"[^\"]*\"\s+)?fn\s+([A-Za-z_]\w*)")),
    ("struct",   re.compile(r"^\s*pub\s+(?:unsafe\s+)?struct\s+([A-Za-z_]\w*)")),
    ("enum",     re.compile(r"^\s*pub\s+enum\s+([A-Za-z_]\w*)")),
    ("trait",    re.compile(r"^\s*pub\s+(?:unsafe\s+)?(?:auto\s+)?trait\s+([A-Za-z_]\w*)")),
    ("union",    re.compile(r"^\s*pub\s+union\s+([A-Za-z_]\w*)")),
    ("type",     re.compile(r"^\s*pub\s+type\s+([A-Za-z_]\w*)")),
    ("const",    re.compile(r"^\s*pub\s+const\s+([A-Za-z_]\w*)\s*[:=]")),
    ("static",   re.compile(r"^\s*pub\s+static\s+(?:mut\s+)?([A-Za-z_]\w*)\s*:")),
]
RE_TRAIT_FN = re.compile(r"^\s+(?:(?:unsafe|async|const)\s+)*fn\s+([A-Za-z_]\w*)")
RE_TRAIT_CONST = re.compile(r"^\s+const\s+([A-Za-z_]\w*)\s*[:=]")
RE_TRAIT_TYPE = re.compile(r"^\s+type\s+([A-Za-z_]\w*)")
RE_MACRO = re.compile(r"macro_rules!\s+([A-Za-z_]\w*)")
RE_MOD = re.compile(r"^\s*(?:pub\s*(?:\([^)]*\)\s*)?)?mod\s+([A-Za-z_]\w*)")
RE_IMPL = re.compile(r"^\s*(?:const\s+)?impl\b(.*)$")
RE_TRAITDECL = re.compile(r"^\s*pub\s+(?:unsafe\s+)?(?:auto\s+)?(?:const\s+)?trait\s+([A-Za-z_]\w*)")


def sanitize(text):
    """Remove comments; blank contents of string/char/raw-string literals.
    Returns sanitized full text (newlines preserved)."""
    out = []
    i, n = 0, len(text)
    block = 0
    while i < n:
        two = text[i:i + 2]
        if block:
            if two == "/*":
                block += 1
                i += 2
            elif two == "*/":
                block -= 1
                i += 2
            else:
                if text[i] == "\n":
                    out.append("\n")
                i += 1
            continue
        if two == "//":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if two == "/*":
            block = 1
            i += 2
            continue
        c = text[i]
        # raw string: r"..." or r###"..."###
        if c == "r" and i + 1 < n and (text[i + 1] == '"' or text[i + 1] == "#"):
            j = i + 1
            hashes = 0
            while j < n and text[j] == "#":
                hashes += 1
                j += 1
            if j < n and text[j] == '"':
                closer = '"' + "#" * hashes
                k = text.find(closer, j + 1)
                seg = text[i:(n if k == -1 else k + len(closer))]
                out.append("r" + seg.count("\n") * "\n" + '""')
                i = n if k == -1 else k + len(closer)
                continue
        if c == '"' or (c == "b" and i + 1 < n and text[i + 1] == '"'):
            j = i + 1 if c == '"' else i + 2
            start = i
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            seg = text[start:j]
            out.append(seg.count("\n") * "\n" + '""')
            i = j
            continue
        if c == "'":
            # char literal vs lifetime: try to consume a full char literal
            # 'x'  '\n'  '\u{1F600}'  '\x41' — lifetimes ('a, 'static) never
            # match because they lack the closing quote in this shape.
            j = i + 1
            ok = False
            if j < n and text[j] == "\\":
                j += 1
                if j < n and text[j] == "u" and j + 1 < n and text[j + 1] == "{":
                    k = text.find("}", j + 2)
                    if k != -1:
                        j = k + 1
                        ok = j < n and text[j] == "'"
                        if ok:
                            j += 1
                elif j + 1 < n and text[j + 1] == "'":
                    j += 2
                    ok = True
            elif j + 1 < n and text[j + 1] == "'" and text[j] != "'":
                j += 2
                ok = True
            if ok:
                out.append("' '")
                i = j
                continue
        out.append(c)
        i += 1
    return "".join(out)

def balanced_generics(s):
    depth = 0
    for i, c in enumerate(s):
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(s)

def parse_impl_self(rest):
    s = rest.strip()
    if s.startswith("<"):
        s = s[balanced_generics(s):].strip()
    parts = re.split(r"\s+for\s+", s, maxsplit=1)
    is_trait = len(parts) == 2
    ty = parts[-1].strip()
    ty = re.sub(r"^(?:dyn\s+|mut\s+)", "", ty)
    if ty.startswith("&"):
        ty = ty[1:].strip()
        ty = re.sub(r"^(?:mut\s+)?(?:'\w+\s+)?", "", ty)
    ty = ty.split("::")[-1].strip()
    if ty.startswith("<"):
        ty = ty[balanced_generics(ty):].strip().split("::")[-1]
    if ty.startswith("["):
        return ("slice", is_trait)
    if ty.startswith("("):
        return ("tuple", is_trait)
    m = re.match(r"([A-Za-z_]\w*|str|char|bool)", ty)
    if not m:
        return ("?", is_trait)
    return (m.group(1), is_trait)

def extract_file(crate, path, modpath, rows):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = sanitize(f.read())
    relfile = os.path.relpath(path, LIB)
    stack = []   # (kind, name, depth, istrait) kind in mod/impl/trait/other
    depth = 0
    pending = None
    for line in text.split("\n"):
        stripped = line.strip()
        mm = RE_MACRO.search(line)
        if mm:
            rows.append((crate, modpath, "macro", "", mm.group(1), relfile))
        if pending is None:
            # header may span lines (where clauses): pending is consumed by
            # the first '{' that follows, or expires at a ';'-terminated line
            tm = RE_TRAITDECL.match(line)
            if tm:
                pending = ("trait", tm.group(1), False)
            else:
                im = RE_IMPL.match(line)
                if im:
                    st, istrait = parse_impl_self(im.group(1).split("{")[0])
                    pending = ("impl", st, istrait)
                else:
                    md = RE_MOD.match(line)
                    if md and not stripped.endswith(";"):
                        pending = ("mod", md.group(1), False)
        elif stripped.endswith(";") and "{" not in line:
            pending = None
        ctx_trait = None
        ctx_impl = None
        for entry in reversed(stack):
            if entry[0] == "trait" and ctx_trait is None:
                ctx_trait = entry[1]
            if entry[0] == "impl" and ctx_impl is None:
                ctx_impl = entry[1]
        matched = False
        for kind, rx in RE_ITEM:
            m = rx.match(line)
            if m:
                name = m.group(1)
                if kind == "fn":
                    if ctx_impl is not None:
                        rows.append((crate, modpath, "method", ctx_impl, name, relfile))
                    elif ctx_trait is not None:
                        rows.append((crate, modpath, "trait_method", ctx_trait, name, relfile))
                    else:
                        rows.append((crate, modpath, "fn", "", name, relfile))
                elif kind in ("const", "type") and ctx_trait is not None:
                    rows.append((crate, modpath, kind, ctx_trait, name, relfile))
                else:
                    rows.append((crate, modpath, kind, "", name, relfile))
                matched = True
                break
        if not matched and ctx_trait is not None and ctx_impl is None and not stripped.startswith("pub"):
            m = RE_TRAIT_FN.match(line)
            if m:
                rows.append((crate, modpath, "trait_method", ctx_trait, m.group(1), relfile))
            else:
                m = RE_TRAIT_CONST.match(line)
                if m:
                    rows.append((crate, modpath, "const", ctx_trait, m.group(1), relfile))
                else:
                    m = RE_TRAIT_TYPE.match(line)
                    if m:
                        rows.append((crate, modpath, "type", ctx_trait, m.group(1), relfile))
        for c in line:
            if c == "{":
                depth += 1
                if pending is not None:
                    stack.append((pending[0], pending[1], depth, pending[2]))
                    pending = None
                else:
                    stack.append(("other", "", depth, False))
            elif c == "}":
                while stack and stack[-1][2] == depth:
                    stack.pop()
                depth -= 1

def main():
    rows = []
    for crate in CRATES:
        src = os.path.join(LIB, crate, "src")
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in ("tests", "benches")]
            for fn in files:
                if not fn.endswith(".rs") or fn == "tests.rs":
                    continue
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src)
                parts = rel[:-3].split(os.sep)
                if parts[-1] in ("mod", "lib", "main"):
                    parts = parts[:-1]
                modpath = crate + "::" + "::".join(parts) if parts else crate
                extract_file(crate, path, modpath, rows)
    rows.sort()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("crate\tmodule\tkind\towner\tname\tfile\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    dedup = {(r[0], r[2], r[3], r[4]) for r in rows}
    print(f"total rows: {len(rows)}; distinct (crate,kind,owner,name): {len(dedup)}")

if __name__ == "__main__":
    main()
