"""Step 10: feature table, column file and per-command table.

Implements `real_lab3_feature_trial_design.md` sections 3 and 4 (60 columns in four tiers).

Reads only `data/`: the window table, the records of each kept window, the cleaned recorder
stream of each login used and the command list written by the preprocessing. Every input is
checked against Freeze 1 before it is read. It never reads a label, the split file, a stage
or the description files, and it does not find commands again: the command list is the one
written by step 4.

Writes `data/features/w30/` and `w60/`:
  features.csv          one row for each kept window: window_id and the 60 columns; undefined is empty
  feature_columns.json  tier, kind, definition and undefined rule of every column, with input and output hashes
  per_command.jsonl     for the EDA: command text, entry style, programs started (commands of kept windows)
and `reports/10_features_report.json`.

Every feature is a fixed rule applied to one window and, for the context tier, to earlier
windows of the same login. Nothing is fitted across windows.

Version 1.1 (user, 2026-11-13, F13 and F14 of the design): programs that ran before a login's
first submitted line are not counted, and gap_autocorr needs four gaps.

Run:  python3 -I -B code/features/step10_features.py
"""
import base64
import bisect
import csv
import datetime
import difflib
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, CODE)                      # allows python3 -I; the terminal tokens of the preprocessing
import s3_term as T

FEATURE_VERSION = "study3-features-1.1"
ROOT = os.environ.get("S3_ROOT") or os.path.dirname(CODE)
OUT_ROOT = os.environ.get("S3_FEATURE_OUT") or ROOT          # redirect for the rerun check
LENGTHS = [("w30", 30.0, 4), ("w60", 60.0, 2)]               # name, seconds, look-back windows (2 minutes)
FLAG_CAP = 12
SIMILAR_SAME_PROGRAM = 0.6
SIMILAR_OTHER_PROGRAM = 0.8
SIMILAR_CHARS = 200
WINDOW_COLUMNS_READ = ["window_id", "session_key", "login_key", "w_index",
                       "n_input", "n_output", "n_exec", "keep"]          # never stage, stage_group

# ------------------------------------------------------------------ section 4.5: patterns and constants
ERROR_LINE = ["command not found", "no such file or directory", "permission denied", "syntax error", "error:",
              "failed", "denied", "refused", "timed out", "traceback (most recent call last)"]   # any letter case
SHELL_ERROR_LINE = ["command not found", "No such file or directory", "Permission denied", "syntax error",
                    "cannot access", "Is a directory", "Not a directory", "invalid option"]      # as written
RE_ENV_WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
RE_HEREDOC = re.compile(r"<<(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|\\?([A-Za-z_][\w.-]*))")
RE_SINGLE_QUOTED = re.compile(r"'[^']*'")
RE_PIPE = re.compile(r"(?<!\|)\|(?!\|)")
RE_CHAIN = re.compile(r"&&|\|\||;")
RE_REDIRECT = re.compile(r"[<>]")
RE_HELP = re.compile(r" --help| -h(?![\w-])|^(?:man|help) ", re.M)
ALT_SCREEN = (1049, 47, 1047)
PASTE_END = b"\x1b[201~"

