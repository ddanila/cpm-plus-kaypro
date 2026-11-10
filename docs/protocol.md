# KP2 bootstrap and memory contract

External SIO A uses ports 04/06, 8116 selector 15 at port 00, x16 clocking,
19200 baud, eight data bits, odd parity, one stop bit, no software/hardware flow
control. Keyboard SIO B is independently initialized at 300 8N1 through 05/07
and baud port 0C. KP1's 8N1 bootstrap is intentionally incompatible.

| Direction | Bytes | Meaning |
| --- | --- | --- |
| Host → ROM | `K` | Synchronize |
| ROM → host | `KP2` | Protocol identity |
| Host → ROM | length low, high | Payload size 0036–35FF hex |
| Host → ROM | payload, CRC high, low | Fixed load address C000 |
| ROM → host | 06 or 15 | Checked payload accepted or rejected |
| Host → ROM | `G` | Execute jump entry C033 |

CRC-16/CCITT uses polynomial 1021, initial FFFF, no reflection or final XOR;
it covers payload bytes only. This detects corruption, not malicious input.
All guest polls are bounded; failed/partial transfers print a CRT status line
and return to synchronization. A checked payload is never executed without G.
The host retries initial synchronization until its deadline; it does not replay
an ambiguous completed upload. Reset and start a new session after failure.

The host keeps the same descriptor and framing for the disk-service handoff;
no close/reopen, flush, or parity transition occurs. The platform resets channel
A as it enters runtime services, so the host waits for guest protocol requests.
Bootstrap logs distinguish the intended packet from received identity/ACK;
`bootstrap-packet.bin` is not a measurement of physical line transmission.
Runtime wire captures and process logs are retained in the session.

| Region | Use |
| --- | --- |
| 0000–0FFF at reset | Replacement ROM |
| 1000–2FFF in ROM bank | Unmapped, FF read approximation in native core |
| 3000–3FFF in ROM bank | Video aperture, physically packed into 2 KiB |
| 8000 upwards during bootstrap | Relocated ROM receiver/display code |
| 9D00–BFFF | Nonbanked CP/M system, BIOS entry BC00 |
| C000 upwards | Resident platform, console, queue, shared protocols |
| Below F600 | Build-enforced platform limit |
| F700 | CP/M/loader stack top, with reserved clearance below |

Clearing system PIO A bit 7 selects all RAM; ROM-bank writes below 3000 do
not reach underlying RAM. The ROM relocates before banking. Display routines
use a private resident stack, preserve the caller's stack/registers and prior
interrupt-enable state, restore the bank latch and leave other PIO bits intact.
All memory bounds and artifact hashes are checked by `build/manifest.json`.
