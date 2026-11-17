"""Study 3 preprocessing: cleaning rules (design section 6).

All rules are fixed patterns, applied the same way to every session, and none
looks at the label. The same pattern objects are used by the leak audit (6.6).
"""
import re

# ------------------------------------------------------------------ streams
class SegStream:
    """The bytes of consecutive recorder records as one stream, so that a pattern
    is found even when a token was split between two records (single keystrokes,
    or terminal output cut at a read boundary). After a substitution each record
    keeps its own share: the replacement is handed out, in order, to the records
    the match covered, as many bytes to each as it lost; any surplus goes to the
    last of them."""

    def __init__(self, chunks):
        self.data = b"".join(chunks)
        self.ends = []
        acc = 0
        for c in chunks:
            acc += len(c)
            self.ends.append(acc)
        self.split_matches = 0

    def chunks(self):
        out = []
        prev = 0
        for e in self.ends:
            out.append(self.data[prev:e])
            prev = e
        return out

    def start_of(self, i):
        return self.ends[i - 1] if i > 0 else 0

    def replace_spans(self, spans):
        """spans: sorted, non-overlapping (begin, end, replacement bytes)."""
        if not spans:
            return 0
        out = bytearray()
        new_ends = []
        ei = 0
        pos = 0
        ends = self.ends
        n_ends = len(ends)
        for a, b, r in spans:
            # boundaries up to the match start
            while ei < n_ends and ends[ei] <= a:
                new_ends.append(len(out) + (ends[ei] - pos))
                ei += 1
            out += self.data[pos:a]
            base = len(out)
            inside = False
            while ei < n_ends and ends[ei] < b:
                new_ends.append(base + min(ends[ei] - a, len(r)))
                ei += 1
                inside = True
            if inside:
                self.split_matches += 1
            out += r
            pos = b
        while ei < n_ends:
            new_ends.append(len(out) + (ends[ei] - pos))
            ei += 1
        out += self.data[pos:]
        self.data = bytes(out)
        self.ends = new_ends
        return len(spans)

    def sub(self, regex, repl):
        """repl: bytes, or a function of the match returning bytes (None = leave)."""
        spans = []
        for m in regex.finditer(self.data):
            r = repl(m) if callable(repl) else repl
            if r is None or r == m.group(0):
                continue
            spans.append((m.start(), m.end(), r))
        return self.replace_spans(spans)


# ------------------------------------------------------------------ 6.1 Enter
RE_ENTER = re.compile(rb"\r\n|\n")          # CRLF and LF become CR


# ------------------------------------------------------------------ 6.2 identity
USER = b"op_user"
UIDNUM = b"10001"
IP_PLACEHOLDER = b"REDACTED_IP"

# any address in 100.64.0.0/10
RE_CLIENT_IP = re.compile(rb"(?<![\d.])100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}(?![\d.])")
RE_ACCOUNT = re.compile(rb"ahir-p\d{3}")
RE_UID_BARE = re.compile(rb"(?<!\d)24\d{3}(?!\d)")
RE_UID_FIELD = re.compile(rb"\b((?:a|e|s|fs|o|oa|sa)?[ug]id|id|ID)=24\d{3}\b")
RE_PCODE = re.compile(rb"(?<![A-Za-z0-9])([Pp])0\d\d(?=_|(?![A-Za-z0-9]))")
RE_ATTEMPT = re.compile(rb"(?i)(ahir)\d\d")
# dated client release folders inside a validator-family path
RE_FAMILY_PATH = re.compile(rb"/(?:opt|etc)/goad-autonomy/[^\s'\":;,)]*")
RE_DATE_TOKEN = re.compile(rb"\d{8}(?:-v\d+)?")

IDENTITY_RULES = [
    ("client_address", RE_CLIENT_IP, IP_PLACEHOLDER),
    ("account_name", RE_ACCOUNT, USER),
    ("participant_code", RE_PCODE, lambda m: m.group(1) + b"NNN"),
    ("attempt_code", RE_ATTEMPT, lambda m: m.group(1) + b"NN"),
    ("release_folder_date", RE_FAMILY_PATH,
     lambda m: RE_DATE_TOKEN.sub(b"DATE", m.group(0))),
]


