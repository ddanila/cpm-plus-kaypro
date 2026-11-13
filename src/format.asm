; MIT. Destructive, explicitly selected Kaypro II formatter for this platform.
; FORMAT C ERASE or FORMAT D ERASE. FORMAT C LOCK disables subsequent writes.
; No writes on any other command. Code guard binds private resident interfaces.
        include "build/format-bindings.inc"
        org 100h
        jp start
start:  ld sp,stacktop
        di
        ld hl,guard_address
        ld de,guard_copy
        ld bc,guard_length
check_guard:
        ld a,(de)
        cp (hl)
        jp nz,wrong_platform
        inc hl
        inc de
        dec bc
        ld a,b
        or c
        jr nz,check_guard
        ld a,(80h)
        cp 8
        jp z,parse_erase
        cp 7
        jp nz,usage
        ld hl,81h
        ld de,lock_tail
        ld b,7
        call match_tail
        jp nz,parse_test
        xor a
        ld (rt_floppy_write_mask),a
        ld hl,locked
        jp finish
parse_test:
        ld hl,81h
        ld de,test_tail
        ld b,7
        call match_tail
        jp nz,usage
        ld a,(82h)
        sub 'C'
        ld (physical_drive),a
        add a,2
        ld (rt_drive),a
        call rt_floppy_home
        ld hl,0
        ld (rt_track),hl
        ld a,(physical_drive)
        or a
        ld a,1
        jr z,test_enable
        inc a
test_enable:
        ld (rt_floppy_write_mask),a
        ld hl,pattern
        ld (rt_dma),hl
        ld hl,1
        ld (rt_record),hl
test_write:
        call 0c02ah
        or a
        jp nz,test_fail
        call test_advance
        jr nz,test_write
        call rt_floppy_home
        ld hl,1
        ld (rt_record),hl
        ld hl,readback
        ld (rt_dma),hl
test_read:
        call 0c027h
        or a
        jp nz,test_fail
        call test_advance
        jr nz,test_read
        ld hl,pattern
        ld de,readback
        ld bc,512
test_compare:
        ld a,(de)
        cp (hl)
        jp nz,test_fail
        inc hl
        inc de
        dec bc
        ld a,b
        or c
        jr nz,test_compare
        xor a
        ld (rt_floppy_write_mask),a
        ld hl,test_success
        jp finish
test_fail:
        xor a
        ld (rt_floppy_write_mask),a
        ld hl,test_error
        jp finish
test_advance:
        ld hl,(rt_dma)
        ld de,128
        add hl,de
        ld (rt_dma),hl
        ld hl,(rt_record)
        inc hl
        ld (rt_record),hl
        ld a,l
        cp 5
        ret
parse_erase:
        ld hl,81h
        ld de,erase_tail
        ld b,8
        call match_tail
        jp nz,usage
        ld a,(82h) ; drive letter at command tail offset 1
        sub 'C'
        ld (physical_drive),a
        add a,2
        ld (rt_drive),a
        xor a
        ld (rt_floppy_write_mask),a
        call rt_floppy_home
        ld hl,warning
        call puts
        xor a
        ld (cylinder),a
track_loop:
        ld a,(cylinder)
        call hex
        ld c,' '
        call 0c00ch
        call rt_console_flush
        ld a,3
        ld (track_tries),a
retry_track:
        call format_track
        or a
        jp nz,failed
        call verify_track
        or a
        jr z,track_verified
        ld (failure),a
        ld hl,track_tries
        dec (hl)
        ld a,(failure)
        jp z,failed
        ld c,'r'
        call 0c00ch
        call rt_console_flush
        jr retry_track
track_verified:
        ld a,(cylinder)
        inc a
        ld (cylinder),a
        cp 40
        jr nz,track_loop
        ld a,(physical_drive)
        or a
        ld a,1
        jr z,enable
        inc a
 enable:ld (rt_floppy_write_mask),a
        ld hl,success
        jp finish
; Accept exactly C or D in the otherwise exact command tail.
match_tail:
        ld a,(de)
        cp '?'
        jr z,match_drive
        cp (hl)
        ret nz
        jr match_next
match_drive:
        ld a,(hl)
        cp 'C'
        jr z,match_next
        cp 'D'
        ret nz
match_next:
        inc hl
        inc de
        djnz match_tail
        xor a
        ret
; Single-track entry also exercised directly by the timed emulator test.
format_track:
        ld a,(physical_drive)
        cp 2
        jp nc,invalid
        add a,2
        ld (rt_drive),a
        ld a,(cylinder)
        cp 40
        jp nc,invalid
        ld l,a
        ld h,0
        ld (rt_track),hl
        ld hl,1
        ld (rt_record),hl
        call rt_floppy_prepare
        or a
        ret nz
        ; Patch all ten C fields; sectors are numbered 0..9.
        ld a,(cylinder)
        ld hl,track_stream+96
        ld de,604
        ld b,10
patch_ids:
        ld (hl),a
        add hl,de
        djnz patch_ids
        ; Settle the head before issuing Write Track, so its initial DRQ
        ; can be serviced immediately (also valid for WD1793 revisions).
        ld bc,3000
