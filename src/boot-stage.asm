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
        ld a,45h            ; x16, 8O1 (same framing as runtime)
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
        call local_init
        ld hl,boot_waiting
        call boot_print
sync:   call rx
        jr c,sync
        cp 'V'
        jp z,query_version
        cp 'K'
        jr nz,sync
        ld a,'K'
        call tx
        ld a,'P'
        call tx
        ld a,'2'
        call tx
        call rx
        jp c,fail
        ld e,a
        call rx
        jp c,fail
        ld d,a
        cp 36h
        jp nc,fail
        or a
        jr nz,length_ok
        ld a,e
        cp 36h              ; minimum contains C033 jump instruction
        jp c,fail
length_ok:
        ld hl,0c000h
        ld bc,0ffffh
receive:call rx
        jp c,fail
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
        jp c,fail
        cp b
        jp nz,fail
        call rx
        jp c,fail
        cp c
        jp nz,fail
        ld a,6
        call tx
        call rx
        jp c,fail
        cp 'G'
        jp nz,fail
        jp 0c033h
query_version:
        ld a,'K'
        call tx
        ld a,'P'
        call tx
        ld a,'V'
        call tx
        ld hl,rom_version
version_byte:
        ld a,(hl)
        call tx
        inc hl
        cp 13
        jr nz,version_byte
        ld a,10
        call tx
        jp sync
fail:   push hl
        ld hl,boot_failed
        call boot_print
        pop hl
        ld a,30h
        out (6),a
        ld a,15h
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

boot_print:
        ld a,(hl)
        or a
        ret z
        ld c,a
        call localout
        inc hl
        jr boot_print
keyboard_bell:
        ret
boot_waiting:
        db 'Kaypro serial boot ROM v'
rom_version:
        include "src/rom-version.asm"
        db 13,10
        db 'Kaypro 2 / PC81-240A',13,10,13,10
        db 'Serial A: 19200 baud, 8 data bits, odd parity, 1 stop bit',13,10
        db 'Protocol: KP2 (CRC-checked platform upload)',13,10
        db 'Expects: platform.cim, then CP/M Plus 3.1 from host disk',13,10,13,10
        db 'On host: python3 tools/serial_boot.py boot',13,10
        db '         --serial <port> --session <new-session>',13,10
        db '         --host <jukuhost>',13,10,13,10
        db 'Keep the host connected for console and virtual disk.',13,10
        db 'This ROM boots from serial; no floppy diskette is needed.',13,10,13,10
        db 'Waiting for host...',13,10,0
boot_failed: db 'Transfer failed; waiting for retry',13,10,0
        include "src/console.asm"
