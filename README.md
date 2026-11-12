# CP/M Plus for Kaypro 2 (PC81-240A)

Replacement 4 KiB **KP2 serial boot ROM**, nonbanked Digital Research CP/M Plus
3.1, local CRT/keyboard and mirrored host console for PC003, Kaypro 2 S/N 139936.
The external serial link supplies the virtual disk, defaulting to **19200 8O1**.
V3 offers local serial settings, diagnostics and explicit discovery; the selected
configuration is carried into CP/M.
Serial boot and CP/M file operations have also passed on physical PC003.
The owner reports
that V1 showed garbage at first power-on, then displayed the waiting banner
after reset. Cold-start reliability remains unresolved. Physical serial upload
at 19200 8O1 is now verified, including CRC rejection and return to the monitor. CP/M reached its prompt in 15.9 seconds with the pinned host; binary copying,
warm boots and host reattachment passed. A subsequent 5m34s soak verified ten
8 KiB copies and ten more warm boots, with zero host retries or UART errors.
The first attempt exposed a
stale host executable, now rejected by launcher preflight. See the
[physical test report](reports/hardware-pc003-v3-20261112.json). Physical floppy support is deferred.

The guest filesystem loader, BIOS and session approach reuse cpm-plus-1715.
Juku's N4 console and NetDisk v3 guest code is included directly from the pinned
juku-common submodule. The native Z80 board core is in dac-emulation, and the
production disk server is jukuhost in 8080-cosim. Original work is MIT licensed;
[third-party notices](NOTICE.md) remain applicable.

## Build from source

The release archive includes prebuilt guest artifacts; source builds require a
Git checkout with submodules. The boot/attach instructions apply to both.

Use Python 3.9+, C/C++, make, bison, automake, curses development headers and
sha256sum. On Debian/Ubuntu install `build-essential bison automake libncurses-dev
python3-venv git`. On macOS use the Xcode command-line tools and Homebrew
`bison automake coreutils`; the system curses headers suffice.

```sh
git submodule update --init --recursive
python3 -m venv build/venv
build/venv/bin/pip install pexpect==4.9.0
python3 tools/dependencies.py
make all PYTHON=build/venv/bin/python
bash build/deps/8080-cosim/sync/jukuhost_linux_build.sh
```

The dependency fetcher uses isolated checkouts at the revisions in
[dependencies.json](docs/dependencies.json); it rejects dirty checkouts.
ZXCC's old configure helpers are refreshed from installed automake in the
extracted build tree to support Linux ARM64. Vendored archives remain unchanged.

Outputs are `build/boot.rom` (4096 bytes), `build/platform.cim`,
`out/kaypro.img` (819200 bytes) and their matched `build/manifest.json`.
The native800 image has 160 logical tracks × 40 records × 128 bytes; that is
virtual disk geometry, not a physical floppy format. It includes CP/M utilities,
HELLO.TXT, deterministic binary data and KEYS/SCREEN diagnostic transients.

ROM **3.0.0** displays its version, serial settings, expected upload and host
launcher instructions on the CRT. Its version is stored as readable ASCII in
the ROM and recorded as `rom_version` in `build/manifest.json`.
`src/rom-version.asm` is the single version source; bump major/minor/patch for
incompatible firmware changes, features, or fixes respectively. This numbering
is independent of the unchanged **KP2** protocol and repository release tags.
The first hardware candidate had no firmware version string.

While waiting for the host, send ASCII `V` at 19200 8O1 to receive
`KPV3.0.0\r\n`. This query is optional; the existing launcher still uses `K`
and receives `KP2`. See the [protocol contract](docs/protocol.md) for query scope.
The original hardware-candidate release and its qualification reports describe
the earlier ROM; rebuilding produces the new ROM and matched manifest.

## V3 local monitor

Boot starts automatically with nominal 19200 8O1, x16, no flow control. The
CRT shows the version, selected registers, nominal/calculated rate and status.
The 4096-byte image uses 3628 bytes and leaves 468 bytes free. V3 adds a short
power-on settling delay and explicitly initializes both SIO channels; whether
this resolves PC003's intermittent cold-start garbage still needs hardware tests.

| Key | Action |
| --- | --- |
| S | Settings: 1 cycles baud, 2 parity, 3 stop bits, 4 x16/x32/x64 |
| R / T | Receive hex/status or transmit the repeating test pattern |
| L | Local loopback: O once, C continuously |
| W | Loopback sweep through baud selectors, restoring prior settings afterward |
| A | Bounded discovery scan across 9600/19200 selectors and N/O/E parity |
| K | Display keyboard byte codes |
| I / D | Reinitialize selected settings / restore defaults |
| B / Escape | Return to Boot / cancel the current diagnostic |

For local loopback, disconnect the host and bridge Kaypro DB25 pins 2–3.
Loopback checks bytes, not the absolute baud rate. Counts are hexadecimal and
wrap at 65536. Channel B remains independently configured for the keyboard.

Host diagnostics use the same launcher:

```sh
python3 tools/serial_boot.py probe --serial /dev/cu.YOUR_RS232_ADAPTER
python3 tools/serial_boot.py scan --serial /dev/cu.YOUR_RS232_ADAPTER
python3 tools/serial_boot.py rx-test --serial /dev/cu.YOUR_RS232_ADAPTER
python3 tools/serial_boot.py tx-test --serial /dev/cu.YOUR_RS232_ADAPTER
```

