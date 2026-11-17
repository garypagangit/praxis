"""Study 3 preprocessing: command reconstruction (design section 6.7, A7, A14, A15).

Turns one login's keystrokes and screen output into a list of commands: when
each was submitted, its text, and where its output ends.

Rules
  - A line is what is typed up to an Enter. An empty line is not a command.
  - Text, per line: the keystrokes, unless they include history recall, Tab or
    cursor movement; then the text is read from the screen. Where the screen
    cannot be read reliably the line keeps its keystrokes and is counted.
  - A line typed at the shell prompt that the shell does not accept as complete
    (continuation prompt, open quote, here-document) is joined with the lines
    that follow: one command.
  - A line submitted while a program is running (a SQL statement, an smbclient
    command, a reply at a password prompt) is a command in both classes.
  - A command's output starts after its Enter and ends when the shell prompt
    comes back or when the operator starts the next line, whichever comes
    first. The prompt is recognised by its visible text (s3_term.PROMPT_RE).
    The next line starts at the first key of a line that has content; Ctrl-C,
    Ctrl-D and Enter on an empty line do not end a command's output (A17).
  - Keys pressed inside a full-screen program are not lines.
"""
import base64
import bisect
import datetime
import re

import s3_term as T

RE_ENV_WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
RE_HEREDOC = re.compile(r"<<(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|\\?([A-Za-z_][\w.-]*))")
OPEN_WORDS = {"do": "done", "if": "fi", "case": "esac", "{": "}"}
CLOSE_WORDS = {"done", "fi", "esac", "}"}


def epoch(iso):
    return datetime.datetime.fromisoformat(iso).timestamp()


def program_name(text):
    """First word of the first line, after NAME=value words and sudo; basename."""
    words = text.split("\n", 1)[0].split()
    i = 0
    while i < len(words) and (RE_ENV_WORD.match(words[i]) or words[i] == "sudo"):
        i += 1
    if i >= len(words):
        return ""
    w = words[i]
    return w.rsplit("/", 1)[-1] if "/" in w else w


def shell_incomplete(text):
    """True when bash would ask for more input after these lines: an open
    quote, a here-document without its closing word, a trailing backslash or
    operator, or an open do/if/case/{ block."""
    lines = text.split("\n")
    pending = []            # here-document closing words still to come
    quote = None
    depth = []
    paren = 0
    cont = False
    for line in lines:
        if pending and quote is None:
            word, strip = pending[0]
            if (line.lstrip("\t") if strip else line) == word:
                pending.pop(0)
            continue
        cont = False
        i = 0
        n = len(line)
        word_start = True
        cur = ""
        new_docs = []

        def end_word(w):
            if w in OPEN_WORDS:
                depth.append(OPEN_WORDS[w])
            elif w in CLOSE_WORDS and depth and depth[-1] == w:
                depth.pop()

        while i < n:
            c = line[i]
            if quote == "'":
                if c == "'":
                    quote = None
                i += 1
                continue
            if quote == '"':
                if c == "\\" and i + 1 < n:
                    i += 2
                    continue
                if c == '"':
                    quote = None
                i += 1
                continue
            if c == "\\":
                if i + 1 >= n:
                    cont = True
                i += 2
                cur += "x"
                continue
            if c in "'\"":
                quote = c
                cur += "x"
                i += 1
                continue
            if c == "#" and cur == "" and (i == 0 or line[i - 1] in " \t;"):
                break
            if c == "<" and line.startswith("<<", i) and not line.startswith("<<<", i):
                m = RE_HEREDOC.match(line, i)
                if m:
                    new_docs.append((m.group(2) or m.group(3) or m.group(4), bool(m.group(1))))
                    i = m.end()
                    continue
            if c in "()":
                paren += 1 if c == "(" else -1
                end_word(cur)
                cur = ""
                i += 1
                continue
            if c in " \t;|&":
                end_word(cur)
                cur = ""
                i += 1
                continue
            cur += c
            i += 1
        end_word(cur)
        if quote is None:
            pending.extend(new_docs)
            stripped = line.rstrip()
            if stripped.endswith("|") or stripped.endswith("&&"):
                cont = True
    return bool(quote or pending or cont or depth or paren > 0)


