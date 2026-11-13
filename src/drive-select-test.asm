; MIT. PC81-240A LED check. No FDC commands, seeks, reads, or writes.
; Bound to the current platform by the same immutable-code guard as FORMAT.
        include "build/format-bindings.inc"
        org 100h
        jp start
start:  di
        ld sp,stacktop
        ld hl,guard_address
        ld de,guard_copy
        ld bc,guard_length
check:  ld a,(de)
        cp (hl)
        jp nz,mismatch
        inc hl
        inc de
        dec bc
        ld a,b
        or c
        jr nz,check
        xor a
        ld (rt_floppy_write_mask),a
        ld a,2
        ld (rounds),a
round:  call select_none
        ld hl,off_msg
        call puts
        ld b,30
        call delay
        call select_c
        ld hl,c_msg
        call puts
        ld b,100
        call delay
        call select_none
        ld hl,off_msg
        call puts
        ld b,30
        call delay
        call select_d
        ld hl,d_msg
        call puts
        ld b,100
        call delay
        ld hl,rounds
        dec (hl)
        jr nz,round
        call select_none
        ld hl,done_msg
        call puts
        jp 0
select_c:
        ld a,(rt_system_latch)
        and 0bch
        or 1
        jr apply
select_d:
        ld a,(rt_system_latch)
        and 0bch
        or 2
        jr apply
select_none:
        ld a,(rt_system_latch)
        and 0fch
        or 40h
apply:  ld (rt_system_latch),a
        out (1ch),a
        ret
; ~10.4 seconds for B=100 at 2.5 MHz. No console polling that idles motors.
delay: push bc
        ld de,10000
wait:   dec de
        ld a,d
        or e
        jr nz,wait
        pop bc
        djnz delay
        ret
puts:   ld a,(hl)
        or a
        jp z,rt_console_flush
        ld c,a
        call 0c00ch
        inc hl
        jr puts
mismatch:
        ld hl,bad_msg
bad_loop:
        ld a,(hl)
        or a
        jr z,bad_end
        ld c,a
        call 0c00ch
        inc hl
        jr bad_loop
bad_end:
        call 0c006h
        jp 0
rounds: db 0
off_msg: db 13,10,'LED CHECK: both deselected, motors off (3 seconds)',13,10,0
c_msg: db 'LED CHECK: C selected, motor on (10 seconds)',13,10,0
d_msg: db 'LED CHECK: D selected, motor on (10 seconds)',13,10,0
done_msg: db 'LED CHECK DONE: both deselected; physical writes disabled.',13,10,0
bad_msg: db 'Incompatible resident platform; no drive access.',13,10,0
guard_copy: incbin 'build/format-guard.bin'
        ds 128
stacktop:
