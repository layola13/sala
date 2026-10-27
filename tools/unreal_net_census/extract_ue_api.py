#!/usr/bin/env python3
"""Extract UE 5.8 network surface from Epic's official API-reference HTML (dev.epicgames.com).
Source grade 1 = official API reference page (server-rendered, contains header file + tables).
Pages that returned the Angular app shell (~31KB, no <title>) are soft-404s and are NOT evidence.
Outputs: ue_api_surface.tsv (per class), ue_module_index.tsv (per module class inventory),
         ue_doc_keywords.tsv (term counts across fetched documentation pages).
Usage: extract_ue_api.py <raw_dir> <out_dir>
"""
import os, re, sys, html, collections

RAW = sys.argv[1] if len(sys.argv) > 1 else "/content/unreal-census-work/raw"
OUTD = sys.argv[2] if len(sys.argv) > 2 else "/content/unreal-census-work"
BASE = "https://dev.epicgames.com/documentation/en-us/unreal-engine/"

# file -> (class, subsystem)
PAGES = {
    "api_ISocketSubsystem.html": ("ISocketSubsystem", "sockets"),
    "api_FSocket.html": ("FSocket", "sockets"),
    "api_FInternetAddr.html": ("FInternetAddr", "sockets"),
    "api_UNetDriver.html": ("UNetDriver", "netdriver"),
    "api_UNetConnection.html": ("UNetConnection", "netdriver"),
    "api_UChannel.html": ("UChannel", "netdriver"),
    "api_UActorChannel.html": ("UActorChannel", "netdriver"),
    "api_UDemoNetDriver.html": ("UDemoNetDriver", "netdriver"),
    "api_FNetGUIDCache.html": ("FNetGUIDCache", "netdriver"),
    "api_UReplicationGraph_plugin.html": ("UReplicationGraph", "replication_graph"),
    "api_PacketHandler.html": ("PacketHandler", "packet_handler"),
    "api_FRepLayout.html": ("FRepLayout", "replication"),
    "api_UActorComponent.html": ("UActorComponent", "replication"),
    "api_AActor.html": ("AActor", "replication"),
    "api_FVector_NetQuantize.html": ("FVector_NetQuantize", "serialization"),
    "api_FVector_NetQuantize10.html": ("FVector_NetQuantize10", "serialization"),
    "api_FVector_NetQuantize100.html": ("FVector_NetQuantize100", "serialization"),
    "api_UReplicationSystem.html": ("UReplicationSystem", "iris"),
    "api_UReplicationBridge.html": ("UReplicationBridge", "iris"),
    "api_FNetSerializer.html": ("FNetSerializer", "iris"),
    "api_IOnlineSubsystem.html": ("IOnlineSubsystem", "online"),
    "api_IOnlineSession.html": ("IOnlineSession", "online"),
}
INDEXES = {
    "idx_Sockets.html": "Runtime/Sockets",
    "idx_PacketHandler.html": "Runtime/PacketHandler",
    "idx_IrisCore.html": "Runtime/IrisCore",
    "idx_ReplicationGraph.html": "Plugins/ReplicationGraph",
    "idx_OnlineSubsystem.html": "Plugins/OnlineSubsystem",
}
MISSING = {  # URLs probed that returned the app shell (soft-404): recorded, never used as evidence
    "UIpNetDriver": ["API/Runtime/Engine/UIpNetDriver", "API/Plugins/IpNetDriver/UIpNetDriver",
                     "API/Runtime/IpNetDriver/UIpNetDriver"],
    "UIpConnection": ["API/Runtime/Engine/UIpConnection"],
    "FFastArraySerializer": ["API/Runtime/Engine/FFastArraySerializer"],
    "UHandlerComponent": ["API/Runtime/PacketHandler/UHandlerComponent"],
}

def decode(t):
    t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)
    return t.replace("\\n", "\n").replace('\\"', '"')

def textify(t):
    t = decode(t)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)

