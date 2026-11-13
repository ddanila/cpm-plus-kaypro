# Serial disks and Kaypro II floppies

This RAM-platform revision keeps ROM 3.1.0 unchanged. A: is the serial system
image, B: the serial work image, C: the first physical drive and D: the second.
Letters are fixed. CP/M and CCP continue to load from A:.

New sessions automatically create an empty 800 KiB B: image. `--drive-b FILE`
uses a native800 image as its source; the launcher copies it to `disk-b.img`
inside the session. `--drive-b-read-only` protects B:. `--read-only` protects A:.
Source images are never written. A: and B: have independent journals and host
file locks. A legacy session without B: metadata remains single-disk; do not
reuse an old session with rebuilt platform/image files. Start a new session.

Example after building the pinned host and guest artifacts:

```
python3 tools/serial_boot.py auto --serial /dev/cu.usbserial-2110 \
  --session local/disks-session --runtime-profile fast --runtime-baud 19200 \
  --buffer-console --read-ahead 4
```

Physical drives are read-only by default. `--floppy-write C`, `D`, or `CD`
enables writes for the selected drive(s) in the validated RAM upload. This
setting persists in the session identity and automatic recovery configuration.
It does not override the disk's physical write protection. Changing permissions
requires a new session/reload; it is not a live setting.

Only original Kaypro II single-sided, double-density media is supported:
40 cylinders, ten 512-byte sectors numbered 0–9, 250 kbit/s MFM, one reserved
track, 1 KiB allocation blocks and 64 directory entries. Raw emulator fixtures
are exactly 204800 bytes in cylinder/sector-ID order. The 819200-byte serial
images use a different filesystem geometry and cannot be written directly to
a physical diskette. Copy files with PIP instead:

```
DIR C:
PIP B:*=C:*.*
PIP C:EXAMPLE.TXT=B:EXAMPLE.TXT
```

The last command requires writes enabled for C:. Use Ctrl-C to relog disks
after insertion/removal. Do not change a disk during an operation. Sector
writes are synchronous read/modify/write, preserving the other three 128-byte
records; there is no dirty write-back cache. A separate [format-and-verify utility](formatting.md) can initialize an expendable
diskette. A separate [whole-disk image utility](system-disk.md) can create stock
CP/M 2.2 boot disks, including their reserved boot track, from a file on serial
B:. Floppy boot of our CP/M Plus port, physical A:/B: remapping and double-sided
formats are outside this release.

## Qualification and limitations

Software tests execute the actual Z80 driver and CP/M BIOS, including both
serial disks, both floppy images, byte-for-byte copy verification, write
protection, missing media, bounded CRC retries and keyboard input during
spin-up/seek/transfer. The shared WD179x extraction retains Juku's established
API and is checked against its existing controller regression suite. Separate
Kaypro tests cover byte deadlines/lost data, drive selection and HALT/NMI.
MAME cross-checks selected controller error outcomes independently.

The sector model does not represent flux, damaged address marks, exact angular
placement of sectors, or partially overwritten physical magnetic tracks. A raw
image cannot preserve those details. Software qualification is not evidence of
successful physical floppy I/O. The resident sector transfer now uses the
board's HALT/NMI handshake after real PC003 polling transfers reported lost data. On PC003, C: has now passed full-disk format/read verification and an 8 KiB
CP/M file write/read comparison, repeated after warm boot. D: remains
unqualified. Further coverage still needed includes physical write protection,
rename/delete, and compatibility with independently formatted historical media.

On 2026-11-13, PC003 booted this four-drive build over serial. The owner
confirmed that C: and D: each accessed the correct physical drive. An attempted
read from a suspect diskette failed; no known-good medium was available. This was initially recorded as selection confirmation, but the later D:
observation below leaves D: selection unconfirmed. It does not establish
successful sector or filesystem reads. Physical writes remained disabled. See the
[hardware observation report](../reports/hardware-pc003-four-drive-20261113.json).

No archival disk is used for write qualification. No new ROM burn is needed.
The generated system now begins at 9A00h (previously 9D00h), with BIOS entry
B900h and the resident platform still at C000h. The build derives these values
from GENCPM and checks overlap; `build/system-map.json` and `build/manifest.json`
are authoritative. The system boundary is not a claim that every byte below it
is available as the application TPA: CP/M's SCB reports the actual limit.

A later [formatting session](../reports/floppy-format-20261113/hardware.json)
verified all ten sectors of track 0 on C:, but track 1 sector 0 retained CRC
errors after retries. With the same diskette in D:, the formatter stopped
because it could not detect index. At that point neither drive had passed full-disk or physical-file-copy
qualification.

The owner subsequently reported that D:'s LED never lit although its motor
was spinning. The 81-241 sheet 2B has one shared motor-control signal and
separate drive-select outputs, so motor activity does not confirm selection.
The earlier claim that both physical drives were selected is withdrawn for D:.

A subsequent direct selection diagnostic repeated C/off/D/off twice without
FDC commands. The owner confirmed that only C:'s LED lit; D:'s stayed dark.
D:'s select signal, cabling/jumper configuration and drive now need physical
verification; another formatting attempt alone cannot resolve this.

With a replacement expendable diskette in C:, all 40 tracks and 400 sectors
formatted and verified without retries. An 8192-byte PATTERN.BIN was copied
from A: to C: and back to B:, independently compared on the host, then reread
and compared after a warm boot. Both comparisons matched SHA256
`dded5d20af664319fcf79f235e54f79a9fbf57fa90ba4c61369be03e35be5189`.
This strongly suggests the first diskette was faulty; it does not resolve D:.

After this test, `FORMAT C LOCK` disabled physical writes for both drives.
The replacement diskette retains PATTERN.BIN for subsequent read checks.
