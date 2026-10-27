#!/usr/bin/env python3
"""Extract public top-level type names from a desktop OpenJDK source tree
(java.base module) for the packages java.net / javax.net / javax.net.ssl,
as the comparison baseline for Android's libcore (ojluni) surface.

One public top-level type per file is the JDK convention; the declaration
is taken from the file's own `public ... class/interface/enum` line.

Output: desktop_jdk_net_classes.tsv (package, class)
Usage: extract_desktop_jdk_net.py <jdk_src_root> <outdir>
"""
import re
import sys
from pathlib import Path

PKGS = {
    "java.net": "src/java.base/share/classes/java/net",
    "javax.net": "src/java.base/share/classes/javax/net",
    "javax.net.ssl": "src/java.base/share/classes/javax/net/ssl",
}
DECL_RE = re.compile(
    r"^\s*public\s+(?:final\s+|abstract\s+|sealed\s+|non-sealed\s+)*"
    r"(class|interface|enum|@interface|record)\s+(\w+)",
    re.M,
)


def main() -> int:
    root = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for pkg, rel in PKGS.items():
        d = root / rel
        for f in sorted(d.glob("*.java")):
            text = f.read_text(encoding="utf-8", errors="replace")
            m = DECL_RE.search(text)
            if m:
                rows.append((pkg, m.group(2)))
    with (outdir / "desktop_jdk_net_classes.tsv").open("w", encoding="utf-8") as fh:
        fh.write("package\tclass\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    print(f"desktop public types: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
