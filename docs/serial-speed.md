# PC003 serial speed measurements — 2026-11-12

The highest **bidirectional** setting to pass this campaign was SIO x16,
selector 15, with the adapter requested at 19800 (calculated 19801 via its USB
divisor). This uses the same Kaypro clock selection as nominal 19200. Ordinary
19200 remains the default and had already passed the longer CP/M soak.

The Robotron PL2303HXD workaround was reused with **odd parity**, rather than
Robotron's 8N1: an endpoint-zero SET_LINE_CODING sets the HXD divisor and its
readback is checked. Termios/IOSSIOSPEED readback alone was insufficient. The
initial custom-ioctl 19200 baseline produced corrupt input; ordinary termios
and the USB-override baseline both passed. Two later setup rejections were
corrected and rerun; they do not establish target limits.

Each complete direct trial sent a known 512-byte target pattern, delivered a
4096-byte deterministic random host block, and compared its echo independently.
The RAM transient bounded its waits, restored 19200, and coordinated a warm
boot with the host. No EPROM changes, power cycles or user resets were required.

| Requested host rate | SIO mode | Short TX pattern | Receive/echo |
| --- | --- | --- | --- |
| 19200 | x16 | Pass | Pass, both ordinary and USB-override baselines |
| 19800 | x16 | Pass | Four 4096-byte blocks exact, no reported RR1 errors |
| 19200 | x1 | Pass | Corrupt, parity/framing errors |
| 28800 | x1 | Pass | Corrupt, parity/framing errors |
| 32081 | x1 | Pass | Incomplete, parity/framing errors |
| 38400 | x1 | Pass | Incomplete, parity/framing errors |
| 57600 | x1 | Pass | Incomplete, parity/framing errors |
| 76800 | x1 | Pass | Incomplete, parity/framing errors |
| 115200 | x1 | Pass | Incomplete |
| 153600 | x1 | Pass | Incomplete |
| 316800 | x1 | Pass | Incomplete |

CP/M also passed three independent 8 KiB copies and three warm boots with the
adapter overridden to calculated 19801. The production host's protocol timing
remained configured at 19200; this tests the physical adapter rate override,
not a new production launcher mode. Its closed log recorded zero retries and
UART errors. Ordinary 19200 was restored, verified by USB line coding
`004b0000000108`, and TYPE HELLO.TXT passed again with the host left running.

A zero RR1 error summary does not rescue an incomplete receive test. These
short transmit successes are not a sustained-throughput or bidirectional
qualification at those speeds.

