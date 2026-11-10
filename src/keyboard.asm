; MIT. Polling channel B, 300 baud 8N1. Preserve main registers and flags.
keyboard_init:
        xor a
        out (7),a
        ld a,18h
        out (7),a
        ld a,4
        out (7),a
        ld a,44h
        out (7),a
        ld a,3
        out (7),a
        ld a,0c1h
        out (7),a
        ld a,5
        out (7),a
        ld a,0eah
        out (7),a
        ld a,5
        out (0ch),a
        xor a
        ld (keyhead),a
        ld (keytail),a
        ld (keycount),a
        ld (keyhold),a
        ld (keydrops),a
        ld (keydrops+1),a
        ret
keyservice:
        push af
        push bc
        push de
        push hl
        ld b,3
keypoll:
        in a,(7)
        and 1
        jr z,keydone
        in a,(5)
        ld c,a
        ld a,(keycount)
        cp 128
        jr z,keyfull
        inc a
        ld (keycount),a
        ld a,(keytail)
        ld e,a
        ld d,0
        ld hl,keyqueue
        add hl,de
        ld (hl),c
        inc a
        and 127
        ld (keytail),a
        jr keynext
keyfull:
        ld hl,(keydrops)
        inc hl
        ld (keydrops),hl
keynext:
        djnz keypoll
keydone:
        ; Clear sticky receive errors without flushing pending bytes.
        ld a,30h
        out (7),a
        pop hl
        pop de
        pop bc
        pop af
        ret
keypause:
        ld a,1
        ld (keyhold),a
        ret
keyresume:
        xor a
        ld (keyhold),a
        ret
keyboard_get:
        ld a,(keyhead)
        ld e,a
        ld d,0
        ld hl,keyqueue
        add hl,de
        inc a
        and 127
        ld (keyhead),a
        ld a,(keycount)
        dec a
        ld (keycount),a
        ld a,(hl)
        ret
keyboard_bell:
        in a,(7)
        and 4
        ret z
        ld a,4
        out (5),a
        ret
