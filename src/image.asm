; MIT. IMAGE C ERASE: B:KAYPRO.IMG -> all C sectors, immediate read/compare.
; IMAGE C READ: all C sectors -> B:READBACK.IMG (must not already exist).
; Fixed SSDD geometry; exact resident code guard; no D write path.
        include "build/image-bindings.inc"
        org 100h
        jp start
start:  ld sp,stacktop
        di
        ld hl,guard_address
        ld de,guard_copy
        ld bc,guard_length
guard:  ld a,(de)
        cp (hl)
        jp nz,badguard
        inc hl
        inc de
        dec bc
        ld a,b
        or c
        jr nz,guard
        xor a
        ld (rt_floppy_write_mask),a
        ld (mode),a
        ld (cylinder),a
        ld (failure),a
        ld a,(80h)
        cp 8
        jr nz,parse_read
        ld hl,81h
        ld de,erase_tail
        ld b,8
        call match
        jp nz,usage
        ld de,fcb
        ld c,35
        call 5
        or a
        jp nz,file_error
        ld hl,(fcb+33)
        ld de,1600
        or a
        sbc hl,de
        jp nz,file_error
        ld a,(fcb+35)
        or a
        jp nz,file_error
        ld de,fcb
        ld c,15
        call 5
        inc a
        jp z,file_error
        jr begin
parse_read:
        cp 7
        jp nz,usage
        ld hl,81h
        ld de,read_tail
        ld b,7
        call match
        jp nz,usage
        ld a,1
        ld (mode),a
        ld hl,read_name
        ld de,fcb+1
        ld bc,11
        ldir
        ld de,fcb
        ld c,15
        call 5
        inc a
        jp nz,file_error
        ld de,fcb
        ld c,22
        call 5
        inc a
        jp z,file_error
begin:  call rt_floppy_home
next_track:
        ld hl,track_text
        call puts
        ld a,(cylinder)
        call hex
        ld hl,newline
        call puts
        ld a,(mode)
        or a
        jr nz,read_track
        call file_track
        or a
        jp nz,file_error
        call save_disk
        call write_track
        push af
        call restore_disk
        pop af
        or a
        jp nz,disk_error
        jr advance
read_track:
        call save_disk
        call read_track_raw
        push af
        call restore_disk
        pop af
        or a
        jp nz,disk_error
        call file_track
        or a
        jp nz,file_error
advance:
        ld a,(cylinder)
        inc a
        ld (cylinder),a
        cp 40
        jr nz,next_track
        ld de,fcb
        ld c,16
        call 5
        inc a
        jp z,file_error
        ld hl,success
        jp finish
; Sequential 40 records to/from 5120-byte track buffer through BDOS.
file_track:
        ld hl,buffer
        ld (file_ptr),hl
        ld a,40
        ld (remaining),a
file_loop:
        ld de,(file_ptr)
        ld c,26
        call 5
        ld a,(mode)
        add a,20
        ld c,a
        ld de,fcb
        call 5
        or a
        ret nz
        ld hl,(file_ptr)
        ld de,128
        add hl,de
        ld (file_ptr),hl
        ld hl,remaining
        dec (hl)
        jr nz,file_loop
        xor a
        ret
; Save/restore the resident BIOS selection across direct physical I/O.
save_disk:
        ld a,(rt_drive)
        ld (saved_drive),a
        ld hl,(rt_track)
        ld (saved_track),hl
        ld hl,(rt_record)
        ld (saved_record),hl
        ld hl,(rt_dma)
        ld (saved_dma),hl
        ret
restore_disk:
        ld a,(saved_drive)
        ld (rt_drive),a
        ld hl,(saved_track)
        ld (rt_track),hl
        ld hl,(saved_record)
        ld (rt_record),hl
        ld hl,(saved_dma)
        ld (rt_dma),hl
        ret