def func_names(decoded_html):
    names = []
    for m in re.finditer(r"<p>(.*?)</p>", decoded_html, flags=re.S):
        cell = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        cell = re.sub(r"\s+", " ", cell).strip()
        if "(" not in cell or len(cell) > 260:
            continue
        mm = re.match(r"^(?:[\w:<>,\s\*&~]*?)(operator\S+|[~A-Za-z_]\w*)\s*\(", cell)
        if mm:
            names.append(mm.group(1))
    noise = {"if", "for", "while", "switch", "return", "sizeof", "Copy", "Syntax", "class", "struct"}
    return sorted({n for n in names if n not in noise})

rows = []
for fn, (cls, sub) in sorted(PAGES.items()):
    p = os.path.join(RAW, fn)
    raw = open(p, encoding="utf-8", errors="ignore").read()
    if len(raw) < 40000:
        print(f"SKIP shell {fn}")
        continue
    dec = decode(raw)
    txt = textify(raw)
    title = re.search(r"<title>(.*?)</title>", raw, flags=re.S)
    hdr = re.search(r"Header File\s+(\S+)", txt)
    inc = re.search(r'#include\s+"&quot;?([\w./]+)', txt) or re.search(r'#include\s+"([\w./]+)"', txt)
    funcs = func_names(dec)
    rows.append((cls, sub, hdr.group(1) if hdr else "", inc.group(1) if inc else "",
                 len(funcs), ";".join(funcs)))
    print(f"{cls} [{sub}] header={hdr.group(1) if hdr else '?'} sigs={len(funcs)}")

with open(os.path.join(OUTD, "ue_api_surface.tsv"), "w", encoding="utf-8") as f:
    f.write("class\tsubsystem\theader_file\tinclude\tn_signature_candidates\tfunctions\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")

inv = []
for fn, mod in INDEXES.items():
    p = os.path.join(RAW, fn)
    raw = open(p, encoding="utf-8", errors="ignore").read()
    if len(raw) < 40000:
        continue
    links = set(re.findall(r"/API/(?:Runtime|Plugins)/[A-Za-z0-9_]+/([A-Za-z0-9_]+)", decode(raw)))
    # keep only links under this module path
    modname = mod.split("/")[-1]
    sub = set(re.findall(r"/API/" + re.escape(mod.replace("Runtime/", "Runtime/").replace("Plugins/", "Plugins/")) + r"/([A-Za-z0-9_]+)", decode(raw)))
    names = sorted(sub) if sub else sorted(links)
    for n in names:
        inv.append((mod, n))
    print(f"index {mod}: {len(names)} class links")
with open(os.path.join(OUTD, "ue_module_index.tsv"), "w", encoding="utf-8") as f:
    f.write("module\tclass\n")
    for m, n in sorted(set(inv)):
        f.write(f"{m}\t{n}\n")

TERMS = ["FastArray", "FFastArraySerializer", "RepNotify", "OnRep_", "NetQuantize", "NetSerialize",
         "FNetSerializer", "NetGUID", "ReplicationGraph", "Dormancy", "Dormant", "PacketHandler",
         "Encryption", "PacketSimulation", "Network Emulation", "Oodle", "Iris", "NetSerializer",
         "NetDeltaSerialize", "Push Model", "PUSH_MODEL", "RPC", "Multicast", "Seamless",
         "BitWriter", "BitReader", "PackageMap", "Ack", "Reliability", "Fragment"]
docfiles = [f for f in os.listdir(RAW) if f.startswith("doc_") and f.endswith(".html")]
with open(os.path.join(OUTD, "ue_doc_keywords.tsv"), "w", encoding="utf-8") as f:
    f.write("doc\tterm\tcount\n")
    for fn in sorted(docfiles):
        raw = open(os.path.join(RAW, fn), encoding="utf-8", errors="ignore").read()
        if len(raw) < 40000:
            continue
        txt = textify(raw)
        for term in TERMS:
            c = txt.count(term)
            if c:
                f.write(f"{fn}\t{term}\t{c}\n")
print("missing-from-API-ref (soft-404, recorded only):", {k: len(v) for k, v in MISSING.items()})
print("done")
