; MIT. Shared channel A setup and versioned bootstrap handoff.
link_defaults:
        ld a,15
        ld (link_baud),a
        ld a,45h
        ld (link_format),a
        ret
link_init:
        xor a
        out (6),a
        ld a,18h
        out (6),a
        ld a,(link_baud)
        out (0),a
        ld a,4
        out (6),a
        ld a,(link_format)
        out (6),a
        ld a,1
        out (6),a
        xor a
        out (6),a
        ld a,3
        out (6),a
        ld a,0c1h
        out (6),a
        ld a,5
        out (6),a
        ld a,0eah
        out (6),a
        ret
; CRC BC over DE bytes at HL. Preserves no general registers.
link_crc:
        ld bc,0ffffh
lc_byte: ld a,(hl)
        inc hl
        xor b
        ld b,a
        push de
        ld e,8
lc_bit: sla c
        rl b
        jr nc,lc_next
        ld a,b
        xor 10h
        ld b,a
        ld a,c
        xor 21h
        ld c,a
lc_next:dec e
        jr nz,lc_bit
        pop de
        dec de
        ld a,d
        or e
        jr nz,lc_byte
        ret
link_export:
        ld hl,09cf0h
        ld de,09cf1h
        ld bc,15
        ld (hl),0
        ldir
        ld hl,0504bh
        ld (09cf0h),hl
        ld hl,04333h
        ld (09cf2h),hl
        ld a,1
        ld (09cf4h),a
        ld a,(link_baud)
        ld (09cf5h),a
        ld a,(link_format)
        ld (09cf6h),a
        ld hl,09cf0h
        ld de,14
        call link_crc
        ld a,b
        ld (09cfeh),a
        ld a,c
        ld (09cffh),a
        ret
link_import:
        call link_defaults
        ld hl,(09cf0h)
        ld de,0504bh
        or a
        sbc hl,de
        ret nz
        ld hl,(09cf2h)
        ld de,04333h
        or a
        sbc hl,de
        ret nz
        ld a,(09cf4h)
        cp 1
        ret nz
        ld hl,09cf0h
        ld de,14
        call link_crc
        ld a,(09cfeh)
        cp b
        ret nz
        ld a,(09cffh)
        cp c
        ret nz
        ld a,(09cf5h)
        cp 16
        ret nc
        ld e,a
        ld a,(09cf6h)
        ld d,a
        and 30h
        ret nz
        ld a,d
        and 0c0h
        ret z
        ld a,d
        and 0ch
        cp 4
        jr z,li_valid
        cp 0ch
        ret nz
li_valid:
        ld a,e
        ld (link_baud),a
        ld a,d
        ld (link_format),a
        xor a
        ld (09cf0h),a
        ret
