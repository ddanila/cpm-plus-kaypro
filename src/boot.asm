; SPDX-License-Identifier: MIT
; Kaypro 81-240A serial loader. 4 KiB EPROM; no stock firmware needed.
; Relocate to 8000h BEFORE disabling ROM: low writes do not reach RAM.
; Fixed destination C000h, entry C033h. Length 36h..35FFh, CRC16-CCITT.
; Protocol: host 'K', ROM 'KP2', host length LE, payload, CRC BE;
; ROM ACK 06 then host 'G' executes. NAK 15 restarts. Polls time out.
        org 0
        di
        ld sp,0bff0h
        ld a,0cfh           ; PIO A mode 3
        out (1dh),a
        ld a,08h            ; busy input; bank and other outputs
        out (1dh),a
        ld a,0c0h           ; ROM bank, floppy motors off
        out (1ch),a
        ld hl,stage
        ld de,08000h
        ld bc,stage_end-stage
        ldir
        jp 08000h
stage:  incbin "build/boot-stage.cim"
stage_end:
        dc 4096-$,0ffh