The results agree with the [Zilog SIO manual](https://www.hartetechnologies.com/manuals/Zilog/Zilog%20Z80-SIO%20Technical%20Manual.pdf):
x1 asynchronous receive requires external bit synchronization. The
[SMC COM8116 table](https://www.vintagecomputer.net/fjkraan/comp/divcomp/doc/SMC_BaudGen.pdf)
(printed page 282, PDF page 19) specifies 316.8 kHz for selector 15 with a
5.0688 MHz crystal, or 19800 after x16 division. Higher x1 line rates therefore
do not provide a demonstrated software-only fast CP/M link on this board.
There was no oscilloscope clock measurement, and no modified clock hardware
was tested.

[Machine-readable results](../reports/hardware-pc003-speed-20261112.json) include
actual USB coding bytes, calculated adapter rates, setup failures, recovery
results and emulator checks. [Transient and recovery test](../tools/hardware/README.md).
The emulator check covers program recovery, not x1 electrical synchronization.

## Historical results and improvement options

Research on 2026-11-12 found no verified, reproducible stock Kaypro result above
nominal 19200 in the sources reviewed. This is a search result, not proof that
nobody achieved one. Two particularly relevant contemporary accounts are:

- [Planemo's experiments](https://planemo.org/2014/08/10/serial-port-interfacing-to-the-z-100-part-2/):
  the author initially expected 57600 on a TurboROM Kaypro 4-84, then corrected
  that expectation after identifying the 8116 limit. The demonstrated 38400
  result in that article belongs to the Z-100. A Kaypro clock modification was
  proposed, not reported as completed.
- [High Speed IMP 2.46](https://planemo.org/2014/08/19/high-speed-imp-v2-46/):
  rate indexes through 115200 are platform independent. The author explicitly
  keeps the Kaypro at 19200 pending motherboard changes; the fast SIO/CTC
  example is a different machine.
- [The Computer Journal issue 22](https://www.jaysage.org/tcj/tcj_22_OCR.pdf),
  printed page 44, describes KTERM at 19200 and asserts higher rates are possible,
  but gives no higher measured rate or clock configuration in that discussion.
  It is not a reproducible above-19200 qualification.

The [Kaypro schematic](https://retrocmp.de/kaypro/1985_1484-E_KayproTechnicalManual.pdf)
on printed page 6-14 (sheet 2B) shows U78 output pin 3 driving both U70
RxCA and TxCA, and output pin 17 driving the keyboard channel. It shows no
external serial clock connection at J4. U68/U69 are MC1488/MC1489 line
interfaces. Later-board external-clock arrangements must not be assumed to
exist on PC81-240A.

Candidate improvements, not yet implemented or qualified:

| Approach | Expected benefit and limits |
| --- | --- |
| Change runtime 8O1 to 8N1 | 10% more byte capacity at the same baud: 11 wire bits become 10. Keep packet CRC and test error recovery. ROM bootstrap can retain its existing format. |
| Batch records, cache reads, buffer console traffic | Reduce round trips and per-record overhead; profile RAM cost and reconnect/cache invalidation. Does not raise line baud. |
| Faster CRC or compressed boot payload | Can reduce CPU work or transmitted bytes; measure first, since compression adds target CPU and RAM costs. |
| x1 fast transmit, x16 receive between protocol phases | Short TX tests passed, but switching both peers adds complexity. Primarily helps Kaypro-to-host traffic, not boot or disk reads. Requires sustained tests. |
| Replace baud generator and crystal | A documented divider-table route to 38400 exists. Exact chip suffix matters; see below. Requires keyboard and serial initialization changes. |
| Add a reversible clock interposer for channel A | Preserve the keyboard clock and provide 614400 Hz for 38400 at x16. Higher candidate clocks need exact SIO timing, line-interface and CPU-service checks before promising a rate. |
| CPU speed upgrade or additional UART | A CPU upgrade helps servicing but does not change U78's clock. A new UART can bypass the clock limit but is a substantially different hardware project. |

The SMC table on printed page 283 identifies **COM8116T-013A with a 5.52960 MHz
crystal** as one 38400-capable combination. A generic COM8116 replacement does
not imply that table. Its 300-baud selector is 4, versus 5 in our current
initialization, so a replacement without firmware changes would disturb the
keyboard. Socket wiring, supply requirements and exact replacement ratings
must also be checked before installation. Simply overclocking the existing
generator is not an equivalent qualified modification.

Synchronous capture followed by software UART decoding is another research
possibility, not a demonstrated workaround. At the current maximum 316800-Hz
clock, packed samples arrive at 39600 bytes/s: roughly 63 CPU cycles per byte
at 2.5 MHz before decoding, framing, buffering or protocol work. SIO hunt and
synchronization behavior also need a design. Normal x1 asynchronous reception
has already failed the physical tests above.

Recommended order: measure protocol overhead, qualify 8N1 and batching with
recoverable RAM software, then consider a reversible channel-A clock adapter
if a true increase beyond the present clock limit is wanted. No clock
modification was made during this campaign.

## RAM runtime optimization

The runtime now has an independent framing transition. The V3 ROM still boots
at its selected framing; the uploaded platform exchanges CRC-protected `RT`
frames before changing channel A, verifies the new link, and waits for the
host's execution acknowledgement before requesting disk data. Failure restores
the original framing and waits for a recovery acknowledgement. The keyboard
channel and EPROM are unchanged. Warm boots retain the selected runtime.

Explicit experimental launcher options:

```sh
python3 tools/serial_boot.py boot --serial /dev/cu.usbserial-2110 \
  --session local/fast-session --runtime-profile fast --adapter pl2303hxd \
  --read-ahead 4 --buffer-console
```

Use the same options with `attach` to resume that session. `compat` selects
19200 8O1 and `fast` selects 19800 8N1; `--runtime-baud` and
`--runtime-parity` allow controlled comparisons. Bootstrap `--baud`, `--parity`
and `--stop-bits` retain their previous meaning. Existing invocations without
a runtime profile retain their behavior until hardware qualification promotes
a faster default.

The optional `pl2303hxd` backend is macOS-specific and requires libusb. It maps
the exact serial path through IORegistry to the qualified 067b:2303 revision
0400 device, rejects ambiguity, writes the HXD divisor with explicit framing,
and verifies USB line-coding readback. It does not detach the serial driver.
The host preserves an already configured descriptor; it rejects a physical
19800 adoption that would require reprogramming the UART. `posix` retains the
portable termios backend. A USB readback is not a physical clock measurement.

Read-ahead accepts 1, 2, 4 or 8 records. The resident cache has eight slots;
the host's batch size is independently bounded. Every host start increments
a globally locked persistent 32-bit generation without wrapping, advancing past
a copied session's generation too. The initial namespace is randomized to
reduce collisions between independent hosts.
The guest uses advertised CAPS/EPOC support to validate cached data and clears
the cache after errors, writes, warm boots and generation changes. Unsupported
hosts are served without cache reuse. Do not edit a session disk behind its
running host. Cache coherence checks consume serial traffic, so the largest
batch need not be fastest.

Optional console buffering reuses N4's existing 32-byte bulk operation and
flushes at newline, input/status, disk operations and warm boot. Local CRT
rendering remains immediate. Hosts without bulk support retain byte output.
NetDisk CRC uses the shared Robotron-qualified Z80 table implementation;
all 256 entries and 1024 executed state/byte combinations are checked against
an independent bitwise oracle. The installed ROM's CRC routine is unchanged.

`tools/reload_runtime.py` builds a CP/M RAM reload transient for a bench
supervisor that already owns the link. It is not a standalone unattended
uploader: after `RELOAD READY`, that supervisor must stop the disk host,
perform the runtime exchange, and restart the matching disk session. The
emulator tests the copy and recovery paths before physical use.

`tools/benchmark.py` runs repeatable, independently verified file copies and
timed warm boots/console commands through caller-supplied session callbacks.
The 32 KiB fixture consists of `(offset*73+19)&255`; `READTEST` built from
`tools/hardware/read-bench.asm` checks its sequential read length and checksum.
Physical benchmark and soak reports will distinguish tested settings from
experimental options; emulator results alone do not qualify a serial rate.

### Physical checkpoint, 2026-11-12

All four direct 19200/19800, 8O1/8N1 combinations passed 4096-byte
bidirectional checks with zero reported RR1 errors. A RAM-only reload then
booted CP/M at verified adapter 19800 8N1 (calculated divisor rate 19801),
with table CRC, four-record read-ahead and buffered console. TYPE HELLO.TXT
returned the expected text and A> prompt. No reset or ROM change was required.
The host was closed at the owner's requested stopping point.

Five-repeat baseline medians: 8 KiB copy 32.805 s, 32 KiB copy 73.971 s,
warm boot 2.721 s. Matching only the adapter to 19800 gave 32.793 s,
73.612 s and 2.722 s respectively: no material gain by itself.
These copies were independently byte-verified. Initial fixture installation
required a warm boot after an offline disk edit caused an FCB checksum error.

Read-ahead tuning, optimized throughput measurements, the 30-minute/1 MiB
soak and final qualification of the last source changes remain pending.
The earlier full software gate passed; focused tests also passed after the
later cache-miss, generation and custom-rate changes. An earlier emulator
reattach attempt failed because its host binary was rebuilt mid-test; rerunning
with a frozen binary passed. Faster defaults are deliberately not promoted.
