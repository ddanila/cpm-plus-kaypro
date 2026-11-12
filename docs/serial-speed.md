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
