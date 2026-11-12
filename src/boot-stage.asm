; SPDX-License-Identifier: MIT
        org 08000h
        ld a,40h            ; RAM bank, motors off
        out (1ch),a
        call monitor_init
sync:   call monitor_poll
        jr c,sync
        cp 'V'
        jp z,query_version
        cp 'K'
        jr nz,sync
        ld hl,boot_receiving
        call boot_print
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
        ld hl,boot_ready
        call boot_print
        ld a,6
        call tx
        call rx
        jp c,fail
        cp 'G'
        jp nz,fail
        call link_export
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
rxready:ld a,1
        out (6),a
        in a,(6)
        and 70h             ; parity, overrun or framing error invalidates upload
        jr nz,rxerror
        in a,(4)
        pop de
        or a
        ret
rxerror:in a,(4)            ; consume errored byte before resetting sticky flags
        ld a,30h
        out (6),a
        pop de
        scf
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
        call m_service
        inc hl
        jr boot_print
keyboard_bell:
        ret
boot_waiting:
        db 'Kaypro serial boot ROM v'
rom_version:
        include "src/rom-version.asm"
        db 13,10
        db 'Kaypro 2 PC81-240A | KP2 CRC upload -> CP/M Plus 3.1',13,10
        db 'Waiting for host. Start serial_boot.py auto on the host.',13,10
        db 'Keep host connected for console/disk. No diskette needed.',13,10
        db '? Diagnostics/settings   ESC Return to boot',13,10,0
boot_receiving: db 27,'=',52,32,24,'Receiving platform; checking CRC...',0
boot_ready: db 27,'=',52,32,24,'CRC OK; waiting for host execute command.',0
boot_failed: db 27,'=',52,32,24,'Transfer failed; waiting for host retry.',0
        include "src/monitor.asm"
        include "src/link.asm"
        include "src/console.asm"