init_track:
        ld a,(cylinder)
        cp 40
        jr nc,raw_bad
        ld l,a
        ld h,0
        ld (rt_track),hl
        ld a,2
        ld (rt_drive),a
        ld hl,1
        ld (rt_record),hl
        ld hl,buffer
        ld (sector_ptr),hl
        xor a
        ret
raw_bad:ld a,1
        or a
        ret
write_track:
        call init_track
        ret nz
write_sector:
        call rt_floppy_prepare
        or a
        ret nz
        ld hl,(sector_ptr)
        ld de,rt_floppy_buffer
        ld bc,512
        ldir
        call rt_floppy_nmi_begin
        ld hl,rt_floppy_buffer
        ld bc,13h
        ld d,2
        ld a,0a0h
        out (10h),a
        call rt_floppy_write_loop
        or a
        ret nz
        call rt_floppy_read_sector
        or a
        ret nz
        ld hl,(sector_ptr)
        ld de,rt_floppy_buffer
        ld bc,512
compare:
        ld a,(de)
        cp (hl)
        jr nz,raw_bad
        inc hl
        inc de
        dec bc
        ld a,b
        or c
        jr nz,compare
        call next_sector
        jr c,write_sector
        xor a
        ret
read_track_raw:
        call init_track
        ret nz
read_sector:
        call rt_floppy_prepare
        or a
        ret nz
        call rt_floppy_read_sector
        or a
        ret nz
        ld hl,rt_floppy_buffer
        ld de,(sector_ptr)
        ld bc,512
        ldir
        call next_sector
        jr c,read_sector
        xor a
        ret
next_sector:
        ld hl,(sector_ptr)
        ld de,512
        add hl,de
        ld (sector_ptr),hl
        ld hl,(rt_record)
        ld de,4
        add hl,de
        ld (rt_record),hl
        ld a,l
        cp 41
        ret
match:  ld a,(de)
        cp (hl)
        ret nz
        inc de
        inc hl
        djnz match
        ret
puts:   ld a,(hl)
        or a
        ret z
        inc hl
        push hl
        ld c,a
        call 0c00ch
        pop hl
        jr puts
hex:    push af
        rrca
        rrca
        rrca
        rrca
        call nibble
        pop af
nibble: and 15
        add a,'0'
        cp '9'+1
        jr c,emit
        add a,7
emit:   ld c,a
        jp 0c00ch
file_error:
        ld hl,file_msg
        jr failed
disk_error:
        ld hl,disk_msg
        jr failed
usage:  ld hl,usage_msg
failed: ld a,1
        ld (failure),a
finish: push hl
        xor a
        ld (rt_floppy_write_mask),a
        call rt_floppy_home
        pop hl
        call puts
        call rt_console_flush
        jp 0
badguard:
        ld hl,guard_msg
        call puts
        jp 0
mode: db 0
failure: db 0
cylinder: db 0
remaining: db 0
file_ptr: dw 0
sector_ptr: dw 0
saved_drive: db 0
saved_track: dw 0
saved_record: dw 0
saved_dma: dw 0
fcb: db 2,'KAYPRO  IMG'
        ds 24
read_name: db 'READBACKIMG'
erase_tail: db ' C ERASE'
read_tail: db ' C READ'
track_text: db 'Track ',0
newline: db 13,10,0
success: db 'IMAGE complete; physical writes disabled.',13,10,0
file_msg: db 'IMAGE file error (source must be 204800 bytes; readback must be new).',13,10,0
disk_msg: db 'IMAGE disk/compare error; stopped. Disk may be incomplete.',13,10,0
usage_msg: db 'IMAGE C ERASE or IMAGE C READ',13,10,0
guard_msg: db 'IMAGE resident driver mismatch.',13,10,0
guard_copy: incbin 'build/image-guard.bin'
        ds 256
stacktop:
; Above COM + below CP/M TPA ceiling; not part of on-disk program.
buffer: equ 6000h
