# Formatting an expendable Kaypro II diskette

`make formatter-check` builds `build/format.cim` (install as `FORMAT.COM`) and
executes it in the timed Kaypro emulator. It is bound to the matching
`build/platform.cim`: an instruction-byte guard rejects an incompatible
resident floppy driver before accessing a drive. It needs no ROM changes.

Copy the COM file to a serial disk. To erase and verify the first physical disk:

```
B:FORMAT C ERASE
```

`FORMAT D ERASE` selects the second physical disk. No other command enables
formatting. The selected disk's entire contents are erased. The layout is
40 single-sided tracks, ten 512-byte MFM sectors numbered 0–9, filled with E5.
This creates an empty CP/M filesystem; it does not install a boot system.

Every track is read back and every byte checked. Reads have three attempts;
a failed read-back permits up to three format/verify attempts for that track,
shown by `r`. A format-command error stops immediately. Persistent failure
stops the test and disables physical writes. The final failure line reports
the controller status, sector, and streamed-byte count in hexadecimal.

Only complete verification enables ordinary CP/M sector writes, and only for
the selected drive. Copy a known file from a serial disk, read it back to a
different name, and compare the bytes independently on the host. After testing:

```
B:FORMAT C LOCK
```

LOCK disables writes for both physical drives. A CP/M warm boot alone does not
clear the permission; a fresh platform upload uses its configured write mask
(default zero). D remains disabled when formatting C.

The formatter checks for an index edge before writing. Transfers use the
PC81-240A HALT/NMI handshake and temporarily install a RETN at 0066h, restoring
the previous bytes afterwards. An early controller error completes via INTRQ
and is rejected by the final status check. A controller that stops producing
both DRQ and INTRQ during a transfer can still require Reset; no independent
hardware watchdog exists in this utility. Keyboard service is deferred during
a track write, so do not type while formatting.

The track stream follows the WD1793 MFM address-mark/CRC token conventions
([Western Digital FD179X data sheet](https://bitsavers.trailing-edge.com/components/westernDigital/FD179X-01_Data_Sheet_Oct1979.pdf),
Write Track and formatting sections). The sector-based emulator validates IDs,
data, selection, protection, and guest execution; it does not qualify physical
magnetic recording quality or all board timing effects.

`FORMAT C TEST` (or D) is a separate destructive raw-sector diagnostic for an
expendable disk: it writes the 512-byte pattern `(offset*73+19)&255` through
four ordinary 128-byte BIOS writes to track 0, relogs the head position, reads
all four records back and compares every byte. It does not create a file or
format the disk, and it overwrites any existing boot data in that sector. It
always disables physical writes afterwards. A pass qualifies only that sector,
not the rest of the diskette or its filesystem.

For a write-free drive-selection/LED check, run `make drive-select-check` and
install `build/drvled.cim` as `DRVLED.COM` on a serial disk. `B:DRVLED` runs two
labelled rounds: off for three seconds, C selected with motors on for ten,
off for three, D selected with motors on for ten. It issues no FDC commands
and does not seek or access disk data. It disables physical writes and ends
with both drives deselected and motors off. Observe the LEDs separately from
motor noise: the board has shared motor control but separate drive selects.