def infer_widths(recs):
    """Terminal widths shown by the stream itself. When a typed character
    fills the last column, readline prints it followed by a space and a
    carriage return. Returns [(record index, width)]."""
    scr = T.Screen(None)
    found = []
    prev_input = False
    for i, r in enumerate(recs):
        if r["kind"] == "input":
            prev_input = True
            continue
        if r["kind"] != "output":
            continue
        d = r["data"]
        if prev_input and 3 <= len(d) <= 8 and d.endswith(b" \r") and d[-3] >= 0x20:
            scr.feed(d[:-2])
            if not scr.alt and scr.c >= 20:
                found.append((i, scr.c))
            scr.feed(d[-2:])
        else:
            scr.feed(r.get("shown", d))
        prev_input = False
    return found


class Reconstruction:
    """One pass over a login's recorder records.
    recs: list of dicts with kind ('input' / 'output' / other), t (epoch), data."""

    def __init__(self, recs):
        self.recs = recs
        self.idx_out = [i for i, r in enumerate(recs) if r["kind"] == "output"]
        self.idx_in = [i for i, r in enumerate(recs) if r["kind"] == "input"]
        self.out_starts = []
        acc = 0
        for i in self.idx_out:
            self.out_starts.append(acc)
            acc += len(recs[i]["data"])
        self.out_len = acc
        self.out = b"".join(recs[i]["data"] for i in self.idx_out)
        self.prompts = T.prompt_spans(self.out)
        self.prompt_begins = [a for a, b in self.prompts]
        self.commands = []
        self.stats = dict(lines=0, empty_enters=0, interrupts=0, eof_keys=0, fullscreen_input_records=0,
                          terminal_replies=0, plain_lines=0, screen_lines=0, screen_fallback=0,
                          continuation_lines=0, plain_shell_lines=0, plain_shell_agree=0,
                          plain_shell_unreadable=0, prompts=len(self.prompts),
                          ps2_and_syntax_disagree=0)
        self.disagreements = []
        self.widths = infer_widths(recs)
        self._run()
        self._spans()

    # ------------------------------------------------------------ offsets
    def out_off(self, i):
        """Bytes of output that came before record i."""
        j = bisect.bisect_left(self.idx_out, i)
        return self.out_starts[j] if j < len(self.idx_out) else self.out_len

    def rec_of_out(self, off):
        """(record index, byte in record) of an output offset."""
        if not self.idx_out:
            return None, 0
        j = bisect.bisect_right(self.out_starts, off) - 1
        j = max(0, min(j, len(self.idx_out) - 1))
        return self.idx_out[j], off - self.out_starts[j]

    def _width_at(self, i):
        if not self.widths:
            return None
        best = min(self.widths, key=lambda w: abs(w[0] - i))
        return best[1]

    # ------------------------------------------------------------ pass
    def _run(self):
        recs = self.recs
        scr = T.Screen(self._width_at(0))
        state = "running"            # 'prompt', 'cont' or 'running'
        line = T.Line()
        pending = []                 # lines of a command the shell has not accepted yet
        pending_meta = None
        in_paste = False
        keybuf = b""
        # prompt completions by output record
        prompt_at = {}
        for a, b in self.prompts:
            ri, _ = self.rec_of_out(max(a, b - 1))
            prompt_at.setdefault(ri, []).append((a, b))
        # is the output between an input record and the next input record just "> "?
        ps2_after = {}
        for n, i in enumerate(self.idx_in):
            nxt = self.idx_in[n + 1] if n + 1 < len(self.idx_in) else len(recs)
            a, b = self.out_off(i), self.out_off(nxt)
            if b > a and b - a < 200:
                vis = T.strip_controls(self.out[a:b]).replace(b"\r", b"").replace(b"\n", b"")
                ps2_after[i] = (vis == b"> " or vis == b">")
            elif b > a:
                ps2_after[i] = False
        self.line_starts = []        # record index of the first key of every line begun

        def start_line(i, t):
            if line.t_first is None:
                line.t_first = t
                line.rec_first = i
                line.anchor = scr.position() if not scr.alt else None
                line.vert0 = scr.vertical
                line.w_at_start = scr.W
                self.line_starts.append(i)

        def read_screen(in_cont):
            """(text, ok) of the command line on screen."""
            if scr.alt:
                return "", False
            text, cur, first = scr.logical_line()
            if scr.W is None and scr.vertical != getattr(line, "vert0", scr.vertical):
                return "", False
            m = T.PROMPT_LINE2_RE.match(text)
            if m:
                return text[m.end():].rstrip(), True
            if in_cont and T.PS2_RE.match(text):
                return text[2:].rstrip(), True
            anchor = getattr(line, "anchor", None)
            if anchor is not None and anchor[0] == first and anchor[1] <= len(text):
                return text[anchor[1]:].rstrip(), True
            return "", False

        def submit(i, t, n_cr, text, source, at_prompt, lines_meta):
            first = lines_meta[0]
            cmd = dict(rec_first=first["rec_first"], rec_enter=i, t_first=first["t_first"], t_enter=t,
                       text=text, source=source, at_prompt=at_prompt, n_lines=len(lines_meta), n_cr=n_cr,
                       typed=sum(m["typed"] for m in lines_meta), pasted=sum(m["pasted"] for m in lines_meta),
                       backspaces=sum(m["backspaces"] for m in lines_meta),
                       history=any(m["history"] for m in lines_meta), tab=any(m["tab"] for m in lines_meta),
                       cursor=any(m["cursor"] for m in lines_meta), paste=any(m["paste"] for m in lines_meta),
                       edit=any(m["edit"] for m in lines_meta),
                       in_records=sum(m["records"] for m in lines_meta),
                       ranges=[r for m in lines_meta for r in m["ranges"]])
            cmd["in_records"] = len({r[0] for r in cmd["ranges"]}) or 1
            cmd["one_write"] = (cmd["in_records"] == 1)
            self.commands.append(cmd)

        for i, r in enumerate(recs):
            kind = r["kind"]
            if kind == "output":
                scr.feed(r.get("shown", r["data"]))
                if i in prompt_at:
                    scr.alt = False
                    if state == "cont":
                        pending, pending_meta = [], None
                    state = "prompt"
                    w = self._width_at(i)
                    if w != scr.W and line.t_first is None:
                        scr.W = w
                continue
            if kind != "input":
                continue
            carry = len(keybuf)
            data = keybuf + r["data"]
            keybuf = b""
            t = r["t"]
            if scr.alt:
                self.stats["fullscreen_input_records"] += 1
                continue
            rec_cr = [0]
            echo_lines = [None]
            seg_begin = 0            # start of the current line's bytes inside this record
            touched = False

            def note(a, b):
                nonlocal touched
                if not touched:
                    line.records += 1
                    touched = True

            def close_range(end):
                if end > seg_begin:
                    line.ranges.append((i, max(0, seg_begin - carry), max(0, end - carry)))

            toks = list(T.tokens(data))
            # end offset of the last Enter in this record (Enters inside a paste do not submit)
            last_cr_end = [0]
            _p = in_paste
            for kind2, a, b, p in toks:
                if kind2 == "csi" and p[1] == "~" and p[0] in ("200", "201"):
                    _p = (p[0] == "200")
                elif kind2 == "c0" and p == 0x0d and not _p:
                    last_cr_end[0] = b
            for kind2, a, b, p in toks:
                if kind2 == "partial":
                    keybuf = data[a:b]
                    break
                if kind2 == "text":
                    start_line(i, t)
                    note(a, b)
                    for ch in p:
                        line.chars.append(ch)
                    if in_paste:
                        line.pasted += len(p)
                    else:
                        line.typed += len(p)
                    continue
                if kind2 == "csi":
                    params, final = p
                    if T.is_terminal_reply(params, final):
                        self.stats["terminal_replies"] += 1
                        continue
                    if final == "~" and params == "200":
                        start_line(i, t)
                        note(a, b)
                        in_paste = True
                        line.paste = True
                        continue
                    if final == "~" and params == "201":
                        in_paste = False
                        note(a, b)
                        continue
                    start_line(i, t)
                    note(a, b)
                    if final in T.HISTORY_CSI or (final == "~" and params.split(";")[0] in ("5", "6")):
                        line.history = True
                    elif final in T.CURSOR_CSI or (final == "~" and params.split(";")[0] in ("1", "3", "4", "7", "8")):
                        line.cursor = True
                    else:
                        line.edit = True
                    continue
                if kind2 in ("osc", "str"):
                    self.stats["terminal_replies"] += 1
                    continue
                if kind2 == "esc":
                    start_line(i, t)
                    note(a, b)
                    if p == 0x4f:                       # SS3: application cursor keys
                        key = chr(data[b - 1])
                        if key in T.HISTORY_CSI:
                            line.history = True
                        elif key in T.CURSOR_CSI:
                            line.cursor = True
                        else:
                            line.edit = True
                    else:
                        line.edit = True
                    continue
                # ---- C0
                if p == 0x0d:
                    if in_paste:
                        start_line(i, t)
                        note(a, b)
                        line.chars.append("\n")
                        line.pasted += 1
                        continue
                    note(a, b)
                    rec_cr[0] += 1
                    last_in_record = (b == len(data))
                    in_cont = (state == "cont")
                    if line.empty() and not in_cont:
                        # Enter on an empty line: not a command and not the start of a line (A17)
                        self.stats["empty_enters"] += 1
                        line = T.Line()
                        seg_begin = b
                        touched = False
                        continue
                    start_line(i, t)
                    close_range(b)
                    self.stats["lines"] += 1
                    key_text = line.text()
                    scr_text, scr_ok = read_screen(in_cont)
                    if line.plain():
                        text, source = key_text, "keys"
                        self.stats["plain_lines"] += 1
                        if state in ("prompt", "cont") and not line.paste and line.records > 1:
                            # typed lines at the shell: does the screen agree with the keys?
                            self.stats["plain_shell_lines"] += 1
                            if not scr_ok:
                                self.stats["plain_shell_unreadable"] += 1
                            elif scr_text.strip() == key_text.strip():
                                self.stats["plain_shell_agree"] += 1
                            elif len(self.disagreements) < 40:
                                self.disagreements.append(dict(t=t, keys=key_text[:120], screen=scr_text[:120]))
                    elif scr_ok and (scr_text or not key_text.strip()):
                        text, source = scr_text, "screen"
                        self.stats["screen_lines"] += 1
                    else:
                        text, source = key_text, "keys_fallback"
                        self.stats["screen_fallback"] += 1
                    if not text.strip() and not in_cont:
                        self.stats["empty_enters"] += 1
                        self.stats["lines"] -= 1
                        line = T.Line()
                        seg_begin = b
                        touched = False
                        continue
                    meta = dict(rec_first=line.rec_first, t_first=line.t_first, typed=line.typed,
                                pasted=line.pasted, backspaces=line.backspaces, history=line.history,
                                tab=line.tab, cursor=line.cursor, paste=line.paste, edit=line.edit,
                                records=line.records, ranges=line.ranges, source=source)
                    if state in ("prompt", "cont"):
                        pending.append(text)
                        pending_meta = (pending_meta or []) + [meta]
                        syn = shell_incomplete("\n".join(pending))
                        if not syn and echo_lines[0] is None:
                            echo_lines[0] = rec_cr[0]       # the shell runs the text from here on
                        if b <= last_cr_end[0] - 1:
                            # more Enters follow in this write: at the shell prompt every
                            # line of one write is one command
                            inc = True
                        elif rec_cr[0] > 1:
                            inc = False                  # the write is complete as a unit
                        elif last_in_record and i in ps2_after:
                            inc = ps2_after[i]           # the shell's own answer
                            if inc != syn:
                                self.stats["ps2_and_syntax_disagree"] += 1
                        else:
                            inc = syn
                        if inc:
                            state = "cont"
                            self.stats["continuation_lines"] += 1
                        else:
                            while len(pending) > 1 and not pending[-1].strip():
                                pending.pop()
                            srcs = {m["source"] for m in pending_meta}
                            src = "keys" if srcs == {"keys"} else ("screen" if "keys_fallback" not in srcs else "keys_fallback")
                            submit(i, t, echo_lines[0] or rec_cr[0], "\n".join(pending), src, True, pending_meta)
                            rec_cr[0] = 0
                            echo_lines[0] = None
                            pending, pending_meta = [], None
                            state = "running"
                    else:
                        submit(i, t, 1, text, source, False, [meta])
                        rec_cr[0] = 0
                    line = T.Line()
                    seg_begin = b
                    touched = False
                    continue
                if p in (0x7f, 0x08):
                    start_line(i, t)
                    note(a, b)
                    line.backspaces += 1
                    if line.chars:
                        line.chars.pop()
                    continue
                if p == 0x09:
                    start_line(i, t)
                    note(a, b)
                    line.tab = True
                    continue
                if p == 0x03:
                    # the interrupt key ends the line being typed; it is not the start of a line (A17)
                    self.stats["interrupts"] += 1
                    line = T.Line()
                    seg_begin = b
                    touched = False
                    in_paste = False
                    if state == "cont":
                        pending, pending_meta = [], None
                        state = "prompt"
                    continue
                if p == 0x04:
                    if line.empty():
                        self.stats["eof_keys"] += 1          # not the start of a line (A17)
                    else:
                        line.cursor = True
                    continue
                if p == 0x15:
                    start_line(i, t)
                    note(a, b)
                    line.chars = []
                    continue
                if p == 0x17:
                    start_line(i, t)
                    note(a, b)
                    if line.plain():
                        while line.chars and line.chars[-1] == " ":
                            line.chars.pop()
                        while line.chars and line.chars[-1] != " ":
                            line.chars.pop()
                    continue
                if p in T.HISTORY_C0:
                    start_line(i, t)
                    note(a, b)
                    line.history = True
                elif p in T.CURSOR_C0:
                    start_line(i, t)
                    note(a, b)
                    line.cursor = True
                elif p in T.EDIT_C0:
                    start_line(i, t)
                    note(a, b)
                    line.edit = True
            # bytes of an unfinished line in this record
            end = len(data) - len(keybuf)
            if line.t_first is not None and end > seg_begin and touched:
                line.ranges.append((i, max(0, seg_begin - carry), max(0, end - carry)))
        self.line_starts.sort()

    # ------------------------------------------------------------ spans
    def _spans(self):
        cmds = self.commands
        for n, c in enumerate(cmds):
            S = self.out_off(c["rec_enter"])
            # the operator starts the next line
            j = bisect.bisect_right(self.line_starts, c["rec_enter"])
            nxt = self.line_starts[j] if j < len(self.line_starts) else None
            if n + 1 < len(cmds) and cmds[n + 1]["rec_first"] is not None:
                cand = cmds[n + 1]["rec_first"]
                if cand > c["rec_enter"] and (nxt is None or cand < nxt):
                    nxt = cand
                if cmds[n + 1]["rec_enter"] == c["rec_enter"]:
                    nxt = c["rec_enter"]                 # next command came in the same write
            E_next = self.out_off(nxt) if nxt is not None else self.out_len
            k = bisect.bisect_left(self.prompt_begins, S)
            if k < len(self.prompts):
                E_prompt, P_end = self.prompts[k]
            else:
                E_prompt, P_end = self.out_len + 1, None
            if E_prompt <= E_next:
                E, ended = E_prompt, "prompt"
            elif nxt is not None:
                E, ended = E_next, "next_line"
            else:
                E, ended = self.out_len, "end"
            # the Enter's own echo: one line break for each Enter of the command in that write
            pos = S
            for _ in range(max(1, c["n_cr"])):
                q = self.out.find(b"\n", pos, E)
                if q < 0:
                    pos = E if ended != "prompt" else pos
                    break
                pos = q + 1
            echo_end = min(pos, E)
            c["out_from"] = S
            c["out_begin"] = echo_end
            c["out_end"] = E
            c["ended_by"] = ended
            c["prompt_end"] = P_end if ended == "prompt" else None
            c["next_prompt_end"] = P_end
            c["t_prompt"] = None
            if k < len(self.prompts):
                ri, _ = self.rec_of_out(max(self.prompts[k][0], self.prompts[k][1] - 1))
                c["t_prompt"] = self.recs[ri]["t"]
            seg = self.out[echo_end:E]
            c["out_raw_bytes"] = len(seg)
            c["out_text_bytes"] = len(T.strip_controls(seg).replace(b"\r", b""))
            ri, _ = self.rec_of_out(max(echo_end, E - 1))
            c["t_out_end"] = self.recs[ri]["t"] if ri is not None and E > echo_end else c["t_enter"]
            c["text"] = c["text"].strip()
            c["program"] = program_name(c["text"])
            c["is_exit"] = c["text"] in ("exit", "logout")
        for c in cmds:
            c["closing_exit"] = False
        if cmds:
            last = [l for l in cmds[-1]["text"].split("\n") if l.strip()]
            if last and last[-1].strip() in ("exit", "logout"):
                cmds[-1]["closing_exit"] = True
