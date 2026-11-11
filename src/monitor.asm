; MIT. V3 local monitor. All mutable diagnostic storage is outside the ROM.
link_baud equ 9000h
link_format equ 9001h
m_mode equ 9002h
m_saved equ 9003h
m_tick equ 9005h
m_index equ 9007h
m_pending equ 9009h
m_expected equ 900ah
m_timeout equ 900bh
m_repeat equ 900dh
m_sweep equ 900eh
m_rxcount equ 9010h
m_txcount equ 9012h
m_bad equ 9014h
m_errors equ 9016h
m_rr0 equ 9017h
m_rr1 equ 9018h
m_head equ 9019h
m_tail equ 901ah
m_count equ 901bh
m_drops equ 901ch
m_scan equ 901eh
m_first equ 901fh
m_nonce equ 9020h
m_refresh equ 9024h
m_rounds equ 9025h
m_buffer equ 9100h
m_packet equ 9200h
monitor_init:
        ld hl,9000h
        ld de,9001h
        ld bc,02ffh
        ld (hl),0
        ldir
        call link_defaults
        call link_init
        ; Independent B setup, 300 8N1, polling only.
        xor a
        out (7),a
        ld a,18h
        out (7),a
        ld a,5
        out (0ch),a
        ld hl,m_keyboard_init
        ld b,8
        ld c,7
        otir
        call local_init
        ld hl,boot_waiting
        call boot_print
        jp m_show
m_keyboard_init: db 4,44h,1,0,3,0c1h,5,0eah
; Approximately 1ms; diagnostics poll keys every iteration, including waits.
m_delay:
        ld b,180
md_loop:djnz md_loop
        ret
m_key:
        in a,(7)
        and 1
        ret z
        in a,(5)
        or a
        ret
monitor_poll:
        call m_key
        call nz,m_command
        ld a,(m_mode)
        or a
        jr z,m_boot
        cp 6
        jp nc,m_scan_poll
        cp 3
        jp z,m_test
        cp 4
        jp z,m_test
        cp 2
        call z,m_capture
        call m_delay
        ld hl,m_refresh
        inc (hl)
        ld a,(hl)
        and 63
        call z,m_status
        scf
        ret
m_boot: in a,(6)
        and 1
        jp z,m_none
        in a,(4)
        cp 7eh
        jp z,m_protocol
        push af
        ld hl,(m_rxcount)
        inc hl
        ld (m_rxcount),hl
        pop af
        or a
        ret
m_none: scf
        ret
m_command:
        ld c,a
        ld a,(m_mode)
        cp 5
        jr nz,mc_other
        ld a,c
        cp 27
        jr z,mc_boot
        push af
        ld hl,m_bytespos
        call boot_print
        pop af
        call m_hex
        ret
mc_other:
        ld a,c
        cp 27
        jr z,mc_boot
        cp 'a'
        jr c,mc_upper
        cp 'z'+1
        jr nc,mc_upper
        and 0dfh
mc_upper:
        ld c,a
        ld a,(m_mode)
        cp 1
        jp z,m_settings
        cp 8
        jp z,m_loop_choice
        ld a,c
        cp 'B'
        jr z,mc_boot
        cp 'D'
        jr nz,mc_i
        call link_defaults
mc_i:   cp 'I'
        jr z,mc_init
        ld a,c
        cp 'D'
        jr z,mc_init
        cp 'S'
        ld b,1
        jr z,mc_mode
        cp 'R'
        ld b,2
        jr z,mc_mode
        cp 'T'
        jr z,mc_tx
        cp 'L'
        jr z,mc_loop
        cp 'W'
        jr z,mc_sweep
        cp 'K'
        ld b,5
        jr z,mc_mode
        cp 'A'
        jp z,m_scan_start
        ret
mc_boot:
        call m_restore
        xor a
        ld (m_mode),a
mc_init:
        call link_init
        jp m_show
mc_tx:  ld a,1
        ld (m_repeat),a
        ld b,3
        jr mc_begin
mc_loop:
        ld b,8
        jr mc_mode
mc_sweep:
        ld hl,(link_baud)
        ld (m_saved),hl
        ld a,1
        ld (m_sweep),a
        ld a,5
        ld (link_baud),a
        ld a,(link_format)
        and 3fh
        or 40h
        ld (link_format),a
        call link_init
        xor a
        ld (m_repeat),a
        ld b,4
mc_begin:
        push bc
        call m_reset_counts
        pop bc
mc_mode:
        ld a,b
        ld (m_mode),a
        jp m_show
m_loop_choice:
        ld a,c
        cp 'O'
        jr z,ml_once
        cp 'C'
        ret nz
        ld a,1
        jr ml_start
ml_once:xor a
ml_start:
        ld (m_repeat),a
        ld b,4
        jr mc_begin
m_restore:
        ld a,(m_sweep)
        or a
        jr nz,m_restore_yes
        ld a,(m_mode)
        cp 6
        ret c
        cp 8
        ret nc
m_restore_yes:
        ld hl,(m_saved)
        ld (link_baud),hl
        xor a
        ld (m_sweep),a
        ret
m_reset_counts:
        ld hl,9007h
        ld de,9008h
        ld bc,29
        ld (hl),0
        ; Preserve repeat/sweep flags across counter reset.
        ld a,(m_repeat)
        push af
        ld a,(m_sweep)
        push af
        ldir
        pop af
        ld (m_sweep),a
        pop af
        ld (m_repeat),a
        ret
m_settings:
        ld a,c
        cp 'B'
        jp z,mc_boot
        cp '1'
        jr nz,ms_parity
        call m_nextbaud
        jr ms_apply
ms_parity:
        cp '2'
        jr nz,ms_stop
        ld a,(link_format)
        ld b,a
        and 3
        inc a
        cp 2
        jr nz,ms_p2
        inc a
ms_p2:  and 3
        ld c,a
        ld a,b
        and 0fch
        or c
        jr ms_fmt
ms_stop:cp '3'
        jr nz,ms_clock
        ld a,(link_format)
        xor 8
        jr ms_fmt
ms_clock:
        cp '4'
        ret nz
        ld a,(link_format)
        add a,40h
        jr c,ms_wrap
        jr ms_fmt
ms_wrap:or 40h
ms_fmt: ld (link_format),a
ms_apply:
        call link_init
        jp m_show
m_nextbaud:
        ld hl,m_bauds
        ld a,(link_baud)
        ld b,7
mn_loop:cp (hl)
        inc hl
        jr z,mn_found
        djnz mn_loop
mn_found:
        ld a,(hl)
        or a
        jr nz,mn_save
        ld a,5
mn_save:ld (link_baud),a
        ret
m_bauds:db 5,6,7,10,12,14,15,0
; Receiver status is sampled BEFORE consuming the associated FIFO byte.
m_read:
        in a,(6)
        ld (m_rr0),a
        and 1
        jp z,m_none
        ld a,1
        out (6),a
        in a,(6)
        ld (m_rr1),a
        and 70h
        ld b,a
        ld a,(m_errors)
        or b
        ld (m_errors),a
        in a,(4)
        push af
        ld a,30h
        out (6),a
        ld hl,(m_rxcount)
        inc hl
        ld (m_rxcount),hl
        pop af
        or a
        ret
m_capture:
        call m_read
        ret c
        ld c,a
        ld a,(m_count)
        cp 255
        jr z,m_drop
        inc a
        ld (m_count),a
        ld a,(m_tail)
        ld l,a
        ld h,91h
        ld (hl),c
        inc a
        ld (m_tail),a
        jr m_capture
m_drop: ld hl,(m_drops)
        inc hl
        ld (m_drops),hl
        jr m_capture
m_test:
        call m_delay
        ld a,(m_pending)
        or a
        jr z,mt_send
        call m_read
        jr c,mt_wait
        ld b,a
        ld a,(m_expected)
        cp b
        jr z,mt_done
        ld a,b
        ld (m_first),a
        jr mt_bad
mt_wait:ld hl,(m_timeout)
        dec hl
        ld (m_timeout),hl
        ld a,h
        or l
        jp nz,m_none
        ld a,0ffh
        ld (m_first),a
