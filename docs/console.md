# Kaypro local and mirrored console

The native console is 80×24. The control contract follows the original
[Kaypro II User's Guide](https://retrocmp.de/kaypro/1982_kaypro-II-users-guide.pdf),
printed page 56 / PDF page 62, not the later 1984 CRTC machine's extensions.

| Input | Behavior |
| --- | --- |
| 07 | Send keyboard bell command if channel B TX can accept it |
| 08 / 0B | Cursor left / up, clamped at the edge |
| 0A | Down, scrolling at bottom |
| 0C | Right, wrapping at right edge |
| 0D | Return to column zero |
| 17 / 18 | Clear through end of screen / line |
| 1A / 1E | Clear and home / home |
| ESC `=` row+32 column+32 | Absolute cursor position |
| ESC `E` / ESC `R` | Insert / delete current line |
| ESC `A` / ESC `G` | Ordinary lowercase / Greek character-ROM slots |
| 09 | Tab to the next eight-column stop (project extension) |

Printing wraps and scrolls. Unknown escape commands are discarded; invalid
cursor parameters cancel that sequence without changing the cursor. Partial
sequences remain pending across calls. Other bytes retain character-ROM slot
semantics, including the documented NUL glyph. Blink is implemented by the
character's high bit; the software cursor overlays that bit and restores the
underlying character when it moves.

The host bridge implements the same cursor/control operations on an ANSI
terminal. ANSI arrow keys become Kaypro control bytes. Its cell model preserves
raw character codes. Printable ASCII is rendered as text; non-ASCII/control
ROM glyph slots display `?` on the host, since PC003's character set is unknown.
Thus the tests establish cell/code equivalence, not identical custom glyphs on
an ANSI terminal. The native PGM renderer can use PC003's actual character dump.

SIO B is explicitly initialized at 300 baud 8N1; it receives complete character
bytes, without Robotron's E0 prefix convention. A 128-byte ring retains oldest
input and counts dropped newest bytes when full. Warm boot hides queued input
from BDOS break polling until CONIN releases it. Local input wins when both
local and remote input are pending; no attempt is made to timestamp-merge them.

Cooperative service runs in console and filesystem routines and every 16 serial
poll iterations. This keeps keyboard service independent of a stalled disk
reply. Qualification reports the worst observed service gap while keyboard
traffic is active, with a one-character bound (83334 CPU clocks at 300 8N1),
and separately counts hardware-FIFO rejection and software overflow. It does
not guarantee input retention in arbitrary transients that never call the BIOS.

Bell behavior and the actual keyboard variant still need a physical check.
MAME documents keyboard variants and an undumped firmware version; its synthetic
keyboard fixture is not evidence that PC003's keyboard has been emulated.
