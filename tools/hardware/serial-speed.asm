; MIT. CP/M transient: SPEED <selector hex> <WR4 hex>.
; Direct SIO A test. Leaves keyboard alone; restores 19200 8O1 on all paths.
; 512-byte ascending TX pattern, 4096-byte RX then echo. Receive polls and
; individual TX waits are bounded. At baseline emit KEND/count/errors until
; host sends !, then delay and warm boot. No ROM writes or reset required.
        org 100h
        ld hl,81h
        call hexbyte
        ld (selector),a
        call hexbyte
        ld (format),a
        ld de,ready
        ld c,9
        call 5
        di
        ld sp,8000h
        ld b,4
        call pause
        ld a,(selector)
        ld c,a
        ld a,(format)
        call setup
        ld hl,0
        ld (count),hl
        xor a
        ld (errors),a
        ld bc,512
pattern:
        ld a,c
        neg
        call tx
        jp c,restore
        dec bc
        ld a,b
        or c
        jr nz,pattern
        ld hl,4000h
        ld bc,4096
        ld de,0
        ld a,8
        ld (budget),a
receive:
        ; Every poll consumes budget, including received bytes.
        dec de
        ld a,d
        or e
        jr nz,poll
        ld a,(budget)
        dec a
        ld (budget),a
        jp z,restore
poll:   in a,(6)
        and 1
        jr z,receive
        ld a,1
        out (6),a
        in a,(6)
        and 70h
        push hl
        ld hl,errors
        or (hl)
        ld (hl),a
        pop hl
        in a,(4)
        ld (hl),a
        inc hl
        ld a,30h
        out (6),a
        push hl
        ld hl,(count)
        inc hl
        ld (count),hl
        pop hl
        dec bc
        ld a,b
        or c
        jr nz,receive
        ld hl,4000h
        ld bc,4096
send_echo:
        ld a,(hl)
        call tx
        jp c,restore
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,send_echo
restore:
        ld b,1
        call pause
        ld c,15
        ld a,45h
        call setup
        ld a,32
        ld (budget),a
report:
        ld hl,tag
        ld b,4
report_tag:
        ld a,(hl)
        call tx
        inc hl
        djnz report_tag
        ld hl,(count)
        ld a,l
        call tx
        ld a,h
        call tx
        ld a,(errors)
        call tx
        ld de,0
wait_ack:
        in a,(6)
        and 1
        jr z,wait_tick
        in a,(4)
        cp '!'
        jr z,finish
wait_tick:
        dec de
        ld a,d
        or e
        jr nz,wait_ack
        ld a,(budget)
        dec a
        ld (budget),a
        jr nz,report
finish:
        ld b,4
        call pause
        jp 0
setup:  push af
        xor a
        out (6),a
        ld a,18h
        out (6),a
        ld a,c
        out (0),a
        ld a,4
        out (6),a
        pop af
        out (6),a
        ld a,1
        out (6),a
        xor a
        out (6),a
        ld a,3
        out (6),a
        ld a,0c1h
        out (6),a
        ld a,5
        out (6),a
        ld a,0eah
        out (6),a
        ret
tx:     push af
        push de
        ld de,0
tx_poll:in a,(6)
        and 4
        jr nz,tx_ready
        dec de
        ld a,d
        or e
        jr nz,tx_poll
        pop de
        pop af
        scf
        ret
tx_ready:
        pop de
        pop af
        out (4),a
        or a
        ret
pause:  ld de,0
pause_inner:
        dec de
        ld a,d
        or e
        jr nz,pause_inner
        djnz pause
        ret
hexbyte:
        ld a,(hl)
        inc hl
        cp ' '
        jr z,hexbyte
        call nibble
        rlca
        rlca
        rlca
        rlca
        ld c,a
        ld a,(hl)
        inc hl
        call nibble
        or c
        ret
nibble:
        sub '0'
        cp 10
        ret c
        sub 7
        ret
ready:  db 'SPEED READY',13,10,'$'
tag:    db 'KEND'
selector: db 15
format: db 45h
budget: db 0
count:  dw 0
errors: db 0
