; MIT. Kaypro glue for the shared N4 / NetDisk engines.
home:   call N3INV
        ld hl,0
        ld (track),hl
        xor a
        ret
serial_position:
        call keyservice
        ld a,(drive)
        or a
        jp nz,error
        ld hl,(track)
        ld a,h
        or a
        jp nz,error
        ld a,l
        cp 160
        jp nc,error
        ld (SEKTRK),hl
        ld hl,(record)
        ld a,h
        or a
        jp nz,error
        ld a,l
        or a
        jp z,error
        cp 41
        jp nc,error
        ld (SEKSEC),a
        ld hl,(dma)
        ld (MEMADR),hl
        xor a
        ld (SEKDSK),a
        ret
read:   call serial_position
        or a
        ret nz
        ; One-record requests; no stale cache survives a host reconnect.
        call N3INV
        jp N3READ
write:  call serial_position
        or a
        ret nz
        jp N3WRITE

remote_init:
        call link_init
        ld hl,remote_state
        ld de,remote_state+1
        ld bc,remote_state_end-remote_state-1
        ld (hl),0
        ldir
        ld hl,net_cache
        ld (N3CACHE),hl
        ld a,3
        call N3ENA
        call rh_enable
        call rh_caps
        or a
        ret nz              ; bounded discovery will retry from CONST
        inc hl
        inc hl              ; capabilities: version, max records, features, reserved
        ld a,(hl)
        ld (RHINPUT),a
        jp rh_config

; SHARED_SERIAL ABI: A byte in/out; carry indicates failure. Preserve
; BC/DE/HL. Begin/finish preserve A too; all polling is finite.
serial_begin:
        push af
        ld a,30h            ; reset SIO receive errors, no FIFO flush
        out (6),a
        pop af
        or a
        ret
serial_finish:
        ; Full-duplex RS232 needs no transmitter direction switch.
        or a
        ret
serial_tx:
        push bc
        push af
        ld bc,0
serial_tx_wait:
        ld a,c
        and 15
        call z,keyservice
        in a,(6)
        and 4
        jr nz,serial_tx_ready
        dec bc
        ld a,b
        or c
        jr nz,serial_tx_wait
        pop af
        pop bc
        scf
        ret
serial_tx_ready:
        pop af
        out (4),a
        pop bc
        or a
        ret
serial_rx:
        push bc
        ld bc,0
serial_rx_wait:
        ld a,c
        and 15
        call z,keyservice
        in a,(6)
        and 1
        jr nz,serial_rx_ready
        dec bc
        ld a,b
        or c
        jr nz,serial_rx_wait
        pop bc
        scf
        ret
serial_rx_ready:
        in a,(4)
        pop bc
        or a
        ret
