#!/usr/bin/env python3
"""Strict clean SSDD Kaypro II IMD <-> canonical sector image. MIT."""
import argparse
from pathlib import Path

def decode(data):
    if not data.startswith(b'IMD '):
        raise ValueError('not ImageDisk')
    pos = data.index(b'\x1a') + 1
    sectors = {}
    def take(n):
        nonlocal pos
        value = data[pos:pos+n]
        if len(value) != n:
            raise ValueError('truncated image')
        pos += n
        return value
    while pos < len(data):
        mode, cylinder, head, count, size = take(5)
        if mode != 5 or cylinder >= 40 or head & 0x3f or count != 10 or size != 2:
            raise ValueError('expected 250-kbit MFM, 40 x 1 x 10 x 512')
        ids = take(count)
        cylinders = take(count) if head & 0x80 else bytes([cylinder])*count
        heads = take(count) if head & 0x40 else bytes(count)
        if set(ids) != set(range(10)) or cylinders != bytes([cylinder])*count or any(heads):
            raise ValueError('unexpected sector ID map')
        for sector in ids:
            kind = take(1)[0]
            if kind not in (1, 2):
                raise ValueError('missing/deleted/error sector')
            payload = take(512) if kind == 1 else take(1)*512
            key = (cylinder, sector)
            if key in sectors:
                raise ValueError('duplicate sector')
            sectors[key] = payload
    if len(sectors) != 400:
        raise ValueError('incomplete disk')
    return b''.join(sectors[t,s] for t in range(40) for s in range(10))

def encode(raw):
    if len(raw) != 204800:
        raise ValueError('expected exactly 204800 bytes')
    data = bytearray(b'IMD 1.18: canonical Kaypro II sector image\r\n\x1a')
    for t in range(40):
        data += bytes([5,t,0,10,2]) + bytes(range(10))
        for s in range(10):
            data += b'\x01' + raw[(t*10+s)*512:(t*10+s+1)*512]
    return bytes(data)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--encode',action='store_true');a=p.parse_args()
    a.destination.write_bytes((encode if a.encode else decode)(a.source.read_bytes()))
