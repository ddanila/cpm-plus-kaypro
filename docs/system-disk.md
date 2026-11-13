# Creating a stock Kaypro II system disk through serial CP/M

The serial disks can carry a historical disk image as a **file**. A normal PIP
copy does not transfer its reserved boot track. `IMAGE.COM` transfers all 400
512-byte sectors, including track zero, to the already formatted physical C:.
A:/B: keep their native800 geometry; do not mount a 200 KiB Kaypro image directly
as the native800 B: backing store.

Target: early single-sided Kaypro II, 40 tracks, 10 sectors per track, 512 bytes,
sector IDs 0–9, double density. The stock 81-232 ROM and original CP/M 2.2 disk
have been checked together in MAME. This does not establish compatibility with
later double-sided 2/84, 2X, 4 or 10 models or third-party firmware.

## Prepare and test

```
make imager-check
python3 extras/kaypro_imd.py KAYPRO1.IMD KAYPRO.IMG
```

The converter rejects missing/error/deleted sectors, duplicate sectors, foreign
geometry and truncated input. Its output is exactly 204800 bytes, in ascending
track and sector-ID order. `--encode` converts this canonical image back to IMD
for an independent emulator check. The guest imager binds to the exact resident
physical driver through a full immutable-code comparison; rebuild it when that
driver changes. It requires the same platform as `FORMAT.COM`.

Stop the serial host cleanly before importing `build/image.cim` as B:IMAGE.COM
and the image as B:KAYPRO.IMG. Restart the host and press Ctrl-C to relog the
serial disks. Use a formatted expendable diskette in C:, then:

```
B:IMAGE C ERASE
B:IMAGE C READ
```

**ERASE replaces the entire physical C: disk**, including its directory and boot
track. It first checks the input file's size, reads one track at a time through
BDOS, writes whole 512-byte sectors, and immediately rereads and compares every
sector. It stops at the first disk or comparison error. Track numbers on screen
are hexadecimal, 00–27. It has no D: write command. On completion or an ordinary
error, both physical drives' filesystem write permissions are disabled.

READ creates B:READBACK.IMG without altering C:. It refuses to replace an
existing readback file. Stop the host cleanly, extract that file from native800
B:, and compare **all 204800 bytes** against the canonical source. Convert the
readback to IMD and boot it under the stock ROM in MAME. Preserve the source URL,
input hash, raw hash, readback hash, and boot transcript with the test record.
The historical image and stock ROM are external inputs, not included here.

```
python3 extras/kaypro_imd.py --encode READBACK.IMG readback.imd
python3 extras/check_stock_boot.py --image readback.imd \
  --rom 81-232.u47 --chargen 81-146.u43 --out local/stock-readback-check
```

Do not run the disk's stock COPY, FORMAT or SYSGEN under our four-drive CP/M
Plus BIOS: their hardware and drive assumptions differ. This process produces
a stock **CP/M 2.2** disk, not a floppy-booting version of our CP/M Plus port.
The physical C: here is the first drive, called A: by stock firmware.

## Sources and boot verification

- [Dave Dunfield's system image archive](https://www.classiccmp.org/dunfield/img42841/system.htm),
  `d/kayproii.zip`, member `KAYPRO1.IMD`.
- [MAME Kaypro software list](https://github.com/mamedev/mame/blob/master/hash/kaypro.xml):
  the `cpm22` image has the same SHA-1, `c4158b4f84066514af2b74cb6d0915f661402819`.
- [Archived Kaypro ROMs](https://www.mrynet.com/FTP/os/Kaypro/kaypro_roms/),
  `kayproii_u47.bin` and `kayproii_u43.bin`.
- [MAME driver ROM definitions](https://github.com/mamedev/mame/blob/master/src/mame/kaypro/kaypro.cpp):
  stock 81-232 SHA-1 `cd9f45cc3546bcaad7254b92c5d501c40e2ef0b2` and character ROM
  81-146 SHA-1 `5cb880083b94bd8220aac1f87d537db7cfeb9013`.

MAME boot checks use the actual stock boot and character ROMs, with a synthetic
unused keyboard MCU ROM. They qualify disk boot to `64k CP/M v 2.2` and `A>`;
they do not qualify keyboard operation or replace a physical stock-ROM boot.

The imager shares the resident HALT/NMI transfer path. As with the formatter,
there is no independent watchdog if hardware stops asserting both DRQ and
INTRQ mid-transfer. Emulator checks cover ordinary missing media, write
protection and CRC errors, plus full commands with a BDOS filesystem fixture.