mt_bad: ld hl,(m_bad)
        inc hl
        ld (m_bad),hl
mt_done:xor a
        ld (m_pending),a
        call m_status
mt_send:
        ld hl,(m_index)
        ld de,260
        or a
        sbc hl,de
        jr z,mt_complete
        in a,(6)
        and 4
        jp z,m_none
        ld hl,(m_index)
        ld a,h
        or a
        jr nz,mt_value
        ld a,l
        cp 4
        jr nc,mt_value
        ld de,m_prefix
        add hl,de
        ld a,(hl)
        jr mt_out
mt_value:
        ld a,l
        sub 4
mt_out: ld (m_expected),a
        out (4),a
        ld hl,(m_txcount)
        inc hl
        ld (m_txcount),hl
        ld hl,(m_index)
        inc hl
        ld (m_index),hl
        ld a,(m_mode)
        cp 4
        jr nz,mt_finish
        ld a,1
        ld (m_pending),a
        ld hl,250
        ld (m_timeout),hl
mt_finish:
        scf
        ret
mt_complete:
        ld a,1
        out (6),a
        in a,(6)
        and 1
        jp z,m_none
        call m_status
        ld hl,m_pass
        ld a,(m_errors)
        ld b,a
        ld hl,(m_bad)
        ld a,h
        or l
        or b
        ld hl,m_pass
        jr z,mt_report
        ld hl,m_fail
mt_report:
        call boot_print
        ld a,(m_sweep)
        or a
        jr z,mt_repeat
        ld a,(link_baud)
        cp 15
        jr z,mt_end
        call m_nextbaud
        call link_init
        call m_reset_counts
        call m_show
        jp m_none
mt_repeat:
        ld a,(m_repeat)
        or a
        jr z,mt_end
        ld hl,0
        ld (m_index),hl
        jp m_none
mt_end: call m_restore
        call link_init
        ld a,1
        ld (m_mode),a
        jp m_none
m_prefix:db 55h,0aah,0,0ffh
m_pass: db ' PASS ',0
m_fail: db ' FAIL ',0
m_show:
        ld hl,m_home
        call boot_print
        ld a,(m_mode)
        call m_hex
        ld hl,m_configtext
        call boot_print
        ld a,(link_baud)
        call m_hex
        ld a,(link_format)
        call m_hex
        ld hl,m_options
        call boot_print
        call m_description
        call m_status
        ret
m_home: db 27,'=',40,32,24,'Mode ',0
m_configtext:db '  Shadows BAUD/WR4 (WR1=00 WR3=C1 WR5=EA): ',0
m_options:db 13,10,24,'Settings: 1 Baud 2 N/O/E 3 Stop 4 Clock. B Boot ESC Back',13,10
        db 24,'Loop: disconnect host, bridge DB25 2-3. O Once / C Continuous',13,10
        db 24,'Loop verifies bytes, NOT absolute baud. Counts are hex modulo 65536.',13,10,0
m_status:
        ld hl,m_statuspos
        call boot_print
        ld hl,m_rxcount
        ld b,3
mst_words:
        push bc
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push hl
        ld a,d
        call m_hex
        ld a,e
        call m_hex
        pop hl
        pop bc
        djnz mst_words
        ld hl,(m_drops)
        ld a,h
        call m_hex
        ld a,l
        call m_hex
        in a,(6)
        ld (m_rr0),a
        call m_hex
        ld a,1
        out (6),a
        in a,(6)
        call m_hex
        ld a,(m_errors)
        call m_hex
        ld a,(m_first)
        call m_hex
        call m_flags
        ld a,(m_mode)
        cp 2
        ret nz
        ld hl,m_bytespos
        call boot_print
        ld b,16
mst_byte:
        push bc
        call m_capture
        ld a,(m_count)
        or a
        jr z,mst_empty
        dec a
        ld (m_count),a
        ld a,(m_head)
        ld l,a
        ld h,91h
        inc a
        ld (m_head),a
        ld a,(hl)
        call m_hex
