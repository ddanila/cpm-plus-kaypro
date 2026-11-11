# CP/M Plus for Kaypro 2 (PC81-240A)

Replacement 4 KiB **KP2 serial boot ROM**, nonbanked Digital Research CP/M Plus
3.1, local CRT/keyboard and mirrored host console for PC003, Kaypro 2 S/N 139936.
The external serial link supplies the virtual disk at **19200 8O1** throughout.
This is a software-qualified hardware candidate; **PC003 has not been booted
with it**. Physical floppy support is deferred.

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

ROM **2.0.0** displays its version, serial settings, expected upload and host
launcher instructions on the CRT. Its version is stored as readable ASCII in
the ROM and recorded as `rom_version` in `build/manifest.json`.
`src/rom-version.asm` is the single version source; bump major/minor/patch for
incompatible firmware changes, features, or fixes respectively. This numbering
is independent of the unchanged **KP2** protocol and repository release tags.
The first hardware candidate had no firmware version string.

While waiting for the host, send ASCII `V` at 19200 8O1 to receive
`KPV2.0.0\r\n`. This query is optional; the existing launcher still uses `K`
and receives `KP2`. See the [protocol contract](docs/protocol.md) for query scope.
The original hardware-candidate release and its qualification reports describe
the earlier ROM; rebuilding produces the new ROM and matched manifest.

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
ROM fault cases, driver/terminal tests, production-launcher boot, real CP/M
file operations, timed keyboard input during disk writes, read-only rejection,
corrupt-reply recovery, warm boot and host reattach. CRT and host character
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