Select A on the Kaypro for scan, T for host rx-test, or R for host tx-test.
Discovery uses CRC and nonce confirmation; a confirmed link stays locked.
After scan, press **B** on the Kaypro before launching boot, then pass the
reported settings as `--baud`, `--parity` and `--stop-bits`. For example,
`--baud 9600 --parity E --stop-bits 2`. Use the same options when attaching.
Probe/scan do not upload or execute code. Reports and captures go under `local/`.

The highest selector is conventionally called 19200; the modeled 5.0688 MHz
clock and /16 BRG divider calculate to 19800 at SIO x16. The screen distinguishes
these values. Host scan tries both 19200 and 19800, plus 9600. The physical [speed campaign](docs/serial-speed.md) passed bidirectional 19800
using the PL2303HXD USB divisor workaround; ordinary macOS custom-rate
requests were unreliable. Target bit timing was not measured directly.
No faster bidirectional x1 candidate passed; 19200 remains the default.

## Boot or reattach

Complete the [bench checklist](docs/hardware-trial.md) before using a physical
port. In a source checkout or extracted release:

```sh
python3 tools/serial_boot.py boot \
  --serial /dev/cu.YOUR_RS232_ADAPTER --session local/pc003-first \
  --host build/deps/8080-cosim/build/jukuhost
```

Linux uses the corresponding `/dev/ttyUSB…` or `/dev/ttyACM…` device. Choose the
actual adapter path; the launcher never selects or probes an arbitrary port.
The launcher checks host option compatibility before opening the serial port.
It waits up to 30 seconds for KP2, uploads the platform and starts the disk host.
The interactive host console mirrors the CRT; **Ctrl-] detaches**, while Ctrl-C
is sent to CP/M. The original disk image is never modified: each new session
gets `disk.img`. Add `--read-only` for a write-protected session.

```sh
python3 tools/serial_boot.py attach \
  --serial /dev/cu.YOUR_RS232_ADAPTER --session local/pc003-first \
  --host build/deps/8080-cosim/build/jukuhost
```

Attach retains the session disk and does not upload or reset the machine. Use
the same source artifacts, host executable and read-only setting. A session
lock prevents concurrent owners. After an uncertain execution failure, reset
the Kaypro and use a new boot session; do not blindly replay a payload.
`--console-pty DEVICE` supplies a raw Kaypro console endpoint for automation.
Local input takes priority when both keyboards have queued input.

The release contains guest artifacts and Python launcher, not architecture-
specific host executables. Run `python3 tools/dependencies.py --host-only`
and the host build command above to obtain the pinned native server.

## Qualification

```sh
build/venv/bin/python tools/qualify.py \
  --dac build/deps/dac-emulation --host-repo build/deps/8080-cosim \
  --out local/qualification
# Optional independent MAME startup/display check:
python3 tools/check_mame.py --mame mame --out local/mame-check
```

Output directories must be new. The complete gate runs the board/host tests,
ROM fault cases, monitor loopback/discovery tests, driver/terminal tests, production-launcher boot, real CP/M
file operations, timed keyboard input during disk writes, read-only rejection,
corrupt-reply recovery, warm boot and host reattach. A second writable run
selects 9600 8E2 through the ROM keyboard and verifies configuration handoff. CRT and host character
cells are compared independently; timing and receiver drops are recorded.

ROM/CP/M integration starts at CPU reset, without OS RAM injection. Resident
unit tests intentionally RAM-load driver code and are labeled separately.
PTYs model logical framing only. MAME independently checks reset, relocation,
banking and the CRT startup banner, using synthetic character/keyboard fixtures;
it does not qualify the keyboard MCU or the full serial CP/M session.

The probe writes RAM, physical video RAM, screen cells and a 560×240 PGM snapshot.
`KAYPRO_CHARGEN=/path/to/2048-byte-dump` selects an external character ROM;
otherwise the renderer uses an explicitly synthetic fixture. PC003's handwritten
81-233A label alone does not establish its character contents.

See [protocol/memory contract](docs/protocol.md),
[console behavior](docs/console.md), [hardware sources](docs/hardware-sources.md)
and [hardware trial checklist](docs/hardware-trial.md).

## Automatic boot and reconnection

Use `tools/serial_boot.py auto` with the same arguments and session directory
as boot/attach. A new session copies the source disk once; an existing session
retains its writable disk and journal. The shared native host identifies V3
boot-wait versus running CP/M and also handles a later reset without restarting
the host. No keypress or ROM change is needed in Mode 00. V3 speed scanning is
still explicit; automatic host recovery checks saved runtime and configured
boot settings rather than changing the ROM's diagnostic mode blindly.

Use the pinned host and its `host/python/jh_recovery` support (included under
`python/` in packages). `boot`, `attach`, and diagnostic modes remain available.
Recovery preserves artifact checks and serial options; fast runtime settings
remain opt-in pending their separate hardware qualification.
See [shared recovery](https://github.com/ddanila/8080-cosim/blob/master/docs/serial-recovery.md).
