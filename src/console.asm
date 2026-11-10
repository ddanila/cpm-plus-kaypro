; MIT. PC81-240A local console. Code, state and stack must be above 3FFF.
; Logical video rows have stride 128; only columns 0..79 are displayed.
; All guest console calls preserve registers; C contains the character.
local_init:
        xor a
        ld (vrow),a
        ld (vcol),a
        ld (vescape),a
        ld (vgreek),a
        ld (vcursor),a
        ld c,26
        jp localout
localout:
        push af
        push bc
        push de
        push hl
        ld a,i
        di
        push af
        ld (video_caller_sp),sp
        ld sp,video_stack_top
        ld a,(system_latch)
        push af
        or 80h
        out (1ch),a
        call cursor_hide
        call video_char
        call cursor_show
        pop af
        out (1ch),a
        ld sp,(video_caller_sp)
        pop af
        jp po,video_restore
        ei
video_restore:
        pop hl
        pop de
        pop bc
        pop af
        ret
video_address:
        ld a,(vrow)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,(vcol)
        ld e,a
        ld d,30h
        add hl,de
        ret
cursor_hide:
        ld a,(vcursor)
        or a
        ret z
        call video_address
        ld a,(vsaved)
        ld (hl),a
        xor a
        ld (vcursor),a
        ret
cursor_show:
        call video_address
        ld a,(hl)
        ld (vsaved),a
        xor 80h
        ld (hl),a
        ld a,1
        ld (vcursor),a
        ret
video_char:
        ld a,(vescape)
        or a
        jr z,video_normal
        cp 1
        jp z,video_escape
        cp 2
        jr z,video_row
        xor a
        ld (vescape),a
        ld a,c
        sub 32
        cp 80
        ret nc
        ld (vcol),a
        ld a,(vpendingrow)
        ld (vrow),a
        ret
video_row:
        ld a,c
        sub 32
        cp 24
        jr nc,escape_cancel
        ld (vpendingrow),a
        ld a,3
        ld (vescape),a
        ret
video_escape:
        xor a
        ld (vescape),a
        ld a,c
        cp '='
        jr z,escape_position
        cp 'A'
        jr z,escape_latin
        cp 'G'
        jr z,escape_greek
        cp 'E'
        jp z,video_insert
        cp 'R'
        jp z,video_delete
        ret
escape_position:
        ld a,2
        ld (vescape),a
        ret
escape_latin:
        xor a
        ld (vgreek),a
        ret
escape_greek:
        ld a,1
        ld (vgreek),a
        ret
escape_cancel:
        xor a
        ld (vescape),a
        ret
video_normal:
        ld a,c
        cp 27
        jp z,video_esc
        cp 7
        jp z,keyboard_bell
        cp 8
        jr z,video_left
        cp 9
        jr z,video_tab
        cp 10
        jp z,video_down
        cp 11
        jr z,video_up
        cp 12
        jr z,video_right
        cp 13
        jr z,video_cr
        cp 23
        jp z,video_eos
        cp 24
        jp z,video_eol
        cp 26
        jp z,video_clear
        cp 30
        jp z,video_home
        ; Unassigned control bytes retain the character-ROM glyph semantics.
        call video_address
        ld a,(vgreek)
        or a
        ld a,c
        jr z,video_store
        cp 60h
        jr c,video_store
        cp 80h
        jr nc,video_store
        sub 60h
video_store:
        ld (hl),a
video_right:
        ld a,(vcol)
        inc a
        cp 80
        jr c,video_setcol
        xor a
        ld (vcol),a
        jp video_down
video_setcol:
        ld (vcol),a
        ret
video_cr:
        xor a
        jr video_setcol
video_left:
        ld a,(vcol)
        or a
        ret z
        dec a
        jr video_setcol
video_up:
        ld a,(vrow)
        or a
        ret z
        dec a
        ld (vrow),a
        ret
video_tab:
        ld a,(vcol)
        add a,8
        and 0f8h
        cp 80
        jr c,video_setcol
        xor a
        ld (vcol),a
        jp video_down
video_esc:
        ld a,1
        ld (vescape),a
        ret
video_down:
        ld a,(vrow)
        inc a
        cp 24
        jr c,video_setrow
        ; Scroll while retaining cursor column.
        ld a,(vcol)
        push af
        xor a
        ld (vrow),a
        call video_delete
        ld a,23
        ld (vrow),a
        pop af
        ld (vcol),a
        ret
video_setrow:
        ld (vrow),a
        ret
video_home:
        xor a
        ld (vrow),a
        ld (vcol),a
        ret
video_clear:
        call video_home
video_eos:
        call video_eol
        ld a,(vrow)
        inc a
video_clear_rows:
        cp 24
        ret nc
        push af
        call video_row_address
        call video_blank_row
        pop af
        inc a
        jr video_clear_rows
video_eol:
        call video_address
        ld a,(vcol)
        ld b,a
        ld a,80
        sub b
        ld b,a
        jr video_blank
video_blank_row:
        ld b,80
video_blank:
        ld (hl),32
        inc hl
        djnz video_blank
        ret
; A row -> HL first cell, preserving BC.
video_row_address:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,3000h
        add hl,de
        ret
video_delete:
        ld a,(vrow)
video_delete_next:
        cp 23
        jr z,video_last_blank
        push af
        call video_row_address
        push hl
        ld de,128
        add hl,de
        pop de
        ld bc,80
        ldir
        pop af
        inc a
        jr video_delete_next
video_last_blank:
        call video_row_address
        jp video_blank_row
video_insert:
        ld a,23
video_insert_next:
        ld b,a
        ld a,(vrow)
        cp b
        jr z,video_last_blank
        ld a,b
        push af
        dec a
        call video_row_address
        push hl
        ld de,128
        add hl,de
        ex de,hl
        pop hl
        ld bc,80
        ldir
        pop af
        dec a
        jr video_insert_next
system_latch: db 40h
vrow: db 0
vcol: db 0
vescape: db 0
vpendingrow: db 0
vgreek: db 0
vcursor: db 0
vsaved: db 32

video_caller_sp: dw 0
video_stack: ds 64
video_stack_top:
