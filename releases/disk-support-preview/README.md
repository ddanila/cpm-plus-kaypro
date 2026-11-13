# Four-drive software-qualified preview

Matched RAM platform and CP/M image for ROM 3.1.0. No new ROM burn.
A:/B: are serial disks; C:/D: are physical Kaypro II SSDD floppies, read-only
by default. C: has passed full-disk format/read verification and an 8 KiB file
write/read test, including a reread after warm boot. D: remains unqualified; see the
[PC003 hardware results](../../reports/floppy-format-20261113/hardware.json).

Use a new session with the pinned shared host and current launcher:

```
python3 tools/serial_boot.py auto --serial /dev/cu.usbserial-2110 \
  --platform releases/disk-support-preview/platform.cim \
  --image releases/disk-support-preview/kaypro.img --session local/disk-preview
```

The manifest must remain beside platform.cim. See ../../docs/disk-drives.md
for permissions and qualification gates, and ../../reports/four-drive-software-20261113
for software evidence. CP/M components retain the notices in
../../third_party/cpm3/LICENSE.md; original project code is MIT licensed.
This preview does not assert completion of both OS CI gates.

The platform now uses HALT/NMI for physical-sector transfers. `FORMAT.COM`
is the matching destructive formatter/diagnostic; see
[formatting instructions](../../docs/formatting.md). Emulator evidence for
this revision is in [floppy-format-20261113](../../reports/floppy-format-20261113).

`IMAGE.COM` writes a canonical 200 KiB stock system image from serial B: to
physical C:, including its boot track, and can read the entire disk back.
See [system-disk instructions](../../docs/system-disk.md). Historical CP/M disk
images and stock ROMs remain external inputs.
