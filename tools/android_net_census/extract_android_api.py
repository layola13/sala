#!/usr/bin/env python3
"""Extract public API surface for network packages from an Android SDK
public API signature file (prebuilts/sdk/<level>/public/api/android.txt,
signature format 2.0, metalava style).

Outputs two TSVs next to the script's --outdir:
  android_classes.tsv : package, class, kind, n_ctor, n_method, n_field
  android_members.tsv : package, class, member_kind, signature

Usage: extract_android_api.py <android.txt> <outdir>
"""
import re
import sys
from pathlib import Path

# packages in scope: full depth
FULL_PACKAGES = {
    "android.net",
    "android.net.http",
    "android.net.ssl",
    "android.net.nsd",
    "android.net.rtp",
    "android.net.sip",
    "android.net.ipsec.ike",
    "android.net.ipsec.ike.exceptions",
    "android.net.vcn",
    "android.net.eap",
    "java.net",
    "javax.net",
    "javax.net.ssl",
}
# registration only: class rows emitted, members counted but flagged
REGISTRATION_PREFIXES = ("android.net.wifi", "android.telephony")

PKG_RE = re.compile(r"^package ([\w.]+) \{$")
CLASS_RE = re.compile(
    r"^\s+(?:@[\w.]+(?:\([^)]*\))?\s+)*(?:public|protected).*?"
    r"\b(class|interface|enum|@interface)\s+([\w.]+)"
)
CTOR_RE = re.compile(r"^\s+ctor\b")
METHOD_RE = re.compile(r"^\s+(?:method|ctor)\b")
FIELD_RE = re.compile(r"^\s+field\b")


def in_scope(pkg: str) -> str | None:
    if pkg in FULL_PACKAGES:
        return "full"
    if any(pkg == p or pkg.startswith(p + ".") for p in REGISTRATION_PREFIXES):
        return "registration"
    return None


def main() -> int:
    src = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    classes = []  # (pkg, cls, kind, n_ctor, n_method, n_field, scope)
    members = []  # (pkg, cls, kind, signature)
    pkg = None
    cur = None  # [pkg, cls, kind, n_ctor, n_method, n_field, scope]

    def flush():
        nonlocal cur
        if cur is not None:
            classes.append(tuple(cur))
            cur = None

    for raw in src.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PKG_RE.match(raw)
        if m:
            flush()
            pkg = m.group(1)
            continue
        if pkg is None:
            continue
        scope = in_scope(pkg)
        if scope is None:
            continue
        cm = CLASS_RE.match(raw)
        if cm and not raw.strip().startswith(("method", "field", "ctor")):
            flush()
            kind, name = cm.group(1), cm.group(2)
            cur = [pkg, name, kind, 0, 0, 0, scope]
            continue
        if cur is None:
            continue
        line = raw.strip()
        if CTOR_RE.match(raw):
            cur[3] += 1
            members.append((pkg, cur[1], "ctor", line))
        elif line.startswith("method "):
            cur[4] += 1
            members.append((pkg, cur[1], "method", line))
        elif FIELD_RE.match(raw):
            cur[5] += 1
            members.append((pkg, cur[1], "field", line))
    flush()

    with (outdir / "android_classes.tsv").open("w", encoding="utf-8") as f:
        f.write("package\tclass\tkind\tn_ctor\tn_method\tn_field\tscope\n")
        for row in classes:
            f.write("\t".join(str(x) for x in row) + "\n")
    with (outdir / "android_members.tsv").open("w", encoding="utf-8") as f:
        f.write("package\tclass\tmember_kind\tsignature\n")
        for row in members:
            f.write("\t".join(row) + "\n")
    print(f"classes={len(classes)} members={len(members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
