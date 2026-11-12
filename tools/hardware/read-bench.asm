; MIT. READTEST BENCH32.BIN: sequentially read and check the deterministic
; 32768-byte benchmark fixture ((offset*73+19)&255). No writes.
        org 100h
        ld de,5ch
        ld c,15
        call 5
        inc a
        jr z,fail
        ld hl,0
        ld (records),hl
        ld (checksum),hl
next:
        ld de,5ch
        ld c,20
        call 5
        or a
        jr nz,finished
        ld hl,(checksum)
        ld de,80h
        ld b,128
sum:
        ld a,(de)
        add a,l
        ld l,a
        jr nc,nocarry
        inc h
nocarry:
        inc de
        djnz sum
        ld (checksum),hl
        ld hl,(records)
        inc hl
        ld (records),hl
        jr next
finished:
        cp 1
        jr nz,fail
        ld hl,(records)
        ld de,256
        or a
        sbc hl,de
        jr nz,fail
        ld hl,(checksum)
        ld de,0c000h
        or a
        sbc hl,de
        jr nz,fail
        ld de,ok
        jr print
fail:
        ld de,bad
print:
        ld c,9
        call 5
        jp 0
records: dw 0
checksum: dw 0
ok: db 'READ PASS',13,10,'$'
bad: db 'READ FAIL',13,10,'$'
