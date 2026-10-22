#!/usr/bin/env python3
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTS = [18092, 18093, 18094, 18095]
ADDRS = ",".join(f"127.0.0.1:{p}" for p in PORTS)


def wait_port(port, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            s.close()
            return True
        except OSError:
            time.sleep(0.02)
    return False


def rss_kb(pid):
    try:
        for line in open(f"/proc/{pid}/status", encoding="ascii"):
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def start(spec):
    name = spec["name"]
    if name == "sla":
        procs = [
            subprocess.Popen(
                [str(ROOT / "sla" / f"server-{port}")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            for port in PORTS
        ]
    elif name == "rust":
        procs = [
            subprocess.Popen(
                [str(ROOT / "rust" / "server"), f"127.0.0.1:{port}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            for port in PORTS
        ]
    elif name == "go":
        procs = [
            subprocess.Popen(
                [str(ROOT / "go" / "server"), f"127.0.0.1:{port}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            for port in PORTS
        ]
    else:
        raise SystemExit(f"unknown server {name}")
    for port in PORTS:
        if not wait_port(port):
            stop(procs)
            raise SystemExit(f"{name}: port {port} did not open")
    return procs


def stop(procs):
    for p in procs:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except OSError:
            pass
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except OSError:
                pass
            p.wait()


def run_client(concurrency, requests, warmup):
    out = subprocess.check_output(
        [
            str(ROOT / "client" / "client"),
            ADDRS,
            str(concurrency),
            str(requests),
            str(warmup),
        ],
        text=True,
        timeout=300,
    )
    return json.loads(out.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--servers", default="sla,rust,go")
    ap.add_argument("--concurrency", default="1,16,64,256")
    ap.add_argument("--requests", type=int, default=20000)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--out", default=str(ROOT / "results.jsonl"))
    args = ap.parse_args()

    rows = []
    levels = [int(x) for x in args.concurrency.split(",")]
    for name in args.servers.split(","):
        for rep in range(args.reps):
            for c in levels:
                # Fresh process per level: the SLA runtime grows ~56 KB per
                # handled request, so reusing a server across levels would
                # conflate steady-state throughput with allocator degradation.
                procs = start({"name": name})
                try:
                    res = run_client(c, args.requests, args.warmup)
                    res.update(
                        server=name,
                        rep=rep,
                        rss_kb=sum(rss_kb(p.pid) for p in procs),
                        threads=sum(
                            len(os.listdir(f"/proc/{p.pid}/task"))
                            for p in procs
                            if os.path.exists(f"/proc/{p.pid}/task")
                        ),
                    )
                    rows.append(res)
                    print(json.dumps(res, ensure_ascii=False), flush=True)
                finally:
                    stop(procs)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
