; MIT. PC81-240A WD1793, Kaypro II SSDD. 128-byte BIOS records,
; 512-byte write-through physical sectors. No host calls inside DRQ loops.
floppy_home:
        ld hl,0ffffh
        ld (floppy_tracks),hl
        ld a,(system_latch)
        and 0fch
        or 40h
        ld (system_latch),a
        out (1ch),a
        ret
floppy_idle:
        ld a,(floppy_idle_count)
        or a
        ret z
        dec a
        ld (floppy_idle_count),a
        ret nz
        ld a,(system_latch)
        or 40h
        ld (system_latch),a
        out (1ch),a
        ret
floppy_prepare:
        call console_flush
        call keyservice
        call N3INV
        ld a,(drive)
        sub 2
        cp 2
        jp nc,error
        ld e,a
        ld d,0
        ld hl,floppy_tracks
        add hl,de
        ld (floppy_track_ptr),hl
        ld a,e
        or a
        ld a,1
        jr z,floppy_latch
        inc a
floppy_latch:
        ld b,a
        ld a,(system_latch)
        ld c,a
        and 98h             ; retain BANK, printer strobe and input bit
        or b                ; side 0, double density, motors on
        ld (system_latch),a
        out (1ch),a
        bit 6,c
        jr z,floppy_spun
        ; >= 500 ms at 2.5 MHz; no active controller transfer yet.
        ld b,6
floppy_spin:
        push bc
        ld bc,10000
floppy_spin_loop:
        ld a,c
        or a
        call z,keyservice
        dec bc
        ld a,b
        or c
        jr nz,floppy_spin_loop
        call keyservice
        pop bc
        djnz floppy_spin
floppy_spun:
        ld a,32
        ld (floppy_idle_count),a
        ld hl,(track)
        ld a,h
        or a
        jp nz,error
        ld a,l
        cp 40
        jp nc,error
        ld hl,(record)
        ld a,h
        or a
        jp nz,error
        ld a,l
        dec a
        cp 40
        jp nc,error
        ld b,a
        and 1
        rrca
        ld l,a
        ld h,0
        ; record offset: (record-1)%4 * 128.
        ld a,b
        and 2
        rrca
        ld h,a
        ld (floppy_offset),hl
        ld a,b
        srl a
        srl a
        out (12h),a
        ld hl,(floppy_track_ptr)
        ld a,(hl)
        cp 0ffh
        jr nz,floppy_known
        xor a
        out (10h),a         ; restore, 6 ms step rate at 1 MHz
        call floppy_settle
        call floppy_wait
        and 90h
        jp nz,error
        xor a
        ld hl,(floppy_track_ptr)
        ld (hl),a
floppy_known:
        out (11h),a
        ld b,a
        ld a,(track)
        cp b
        jr nz,floppy_seek
        xor a
        ret
floppy_seek:
        out (13h),a
        ld a,10h
        out (10h),a
        call floppy_settle
        call floppy_wait
        and 90h
        jr nz,floppy_bad_track
        ld a,(track)
        ld hl,(floppy_track_ptr)
        ld (hl),a
        xor a
        ret
floppy_bad_track:
        ld hl,(floppy_track_ptr)
        ld (hl),0ffh
        jp error
floppy_settle:
        push bc
        ld b,20
floppy_settle_loop:
        djnz floppy_settle_loop
        pop bc
        ret
; Bounded command wait (under 8 seconds at 2.5 MHz), returns status or synthetic not-ready.
floppy_wait:
        ld de,0
        ld b,4
floppy_wait_loop:
        ld a,e
        or a
        call z,keyservice
        in a,(10h)
        bit 0,a
        ret z
        dec de
        ld a,d
        or e
        jr nz,floppy_wait_loop
        djnz floppy_wait_loop
floppy_abort:
        ld a,0d0h
        out (10h),a
        ld a,80h
        ret
floppy_read:
        ld a,3
        ld (floppy_attempts),a
floppy_retry:
        call floppy_prepare
        or a
        ret nz
        call floppy_read_sector
        or a
        jr z,floppy_copy_out
        ld hl,floppy_attempts
        dec (hl)
        jr nz,floppy_retry
        jp error
floppy_copy_out:
        ld hl,(floppy_offset)
        ld de,floppy_buffer
        add hl,de
        ld de,(dma)
        ld bc,128
        ldir
        call keyservice
        xor a
        ret
floppy_write:
        ld a,(drive)
        cp 2
        ld b,1
        jr z,floppy_permission
        cp 3
        jp nz,error
        ld b,2
floppy_permission:
        ld a,(floppy_write_mask)
        and b
        jp z,error
        call floppy_prepare
        or a
        ret nz
        call floppy_read_sector
        or a
        jp nz,error
        ld hl,(floppy_offset)
        ld de,floppy_buffer
        add hl,de
        ex de,hl
        ld hl,(dma)
        ld bc,128
        ldir
        call floppy_nmi_begin
        ld hl,floppy_buffer
        ld bc,13h
        ld d,2
        ld a,0a0h
        out (10h),a
floppy_write_loop:
        halt
        outi
        jp nz,floppy_write_loop
        dec d
        jr nz,floppy_write_loop
        jr floppy_finish
floppy_read_sector:
        call floppy_nmi_begin
        ld hl,floppy_buffer
        ld bc,13h
        ld d,2
        ld a,80h
        out (10h),a
floppy_read_loop:
        halt
        ini
        jp nz,floppy_read_loop
        dec d
        jr nz,floppy_read_loop
floppy_finish:
        call floppy_nmi_end
        call floppy_wait
        and 0fch            ; CRC, lost data, RNF, deleted/fault, WP, ready
        ret z
        jp error
; PC81-240A gates DRQ/INTRQ to NMI only while HALTed. An early command
; error wakes the remaining iterations through INTRQ; status still rejects
; the entire operation. Never call console/keyboard services inside this loop.
; The private NMI vector is restored before returning to CP/M.
floppy_nmi_begin:
        ld hl,(66h)
        ld (floppy_saved_nmi),hl
        ld hl,45edh         ; RETN
        ld (66h),hl
        ret
floppy_nmi_end:
        ld hl,(floppy_saved_nmi)
        ld (66h),hl
        ret
floppy_write_mask: db 0
floppy_saved_nmi: dw 0
floppy_idle_count: db 0
floppy_tracks: db 0ffh,0ffh
floppy_track_ptr: dw 0
floppy_offset: dw 0
floppy_attempts: db 0
floppy_buffer: ds 512