# ------------------------------------------------------------------ columns (design section 4)
C, S, TM, R, SH, EN, CO = "count", "size", "time", "ratio", "share", "entropy", "correlation"
COLUMNS = [
    # 4.1 behavior (18)
    ("cmd_count", "behavior", C, "Commands submitted in the window", "never"),
    ("gap_mean", "behavior", TM, "Mean of the gaps of the window's commands", "no gap in the window"),
    ("gap_median", "behavior", TM, "Median of the gaps of the window's commands", "no gap in the window"),
    ("gap_min", "behavior", TM, "Smallest gap of the window's commands", "no gap in the window"),
    ("gap_max", "behavior", TM, "Largest gap of the window's commands", "no gap in the window"),
    ("gap_std", "behavior", TM, "Standard deviation of the gaps of the window's commands", "no gap in the window"),
    ("gap_cv", "behavior", R, "gap_std / gap_mean", "no gap, or mean 0"),
    ("gap_autocorr", "behavior", CO, "Correlation between each gap and the next, within the window", "fewer than 4 gaps, or no variation"),
    ("exec_count", "behavior", C, "Programs started by the login in the window, from the login's first submitted line onward", "never"),
    ("exec_distinct", "behavior", C, "Distinct programs among them", "never"),
    ("exec_per_cmd", "behavior", R, "exec_count / cmd_count", "no command"),
    ("proc_depth_max", "behavior", C, "Longest parent-to-child chain of program starts; the login shell is 0", "never"),
    ("output_bytes", "behavior", S, "Program output bytes that appear in the window", "never"),
    ("output_per_cmd_mean", "behavior", S, "Mean of the total output of each command submitted in the window", "no command"),
    ("output_per_cmd_cv", "behavior", R, "Standard deviation / mean of the total output of each command submitted in the window", "no command, or mean 0"),
    ("fail_ratio", "behavior", SH, "Share of the window's commands whose output holds an error line", "no command"),
    ("shell_error_count", "behavior", C, "Shell error lines in the output of the window's commands", "never"),
    ("retry_count", "behavior", C, "Failed commands in the window that are followed by a similar command", "never"),
    # 4.2 command content (14)
    ("chars_submitted", "command_content", S, "Characters of command text submitted", "never"),
    ("cmd_len_mean", "command_content", S, "Mean length of each command's first line", "no command"),
    ("cmd_len_max", "command_content", S, "Largest length of a command's first line", "no command"),
    ("cmd_unique", "command_content", C, "Distinct command texts", "never"),
    ("cmd_diversity", "command_content", R, "cmd_unique / cmd_count (H1)", "no command"),
    ("transition_entropy", "command_content", EN, "Entropy of the program-to-program transitions in the window, in bits (H1)", "fewer than 2 commands"),
    ("prog_distinct", "command_content", C, "Distinct program names (the first word of each command)", "never"),
    ("prog_entropy", "command_content", EN, "Entropy of the program-name counts, in bits", "no command"),
    ("flags_per_cmd", "command_content", R, "Mean number of flags in a command, capped at 12 a command", "no command"),
    ("pipes_per_cmd", "command_content", R, "Mean number of pipes in a command", "no command"),
    ("chain_ratio", "command_content", SH, "Share of commands that chain with &&, || or ;", "no command"),
    ("redirect_ratio", "command_content", SH, "Share of commands with < or >", "no command"),
    ("help_count", "command_content", C, "Commands that ask for help", "never"),
    ("io_ratio", "command_content", R, "output_bytes / chars_submitted", "no characters"),
    # 4.3 context (12)
    ("ctx_cmd_count", "context", C, "Sum of cmd_count over the look-back", "never", "behavior"),
    ("ctx_exec_count", "context", C, "Sum of exec_count over the look-back", "never", "behavior"),
    ("ctx_output_bytes", "context", S, "Sum of output_bytes over the look-back", "never", "behavior"),
    ("ctx_active_windows", "context", C, "Look-back windows with at least one command", "never", "behavior"),
    ("ctx_chars_submitted", "context", S, "Sum of chars_submitted over the look-back", "never", "command_content"),
    ("ctx_cmd_len_max", "context", S, "Longest command (first line) in the look-back", "no command in the look-back", "command_content"),
    ("ctx_cmd_diversity", "context", R, "cmd_diversity over the commands of the look-back and the window together (H1)", "no command", "command_content"),
    ("ctx_transition_entropy", "context", EN, "transition_entropy over the commands of the look-back and the window together, in order (H1)", "fewer than 2 commands", "command_content"),
    ("ctx_entry_typed", "context", C, "Sum of entry_typed over the look-back", "never", "input_channel"),
    ("ctx_entry_paste", "context", C, "Sum of entry_paste over the look-back", "never", "input_channel"),
    ("ctx_entry_recall", "context", C, "Sum of entry_recall over the look-back", "never", "input_channel"),
    ("ctx_entry_line", "context", C, "Sum of entry_line over the look-back", "never", "input_channel"),
    # 4.4 input channel (16)
    ("entry_typed", "input_channel", C, "Commands typed", "never"),
    ("entry_paste", "input_channel", C, "Commands pasted", "never"),
    ("entry_recall", "input_channel", C, "Commands recalled from history", "never"),
    ("entry_line", "input_channel", C, "Commands that arrived as a whole line in one write", "never"),
    ("typed_ratio", "input_channel", SH, "entry_typed / cmd_count", "no command"),
    ("paste_ratio", "input_channel", SH, "entry_paste / cmd_count", "no command"),
    ("line_ratio", "input_channel", SH, "entry_line / cmd_count", "no command"),
    ("interkey_median", "input_channel", TM, "Median time between keystrokes in typed commands", "fewer than 3 intervals"),
    ("interkey_cv", "input_channel", R, "Standard deviation / mean of the time between keystrokes in typed commands", "fewer than 3 intervals, or mean 0"),
    ("backspace_rate", "input_channel", R, "Backspaces / characters typed, in typed commands", "no typed characters"),
    ("paste_enter_latency", "input_channel", TM, "Median time from the end of a paste to its Enter", "no pasted command"),
    ("multi_cmd_write_ratio", "input_channel", SH, "Share of commands that arrived several to one write", "no command"),
    ("fullscreen_keys", "input_channel", C, "Input records while a full-screen program is open", "never"),
    ("compose_time_median", "input_channel", TM, "Median time from a command's first keystroke to its Enter", "no command"),
    ("input_writes_per_cmd", "input_channel", R, "Input records / cmd_count", "no command"),
    ("input_bytes", "input_channel", S, "Raw input bytes", "never"),
]
NAMES = [c[0] for c in COLUMNS]
EXPECTED_TIER_COUNTS = {"behavior": 18, "command_content": 14, "context": 12, "input_channel": 16}


