#!/usr/bin/env python3
"""Remove DWARF/name custom sections so WASM sizes are deployment-comparable.

Usage: python3 scripts/strip_wasm.py IN.wasm OUT.wasm
"""
import sys
from pathlib import Path


def leb(b, i):
    value = 0
    shift = 0
    while True:
        byte = b[i]
        i += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, i
        shift += 7


def encode_leb(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def section_name(payload):
    n, i = leb(payload, 0)
    return payload[i:i + n].decode("utf-8", "replace")


def strip(data):
    if data[:4] != b"\0asm":
        raise ValueError("not a wasm module")
    out = bytearray(data[:8])
    i = 8
    while i < len(data):
        start = i
        sid = data[i]
        i += 1
        size, i = leb(data, i)
        payload = data[i:i + size]
        i += size
        keep = True
        if sid == 0:
            name = section_name(payload)
            keep = not (name == "name" or name.startswith(".debug"))
        if keep:
            out += data[start:i]
    return bytes(out)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    data = strip(src.read_bytes())
    dst.write_bytes(data)
    print(f"{src} {src.stat().st_size} -> {dst} {len(data)}")


if __name__ == "__main__":
    main()
