; SPDX-License-Identifier: MIT
; Copyright (c) 2026 Danila Sukharev
; Kaypro serial-only services adapted from cpm-plus-1715. No historical BIOS code included.
        include "build/system.inc"
        org 0c000h
        jp unavailable
        jp home
        jp const
        jp conin
        jp conout
        jp unavailable
        jp unavailable
        jp unavailable
        jp home
        jp seldsk
        jp settrk
        jp setsec
        jp setdma
        jp read
        jp write
        jp unavailable
        jp sectrn
        jp loader
        jp keypause
        jp keyresume
init:   di
        call remote_init
        jp home
unavailable:
keyservice:
keypause:
keyresume:
        xor a
        ret
const:  jp rh_status
conin:  call rh_status
        or a
        jr z,conin
        jp rh_input
conout: push af
        push bc
        push de
        push hl
        ld a,c
        ld (RHINPUT),a
        call rh_output
        pop hl
        pop de
        pop bc
        pop af
        ret
seldsk: ld a,c
        ld (drive),a
        ld hl,0
        or a
        ret nz
        inc hl
        ret
settrk: ld (track),bc
        ret
setsec: ld (record),bc
        ret
setdma: ld (dma),bc
        ret
sectrn: ld h,b
        ld l,c
        inc hl
        ret
error:  call keyservice
        ld a,1
        ret
; CRC CCITT, HL source, DE length, BC accumulator. Stream already stopped.
crc:    ld a,e
        and 31
        call z,keyservice
        ld a,(hl)
        xor b
        ld b,a
        push de
        ld e,8
crcbit: sla c
        rl b
        jr nc,crcnox
        ld a,b
        xor 10h
        ld b,a
        ld a,c
        xor 21h
        ld c,a
crcnox: dec e
        jr nz,crcbit
        pop de
        inc hl
        dec de
        ld a,d
        or e
        jr nz,crc
        ret
        include "src/serial-platform.asm"
; Bootstrap scans the user-0 directory for the single-extent CPM3.SYS.
; GENCPM's reverse 128-byte record order is retained on disk.
loader: di
        ld sp,0f700h
        call init
        ld bc,0
        call seldsk
        ld bc,4
        call settrk
        ld bc,1
        call setsec
        ld bc,dirrecord
        call setdma
        ld a,32
        ld (dirleft),a
scanrecord: call keyservice
        call read
        or a
        jp nz,booterror
        ld hl,dirrecord
        ld b,4
scanentry: push bc
        push hl
        ld a,(hl)
        or a
        jr nz,nomatch
        inc hl
        ld de,sysname
        ld b,11
matchname: ld a,(hl)
        and 7fh
        ld c,a
        ld a,(de)
        cp c
        jr nz,nomatch
        inc hl
        inc de
        djnz matchname
        ld a,(hl)
        or a
        jr nz,nomatch
        pop hl
        pop bc
        ld de,sysentry
        ld bc,32
        ldir
        jp loadsys
nomatch: pop hl
        ld de,32
        add hl,de
        pop bc
        djnz scanentry
        ld hl,(record)
        inc hl
        ld (record),hl
        ld a,(dirleft)
        dec a
        ld (dirleft),a
        jr nz,scanrecord
        jp booterror
loadsys: ld a,(sysentry+14)
        or a
        jp nz,booterror
        ; Exactly five blocks contain the 72-record generated system.
        ; Validate all before reading any payload into resident memory.
        ld ix,sysentry+16
        ld b,5
sysblocks: ld l,(ix+0)
        ld h,(ix+1)
        ld de,2
        or a
        sbc hl,de
        jp c,booterror
        ld de,388
        or a
        sbc hl,de
        jp nc,booterror
        ld hl,sysentry+16
        ld a,5
        sub b
        ld c,a
        jr z,sysblocknext
sysunique: ld a,(hl)
        cp (ix+0)
        inc hl
        jr nz,sysdifferent
        ld a,(hl)
        cp (ix+1)
        jp z,booterror
sysdifferent: inc hl
        dec c
        jr nz,sysunique
sysblocknext: inc ix
        inc ix
        djnz sysblocks
        ld b,6
sysunused: ld a,(ix+0)
        or a
        jp nz,booterror
        inc ix
        djnz sysunused
        ld a,(sysentry+15)
        cp 72
        jp nz,booterror
        xor a
        ld (filerec),a
        call sysread
        or a
        jp nz,booterror
        ld hl,dirrecord
        ld de,sysheader
        ld b,6
checkheader: ld a,(de)
        cp (hl)
        jp nz,booterror
        inc hl
        inc de
        djnz checkheader
        ld a,2
        ld (filerec),a
        ld hl,0bf80h
        ld (destination),hl
sysloop: call sysread
        or a
        jp nz,booterror
        ld hl,dirrecord
        ld de,(destination)
        ld bc,128
        ldir
        ld hl,(destination)
        ld de,128
        or a
        sbc hl,de
        ld (destination),hl
        ld a,(filerec)
        inc a
        ld (filerec),a
        cp 72
        jr nz,sysloop
        ld hl,09d00h
        ld de,2300h
        ld bc,0ffffh
        call crc
        ld hl,system_crc
        or a
        sbc hl,bc
        jp nz,booterror
        jp 0bc00h
sysread: ld a,(filerec)
        srl a
        srl a
        srl a
        srl a
        add a,a
        ld l,a
        ld h,0
        ld de,sysentry+16
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,d
        cp 2
        jp nc,error
        ex de,hl
        ld a,h
        or l
        jp z,error
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,(filerec)
        and 15
        ld e,a
        ld d,0
        add hl,de
        ld de,160
        add hl,de
        ld bc,0
        ld de,40
sysdivide: or a
        sbc hl,de
        jr c,sysdivdone
        inc bc
        jr sysdivide
sysdivdone: add hl,de
        inc hl
        ld (record),hl
        ld (track),bc
        ld bc,dirrecord
        call setdma
        jp read
booterror: ld hl,bootmsg
bootprint: ld a,(hl)
        or a
        jr z,boothalt
        ld c,a
        call conout
        inc hl
        jr bootprint
boothalt: di
        halt
        jr boothalt
sysname: db 'CPM3    SYS'
sysheader: db 0c0h,23h,0,0,0,0bch
bootmsg: db 'CP/M 3 boot error: CPM3.SYS',13,10,0
idonly: db 0
valid: db 0
cachedtrack: db 0
cachedsector: db 0
cursor: dw 0f800h
column: db 0
keyhold: db 0
keyhead: db 0
keytail: db 0
keycount: db 0
keydrops: dw 0
keydecoded: dw 0
keycalls: dw 0
prefix: db 0
drive: db 0
track: dw 0
record: dw 1
dma: dw 80h
cylinder: db 0
head: db 0
sector: db 1
subrecord: db 0
attempts: db 0
dirleft: db 0
filerec: db 0
destination: dw 0
sysentry: ds 32
dirrecord: ds 128
keyqueue: ds 128
        include "src/serial-common.asm"
platform_end:
        end
