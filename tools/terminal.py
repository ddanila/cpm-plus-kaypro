"""Kaypro II/ADM-3A screen model and ANSI terminal bridge. MIT."""
class Screen:
    def __init__(self):
        self.cells = [bytearray(b' ' * 80) for _ in range(24)]
        self.row = self.col = self.state = self.pending = self.greek = 0
        self.bells = 0

    def down(self):
        if self.row < 23:
            self.row += 1
        else:
            self.cells.pop(0)
            self.cells.append(bytearray(b' ' * 80))

    def right(self):
        self.col += 1
        if self.col == 80:
            self.col = 0
            self.down()

    def feed(self, data):
        for b in data:
            if self.state:
                state, self.state = self.state, 0
                if state == 1:
                    if b == 61: self.state = 2
                    elif b == 65: self.greek = 0
                    elif b == 71: self.greek = 1
                    elif b == 69:
                        self.cells.insert(self.row, bytearray(b' '*80)); self.cells.pop()
                    elif b == 82:
                        self.cells.pop(self.row); self.cells.append(bytearray(b' '*80))
                elif state == 2 and 32 <= b < 56:
                    self.pending, self.state = b-32, 3
                elif state == 3 and 32 <= b < 112:
                    self.row, self.col = self.pending, b-32
                continue
            if b == 27: self.state = 1
            elif b == 7: self.bells += 1
            elif b == 8: self.col = max(0, self.col-1)
            elif b == 9:
                self.col = (self.col+8)&~7
                if self.col >= 80: self.col = 0; self.down()
            elif b == 10: self.down()
            elif b == 11: self.row = max(0, self.row-1)
            elif b == 12: self.right()
            elif b == 13: self.col = 0
            elif b in (23,24):
                self.cells[self.row][self.col:] = b' '*(80-self.col)
                if b == 23:
                    for row in self.cells[self.row+1:]: row[:] = b' '*80
            elif b == 26:
                for row in self.cells: row[:] = b' '*80
                self.row = self.col = 0
            elif b == 30: self.row = self.col = 0
            else:
                self.cells[self.row][self.col] = b-96 if self.greek and 96<=b<128 else b
                self.right()

    def text(self):
        return b'\n'.join(self.cells)

    def ansi(self):
        # Disable automatic wrapping during repaint, then restore it. Greek ROM
        # slots have no assumed Unicode mapping until PC003's ROM is identified.
        rows=[]
        for i,row in enumerate(self.cells):
            safe=bytes((v&127) if 32 <= (v&127) < 127 else 63 for v in row)
            rows.append(f'\x1b[{i+1};1H'.encode()+safe)
        return b'\x1b[?7l'+b''.join(rows)+b'\x1b[?7h'+f'\x1b[{self.row+1};{self.col+1}H'.encode()

class Keys:
    """Translate ANSI arrows; preserve partial sequences until flush()."""
    MAP={b'\x1b[A':b'\x0b',b'\x1b[B':b'\x0a',b'\x1b[C':b'\x0c',b'\x1b[D':b'\x08',
         b'\x1bOA':b'\x0b',b'\x1bOB':b'\x0a',b'\x1bOC':b'\x0c',b'\x1bOD':b'\x08',b'\x1b[3~':b'\x7f'}
    def __init__(self): self.pending=b''
    def feed(self,data):
        out=bytearray()
        for b in data:
            self.pending+=bytes([b])
            if self.pending in self.MAP:
                out+=self.MAP[self.pending]; self.pending=b''
            elif not any(k.startswith(self.pending) for k in self.MAP):
                out+=self.pending; self.pending=b''
        return bytes(out)
    def flush(self):
        data,self.pending=self.pending,b''
        return data
