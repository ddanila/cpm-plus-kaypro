# Kaypro firmware 3.1.0 candidate

The boot ROM stays 4096 bytes and retains KP2, D3 and the KP3C configuration
handoff. Default boot remains nominal 19200 8O1; custom adapter rates and CP/M
optimizations remain host/runtime choices. Existing V3 launchers accept 3.1.0.

Changes:
- Quiet waiting screen and current rate/framing. `?` opens diagnostics/settings;
  ESC returns to the boot screen. Existing diagnostic keys and loopback remain.
- Fixed-position receiving, CRC accepted and retry status, without scrolling
  away the version or contaminating the serial protocol.
- Reject SIO parity, framing and overrun errors in length, payload, checksum or
  execution command, even if the received byte values happen to match.

We retain diagnostics: hiding their details costs less risk than removing a
useful fallback when cabling or a replacement adapter fails. Baud defaults are
not raised: the measured gains depend chiefly on RAM-loaded CP/M and host code.

Validation executes the ROM from reset, injects all three UART error types at
four transfer phases, tests truncated/corrupt uploads and version queries, and
exercises the keyboard monitor and full loopback. CP/M automatic-recovery
qualification additionally checks host restart and modeled power cycles with
persistent session writes. These are emulator tests; physical qualification of
3.1.0 is pending. The installed 3.0.0 remains the hardware-tested fallback.