# ------------------------------------------------------------------ small helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def epoch(iso):
    return datetime.datetime.fromisoformat(iso).timestamp()


def mean(x):
    return sum(x) / float(len(x))


def pstdev(x):
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / float(len(x)))


def median(x):
    s = sorted(x)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def entropy_bits(counts):
    n = float(sum(counts))
    return -sum((c / n) * math.log(c / n, 2) for c in counts if c)


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sx = sum((a - mx) ** 2 for a in x)
    sy = sum((b - my) ** 2 for b in y)
    if sx <= 0 or sy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy)


def count_of(items):
    d = {}
    for it in items:
        d[it] = d.get(it, 0) + 1
    return d


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    s = "%.6f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ command text (section 4.5)
def program_name(text):
    """First word of the first line, after NAME=value words and sudo; the part after the last /."""
    words = text.split("\n", 1)[0].split()
    i = 0
    while i < len(words) and (RE_ENV_WORD.match(words[i]) or words[i] == "sudo"):
        i += 1
    if i >= len(words):
        return ""
    w = words[i]
    return w.rsplit("/", 1)[-1] if "/" in w else w


def without_heredoc_bodies(text):
    """The lines between a here-document's opening line and its closing word are set aside (F12)."""
    out, waiting = [], []                       # waiting: closing words still open, with their tab rule
    for line in text.split("\n"):
        if waiting:
            word, strip_tabs = waiting[0]
            if (line.lstrip("\t") if strip_tabs else line).rstrip("\r") == word:
                waiting.pop(0)
                out.append(line)
            continue                            # a body line: set aside
        out.append(line)
        for m in RE_HEREDOC.finditer(line):
            waiting.append((m.group(2) or m.group(3) or m.group(4), m.group(1) == "-"))
    return "\n".join(out)


def shape_counts(text):
    shape = without_heredoc_bodies(text)
    unquoted = RE_SINGLE_QUOTED.sub("", shape)
    return dict(flags=min(FLAG_CAP, shape.count(" -")),
                pipes=len(RE_PIPE.findall(unquoted)),
                chain=1 if RE_CHAIN.search(unquoted) else 0,
                redirect=1 if RE_REDIRECT.search(unquoted) else 0,
                help=1 if RE_HELP.search(text) else 0)


def similar(a, b):
    ratio = difflib.SequenceMatcher(None, a["text"][:SIMILAR_CHARS], b["text"][:SIMILAR_CHARS]).ratio()
    return ratio > (SIMILAR_SAME_PROGRAM if a["prog"] == b["prog"] else SIMILAR_OTHER_PROGRAM)


def entry_style(c):
    """In this order: recalled, pasted, whole line, typed (section 4.5)."""
    if c["has_history_key"]:
        return "recall"
    if c["has_paste"]:
        return "paste"
    if c["one_write"]:
        return "line"
    return "typed"


def exec_program(r):
    p = r.get("path") or r.get("exe") or r.get("comm") or ""
    return p.rsplit("/", 1)[-1]


