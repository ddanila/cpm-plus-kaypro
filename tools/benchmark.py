#!/usr/bin/env python3
"""Repeatable CP/M workloads, independent disk verification and JSON evidence. MIT.

The caller owns the serial connection and supplies command/warm-boot callbacks.
No port is opened and no disk is modified outside CP/M by this module.
"""
import hashlib
import json
import statistics
import time
from pathlib import Path
from media import inspect

def run(command, warm_boot, disk, report, identity, repeats=5):
    report = Path(report)
    result = dict(complete=False, identity=identity, samples=[], medians={})
    def save():
        report.write_text(json.dumps(result, indent=2)+'\n')
    save()
    for iteration in range(repeats):
        for source, destination in [('PATTERN.BIN','BENCH8.OUT'), ('BENCH32.BIN','BENCH32.OUT')]:
            expected = inspect(Path(disk).read_bytes())[(0,source)].data
            start=time.monotonic()
            response=command(f'PIP {destination}={source}[O]')
            elapsed=time.monotonic()-start
            if b'ERROR' in response:raise RuntimeError(response)
            actual=inspect(Path(disk).read_bytes())[(0,destination)].data
            if actual!=expected:raise AssertionError('independent copy verification failed')
            result['samples'].append(dict(workload=f'copy-{len(expected)}',iteration=iteration,
                seconds=elapsed,verified_bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest()))
            save()
        for name, action in [('warm-boot',warm_boot),('console',lambda:command('TYPE HELLO.TXT'))]:
            start=time.monotonic();response=action()
            if name=='console' and b'Kaypro 2' not in response:raise AssertionError(response)
            result['samples'].append(dict(workload=name,iteration=iteration,seconds=time.monotonic()-start))
            save()
    for name in {s['workload'] for s in result['samples']}:
        result['medians'][name]=statistics.median(s['seconds'] for s in result['samples'] if s['workload']==name)
    result['complete']=True;save()
    return result
