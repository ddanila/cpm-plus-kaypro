#!/usr/bin/env python3
"""Device-selection and checked-divisor regression tests; no USB writes. MIT."""
import ctypes
import json
import plistlib
import tempfile
from pathlib import Path
from unittest.mock import patch
import pl2303
from runtime_link import next_generation

def main():
    device={'IOObjectClass':'IOUSBHostDevice','idVendor':0x67b,'idProduct':0x2303,
        'bcdDevice':0x400,'USB Address':3,'locationID':0x2110000,
        'IORegistryEntryChildren':[{'IOCalloutDevice':'/dev/cu.test'}]}
    tree=[{'IOObjectClass':'IOUSBHostDevice','idVendor':1,'IORegistryEntryChildren':[device]}]
    with patch.object(pl2303.sys,'platform','darwin'),patch.object(pl2303.subprocess,'check_output',return_value=plistlib.dumps(tree)):
        assert pl2303.device_identity('/dev/cu.test')['address']==3
        try:pl2303.device_identity('/dev/cu.other')
        except RuntimeError:pass
        else:raise AssertionError('unmatched serial device accepted')
    class USB:
        coding=None
        def libusb_control_transfer(self,handle,kind,request,value,index,buffer,length,timeout):
            if request==0x20:self.coding=bytes(buffer)
            else:ctypes.memmove(buffer,self.coding,7)
            return 7
    adapter=object.__new__(pl2303.USBRate);adapter.u=USB();adapter.h=1;adapter.identity={'test':True}
    for parity in (0,1,2):
        for stop in (1,2):
            report=adapter.set(19800,parity,stop)
            assert report['calculated_actual']==19801
            assert adapter.u.coding[-3:]==bytes([0 if stop==1 else 2,parity,8])
    with patch.object(adapter,'get',return_value=bytes(7)):
        try:adapter.set(19800)
        except RuntimeError:pass
        else:raise AssertionError('mismatched USB readback accepted')
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        registry=root/'registry'
        with patch('runtime_link.secrets.randbits',return_value=0):
            assert [next_generation(root,registry),next_generation(root,registry)]==[1,2]
        other=root/'other';other.mkdir()
        assert next_generation(other,registry)==3
        (root/'generation.json').write_text('4294967295')
        try:next_generation(root,registry)
        except ValueError:pass
        else:raise AssertionError('generation wrapped')
    result=dict(complete=True,physical_usb_access=False,cases=['nested USB identity matched to serial path','unmatched device rejected','19800 divisor and all framings','USB mismatch rejected','monotonic nonwrapping generation'])
    Path('build/adapter-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