# ------------------------------------------------------------------ inputs
class Inputs:
    """Opens only data files of the feature step, checks each against Freeze 1, logs its hash."""
    ALLOWED = ("data/windows/", "data/commands/", "data/cleaned/")
    REFUSED = ("data/labels", "data/splits", "data/description", "_private", "set_aside", "AHIR Participant Evidence")

    def __init__(self):
        with open(os.path.join(ROOT, "reports", "FREEZE_1.json"), encoding="utf-8") as f:
            self.freeze = json.load(f)["files"]
        self.freeze_sha256 = sha256_file(os.path.join(ROOT, "reports", "FREEZE_1.json"))
        self.opened = {}

    def path(self, rel):
        if any(x in rel for x in self.REFUSED) or not rel.startswith(self.ALLOWED):
            raise SystemExit("REFUSED: the feature step never opens " + rel)
        if rel.endswith(".audit.jsonl"):
            raise SystemExit("REFUSED: exec events are read from the window files: " + rel)
        p = os.path.join(ROOT, *rel.split("/"))
        if rel not in self.opened:
            digest = sha256_file(p)
            frozen = self.freeze.get(rel)
            if frozen is None or frozen["sha256"] != digest:
                raise SystemExit("STOP: input does not match Freeze 1: " + rel)
            self.opened[rel] = digest
        return p


