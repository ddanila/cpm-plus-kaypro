# Kaypro serial speed transient

`serial-speed.asm` is an experimental CP/M transient for the PC81-240A SIO A.
It accepts two uppercase hexadecimal byte arguments: baud-generator selector
and SIO WR4. For example, `SPEED 0F 45` selects the normal x16, 8O1 profile.
Use only with a coordinating host diagnostic; this is not a CP/M baud-setting
utility. The host must stop the disk service after the complete `SPEED READY`
line, capture the direct serial exchange, and restart the service before warm
boot. Arguments are supplied by the test harness, not validated interactively.

The transient sends 512 ascending bytes, receives 4096 bytes while accumulating
RR1 errors, and echoes only a complete block. Receive polls and TX waits are
bounded. It restores selector 15 / WR4 45, repeats `KEND` + count (little-endian)
+ RR1 errors, waits for `!` with a bounded timeout, and delays before warm boot.
The receive buffer is 4000–4FFF; its private stack starts at 8000. No ROM writes
or changes to the keyboard channel are made.

Build and check recovery logic from the repository root (requires `z80asm`):

```
make board-test DAC=build/deps/dac-emulation
build/venv/bin/python tools/check_speed_transient.py
```

These tests execute the transient in RAM with stub BDOS/warm-boot calls. They
cover echo, injected receive errors, no input and missing acknowledgement.
They do not model asynchronous x1 clock synchronization or electrical timing.

The physical 2026-11-12 campaign reused the Robotron PL2303HXD endpoint-zero
divisor override, adapted to 8O1. Standard termios was used for ordinary 19200;
nonstandard rate readback alone did not establish the actual adapter setting.
USB line-coding bytes and calculated adapter rates are recorded with each trial.
The initial custom-ioctl baseline and a harness rate-range rejection are retained
as failed setup attempts, not treated as Kaypro speed limits.

See [physical speed results](../../reports/hardware-pc003-speed-20261112.json)
and [hardware sources](../../docs/hardware-sources.md). These short tests do not
establish long-term reliability at higher transmit-only rates.
