; MIT. Test-only BDOS fixture, source data at 8000h..93ffh, DMA at 7f00h.
        org 7600h
        ld a,c
        cp 35
        jr z,size
        cp 26
        jr z,dma
        cp 20
        jr z,read
        cp 21
        jr z,write
        cp 15
        jr z,open
        xor a
        ret
size:   ld a,(7f06h)
        or a
        ret nz
        ld hl,33
        add hl,de
        ld (hl),40h
        inc hl
        ld (hl),6
        inc hl
        ld (hl),0
        xor a
        ret
dma:    ld (7f00h),de
        xor a
        ret
open:   ld a,(7f04h)
        neg
        ret
read:   ld hl,(7f02h)
        ld de,(7f00h)
        ld bc,128
        ldir
        jr next
write:  ld hl,(7f02h)
        ld de,(7f00h)
        ld b,128
compare:ld a,(de)
        cp (hl)
        jr nz,bad
        inc hl
        inc de
        djnz compare
next:   ld a,h
        cp 94h
        jr nz,keep
        ld hl,8000h
keep:   ld (7f02h),hl
        xor a
        ret
bad:    ld a,1
        ld (7f05h),a
        ret
