; SPDX-License-Identifier: MIT
        org 08000h
        ld a,40h            ; RAM bank, motors off
        out (1ch),a
        xor a
        out (6),a           ; force pointer to WR0
        ld a,18h
        out (6),a
        ld a,4
        out (6),a
        ld a,44h            ; x16, 8N1
        out (6),a
        ld a,3
        out (6),a
        ld a,0c1h
        out (6),a
        ld a,5
        out (6),a
        ld a,0eah
        out (6),a
        ld a,15
        out (0),a
sync:   call rx
        jr c,sync
        cp 'K'
        jr nz,sync
        ld a,'K'
        call tx
        ld a,'P'
        call tx
        ld a,'1'
        call tx
        call rx
        jr c,fail
        ld e,a
        call rx
        jr c,fail
        ld d,a
        cp 36h
        jr nc,fail
        or e
        jr z,fail
        ld hl,0c000h
        ld bc,0ffffh
receive:call rx
        jr c,fail
        ld (hl),a
        inc hl
        xor b
        ld b,a
        push de
        ld e,8
crcbit: sla c
        rl b
        jr nc,noxor
        ld a,b
        xor 10h
        ld b,a
        ld a,c
        xor 21h
        ld c,a
noxor:  dec e
        jr nz,crcbit
        pop de
        dec de
        ld a,d
        or e
        jr nz,receive
        call rx
        jr c,fail
        cp b
        jr nz,fail
        call rx
        jr c,fail
        cp c
        jr nz,fail
        ld a,6
        call tx
        call rx
        jr c,fail
        cp 'G'
        jr nz,fail
        jp 0c033h
fail:   ld a,15h
        call tx
        jp sync
rx:     push de
        ld de,0
rxwait: in a,(6)
        and 1
        jr nz,rxready
        dec de
        ld a,d
        or e
        jr nz,rxwait
        pop de
        scf
        ret
rxready:in a,(4)
        pop de
        or a
        ret
tx:     push af
        push de
        ld de,0
txwait: in a,(6)
        and 4
        jr nz,txready
        dec de
        ld a,d
        or e
        jr nz,txwait
        pop de
        pop af
        scf
        ret
txready:pop de
        pop af
        out (4),a
        or a
        ret
