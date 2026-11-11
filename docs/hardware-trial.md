# PC003 first hardware trial

Status: **V3 hardware trial not performed**. Software qualification is a prerequisite, not proof
of electrical timing or compatibility with this particular board.

## Record equipment and preserve the original

- [ ] Confirm PC003: Kaypro 2, S/N 139936, PC81-240A, U70 MK3884N.
- [ ] Record programmer model/software, replacement EPROM part and speed grade.
- [ ] Record original boot device type, socket orientation and ROM-size jumpers.
  The candidate is a 4096-byte image; confirm a compatible 2732 configuration.
  Do not guess programming voltage from the ROM label.
- [ ] Read the original boot ROM twice; compare complete files and SHA-256 hashes.
  Save both reads, photographs/notes and programmer settings. Retain the original
  chip intact and labeled for rollback.
- [ ] Record character ROM type and obtain matching repeated reads where practical.
  Identify the contents of the handwritten 81-233A before claiming glyph fidelity.
- [ ] Record keyboard model/controller markings; distinguish early-board variants.
- [ ] Record USB-to-RS-232 adapter model, driver, OS and device path. Use an actual
  RS-232-level adapter at the external serial connector, not TTL UART wiring.
- [ ] Verify connector orientation and signal directions against sheet 2B. Record
  the actual cable mapping in a table: Kaypro pin/signal → adapter pin/signal.
  Cross TX to RX as required by the two endpoints; connect signal ground. Do not
  infer straight-through/null-modem wiring from connector gender alone. No flow
  control is used by the candidate. Record any modem-line connections explicitly.
- [ ] Program a separate compatible EPROM and verify full readback against the
  release `build/boot.rom` hash. Retain the original for restoration.

Perform socket work with the machine off and disconnected. This procedure does
not require opening or adjusting the CRT's high-voltage section.

## Software gate

- [ ] Use one matched release; verify SHA256SUMS and build/manifest.json.
- [ ] Both macOS and Linux reports say complete, with matching guest hashes.
- [ ] Review ROM negative tests, driver tests, writable/read-only runtime reports
  and the independent MAME startup/display result. PTY tests do not test parity
  generation, voltage levels or USB adapter latency.
- [ ] Build the pinned host and record its hash. Keep other programs off the port.
- [ ] Prepare a new session directory and an untouched source disk image.

## Staged trial and stop points

First owner observation (2026-11-11, V1): initial power-on showed a screen full
of garbage; reset produced the waiting-for-host banner. No physical serial or
CP/M result has been reported. Record cold-start versus reset behavior on the
next trial, including whether garbage persists after CRT warm-up and whether
reset consistently recovers. The ROM initializes console state and clears the
visible screen; the cause of this discrepancy is not yet established. ROM
2.0.0's version/banner/query changes are not a verified cold-start fix.

1. **Reset/startup:** install the candidate and observe the CRT waiting banner.
   If absent or corrupt, stop before sending a payload; check board/ROM identity,
   jumper settings and readback. Restore the original ROM if needed.
2. **Diagnostics/bootstrap:** check V3 version, local keyboard, receive display
   and disconnected local loopback first. Start with 19200 8O1; use the V3
   monitor and logged host scan if needed, then press B and run the launcher
   with the selected settings. Require KP2 and a
   checked upload. On repeated failure, preserve logs and reset; do not change
   baud or EPROM wiring speculatively within the same recorded run.
3. **CP/M:** require the sign-on and A> prompt on both CRT and host. Record both.
4. **Consoles:** run SCREEN and TYPE HELLO.TXT from each keyboard. Check cursor
   motion, scrolling, editing, arrows, bell and the actual Greek/custom glyphs.
5. **Disk:** run `PIP COPY.BIN=PATTERN.BIN`, then stop/reattach the host cleanly and
   independently compare the file bytes using the media parser. Record hashes.
6. **Recovery:** check Ctrl-C warm boot, host detach/attach without guest reset,
   source image immutability and a separate read-only session.

Stop at the first unexplained mismatch. Save the ROM/platform/image/host hashes,
OS/adapter details, console captures, wire logs, session disk and observations.
Never overwrite a failed session with a new attempt. Restore the untouched
original ROM and recorded jumper settings for rollback.

Only a completed physical campaign may change hardware qualification to true.

V3 includes a settling delay and explicit SIO reinitialization. Neither is a
physically established fix yet. Keep cold-start/reset statistics (including CRT
warm-up), the ROM hash and all host settings with the next hardware results.
