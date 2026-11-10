# CP/M Plus for Kaypro 2 (PC81-240A)

A replacement 4 KiB serial boot ROM and nonbanked Digital Research CP/M Plus
3.1 port for inventory PC003, Kaypro 2 S/N 139936. This is a **simulation-tested
bring-up**, not yet a physically tested EPROM. The console and disk both use
the external serial port. Local CRT, keyboard and floppy operation are not
implemented by this port.

The Z80 machine core lives in [dac-emulation](https://github.com/ddanila/dac-emulation/tree/main/machines/kaypro2).
The production disk/console server is [jukuhost](https://github.com/ddanila/8080-cosim).
The guest filesystem loader and BIOS are adapted from cpm-plus-1715; the
console and NetDisk v3 implementation is shared directly with Juku through
the pinned juku-common submodule. See [NOTICE.md](NOTICE.md).

## Build and exercise

Requires a C/C++ toolchain, make, bison, Python 3 with pexpect, and sha256sum.
Build tools and Digital Research inputs are vendored with checksum checks.

```sh
git submodule update --init --recursive
python3 -m venv build/venv
build/venv/bin/pip install pexpect==4.9.0
make all PYTHON=build/venv/bin/python
make probe DAC=../dac-emulation
# In a sibling 8080-cosim checkout: bash sync/jukuhost_linux_build.sh
build/venv/bin/python tools/check_runtime.py \
  --host ../8080-cosim/build/jukuhost --out local/qualification
```

The output directory must be new. The test boots actual Z80 instructions from
`build/boot.rom`, uploads `build/platform.cim` over a paced PTY, and runs the
production host against a private copy of `out/kaypro.img`. It checks bad CRC
rejection, cold/warm boots, directory/file operations, independent disk
readback and host restart without resetting the guest. No OS is injected
into guest RAM. The source image remains unchanged.

`build/boot.rom` is exactly 4096 bytes. The image is 819200 bytes (160 logical
tracks, 40 records of 128 bytes), containing CPM3.SYS, CCP and utility programs.
This is the serial virtual disk geometry, not a claim about physical floppies.

## Boot and memory contract

Reset ROM configures system PIO A, relocates its receiver to 8000, and clears
PIO A bit 7 to expose RAM. Writes beneath enabled ROM do not reach RAM.
The stock 8116 baud selector 15 with SIO x16 supplies 19200 baud.
Bootstrap framing is 8N1; the platform switches to 8O1 for shared N4 console
and NetDisk v3. Channel B (keyboard) is not reset by the serial driver.

The host sends `K`; ROM replies `KP1`. It then accepts a two-byte little-endian
length (1 through 35FF hex), that many bytes for C000, and CRC-16/CCITT
(polynomial 1021, initial FFFF, no reflection/final XOR), high byte first.
ACK is 06; NAK is 15. Following ACK, `G` executes C033. Drain this final 8N1
byte before adopting 8O1. Timeouts return to synchronization. CRC detects
transfer errors; this protocol provides no authentication.

The platform loads CPM3.SYS through the real directory/allocation structures,
checks its expected CRC and enters the BIOS. CP/M occupies 9D00–BFFF, BIOS
entry BC00, platform C000 upwards, stack top F700. The platform selects the
same single-record native800 host contract used by Robotron.

## Evidence and remaining work

[Source review](docs/hardware-sources.md) records schematic and MAME findings.
[Qualification](docs/qualification.json) records the tested artifact hashes
and checks; `hardware_executed` is false. The independent MAME check exercises
the same ROM through relocation, RAM switching and its serial receive wait;
it does not run the full serial CP/M session.

Before programming PC003, verify its ROM socket/jumper configuration and
obtain a backup of its original ROM. Its handwritten 81-233A character ROM
has not been dumped or identified by content. Physical serial timing,
RS-232 wiring and parity transitions remain to be qualified. The native core
models polling SIO use, not interrupt or electrical behavior. See its README
for the complete model limitations.

To repeat the independent startup test with MAME installed:

```sh
python3 tools/check_mame.py --mame mame --out local/mame-check
```

This creates zero-filled character/keyboard fixtures; checksum warnings are
expected. They are not original ROMs and cannot qualify those peripherals.
