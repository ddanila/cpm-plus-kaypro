; MIT. Independent transient: real BIOS disk calls while keyboard bytes arrive.
        org 100h
        ld sp,stacktop
        ld hl,starting
announce:
        ld a,(hl)
        cp '$'
        jr z,start_disk
        ld c,a
        call 0c00ch
        inc hl
        jr announce
start_disk:
        ld bc,0
        call 0c01eh          ; track 0 (reserved area)
        ld bc,1
        call 0c021h          ; logical record 1
        ld bc,buffer
        call 0c024h
        call 0c027h          ; read before writing unchanged reserved record
        or a
        jp nz,failed
        ld a,40
        ld (remaining),a
again:  call 0c02ah
        or a
        jp nz,failed
        ld a,(remaining)
        dec a
        ld (remaining),a
        jr nz,again
        ld a,32
        ld (remaining),a
readkey:call 0c009h
        ld b,a
        ld a,(remaining)
        ld c,a
        ld a,32
        sub c
        and 15
        add a,'A'
        cp b
        jr nz,failed
        ld a,(remaining)
        dec a
        ld (remaining),a
        jr nz,readkey
        ld de,good
        jr report
failed: ld de,bad
report: ld c,9
        call 5
        jp 0
starting: db 'KEYS START',13,10,'$'
good:   db 'KEYS PASS',13,10,'$'
bad:    db 'KEYS FAIL',13,10,'$'
remaining: db 0
buffer: ds 128
        ds 128
stacktop:
