# PC003 stock system disk, 2026-11-13

The expendable replacement diskette in physical C: now contains Dave Dunfield's
Kaypro II CP/M 2.2 system image. The original IMD matches MAME's `cpm22` catalog
SHA-1. Input sources and hashes are in `inputs.json`; downloads remain local.

- All 400 sectors written, including track zero, with immediate read/compare.
- Separate complete read-back to serial B:READBACK.IMG: all 204800 bytes match.
- Raw SHA-256: `908f5288eeba4b22021d26711b6e6a73ec2e1e9c4ef1a87a04cd96fa0995f3b0`.
- The read-back, re-encoded as IMD, boots under stock 81-232 in MAME to
  `KAYPRO II`, `64k CP/M v 2.2`, `A>`.
- C: directory listed successfully under the running serial CP/M Plus port.
- D: was not written. Physical filesystem writes are disabled afterward.

This is a stock CP/M **2.2** system disk. The hardware still runs serial ROM
3.1.0 and CP/M Plus; no firmware was changed and no reset was required.
A physical stock-ROM boot is not claimed. MAME uses the real boot and character
ROMs with an unused synthetic keyboard MCU ROM; keyboard operation is outside
that independent boot check. This qualifies the early single-sided II/81-232
combination, not every later machine sold under the Kaypro 2 name.

See `hardware.json`, `console.txt`, `mame-readback.json` and
`imager-emulator.json` for evidence; [instructions](../../docs/system-disk.md)
for reproducing the process. The published `IMAGE.COM` is built from this
repository's MIT-licensed source and bound to the preview platform.