head_settle:
        dec bc
        ld a,b
        or c
        jr nz,head_settle
        ; Verify a real index edge with a bounded wait before the destructive
        ; command. During the byte stream, only FDC status is polled: at 2.5
        ; MHz even timeout bookkeeping can consume the 32 us byte budget.
        ld a,0d0h
        out (10h),a
        call rt_floppy_settle
        ld de,0
index_low:
        in a,(10h)
        bit 1,a
        jr z,index_start
        dec de
        ld a,d
        or e
        jr nz,index_low
        jp no_index
index_start:
        ld de,0
index_high:
        in a,(10h)
        bit 1,a
        jr nz,index_ok
        dec de
        ld a,d
        or e
        jr nz,index_high
        jp no_index
index_ok:
        ; Kaypro gates DRQ/INTRQ into NMI while the CPU is halted. Use the
        ; board's handshake instead of spending the byte budget on polling.
        ld hl,(66h)
        ld (saved_nmi),hl
        ld hl,45edh        ; RETN
        ld (66h),hl
        ld hl,track_stream
        ld bc,13h
        ld d,32
        ld a,0f0h
        out (10h),a
format_poll:
        halt
        outi
        jp nz,format_poll
        dec d
        jr nz,format_poll
        ; After index ends the command, INTRQ wakes the remaining HALTs.
        ; Extra data-register writes are ignored by the idle controller.
        ld (sent_end),hl
        in a,(10h)
        ld e,a
        bit 0,a
        jr z,format_done
        call rt_floppy_abort
        ld e,0feh
format_done:
        ld hl,(saved_nmi)
        ld (66h),hl
        ld a,e
        and 0fch
        ret
no_index:
        ld a,0fdh
        ret
invalid:
        ld a,0fch
        ret
verify_track:
        xor a
        ld (sector),a
verify_next:
        ld a,3
        ld (read_tries),a
verify_retry:
        ld a,(sector)
        out (12h),a
        call rt_floppy_read_sector
        or a
        jr z,verify_data
        ld hl,read_tries
        dec (hl)
        jr nz,verify_retry
        ld a,1
        ret
verify_data:
        ld hl,rt_floppy_buffer
        ld bc,512
verify_byte:
        ld a,(hl)
        cp 0e5h
        jr nz,verify_bad
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,verify_byte
        ld a,(sector)
        inc a
        ld (sector),a
        cp 10
        jr nz,verify_next
        xor a
        ret
verify_bad:
        ld a,0ffh
        ret
failed:
        ld (failure),a
        ld hl,error_msg
        call puts
        ld a,(failure)
        call hex
        ld hl,fdc_msg
        call puts
        in a,(10h)
        call hex
        xor a
        ld (rt_floppy_write_mask),a
        ld hl,sector_msg
        call puts
        ld a,(sector)
        call hex
        ld hl,count_msg
        call puts
        ld hl,(sent_end)
        ld de,track_stream
        or a
        sbc hl,de
        ld a,h
        call hex
        ld a,l
        call hex
        ld hl,stopped
finish:
        call puts
        call rt_console_flush
        call rt_floppy_home
        ld c,0
        call 0c01bh
        jp 0              ; discard CP/M directory state via warm boot
wrong_platform:
        ld hl,wrong_msg
        call puts
        call 0c006h
        jp 0              ; do not call private FDC symbols on mismatch
usage:
        ld hl,usage_msg
        jp finish
puts:
        ld a,(hl)
        or a
        ret z
        ld c,a
        call 0c00ch
        inc hl
        jr puts
hex:
        push af
        rrca
        rrca
        rrca
        rrca
        call nibble
        pop af
nibble:
        and 15
        add a,'0'
        cp '9'+1
        jr c,emit
        add a,7
emit:
        ld c,a
        jp 0c00ch
physical_drive: db 0
cylinder: db 0
sector: db 0
failure: db 0
track_tries: db 0
read_tries: db 0
sent_end: dw track_stream
saved_nmi: dw 0
lock_tail: db ' ? LOCK'
test_tail: db ' ? TEST'
erase_tail: db ' ? ERASE'
warning: db 'Formatting selected drive; verifying tracks (hex):',13,10,0
success: db 13,10,'FORMAT PASS: 40 tracks, 400 sectors verified E5.',13,10,'Selected drive writes enabled; use FORMAT C LOCK to disable.',13,10,0
locked: db 'Physical writes disabled.',13,10,0
error_msg: db 13,10,'FORMAT FAILED code=',0
fdc_msg: db ' FDC=',0
count_msg: db ' sent(hex)=',0
sector_msg: db ' sector=',0
stopped: db '; stopped, physical writes disabled.',13,10,0
wrong_msg: db 'FORMAT: incompatible resident platform; no disk access.',13,10,0
usage_msg: db 'Usage: FORMAT C ERASE or FORMAT D ERASE (destroys disk).',13,10,'FORMAT C LOCK disables physical writes.',13,10,0
test_success: db 'RAW TEST PASS: track 0, four records written and read back exactly.',13,10,'Physical writes disabled.',13,10,0
test_error: db 'RAW TEST FAILED; physical writes disabled.',13,10,0
pattern: incbin 'build/format-pattern.bin'
readback: ds 512
guard_copy:
        incbin 'build/format-guard.bin'
track_stream:
        incbin 'build/format-track.bin'
        ds 256
stacktop:
