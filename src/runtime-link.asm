; MIT. Optional RAM-owned framing transition; ROM and channel B unchanged.
; Six-byte frame: 'RT', phase, WR4, CRC16-CCITT big endian. Host echoes the
; entire frame. At fast settings D is repeated until a G commits disk boot.
runtime_start:
        ld a,(runtime_config)
        or a
        ret z
        ld a,(link_format)
        ld (runtime_old),a
        ld a,'R'
        call runtime_exchange
        jr c,runtime_restore
        ld a,(runtime_config+1)
        ld (link_format),a
        call link_init
        ld bc,10000
runtime_settle:
        dec bc
        ld a,b
        or c
        jr nz,runtime_settle
        ld a,'F'
        call runtime_exchange
        jr c,runtime_restore
        ld a,4
        ld (runtime_tries),a
runtime_commit:
        ld a,'D'
        call runtime_send
        call serial_rx
        jr c,runtime_again
        cp 'G'
        ret z
runtime_again:
        ld a,(runtime_tries)
        dec a
        ld (runtime_tries),a
        jr nz,runtime_commit
runtime_restore:
        ld a,(runtime_old)
        ld (link_format),a
        call link_init
        ; Stay recoverable at the old framing, never silently execute a
        ; disk loader while the host may still be using the new framing.
runtime_recovery:
        ld a,'B'
        call runtime_exchange
        jr c,runtime_recovery
        ret
runtime_exchange:
        call runtime_send
        ld hl,runtime_frame
        ld b,6
runtime_echo:
        call serial_rx
        ret c
        cp (hl)
        scf
        ret nz
        inc hl
        djnz runtime_echo
        or a
        ret
runtime_send:
        ld (runtime_frame+2),a
        ld a,(link_format)
        ld (runtime_frame+3),a
        ld hl,runtime_frame
        ld de,4
        call link_crc
        ld a,b
        ld (runtime_frame+4),a
        ld a,c
        ld (runtime_frame+5),a
        ld hl,runtime_frame
        ld b,6
runtime_send_byte:
        ld a,(hl)
        call serial_tx
        ret c
        inc hl
        djnz runtime_send_byte
        ret
runtime_frame: db 'RT',0,0,0,0
runtime_old: db 45h
runtime_tries: db 0
; Patched only in the validated upload payload, never the installed ROM.
runtime_config: db 0,44h
