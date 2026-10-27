#!/usr/bin/env python3
"""Extract the full surface of sci's sa_std (baseline sci main 8a943911).

Sources: sa_std/**/*.sai (@extern decls), sa_std/**/*.sal (#def constants),
sa_std/**/*.sa ([MACRO] names + @fn definitions), sa_std/**/*.sla
(fn/const/struct/enum), and src/runtime/sa_std.h (#define + C decls).
Output TSV: layer, file, kind, name
kind: extern | sal_def | macro | sa_fn | sla_fn | sla_const | sla_struct |
      sla_enum | h_define | h_fn
"""
import os, re, sys

SCI = sys.argv[1]          # sci repo root
OUT = sys.argv[2]
STD = os.path.join(SCI, "sa_std")

RE_EXTERN = re.compile(r"^\s*@extern\s+([A-Za-z_]\w*)")
RE_SAL_DEF = re.compile(r"^\s*#def\s+([A-Za-z_]\w*)")
RE_MACRO = re.compile(r"\[MACRO\]\s+([A-Za-z_]\w*)")
RE_SA_FN = re.compile(r"^@([A-Za-z_]\w*)\s*\(")
RE_SA_EXPORT = re.compile(r"^@export\s+([A-Za-z_]\w*)\s*\(")
RE_SLA_FN = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)")
RE_SLA_CONST = re.compile(r"^\s*(?:pub\s+)?const\s+([A-Za-z_]\w*)")
RE_SLA_STRUCT = re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_]\w*)")
RE_SLA_ENUM = re.compile(r"^\s*(?:pub\s+)?enum\s+([A-Za-z_]\w*)")
RE_H_DEFINE = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)")
RE_H_FN = re.compile(r"^(?:[A-Za-z_][\w\s\*]*?)\b(sa_[A-Za-z_]\w*)\s*\(")

def walk(exts):
    for root, dirs, files in os.walk(STD):
        dirs[:] = [d for d in dirs if d != ".sla-cache"]
        for fn in sorted(files):
            if os.path.splitext(fn)[1] in exts:
                yield os.path.join(root, fn)

def main():
    rows = []
    for path in walk({".sai"}):
        rel = os.path.relpath(path, SCI)
        for line in open(path, encoding="utf-8", errors="replace"):
            m = RE_EXTERN.match(line)
            if m:
                rows.append(("sai", rel, "extern", m.group(1)))
    for path in walk({".sal"}):
        rel = os.path.relpath(path, SCI)
        for line in open(path, encoding="utf-8", errors="replace"):
            m = RE_SAL_DEF.match(line)
            if m:
                rows.append(("sal", rel, "sal_def", m.group(1)))
    for path in walk({".sa"}):
        rel = os.path.relpath(path, SCI)
        for line in open(path, encoding="utf-8", errors="replace"):
            m = RE_MACRO.search(line)
            if m:
                rows.append(("sa", rel, "macro", m.group(1)))
                continue
            if line.startswith("@import") or line.startswith("@extern"):
                continue
            m = RE_SA_EXPORT.match(line)
            if m:
                rows.append(("sa", rel, "sa_fn", m.group(1)))
                continue
            m = RE_SA_FN.match(line)
            if m:
                rows.append(("sa", rel, "sa_fn", m.group(1)))
    for path in walk({".sla"}):
        rel = os.path.relpath(path, SCI)
        for line in open(path, encoding="utf-8", errors="replace"):
            for kind, rx in (("sla_fn", RE_SLA_FN), ("sla_const", RE_SLA_CONST),
                             ("sla_struct", RE_SLA_STRUCT), ("sla_enum", RE_SLA_ENUM)):
                m = rx.match(line)
                if m:
                    rows.append(("sla", rel, kind, m.group(1)))
                    break
    hpath = os.path.join(SCI, "src/runtime/sa_std.h")
    if os.path.exists(hpath):
        rel = os.path.relpath(hpath, SCI)
        for line in open(hpath, encoding="utf-8", errors="replace"):
            m = RE_H_DEFINE.match(line)
            if m:
                rows.append(("h", rel, "h_define", m.group(1)))
                continue
            m = RE_H_FN.match(line)
            if m and not line.lstrip().startswith(("//", "#", "*")):
                rows.append(("h", rel, "h_fn", m.group(1)))
    rows.sort()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("layer\tfile\tkind\tname\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    names = {r[3] for r in rows}
    print(f"total rows: {len(rows)}; distinct names: {len(names)}")

if __name__ == "__main__":
    main()
