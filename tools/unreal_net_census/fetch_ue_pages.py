#!/usr/bin/env python3
"""Fetch UE 5.8 network surface source material from Epic's official documentation site.

Source-grade record (2026-10-27, Colab box 410dd20b5a78):
- EpicGames/UnrealEngine on GitHub is a GATED repo: anonymous `git clone` and
  `git ls-remote` both fail with "fatal: could not read Username for
  'https://github.com'" (requires an Epic-account-linked GitHub identity with
  EULA-granted org membership). No such credential exists on the box.
- EpicGames org has 56 public repos (api.github.com/orgs/EpicGames); none of
  them contains the engine networking source (media/plugin samples and
  third-party tooling only).
- Therefore the census uses Epic's official API reference + documentation at
  dev.epicgames.com (UE 5.8). The docs app returns HTTP 200 with a ~31KB
  Angular shell (no <title>, robots=noindex) for nonexistent URLs: those are
  SOFT-404s and must never be treated as evidence. Real pages are >40KB and
  carry full class tables (header file, syntax, function/variable/enum rows).

This script re-fetches every page used by the census into ./raw/.
"""
import subprocess, os, sys

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(RAW, exist_ok=True)
BASE = "https://dev.epicgames.com/documentation/en-us/unreal-engine/"

API_PAGES = {
    "ISocketSubsystem": "API/Runtime/Sockets/ISocketSubsystem",
    "FSocket": "API/Runtime/Sockets/FSocket",
    "FInternetAddr": "API/Runtime/Sockets/FInternetAddr",
    "UNetDriver": "API/Runtime/Engine/UNetDriver",
    "UNetConnection": "API/Runtime/Engine/UNetConnection",
    "UChannel": "API/Runtime/Engine/UChannel",
    "UActorChannel": "API/Runtime/Engine/UActorChannel",
    "UDemoNetDriver": "API/Runtime/Engine/UDemoNetDriver",
    "AActor": "API/Runtime/Engine/AActor",
    "UActorComponent": "API/Runtime/Engine/UActorComponent",
    "FRepLayout": "API/Runtime/Engine/FRepLayout",
    "FNetGUIDCache": "API/Runtime/Engine/FNetGUIDCache",
    "FVector_NetQuantize": "API/Runtime/Engine/FVector_NetQuantize",
    "FVector_NetQuantize10": "API/Runtime/Engine/FVector_NetQuantize10",
    "FVector_NetQuantize100": "API/Runtime/Engine/FVector_NetQuantize100",
    "PacketHandler": "API/Runtime/PacketHandler/PacketHandler",
    "UReplicationGraph": "API/Plugins/ReplicationGraph/UReplicationGraph",
    "UReplicationSystem": "API/Runtime/IrisCore/UReplicationSystem",
    "UReplicationBridge": "API/Runtime/IrisCore/UReplicationBridge",
    "FNetSerializer": "API/Runtime/IrisCore/FNetSerializer",
    "IOnlineSubsystem": "API/Plugins/OnlineSubsystem/IOnlineSubsystem",
    "IOnlineSession": "API/Plugins/OnlineSubsystem/IOnlineSession",
}
INDEX_PAGES = {
    "Sockets": "API/Runtime/Sockets/",
    "PacketHandler": "API/Runtime/PacketHandler/",
    "IrisCore": "API/Runtime/IrisCore/",
    "ReplicationGraph": "API/Plugins/ReplicationGraph/",
    "OnlineSubsystem": "API/Plugins/OnlineSubsystem/",
}
DOC_PAGES = {
    "networking_overview": "networking-and-multiplayer-in-unreal-engine",
    "networking_overview2": "networking-overview-for-unreal-engine",
    "rpc": "remote-procedure-calls-in-unreal-engine",
    "replicate_properties": "replicate-actor-properties-in-unreal-engine",
    "dormancy": "actor-network-dormancy-in-unreal-engine",
    "iris_intro": "introduction-to-iris-in-unreal-engine",
    "iris_components": "components-of-iris-in-unreal-engine",
    "iris_glossary": "glossary-of-iris-terms-in-unreal-engine",
    "iris_migrate": "migrate-to-iris-in-unreal-engine",
    "replication_graph": "replication-graph-in-unreal-engine",
    "oodle": "oodle-network",
    "bandwidth_tips": "performance-and-bandwidth-tips-for-unreal-engine",
    "online_subsystem": "online-subsystem-in-unreal-engine",
    "travelling": "travelling-in-multiplayer-in-unreal-engine",
}
# Probed and confirmed SOFT-404 (app shell) in the official API reference index.
SOFT404_PROBES = [
    "API/Runtime/Engine/UIpNetDriver", "API/Plugins/IpNetDriver/UIpNetDriver",
    "API/Runtime/IpNetDriver/UIpNetDriver", "API/Runtime/Engine/UIpConnection",
    "API/Runtime/Engine/FFastArraySerializer", "API/Runtime/PacketHandler/UHandlerComponent",
]

def fetch(name, path):
    out = os.path.join(RAW, name + ".html")
    r = subprocess.run(["curl", "-sL", "--max-time", "60", "-o", out,
                        "-w", "%{http_code} %{size_download}", BASE + path],
                       capture_output=True, text=True)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"{name}: {r.stdout.strip()} bytes={size} {'REAL' if size > 40000 else 'SHELL/404'}")

if __name__ == "__main__":
    for n, p in API_PAGES.items():
        fetch("api_" + n, p)
    for n, p in INDEX_PAGES.items():
        fetch("idx_" + n, p)
    for n, p in DOC_PAGES.items():
        fetch("doc_" + n, p)
    print("soft-404 probes (recorded, not fetched):", SOFT404_PROBES)
