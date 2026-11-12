; MIT. Kaypro glue for the shared N4 / NetDisk engines.
home:   call console_flush
        call N3INV
        ld hl,0
        ld (track),hl
        xor a
        ret
serial_position:
        call console_flush
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
        call cache_validate
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
        ld a,(hl)
        inc hl
        inc hl              ; capabilities: version, max records, features, reserved
        ld a,(hl)
        ld (host_features),a
        ld (RHINPUT),a
        jp rh_config

; CAPS/EPOC is advertised by bit 7. Validate the host generation before
; permitting cached reads, including an otherwise invisible host restart.
cache_validate:
        ld a,(host_features)
        and 80h
        jp z,N3INV
        ld a,(N3COUNT)
        or a
        ret z
        ; A miss will fetch fresh data anyway. Query the epoch only before
        ; serving an actual cache hit, not before every disk request.
        ld b,a
        ld hl,net_cache
cache_find:
        ld a,(SEKTRK)
        cp (hl)
        jr nz,cache_next
        inc hl
        ld a,(SEKTRK+1)
        cp (hl)
        dec hl
        jr nz,cache_next
        inc hl
        inc hl
        ld a,(SEKSEC)
        cp (hl)
        dec hl
        dec hl
        jr z,cache_epoch_check
cache_next:
        ld de,131
        add hl,de
        djnz cache_find
        ret
cache_epoch_check:
        ld hl,epoch_args
        ld de,RHARG
        ld bc,4
        ldir
        ld a,26h
        call rh_call
        or a
        jp nz,N3INV
        ld hl,RHCAPBUF
        ld de,cache_epoch
        ld b,4
cache_compare:
        ld a,(de)
        cp (hl)
        call nz,N3INV
        ld a,(hl)
        ld (de),a
        inc hl
        inc de
        djnz cache_compare
        ret
epoch_args: db 'EPOC'
cache_epoch: ds 4
host_features: db 0

console_queue:
        ld a,(host_features)
        and 40h
        jr z,console_single
        ld a,(console_buffering)
        or a
        jr nz,console_buffer
console_single:
        ld a,c
        ld (RHINPUT),a
        jp rh_output
console_buffer:
        ld a,(console_count)
        ld e,a
        ld d,0
        ld hl,console_bytes
        add hl,de
        ld (hl),c
        inc a
        ld (console_count),a
        cp 32
        jp z,console_flush
        ld a,c
        cp 10
        ret nz
console_flush:
        push af
        push bc
        push de
        push hl
        ld a,(console_count)
        or a
        jr z,console_flushed
        ld b,a
        xor a
        ld (console_count),a
        ld hl,console_bytes
        call rh_bulk
console_flushed:
        pop hl
        pop de
        pop bc
        pop af
        ret
console_buffering: db 0
console_count: db 0
console_bytes: ds 32

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
