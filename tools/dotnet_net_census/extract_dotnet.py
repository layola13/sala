#!/usr/bin/env python3
"""Agent AS census: extract .NET (dotnet/runtime @ v10.0.14) public network surface.
Parses src/libraries/System.Net*/ref/*.cs reference sources (the canonical
public-API contract) and records every public/protected type and member.
Output TSV: assembly \t namespace \t kind \t owner \t name \t obsolete \t file
kind: class/interface/struct/enum/delegate/record (types, owner="")
      ctor/method/property/event/field/enum_member (members, owner=type)
"""
import os, re, sys, glob, collections

ROOT = "/content/dotnet-src/src/libraries"

def strip_comments_strings(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i+1] == '/':
            j = text.find('\n', i)
            i = n if j < 0 else j
        elif c == '/' and i + 1 < n and text[i+1] == '*':
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c == '@' and i + 1 < n and text[i+1] == '"':  # verbatim string
            j = i + 2
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j+1] == '"':
                        j += 2; continue
                    break
                j += 1
            i = j + 1
            out.append('""')
        elif c == '"':
            j = i + 1
            while j < n and text[j] not in '"\n':
                j += 2 if text[j] == '\\' else 1
            i = j + 1
            out.append('""')
        elif c == "'":
            j = i + 1
            while j < n and text[j] not in "'\n":
                j += 2 if text[j] == '\\' else 1
            i = j + 1
            out.append("' '")
        else:
            out.append(c)
            i += 1
    return ''.join(out)

TYPE_RE = re.compile(
    r'^(public|protected)\b[^;{}]*?\b(class|interface|struct|enum|delegate|record)\s+([A-Za-z_][A-Za-z0-9_]*)')
NS_RE = re.compile(r'^namespace\s+([A-Za-z_][A-Za-z0-9_.]*)')
ATTR_OBSOLETE = re.compile(r'Obsolete(Attribute)?\s*\(')
ATTR_RE = re.compile(r'^\s*\[.*\]\s*$')

def member_kind(line, owner_kind):
    """Classify a member declaration line inside a type body."""
    s = line.strip()
    if owner_kind == 'enum':
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*(=|,|$)', s)
        return ('enum_member', m.group(1)) if m else (None, None)
    if re.search(r'\bevent\b', s):
        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*(;|{|=)', s)
        return ('event', m.group(1)) if m else (None, None)
    if re.search(r'\bthis\s*\[', s):
        return ('property', 'this[]')
    # name candidates: last identifier before '(' '{' ';' '=' '=>'
    if '(' in s:
        head = re.sub(r'<[^>]*>', '', s[:s.index('(')])
        ids = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', head)
        if not ids:
            return (None, None)
        name = ids[-1]
        if len(name) == 1 and len(ids) >= 2:
            name = ids[-2]
        return ('method', name)
    m = re.match(r'^(?:public|protected)\b.*?\b([A-Za-z_][A-Za-z0-9_]*)\s*(\{|;|=|=>)', s)
    if m:
        if '{' in s or '=>' in s:
            return ('property', m.group(1))
        return ('field', m.group(1))
    return (None, None)

def parse_file(path, assembly, rows):
    raw = open(path, encoding='utf-8', errors='replace').read()
    text = strip_comments_strings(raw)
    ns = ''
    depth = 0
    pending_obsolete = False
    pending_type = None
    type_stack = []  # (typename, kind, depth_of_body)
    for line in text.split('\n'):
        s = line.strip()
        if not s:
            continue
        if ATTR_RE.match(line):
            if ATTR_OBSOLETE.search(line):
                pending_obsolete = True
            continue
        mns = NS_RE.match(s)
        if mns:
            ns = mns.group(1)
            pending_obsolete = False
            # block namespace opens a scope below via '{'
        mt = TYPE_RE.match(s)
        is_type_decl = False
        if mt and (not type_stack or depth >= type_stack[-1][2]):
            access, kind, name = mt.group(1), mt.group(2), mt.group(3)
            if kind == 'delegate' and '(' in s:
                ids = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', s[:s.index('(')])
                if ids:
                    name = ids[-1]
            base = name.split('`')[0]
            rows.append((assembly, ns, kind, '', base,
                         '1' if pending_obsolete else '0',
                         os.path.relpath(path, ROOT)))
            pending_obsolete = False
            is_type_decl = True
            pending_type = (base, kind)
        # member capture: inside a type body, at exactly body depth
        if type_stack and depth == type_stack[-1][2] and not is_type_decl:
            owner_name, owner_kind, _ = type_stack[-1]
            if re.match(r'^(public|protected)\b', s) or owner_kind == 'enum':
                kind, name = member_kind(s, owner_kind)
                if kind:
                    if kind == 'method' and name == owner_name:
                        kind = 'ctor'
                    rows.append((assembly, ns, kind, owner_name, name,
                                 '1' if pending_obsolete else '0',
                                 os.path.relpath(path, ROOT)))
                    pending_obsolete = False
        # brace tracking
        for ch in line:
            if ch == '{':
                depth += 1
                if pending_type is not None:
                    type_stack.append((pending_type[0], pending_type[1], depth))
                    pending_type = None
            elif ch == '}':
                if type_stack and depth == type_stack[-1][2]:
                    type_stack.pop()
                depth -= 1
        if pending_type is not None and ';' in s:
            pending_type = None  # delegate: no body scope

def main():
    rows = []
    asms = sorted(d for d in os.listdir(ROOT)
                  if d.startswith('System.Net') and os.path.isdir(os.path.join(ROOT, d)))
    sys.stderr.write("assemblies: " + ", ".join(asms) + "\n")
    for asm in asms:
        refs = glob.glob(os.path.join(ROOT, asm, 'ref', '*.cs'))
        for f in sorted(refs):
            parse_file(f, asm, rows)
    out = sys.stdout
    out.write("assembly\tnamespace\tkind\towner\tname\tobsolete\tfile\n")
    for r in rows:
        out.write("\t".join(r) + "\n")
    cnt = collections.Counter((r[0], r[2]) for r in rows)
    sys.stderr.write("== counts by assembly x kind ==\n")
    for (a, k), n in sorted(cnt.items()):
        sys.stderr.write(f"{a}\t{k}\t{n}\n")
    tys = sum(1 for r in rows if r[3] == '')
    sys.stderr.write(f"TOTAL rows={len(rows)} types={tys} members={len(rows)-tys}\n")

if __name__ == '__main__':
    main()
