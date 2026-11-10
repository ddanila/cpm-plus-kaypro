; MIT. CP/M transient exercising the documented Kaypro II terminal controls.
        org 100h
        ld hl,sequence
        ld bc,sequence_end-sequence
next:   ld e,(hl)
        push hl
        push bc
        ld c,2
        call 5
        pop bc
        pop hl
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,next
        jp 0
sequence:
        db 26,'Kaypro terminal qualification',13,10
        db '0123456789',8,'X',12,'Y',9,'TAB',13,10
        db 27,'=',34,37,'addressed',24
        db 27,'=',33,32,27,'E','inserted'
        db 27,'=',35,32,27,'R'
        db 27,'=',37,32,27,'G','abcdefgh',27,'A','abcdefgh'
        db 27,'=',38,32,'erase this',27,'=',38,32,23
        db 30,11,8,27,'=',40,32,'SCREEN PASS',13,10
sequence_end:
