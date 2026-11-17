"""Study 3 preprocessing: terminal streams.

Three tools used by the cleaning and the command reconstruction:
  tokens()      split terminal bytes into text, control bytes and escape sequences
  Visible       the visible text of an output stream with a map back to byte offsets
                (used to recognise the shell prompt by its visible text, A15)
  Screen        a small terminal screen, used to read what a command line looked
                like when Enter was pressed (per-line rule, design sections 6.7 and 9)
  KeyParser     reads keystrokes of one input line
"""
import re

# ------------------------------------------------------------------ tokens
def tokens(data, start=0):
    """Yield (kind, begin, end, payload) for bytes data[start:].
    kind: 'text' (payload str), 'c0' (payload int), 'csi' (payload (params, final)),
    'osc'/'str' (payload bytes), 'esc' (payload int), 'partial' (incomplete tail)."""
    n = len(data)
    i = start
    while i < n:
        b = data[i]
        if b == 0x1b:
            if i + 1 >= n:
                yield ("partial", i, n, None)
                return
            c = data[i + 1]
            if c == 0x5b:                                   # CSI
                j = i + 2
                while j < n and 0x30 <= data[j] <= 0x3f:
                    j += 1
                k = j
                while k < n and 0x20 <= data[k] <= 0x2f:
                    k += 1
                if k >= n:
                    yield ("partial", i, n, None)
                    return
                if 0x40 <= data[k] <= 0x7e:
                    yield ("csi", i, k + 1, (data[i + 2:j].decode("latin-1"), chr(data[k])))
                    i = k + 1
                else:                                       # malformed: drop the ESC [
                    yield ("esc", i, i + 2, c)
                    i += 2
            elif c in (0x5d, 0x50, 0x58, 0x5e, 0x5f):       # OSC, DCS, SOS, PM, APC
                j = i + 2
                end = -1
                while j < n:
                    if data[j] == 0x07 and c == 0x5d:
                        end = j + 1
                        break
                    if data[j] == 0x1b and j + 1 < n and data[j + 1] == 0x5c:
                        end = j + 2
                        break
                    if data[j] == 0x1b and j + 1 >= n:
                        break
                    j += 1
                if end < 0:
                    if n - i > 4096:                        # never terminated: treat as lone ESC
                        yield ("esc", i, i + 2, c)
                        i += 2
                        continue
                    yield ("partial", i, n, None)
                    return
                yield ("osc" if c == 0x5d else "str", i, end, data[i + 2:end])
                i = end
            elif c in (0x28, 0x29, 0x2a, 0x2b, 0x23, 0x25, 0x4f):  # charset, SS3 and similar: one more byte
                if i + 2 >= n:
                    yield ("partial", i, n, None)
                    return
                yield ("esc", i, i + 3, c)
                i += 3
            else:
                yield ("esc", i, i + 2, c)
                i += 2
        elif b < 0x20 or b == 0x7f:
            yield ("c0", i, i + 1, b)
            i += 1
        else:
            j = i
            while j < n and data[j] >= 0x20 and data[j] != 0x7f and data[j] != 0x1b:
                j += 1
            # keep an incomplete UTF-8 tail for the next feed
            cut = j
            if j == n:
                back = 1
                while back <= 3 and j - back >= i:
                    bb = data[j - back]
                    if bb >= 0xc0:
                        need = 2 if bb < 0xe0 else 3 if bb < 0xf0 else 4
                        if back < need:
                            cut = j - back
                        break
                    if bb < 0x80:
                        break
                    back += 1
            if cut > i:
                yield ("text", i, cut, data[i:cut].decode("utf-8", "replace"))
            if cut < j:
                yield ("partial", cut, n, None)
                return
            i = j


# ------------------------------------------------------------------ visible text
class Visible:
    """Visible text of a whole output stream. vis[k] is a character; off[k] is the
    byte offset where it starts; off[len] is the end. CR and LF are kept as
    characters; other controls and all escape sequences are skipped."""

    def __init__(self, data):
        chars = []
        off = []
        for kind, a, b, p in tokens(data):
            if kind == "text":
                raw = data[a:b]
                # byte offset of each decoded character
                pos = a
                for ch in p:
                    chars.append(ch)
                    off.append(pos)
                    pos += len(ch.encode("utf-8", "replace")) if ch != "�" else 1
                    # replacement characters stand for at least one bad byte; offsets are
                    # re-synchronised at the next token, which is all the prompt search needs
            elif kind == "c0" and p in (0x0d, 0x0a):
                chars.append(chr(p))
                off.append(a)
        off.append(len(data))
        self.text = "".join(chars)
        self.off = off


# The lab's two-line shell prompt, by its visible text (A15):
#   ┌─[user@host]─[cwd]            (person's shell; "[✗]─" is added after a failed command)
#   └──╼ $
#   ┌──[user@host]─[cwd]           (harness's shell)
#   └──╼ $
PROMPT_RE = re.compile(
    "┌─{1,2}(?:\\[✗\\]─)?\\[[^\\[\\]\r\n]*@[^\\[\\]\r\n]*\\]─\\[[^\r\n]*?\\]\r*\n└──╼ [$#] ?")
PROMPT_LINE2_RE = re.compile("^└──╼ [$#] ?")
PS2_RE = re.compile("^> ")


def prompt_spans(data):
    """Byte spans (begin, end) of every shell prompt in an output stream. The span
    takes in the colour and paste-mode sequences directly around the prompt."""
    v = Visible(data)
    spans = []
    for m in PROMPT_RE.finditer(v.text):
        a = v.off[m.start()]
        b = v.off[m.end()] if m.end() < len(v.off) else len(data)
        # extend left over escape sequences that sit directly before the prompt
        while True:
            mm = _ESC_TAIL.search(data, max(0, a - 32), a)
            if mm and mm.end() == a:
                a = mm.start()
            else:
                break
        # extend right over SGR sequences that close the prompt, then one space
        while True:
            mm = _SGR_HEAD.match(data, b)
            if mm:
                b = mm.end()
            else:
                break
        if data[b:b + 1] == b" " and not m.group(0).endswith(" "):
            pass      # a space typed by the operator is not part of the prompt
        spans.append((a, b))
    return spans


_ESC_TAIL = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]$")
_SGR_HEAD = re.compile(rb"\x1b\[[0-9;]*m")


def strip_controls(data):
    """Bytes with escape sequences and C0 controls other than CR, LF, TAB removed."""
    out = bytearray()
    for kind, a, b, p in tokens(data):
        if kind == "text":
            out += data[a:b]
        elif kind == "c0" and p in (0x0d, 0x0a, 0x09):
            out.append(p)
    return bytes(out)


# ------------------------------------------------------------------ screen
class Screen:
    """A terminal screen without a height: rows are only ever added. width=None
    means lines never wrap. Enough of VT100/xterm for a shell's line editing."""

    MAXROWS = 600

    def __init__(self, width=None):
        self.W = width
        self.rows = [[]]
        self.wrapped = [False]      # row continues on the next row by automatic wrap
        self.base = 0               # absolute number of rows[0]
        self.r = 0
        self.c = 0
        self.alt = False
        self.saved = (0, 0)
        self.buf = b""
        self.unreliable = 0         # absolute cursor moves outside a full-screen program
        self.paste_marks = 0
        self.vertical = 0           # cursor up/down moves (reset by the caller per line)

    # -- helpers
    def _row(self):
        while self.r >= len(self.rows):
            self.rows.append([])
            self.wrapped.append(False)
        return self.rows[self.r]

    def _trim(self):
        if len(self.rows) > self.MAXROWS:
            cut = len(self.rows) - self.MAXROWS // 2
            del self.rows[:cut]
            del self.wrapped[:cut]
            self.base += cut
            self.r -= cut
            if self.r < 0:
                self.r = 0

    def absrow(self):
        return self.base + self.r

    def _unpend(self):
        if self.W and self.c >= self.W:
            self.c = self.W - 1

    def put(self, ch):
        if self.W and self.c >= self.W:
            self._row()
            self.wrapped[self.r] = True
            self.r += 1
            self.c = 0
        row = self._row()
        if len(row) < self.c:
            row.extend(" " * (self.c - len(row)))
        if self.c < len(row):
            row[self.c] = ch
        else:
            row.append(ch)
        self.c += 1

    def clear(self):
        self.rows = [[]]
        self.wrapped = [False]
        self.base += self.r + 1 + 100000      # earlier anchors can never match again
        self.r = 0
        self.c = 0

    # -- feeding
    def feed(self, data):
        data = self.buf + data
        self.buf = b""
        for kind, a, b, p in tokens(data):
            if kind == "partial":
                self.buf = data[a:b]
                break
            if kind == "csi":
                self._csi(p[0], p[1])
                continue
            if self.alt:
                continue
            if kind == "text":
                for ch in p:
                    self.put(ch)
            elif kind == "c0":
                if p == 0x0d:
                    self.c = 0
                elif p == 0x0a:
                    self._row()
                    self.r += 1
                    self._row()
                    self._trim()
                elif p == 0x08:
                    if self.W and self.c >= self.W:
                        self.c = self.W - 2 if self.W >= 2 else 0
                    elif self.c > 0:
                        self.c -= 1
                elif p == 0x09:
                    self._unpend()
                    self.c = (self.c // 8 + 1) * 8
                    if self.W and self.c >= self.W:
                        self.c = self.W - 1
            elif kind == "esc":
                if p == 0x37:
                    self.saved = (self.absrow(), self.c)
                elif p == 0x38:
                    self.r = max(0, self.saved[0] - self.base)
                    self.c = self.saved[1]
                    self._row()
                elif p == 0x4d:
                    self.r = max(0, self.r - 1)
                elif p in (0x44, 0x45):
                    self.r += 1
                    self._row()
                    if p == 0x45:
                        self.c = 0
                elif p == 0x63:
                    self.clear()

    def _csi(self, params, final):
        private = params.startswith("?")
        nums = []
        for x in params.lstrip("?<=>").split(";"):
            try:
                nums.append(int(x))
            except ValueError:
                nums.append(0)
        n = nums[0] if nums and nums[0] > 0 else 1
        if final in ("h", "l") and private:
            for v in nums:
                if v in (1049, 47, 1047):
                    self.alt = (final == "h")
                elif v == 2004 and final == "h":
                    self.paste_marks += 1
            return
        if self.alt:
            return
        if final == "m":
            return
        if final == "A":
            self._unpend()
            self.r = max(0, self.r - n)
            self.vertical += 1
        elif final in ("B", "e"):
            self._unpend()
            self.r += n
            self._row()
            self.vertical += 1
        elif final in ("C", "a"):
            self._unpend()
            self.c += n
            if self.W and self.c >= self.W:
                self.c = self.W - 1
        elif final == "D":
            self._unpend()
            self.c = max(0, self.c - n)
        elif final in ("G", "`"):
            self.c = n - 1
        elif final in ("H", "f"):
            row = n
            col = nums[1] if len(nums) > 1 and nums[1] > 0 else 1
            if row == 1 and col == 1:
                self.r = 0                 # home; a clear normally follows
                self.c = 0
                self._home = True
            else:
                self.unreliable += 1
                self.c = col - 1
        elif final == "K":
            row = self._row()
            mode = nums[0] if nums else 0
            if mode == 0:
                del row[self.c:]
                self.wrapped[self.r] = False
            elif mode == 1:
                for i in range(min(self.c + 1, len(row))):
                    row[i] = " "
            else:
                del row[:]
                self.wrapped[self.r] = False
        elif final == "J":
            mode = nums[0] if nums else 0
            if mode in (2, 3):
                self.clear()
            elif mode == 0:
                row = self._row()
                del row[self.c:]
                del self.rows[self.r + 1:]
                del self.wrapped[self.r + 1:]
                self.wrapped[self.r] = False
        elif final == "P":
            row = self._row()
            del row[self.c:self.c + n]
        elif final == "@":
            row = self._row()
            if len(row) < self.c:
                row.extend(" " * (self.c - len(row)))
            row[self.c:self.c] = [" "] * n
            if self.W:
                del row[self.W:]
        elif final == "X":
            row = self._row()
            for i in range(self.c, min(self.c + n, len(row))):
                row[i] = " "
        elif final == "L":
            for _ in range(n):
                self.rows.insert(self.r, [])
                self.wrapped.insert(self.r, False)
        elif final == "M":
            for _ in range(n):
                if self.r < len(self.rows):
                    del self.rows[self.r]
                    del self.wrapped[self.r]
            self._row()

    # -- reading
    def logical_line(self):
        """(text, index of the cursor in it, absolute number of its first row)."""
        self._row()
        r0 = self.r
        while r0 > 0 and self.wrapped[r0 - 1]:
            r0 -= 1
        r1 = self.r
        while r1 < len(self.rows) - 1 and self.wrapped[r1]:
            r1 += 1
        parts = []
        for i in range(r0, r1 + 1):
            s = "".join(self.rows[i])
            if i < r1 and self.W:
                s = s.ljust(self.W)[:self.W]
            parts.append(s)
        cur = (self.r - r0) * (self.W or 0) + min(self.c, self.W or self.c)
        return "".join(parts), cur, self.base + r0

    def position(self):
        """Absolute (first row of the logical line, index in the logical line)."""
        _, cur, first = self.logical_line()
        return first, cur


# ------------------------------------------------------------------ keystrokes
HISTORY_CSI = {"A", "B"}                     # up, down
CURSOR_CSI = {"C", "D", "H", "F"}            # right, left, home, end
HISTORY_C0 = {0x10, 0x0e, 0x12, 0x13}        # ^P ^N ^R ^S
CURSOR_C0 = {0x01, 0x05, 0x02, 0x06}         # ^A ^E ^B ^F
EDIT_C0 = {0x0b, 0x19, 0x14, 0x0c, 0x0f, 0x16, 0x18, 0x1f}   # ^K ^Y ^T ^L ^O ^V ^X ^_


class Line:
    """Keystrokes of one input line, as they accumulate."""
    __slots__ = ("chars", "typed", "pasted", "backspaces", "history", "tab", "cursor", "edit",
                 "paste", "records", "t_first", "ranges", "replies", "rec_first",
                 "anchor", "vert0", "w_at_start")

    def __init__(self):
        self.chars = []          # text built from keystrokes alone
        self.typed = 0           # characters typed outside paste markers
        self.pasted = 0          # characters that arrived inside paste markers
        self.backspaces = 0
        self.history = False
        self.tab = False
        self.cursor = False
        self.edit = False
        self.paste = False
        self.records = 0         # input records that carried keys of this line
        self.t_first = None
        self.rec_first = None
        self.ranges = []         # (record index, begin, end) byte ranges of this line
        self.replies = 0
        self.anchor = None
        self.vert0 = 0
        self.w_at_start = None

    def empty(self):
        return not self.chars and not (self.history or self.tab or self.cursor or self.edit)

    def plain(self):
        return not (self.history or self.tab or self.cursor or self.edit)

    def text(self):
        return "".join(self.chars)


def is_terminal_reply(params, final):
    """Cursor-position and device-attribute replies, focus and mouse reports: sent
    by the terminal, not typed (P010 note 2)."""
    if final == "R" and (params == "" or re.match(r"^\??\d+(;\d+)*$", params)):
        return True
    if final == "c" and params[:1] in ("?", ">"):
        return True
    if final in ("I", "O") and params == "":
        return True
    if final in ("M", "m") and params.startswith("<"):
        return True
    if final in ("t", "n", "y", "u") and params:
        return True
    return False
