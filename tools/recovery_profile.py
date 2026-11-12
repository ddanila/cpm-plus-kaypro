"""MIT. Kaypro V3 protocol adapter for the shared native recovery engine."""
import json,time
from pathlib import Path
from diagnostics import query
from serial_boot import validate,bootstrap,write_all
from runtime_link import prepare,transition

def recover(port,config):
    current=dict(config['settings']);options=config['options'];session=Path(config['session'])
    # V3 does not beacon. Only a nonce/CRC checked query authorizes upload.
    candidates=[current,config['boot_settings'],dict(baud=19200,parity='O',stop_bits=1)]
    seen=set();identity=None
    for setting in candidates:
        key=(setting['baud'],setting['parity'],setting['stop_bits'])
        if key in seen:continue
        seen.add(key);port.apply(*key)
        try:identity=query(port.fd,'Q',timeout=2)
        except TimeoutError:continue
        if identity['version'][0]!=3:raise ValueError('unsupported Kaypro ROM')
        if identity['parity']!=setting['parity'] or identity['stop_bits']!=setting['stop_bits']:
            identity=None;continue
        break
    if identity is None:
        port.apply(current['baud'],current['parity'],current['stop_bits'])
        return dict(status='unknown')
    print('ROM confirmed: '+json.dumps(identity),flush=True)
    query(port.fd,'B',timeout=2)
    platform=Path(options['platform']);image=Path(options['image'])
    payload=validate(image,platform)
    if options['optimized']:
        payload=prepare(payload,json.loads(platform.with_name('manifest.json').read_text()),options['runtime_parity'],options['buffer_console'])
    bootstrap(port.fd,payload,session,30)
    write_all(port.fd,b'G',time.monotonic()+3)
    if options['optimized']:
        result=transition(port,options['runtime_baud'],options['runtime_parity'],port.usb)
        (session/'runtime.json').write_text(json.dumps(result,indent=2)+'\n')
    return dict(status='booted',rom=identity)