def scrub_identity_stream(seg, counts, bare_uid=True):
    """Identity rules on a SegStream of recorder text."""
    for name, rx, rep in IDENTITY_RULES:
        n = seg.sub(rx, rep)
        if n:
            counts[name] = counts.get(name, 0) + n
    if bare_uid:
        n = seg.sub(RE_UID_BARE, UIDNUM)
        if n:
            counts["user_number_bare"] = counts.get("user_number_bare", 0) + n


def scrub_identity_bytes(b, counts, bare_uid=False):
    """Identity rules on one piece of text (an audit field)."""
    for name, rx, rep in IDENTITY_RULES:
        b, n = rx.subn(rep, b)
        if n:
            counts[name] = counts.get(name, 0) + n
    if bare_uid:
        b, n = RE_UID_BARE.subn(UIDNUM, b)
        if n:
            counts["user_number_bare"] = counts.get("user_number_bare", 0) + n
    return b


# ------------------------------------------------------------------ 6.3 wrapper
_WRAP_HEAD = rb"printf '\\nAO_([0-9a-f]{32})_BEGIN\\n'; (timeout --signal=TERM --kill-after=\d+s \d+s )?bash -c "
_WRAP_TAIL = rb"; ao_status=\$\?; printf '\\nAO_\1_END:%s\\n' \"\$ao_status\""
# a wrapped input: the whole write, ending in Enter (CR after the Enter rule)
RE_WRAP_INPUT = re.compile(_WRAP_HEAD + rb"(.*?)" + _WRAP_TAIL + rb"\r", re.S)
# the same text shown as program output (shell history, A6): no Enter at the end
RE_WRAP_TEXT = re.compile(_WRAP_HEAD + rb"(.*?)" + _WRAP_TAIL, re.S)
RE_WRAP_HEAD_PIECE = re.compile(rb"printf '\\nAO_[0-9a-f]{32}_BEGIN\\n'; (?:timeout --signal=TERM --kill-after=\d+s \d+s )?(?:bash -c )?")
RE_WRAP_TAIL_PIECE = re.compile(rb"; ao_status=\$\?; printf '\\nAO_[0-9a-f]{32}_END:%s\\n' \"\$ao_status\"")
RE_MARK_BEGIN = re.compile(rb"(?:\r?\n)?AO_([0-9a-f]{32})_BEGIN\r?\n")
RE_MARK_END = re.compile(rb"(?:\r?\n)?AO_([0-9a-f]{32})_END:(-?\d+)\r?\n")
RE_MARK_ANY = re.compile(rb"AO_[0-9a-f]{32}_(?:BEGIN|END(?::(?:%s|-?\d+))?)(?:\\n)?")
# what readline leaves on screen when a long line scrolls sideways
RE_SCROLL_FRAGMENT = re.compile(rb"\r?<[^\r\n]*(?:\$ao_status\"|_END:%s|ao_status=|--kill-after=\d+s)[^\r\n]*")
# pieces of wrapper text that a program printed cut short (a history line cut at a column)
RE_WRAP_TAIL_CUT = re.compile(rb";? ?ao_status=[^\r\n]*")
RE_WRAP_HEAD_CUT = re.compile(rb"printf '\\nAO_[0-9a-f]*(?:_BEGIN)?(?:\\n)?'?;? ?")
RE_WRAP_TIMEOUT_PIECE = re.compile(rb"timeout --signal=TERM --kill-after=\d+s \d+s (?:bash -c )?")
RE_PROBE_TEXT = re.compile(rb"AI_OPERATOR_SESSION_READY(?:\r?\n)?")
PROBE_INNER = b"printf AI_OPERATOR_SESSION_READY"
RE_WRAPPER_TIMEOUT_ARGS = (re.compile(r"^--kill-after=\d+s$"), re.compile(r"^\d+s$"))


def shell_unquote(raw):
    """The word bash would pass to `bash -c`: 'single quoted', "double quoted" and
    bare pieces joined. Returns (text, ok)."""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i:i + 1]
        if c == b"'":
            j = raw.find(b"'", i + 1)
            if j < 0:
                return raw, False
            out += raw[i + 1:j]
            i = j + 1
        elif c == b'"':
            j = i + 1
            while j < n and raw[j:j + 1] != b'"':
                if raw[j:j + 1] == b"\\" and j + 1 < n and raw[j + 1:j + 2] in (b'"', b"\\", b"$", b"`"):
                    out += raw[j + 1:j + 2]
                    j += 2
                else:
                    out += raw[j:j + 1]
                    j += 1
            if j >= n:
                return raw, False
            i = j + 1
        elif c == b"\\" and i + 1 < n:
            out += raw[i + 1:i + 2]
            i += 2
        elif c in (b" ", b"\t", b";", b"&", b"|"):
            return raw, False          # more than one word: not the wrapper's form
        else:
            out += c
            i += 1
    return bytes(out), True