mst_empty:
        pop bc
        djnz mst_byte
        ret
m_statuspos:db 27,'=',45,32,24,'RX TX BAD DROP RR0 RR1 ERR FIRST: ',0
m_bytespos:db 27,'=',47,32,24,0
m_hex:  push af
        rrca
        rrca
        rrca
        rrca
        call mh_digit
        pop af
        call mh_digit
        ld c,' '
        call localout
        jp m_service
mh_digit:
        and 15
        add a,'0'
        cp '9'+1
        jr c,mh_put
        add a,7
mh_put: ld c,a
        call localout
        jp m_service
; Explicit scan mode only; no K/G boot interpretation during discovery.
m_scan_start:
        ld hl,(link_baud)
        ld (m_saved),hl
        xor a
        ld (m_scan),a
        ld a,15
        ld (m_rounds),a
        ld a,6
        ld (m_mode),a
        call m_scan_set
        jp m_show
m_scan_set:
        ld a,(m_scan)
        ld hl,m_scan_profiles
        add a,a
        ld e,a
        ld d,0
        add hl,de
        ld a,(hl)
        ld (link_baud),a
        inc hl
        ld a,(hl)
        ld (link_format),a
        ld hl,2000
        ld (m_tick),hl
        jp link_init
m_scan_profiles:db 14,44h,14,45h,14,47h,15,44h,15,45h,15,47h
m_scan_poll:
        ld a,(m_mode)
        cp 8
        jp z,m_none
        cp 9
        jp z,msp_rx
        call m_delay
        ld hl,(m_tick)
        dec hl
        ld (m_tick),hl
        ld a,h
        or l
        jr nz,msp_rx
        ld a,(m_mode)
        cp 7
        jr z,msp_resume
        ld a,(m_scan)
        inc a
        cp 6
        jr c,msp_next
        ld hl,m_rounds
        dec (hl)
        jr nz,msp_again
        call mc_boot
        jp m_none
msp_again:
        xor a
msp_next:
        ld (m_scan),a
msp_resume:
        ld a,6
        ld (m_mode),a
        call m_scan_set
msp_rx: in a,(6)
        and 1
        jp z,m_none
        in a,(4)
        cp 7eh
        jp nz,m_none
; Frame: ~D3, payload length, command, nonce[4], payload, CRC high/low.
; Response: ~R3, length, command, nonce[4], [selector,WR4,version 3,0,0], CRC.
m_protocol:
        call rx
        jp c,m_none
        cp 'D'
        jp nz,m_none
        call rx
        jp c,m_none
        cp '3'
        jp nz,m_none
        call rx
        jp c,m_none
        or a                ; V3 commands have no request payload
        jp nz,m_none
        ld hl,m_packet
        ld (hl),a
        inc hl
        ld b,5
mp_read:push bc
        push hl
        call rx
        pop hl
        pop bc
        jp c,m_none
        ld (hl),a
        inc hl
        djnz mp_read
        ld hl,m_packet
        ld de,6
        call link_crc
        call rx
        jp c,m_none
        cp b
        jp nz,m_none
        call rx
        jp c,m_none
        cp c
        jp nz,m_none
        ld a,(m_packet+1)
        cp 'Q'              ; report selected configuration
        jr z,mp_reply
        cp 'P'              ; scan probe, temporarily lock
        jr nz,mp_confirm
        ld a,(m_mode)
        cp 6
        jp nz,m_none
        ld hl,m_packet+2
        ld de,m_nonce
        ld bc,4
        ldir
        ld a,7
        ld (m_mode),a
        ld hl,2000
        ld (m_tick),hl
        jr mp_reply
mp_confirm:
        cp 'C'
        jr nz,mp_boot
        ld a,(m_mode)
        cp 7
        jr z,mp_cvalid
        cp 9
        jp nz,m_none
mp_cvalid:
        ld hl,m_packet+2
        ld de,m_nonce
        ld b,4
mp_match:
        ld a,(de)
        cp (hl)
        jp nz,m_none
        inc hl
        inc de
        djnz mp_match
        ld a,9              ; confirmed, no scan timeout
        ld (m_mode),a
        jr mp_reply
