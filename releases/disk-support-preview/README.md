# Four-drive software-qualified preview

Matched RAM platform and CP/M image for ROM 3.1.0. No new ROM burn.
A:/B: are serial disks; C:/D: are physical Kaypro II SSDD floppies, read-only
by default. Physical floppy reads and writes are not yet qualified.

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