# ------------------------------------------------------------------ 6.4 validator
FAMILY_NEEDLES = ("goad-apt29", "/opt/goad-autonomy/", "/etc/goad-autonomy/", "goad-challenge", "/opt/goad-exercise/")
RE_VALIDATOR_PROGRAM = re.compile(r"^(?:goad-apt29[\w.-]*|goad-challenge)$")
RE_FAMILY_SCRIPT = re.compile(r"^(?:.*/)?(?:goad-apt29[\w.-]*|goad-challenge)$|^/opt/goad-exercise/.*\.py$|^/opt/goad-autonomy/.*/bin/[^/]+$")
RE_INTERPRETER = re.compile(r"^(?:python[\d.]*|bash|sh|dash|zsh|perl|ruby|env)$")
# placeholder for family names left in kept text (A6); target content such as
# http://<target>/goad-autonomy/ is not touched
VALIDATOR_NAME_RULES = [
    (re.compile(rb"goad-apt29(?:-[A-Za-z_][\w-]*)?"), b"validator"),
    (re.compile(rb"goad-challenge"), b"validator"),
    (re.compile(rb"(?<![\w.])/(opt|etc)/goad-autonomy(?![\w-])"), lambda m: b"/" + m.group(1) + b"/validator"),
    (re.compile(rb"(?<![\w.])/opt/goad-exercise(?![\w-])"), b"/opt/validator"),
]


def has_family_needle(strings):
    for s in strings:
        for n in FAMILY_NEEDLES:
            if n in s:
                return True
    return False


# ------------------------------------------------------------------ 6.5 scaffolding
RE_SCRATCH = [
    (re.compile(rb"((?:~|/home/op_user)/)ok(?=[/\s'\";\]]|$)"), lambda m: m.group(1) + b"workdir"),
    (re.compile(rb"((?:~|/home/op_user)/)stage\d\d(?=[/\s'\";\]]|$)"), lambda m: m.group(1) + b"workdir"),
]
TOOLING_NEEDLES = ("/PinnedCollector/", "/exercise_autonomy/")
# the same tooling names when a program prints them in kept recorder text
TOOLING_TEXT_RULES = [
    (re.compile(rb"/PinnedCollector(?=/)"), b"/tooling"),
    (re.compile(rb"/exercise_autonomy(?=/)"), b"/tooling"),
]


# ------------------------------------------------------------------ 6.6 leak audit
# Everything 6.2-6.5 should have removed, searched with the same patterns.
LEAK_PATTERNS = [
    ("account_name", RE_ACCOUNT),
    ("client_address", RE_CLIENT_IP),
    ("participant_code", RE_PCODE),
    ("attempt_code", RE_ATTEMPT),
    ("wrapper_marker", re.compile(rb"AO_[0-9a-f]{32}")),
    ("wrapper_status", re.compile(rb"ao_status")),
    ("wrapper_timeout", re.compile(rb"timeout --signal=TERM --kill-after=")),
    ("wrapper_end_format", re.compile(rb"_END:%s")),
    ("readiness_probe", re.compile(rb"AI_OPERATOR_SESSION_READY|SESSION_READY")),
    ("validator_name", re.compile(rb"goad-apt29|goad-challenge")),
    ("validator_path", re.compile(rb"/opt/goad-autonomy/|/etc/goad-autonomy/|/opt/goad-exercise/")),
    ("collection_tooling", re.compile(rb"/PinnedCollector/|/exercise_autonomy/")),
    ("scratch_dir", re.compile(rb"(?:~|/home/op_user)/(?:ok|stage\d\d)(?=[/\s'\";\]]|$)")),
    ("home_identity", re.compile(rb"/home/ahir")),
]
LEAK_UID_FIELD = re.compile(rb"\b(?:(?:a|e|s|fs|o|oa|sa)?[ug]id|id|ID)=24\d{3}\b")
LEAK_UID_BARE = RE_UID_BARE