def read_windows(inp, wl):
    rows = []
    with open(inp.path("data/windows/%s/windows.csv" % wl), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({k: r[k] for k in WINDOW_COLUMNS_READ})         # stage columns are never kept
    for r in rows:
        r["w_index"], r["keep"] = int(r["w_index"]), int(r["keep"])
        for k in ("n_input", "n_output", "n_exec"):
            r[k] = int(r[k])
    return rows


class Login:
    """One login's cleaned recorder stream and command list, independent of the window length."""

    def __init__(self, inp, sk, lk):
        self.sk, self.lk = sk, lk
        kinds, times, datas = [], [], []
        with open(inp.path("data/cleaned/%s/%s.recorder.jsonl" % (sk, lk)), encoding="utf-8") as f:
            for line in f:
                m = json.loads(json.loads(line)["message"])
                kinds.append(m["kind"])
                times.append(epoch(m["time"]))
                datas.append(base64.b64decode(m["data_base64"]) if m.get("data_base64") else b"")
        starts = [i for i, k in enumerate(kinds) if k == "start"]
        if len(starts) != 1:
            raise SystemExit("%s: %d start records" % (lk, len(starts)))
        t0 = times[starts[0]]
        self.kinds, self.datas = kinds, datas
        self.t = [x - t0 for x in times]                       # seconds since the login's start
        self.idx_out = [i for i, k in enumerate(kinds) if k == "output"]
        self.out_starts, acc = [], 0
        for i in self.idx_out:
            self.out_starts.append(acc)
            acc += len(datas[i])
        self.out_len = acc
        self.out = b"".join(datas[i] for i in self.idx_out)
        self._per_record = None
        self._alt_events()
        with open(inp.path("data/commands/%s/%s.commands.jsonl" % (sk, lk)), encoding="utf-8") as f:
            self.all_lines = [json.loads(line) for line in f]
        self._commands()

    # ---- offsets in the output stream
    def out_off(self, i):
        j = bisect.bisect_left(self.idx_out, i)
        return self.out_starts[j] if j < len(self.idx_out) else self.out_len

    def stream_off(self, pair):
        rec, byte = pair
        return 0 if rec is None else self.out_off(rec) + byte

    def rec_at(self, off):
        j = bisect.bisect_right(self.out_starts, off) - 1
        return self.idx_out[max(0, min(j, len(self.idx_out) - 1))]

    # ---- full-screen programs: between the alternate-screen on and off sequences
    def _alt_events(self):
        events = []
        for kind, a, b, p in T.tokens(self.out):
            if kind == "csi" and p[1] in ("h", "l") and p[0].startswith("?"):
                for x in p[0].lstrip("?").split(";"):
                    if x.isdigit() and int(x) in ALT_SCREEN:
                        events.append((a, p[1] == "h"))
        for a, b in T.prompt_spans(self.out):                  # a shell prompt closes a full-screen program
            events.append((a, False))
        events.sort()
        self.alt_offsets = [e[0] for e in events]
        self.alt_states = [e[1] for e in events]

    def fullscreen_at(self, i):
        j = bisect.bisect_right(self.alt_offsets, self.out_off(i) - 1) - 1 if self.out_off(i) > 0 else -1
        return self.alt_states[j] if j >= 0 else False

    # ---- commands
    def _commands(self):
        lines = self.all_lines
        by_enter = count_of(c["in_enter"] for c in lines)
        cmds, prev = [], None
        for k, c in enumerate(lines):
            if c["is_exit"]:
                continue                                        # exit and logout are not commands
            d = dict(c)
            d["prog"] = program_name(c["text"])
            d["first_len"] = len(c["text"].split("\n", 1)[0])
            d["entry"] = entry_style(c)
            d["gap"] = None if prev is None else c["t_enter"] - prev["t_enter"]
            d["multi_write"] = by_enter[c["in_enter"]] > 1
            d["compose"] = max(0.0, c["t_enter"] - c["t_first_key"])
            d["t_next_line"] = lines[k + 1]["t_enter"] if k + 1 < len(lines) else float("inf")
            d.update(shape_counts(c["text"]))
            # output: section 3, and the error lists of section 4.5
            B, E = self.stream_off(c["out_begin"]), self.stream_off(c["out_end"])
            seg = self.out[B:E]
            d["span"] = (B, E)
            text = T.strip_controls(seg).replace(b"\r", b"")
            d["out_text_recount"] = len(text)
            shown = text.decode("utf-8", "replace")
            low = shown.lower()
            d["failed"] = any(p in low for p in ERROR_LINE)
            d["shell_errors"] = sum(1 for ln in shown.split("\n") if any(p in ln for p in SHELL_ERROR_LINE))
            # keystroke intervals of a typed command; the end of a paste
            ins = [i for i in range(c["in_first"], c["in_enter"] + 1) if self.kinds[i] == "input"]
            d["intervals"] = [self.t[b] - self.t[a] for a, b in zip(ins, ins[1:])] if d["entry"] == "typed" else []
            d["paste_latency"] = None
            if d["entry"] == "paste":
                ends = [i for i in ins if PASTE_END in self.datas[i]]
                if ends:
                    d["paste_latency"] = max(0.0, c["t_enter"] - self.t[ends[-1]])
            cmds.append(d)
            prev = c
        for a, b in zip(cmds, cmds[1:]):
            a["retry"] = bool(a["failed"] and similar(a, b))
        if cmds:
            cmds[-1]["retry"] = False
        self.cmds = cmds

    def output_by_record(self):
        """Program output bytes (escape sequences and CR removed) of each output record."""
        if self._per_record is not None:
            return self._per_record
        per = self._per_record = {}
        for c in self.cmds:
            B, E = c["span"]
            seg = self.out[B:E]
            for kind, a, b, p in T.tokens(seg):
                if kind == "text":
                    pos = B + a
                    end = B + b
                    while pos < end:
                        j = bisect.bisect_right(self.out_starts, pos) - 1
                        rec = self.idx_out[j]
                        stop = min(end, self.out_starts[j] + len(self.datas[rec]))
                        per[rec] = per.get(rec, 0) + (stop - pos)
                        pos = stop
                elif kind == "c0" and p in (0x0a, 0x09):
                    rec = self.rec_at(B + a)
                    per[rec] = per.get(rec, 0) + 1
        return per


# ------------------------------------------------------------------ one window length
def build(inp, wl, L, lookback, logins, report):
    rows = read_windows(inp, wl)
    by_login = {}
    for r in rows:
        by_login.setdefault((r["session_key"], r["login_key"]), []).append(r)
    feats, per_command = {}, []
    stats = dict(kept_windows=0, commands_in_kept_windows=0, commands_in_windows_not_kept=0,
                 exec_records=0, exec_successful=0, login_shell_starts_left_out=0,
                 login_programs_left_out=0, output_bytes_recount_differs=0,
                 program_name_differs_from_command_list=0, window_count_checks_failed=0)
    for (sk, lk), wrows in by_login.items():
        key = (sk, lk)
        if key not in logins:
            logins[key] = Login(inp, sk, lk)
        lg = logins[key]
        n_win = len(wrows)
        wrows.sort(key=lambda r: r["w_index"])
        keep = [r["keep"] for r in wrows]

        def widx(t):
            return min(max(int(t // L), 0), n_win - 1)

        # recorder records by window
        n_in, n_out, in_bytes, fs_keys = [0] * n_win, [0] * n_win, [0] * n_win, [0] * n_win
        for i, kind in enumerate(lg.kinds):
            if kind == "input":
                k = widx(lg.t[i])
                n_in[k] += 1
                in_bytes[k] += len(lg.datas[i])
                if lg.fullscreen_at(i):
                    fs_keys[k] += 1
            elif kind == "output":
                n_out[widx(lg.t[i])] += 1
        out_bytes = [0] * n_win
        for rec, n in lg.output_by_record().items():
            out_bytes[widx(lg.t[rec])] += n
        # exec events of kept windows
        execs = [[] for _ in range(n_win)]
        exec_all = [0] * n_win
        first_line_t = lg.all_lines[0]["t_enter"] if lg.all_lines else float("inf")
        with open(inp.path("data/windows/%s/%s/%s.jsonl" % (wl, sk, lk)), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r["src"] != "exec":
                    continue
                stats["exec_records"] += 1
                exec_all[r["w"]] += 1
                if not r["ok"]:
                    continue                                    # successful program starts only
                if r["pid"] == 1 and r["argv"] and r["argv"][0] == "-bash":
                    stats["login_shell_starts_left_out"] += 1   # the login shell's own start
                    continue
                if r["t"] < first_line_t:
                    stats["login_programs_left_out"] += 1       # ran before the login's first submitted line (F13)
                    continue
                stats["exec_successful"] += 1
                execs[r["w"]].append(r)
        # commands by window
        cmds = [[] for _ in range(n_win)]
        for c in lg.cmds:
            k = widx(lg.t[c["in_enter"]])                    # the window that holds its Enter
            cmds[k].append(c)
            if keep[k]:
                stats["commands_in_kept_windows"] += 1
            else:
                stats["commands_in_windows_not_kept"] += 1
            if c["out_text_recount"] != c["out_text_bytes"]:
                stats["output_bytes_recount_differs"] += 1
            if c["prog"] != c["program"]:
                stats["program_name_differs_from_command_list"] += 1
        # checks against the window table
        for k, r in enumerate(wrows):
            if r["n_input"] != n_in[k] or r["n_output"] != n_out[k] or (keep[k] and r["n_exec"] != exec_all[k]):
                stats["window_count_checks_failed"] += 1

        # base values of every window; a window that was not kept counts as empty in a look-back
        base = []
        for k in range(n_win):
            if not keep[k]:
                base.append(None)
                continue
            cw, ew = cmds[k], execs[k]
            depth, d_of = 0, {1: 0}
            for r in ew:                                        # D29a: parent = latest exec of the parent pid
                d = d_of.get(r["ppid"], 0) + 1
                d_of[r["pid"]] = d
                depth = max(depth, d)
            base.append(dict(cmds=cw, cmd_count=len(cw), exec_count=len(ew),
                             exec_distinct=len(set(exec_program(r) for r in ew)), proc_depth_max=depth,
                             output_bytes=out_bytes[k], chars=sum(len(c["text"]) for c in cw),
                             entry=count_of(c["entry"] for c in cw), input_records=n_in[k],
                             input_bytes=in_bytes[k], fullscreen_keys=fs_keys[k], execs=ew))

        for k, r in enumerate(wrows):
            if not keep[k]:
                continue
            stats["kept_windows"] += 1
            b = base[k]
            cw = b["cmds"]
            n = len(cw)
            v = dict.fromkeys(NAMES)
            # ---- behavior
            gaps = [c["gap"] for c in cw if c["gap"] is not None]
            v["cmd_count"] = n
            if gaps:
                v["gap_mean"], v["gap_median"] = mean(gaps), median(gaps)
                v["gap_min"], v["gap_max"], v["gap_std"] = min(gaps), max(gaps), pstdev(gaps)
                if v["gap_mean"] > 0:
                    v["gap_cv"] = v["gap_std"] / v["gap_mean"]
            if len(gaps) >= 4:                                  # three gaps give two points: always +1 or -1 (F14)
                v["gap_autocorr"] = pearson(gaps[:-1], gaps[1:])
            v["exec_count"], v["exec_distinct"], v["proc_depth_max"] = b["exec_count"], b["exec_distinct"], b["proc_depth_max"]
            v["output_bytes"] = b["output_bytes"]
            v["shell_error_count"] = sum(c["shell_errors"] for c in cw)
            v["retry_count"] = sum(1 for c in cw if c["retry"])
            if n:
                v["exec_per_cmd"] = b["exec_count"] / float(n)
                outs = [c["out_text_bytes"] for c in cw]
                v["output_per_cmd_mean"] = mean(outs)
                if v["output_per_cmd_mean"] > 0:
                    v["output_per_cmd_cv"] = pstdev(outs) / v["output_per_cmd_mean"]
                v["fail_ratio"] = sum(1 for c in cw if c["failed"]) / float(n)
            # ---- command content
            progs = [c["prog"] for c in cw]
            v["chars_submitted"] = b["chars"]
            v["cmd_unique"] = len(set(c["text"] for c in cw))
            v["prog_distinct"] = len(set(progs))
            v["help_count"] = sum(c["help"] for c in cw)
            if n:
                v["cmd_len_mean"] = mean([c["first_len"] for c in cw])
                v["cmd_len_max"] = max(c["first_len"] for c in cw)
                v["cmd_diversity"] = v["cmd_unique"] / float(n)
                v["prog_entropy"] = entropy_bits(list(count_of(progs).values()))
                v["flags_per_cmd"] = mean([c["flags"] for c in cw])
                v["pipes_per_cmd"] = mean([c["pipes"] for c in cw])
                v["chain_ratio"] = mean([c["chain"] for c in cw])
                v["redirect_ratio"] = mean([c["redirect"] for c in cw])
            if n >= 2:
                v["transition_entropy"] = entropy_bits(list(count_of(zip(progs, progs[1:])).values()))
            if b["chars"] > 0:
                v["io_ratio"] = b["output_bytes"] / float(b["chars"])
            # ---- context: the look-back, past windows of the same login only
            back = [base[j] for j in range(max(0, k - lookback), k) if base[j] is not None]
            v["ctx_cmd_count"] = sum(x["cmd_count"] for x in back)
            v["ctx_exec_count"] = sum(x["exec_count"] for x in back)
            v["ctx_output_bytes"] = sum(x["output_bytes"] for x in back)
            v["ctx_active_windows"] = sum(1 for x in back if x["cmd_count"] > 0)
            v["ctx_chars_submitted"] = sum(x["chars"] for x in back)
            back_cmds = [c for x in back for c in x["cmds"]]
            if back_cmds:
                v["ctx_cmd_len_max"] = max(c["first_len"] for c in back_cmds)
            both = back_cmds + cw
            if both:
                v["ctx_cmd_diversity"] = len(set(c["text"] for c in both)) / float(len(both))
            if len(both) >= 2:
                bp = [c["prog"] for c in both]
                v["ctx_transition_entropy"] = entropy_bits(list(count_of(zip(bp, bp[1:])).values()))
            for style in ("typed", "paste", "recall", "line"):
                v["ctx_entry_" + style] = sum(x["entry"].get(style, 0) for x in back)
                v["entry_" + style] = b["entry"].get(style, 0)
            # ---- input channel
            v["fullscreen_keys"], v["input_bytes"] = b["fullscreen_keys"], b["input_bytes"]
            if n:
                v["typed_ratio"] = v["entry_typed"] / float(n)
                v["paste_ratio"] = v["entry_paste"] / float(n)
                v["line_ratio"] = v["entry_line"] / float(n)
                v["multi_cmd_write_ratio"] = sum(1 for c in cw if c["multi_write"]) / float(n)
                v["compose_time_median"] = median([c["compose"] for c in cw])
                v["input_writes_per_cmd"] = b["input_records"] / float(n)
            typed = [c for c in cw if c["entry"] == "typed"]
            intervals = [x for c in typed for x in c["intervals"]]
            if len(intervals) >= 3:
                v["interkey_median"] = median(intervals)
                if mean(intervals) > 0:
                    v["interkey_cv"] = pstdev(intervals) / mean(intervals)
            typed_chars = sum(c["typed_chars"] for c in typed)
            if typed_chars > 0:
                v["backspace_rate"] = sum(c["backspaces"] for c in typed) / float(typed_chars)
            lat = [c["paste_latency"] for c in cw if c["paste_latency"] is not None]
            if lat:
                v["paste_enter_latency"] = median(lat)
            feats[r["window_id"]] = v
            # ---- per-command table: programs started between this command's Enter and the next line's
            for c in cw:
                started = []
                for j in range(k, n_win):
                    if base[j] is None:
                        continue
                    if j * L > c["t_next_line"]:
                        break
                    for e in base[j]["execs"]:
                        if c["t_enter"] <= e["t"] < c["t_next_line"]:
                            started.append({"program": exec_program(e), "window_id": wrows[j]["window_id"]})
                per_command.append(dict(window_id=r["window_id"], n=c["n"], text=c["text"], program=c["prog"],
                                        entry_style=c["entry"], at_prompt=c["at_prompt"], lines=c["lines"],
                                        output_bytes=c["out_text_bytes"], failed=c["failed"],
                                        programs_started=started))
    # write, in the order of the window table
    out_dir = os.path.join(OUT_ROOT, "data", "features", wl)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "features.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["window_id"] + NAMES)
        for r in rows:
            if r["keep"]:
                w.writerow([r["window_id"]] + [fmt(feats[r["window_id"]][c]) for c in NAMES])
    order = {r["window_id"]: i for i, r in enumerate(rows)}
    per_command.sort(key=lambda d: (order[d["window_id"]], d["n"]))
    with open(os.path.join(out_dir, "per_command.jsonl"), "w", encoding="utf-8") as f:
        for d in per_command:
            f.write(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n")
    # undefined share of every column, by session key (no label is read)
    by_session = {}
    for r in rows:
        if r["keep"]:
            by_session.setdefault(r["session_key"], []).append(feats[r["window_id"]])
    undefined = {}
    for c in NAMES:
        shares = {sk: round(sum(1 for v in vs if v[c] is None) / float(len(vs)), 4) for sk, vs in sorted(by_session.items())}
        if any(shares.values()):
            undefined[c] = shares
    report[wl] = dict(stats=stats, rows=stats["kept_windows"], per_command_rows=len(per_command),
                      windows_by_session={sk: len(vs) for sk, vs in sorted(by_session.items())},
                      undefined_share_by_session=undefined,
                      outputs={n: sha256_file(os.path.join(out_dir, n)) for n in ("features.csv", "per_command.jsonl")})
    return out_dir


def column_file(wl, out_dir, inp, report):
    cols = []
    for c in COLUMNS:
        d = dict(column=c[0], tier=c[1], kind=c[2], definition=c[3], undefined_when=c[4])
        if len(c) > 5:
            d["goes_with"] = c[5]
        cols.append(d)
    prefix = ("data/windows/%s/" % wl, "data/commands/", "data/cleaned/")
    doc = dict(feature_version=FEATURE_VERSION, design="real_lab3_feature_trial_design.md sections 3 and 4",
               window=wl, n_columns=len(cols),
               tiers={t: sum(1 for c in cols if c["tier"] == t) for t in EXPECTED_TIER_COUNTS},
               scaling_note="logistic regression only: count, size and time get log(1 + x); ratio, share, entropy and "
                            "correlation are left alone (design section 6)",
               undefined="stored as empty; undefined is not zero",
               columns=cols, freeze_1_sha256=inp.freeze_sha256,
               inputs={k: v for k, v in sorted(inp.opened.items()) if k.startswith(prefix)},
               outputs=report[wl]["outputs"])
    p = os.path.join(out_dir, "feature_columns.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    report[wl]["outputs"]["feature_columns.json"] = sha256_file(p)


def main():
    tiers = count_of(c[1] for c in COLUMNS)
    if tiers != EXPECTED_TIER_COUNTS or len(set(NAMES)) != 60:
        raise SystemExit("STOP: the column list does not equal section 4: %s" % tiers)
    inp = Inputs()
    report = dict(step="10_features", feature_version=FEATURE_VERSION, freeze_1_sha256=inp.freeze_sha256,
                  never_read="labels, split files, stage columns, description files, audit files, set_aside/, "
                             "the evidence folder",
                  window_columns_read=WINDOW_COLUMNS_READ, columns=len(NAMES), tiers=tiers,
                  code={n: sha256_file(os.path.join(HERE, n)) for n in sorted(os.listdir(HERE)) if n.endswith(".py")})
    logins = {}
    for wl, L, lookback in LENGTHS:
        out_dir = build(inp, wl, L, lookback, logins, report)
        column_file(wl, out_dir, inp, report)
        s = report[wl]["stats"]
        print(wl, "rows", report[wl]["rows"], "| commands in kept windows", s["commands_in_kept_windows"],
              "| not kept", s["commands_in_windows_not_kept"], "| count checks failed", s["window_count_checks_failed"],
              "| output recount differs", s["output_bytes_recount_differs"])
    report["inputs_opened"] = len(inp.opened)
    report["inputs"] = dict(sorted(inp.opened.items()))
    rp = os.path.join(OUT_ROOT, "reports", "10_features_report.json")
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    bad = sum(report[wl]["stats"]["window_count_checks_failed"] for wl, _, _ in LENGTHS)
    print("COMPLETE: features" if not bad else "STOP: window counts do not agree with the window table")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
