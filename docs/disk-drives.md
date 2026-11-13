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
records; there is no dirty write-back cache. Floppy boot, formatting, physical
A:/B: remapping and double-sided formats are outside this release.

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
successful physical floppy I/O. Physical C:/D: reads and writes remain
**unqualified** until the following gates pass on PC003:

1. Read owner-supplied known-good disks in both drives; copy to B: repeatedly
   and compare the files. Check absent media and keyboard/serial responsiveness.
2. Explicitly identify an expendable, already-formatted disk. Enable writes
   only for its drive, copy/read back a pattern, rename/delete, and test actual
   write protection. Repeat reading after disk relogin and warm boot.

No archival disk is used for write qualification. No new ROM burn is needed.
The generated system now begins at 9A00h (previously 9D00h), with BIOS entry
B900h and the resident platform still at C000h. The build derives these values
from GENCPM and checks overlap; `build/system-map.json` and `build/manifest.json`
are authoritative. The system boundary is not a claim that every byte below it
is available as the application TPA: CP/M's SCB reports the actual limit.