mp_boot:cp 'X'
        jr nz,mp_bcommand
        call m_restore
        call link_init
mp_bcommand:
        ld a,(m_packet+1)
        cp 'X'
        jr z,mp_breturn
        cp 'B'
        jp nz,m_none
mp_breturn:
        xor a
        ld (m_mode),a
mp_reply:
        ld a,7eh
        call tx
        ld a,'R'
        call tx
        ld a,'3'
        call tx
        ld a,5
        ld (m_packet),a
        ld hl,(link_baud)
        ld (m_packet+6),hl
        ld a,3
        ld (m_packet+8),a
        xor a
        ld (m_packet+9),a
        ld (m_packet+10),a
        ld hl,m_packet
        ld de,11
        call link_crc
        push bc
        ld hl,m_packet
        ld b,11
mp_send:ld a,(hl)
        call tx
        inc hl
        djnz mp_send
        pop bc
        ld a,b
        call tx
        ld a,c
        call tx
        jp m_none

; Service RX between displayed characters rather than blocking on CRT output.
m_service:
        push af
        ld a,(m_mode)
        cp 2
        jr nz,msvc_done
        push bc
        push de
        push hl
        call m_capture
        pop hl
        pop de
        pop bc
msvc_done:
        pop af
        ret
m_description:
        ld hl,m_descpos
        call boot_print
        ld hl,m_nominal
        call m_rate
        ld hl,m_actualtext
        call boot_print
        ld hl,m_actual
        call m_rate
        ld hl,m_frametext
        call boot_print
        ld a,(link_format)
        and 3
        ld c,'N'
        jr z,m_descpar
        ld c,'O'
        cp 1
        jr z,m_descpar
        ld c,'E'
m_descpar:
        call localout
        ld a,(link_format)
        and 8
        ld c,'1'
        jr z,m_descstop
        inc c
m_descstop:
        call localout
        ld hl,m_clocktext
        call boot_print
        ld a,(link_format)
        and 0c0h
        ld hl,16
        cp 40h
        jr z,m_descclock
        add hl,hl
        cp 80h
        jr z,m_descclock
        add hl,hl
m_descclock:
        jp m_decimal
m_rate: ld a,(link_baud)
        add a,a
        ld e,a
        ld d,0
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        ld a,(link_format)
        and 0c0h
        cp 40h
        jr z,m_decimal
        srl h
        rr l
        cp 80h
        jr z,m_decimal
        srl h
        rr l
m_decimal:
        ld de,10000
        call m_dec_digit
        ld de,1000
        call m_dec_digit
        ld de,100
        call m_dec_digit
        ld de,10
        call m_dec_digit
        ld de,1
m_dec_digit:
        ld c,'0'-1
mdd_loop:
        inc c
        or a
        sbc hl,de
        jr nc,mdd_loop
        add hl,de
        jp localout
m_nominal:dw 50,75,110,134,150,300,600,1200,1800,2000,2400,3600,4800,7200,9600,19200
m_actual:dw 50,75,110,134,150,300,600,1200,1800,2005,2400,3600,4800,7200,9600,19800
m_descpos:db 27,'=',44,32,24,'Nominal ',0
m_actualtext:db ' calculated ',0
m_frametext:db ' baud, 8',0
m_clocktext:db ' x',0
m_flags:
        ld hl,m_flagpos
        call boot_print
        ld a,(m_rr0)
        ld b,5
        ld hl,m_flagbits
mf_loop:push bc
        push af
        and (hl)
        ld c,'0'
        jr z,mf_put
        inc c
mf_put: call localout
        call m_service
        ld c,' '
        call localout
        call m_service
        pop af
        inc hl
        pop bc
        djnz mf_loop
        ld a,1
        out (6),a
        in a,(6)
        and 1
        add a,'0'
        ld c,a
        jp localout
m_flagbits:db 1,4,20h,8,80h
m_flagpos:db 27,'=',46,32,24,'RX-ready TX-empty CTS DCD Break All-sent: ',0
