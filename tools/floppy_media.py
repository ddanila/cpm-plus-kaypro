# SPDX-License-Identifier: MIT
"""Independent Kaypro II raw-image fixture and filesystem inspection.

40 tracks x ten 512-byte sectors, sector-ID order 0..9, one reserved track.
1 KiB blocks, 64 directory entries, CP/M 2-compatible 8-bit block numbers.
"""
SIZE=204800
BASE=5120
BLOCK=1024

def build(files):
    image=bytearray([0xe5])*SIZE
    block=2;slot=0
    for name,data in files.items():
        stem,_,ext=name.partition('.')
        assert 0<len(stem)<=8 and len(ext)<=3
        data=data+b'\x1a'*((-len(data))%128)
        for extent,start in enumerate(range(0,max(1,len(data)),16384)):
            chunk=data[start:start+16384];count=(len(chunk)+1023)//1024
            assert slot<64 and block+count<=195
            entry=bytearray(32);entry[1:12]=(stem.ljust(8)+ext.ljust(3)).encode('ascii')
            entry[12]=extent&31;entry[14]=extent>>5;entry[15]=len(chunk)//128
            entry[16:16+count]=bytes(range(block,block+count))
            off=BASE+slot*32;image[off:off+32]=entry
            image[BASE+block*BLOCK:BASE+block*BLOCK+len(chunk)]=chunk
            block+=count;slot+=1
    return bytes(image)

def inspect(image):
    assert len(image)==SIZE
    files={};owners=set()
    for offset in range(BASE,BASE+2048,32):
        e=image[offset:offset+32]
        if e[0]==0xe5:continue
        assert e[0]<16 and e[15]<=128
        raw=bytes(c&127 for c in e[1:12]);name=raw[:8].decode().rstrip()+'.'+raw[8:].decode().rstrip()
        name=name.rstrip('.');extent=e[12]+32*e[14];n=(e[15]+7)//8
        blocks=e[16:16+n]
        for block in blocks:
            assert 2<=block<195 and block not in owners
            owners.add(block)
        data=b''.join(image[BASE+b*BLOCK:BASE+(b+1)*BLOCK] for b in blocks)[:e[15]*128]
        files.setdefault((e[0],name),[]).append((extent,data))
    result={}
    for key,extents in files.items():
        extents.sort();assert [i for i,_ in extents]==list(range(len(extents)))
        result[key]=b''.join(data for _,data in extents)
    return result
