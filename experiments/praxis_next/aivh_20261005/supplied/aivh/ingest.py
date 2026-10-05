"""Ingest heterogeneous shell-session logs into a unified Session record.

Supported sources
-----------------
- zenodo   : Honey-for-the-Agent session JSON (DOI 10.5281/zenodo.20818246)
- asciinema: asciinema v2 .cast recordings of human operators
- script   : `script -t` typescript + timing-file pairs
- cowrie   : Cowrie JSON log (one event per line), grouped by session id

Every loader yields `Session` objects with the same fields so downstream
feature extraction is source-agnostic.  Labels: "agent", "human", "bot".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator, Optional

LABELS = ("agent", "human", "bot")


@dataclass
class Command:
    text: str                 # command as executed
    gap_ms: Optional[float]   # time since previous command was issued (None for first)
    output: str = ""          # shell output returned (may be empty)
    exec_ms: Optional[float] = None


@dataclass
class Session:
    session_id: str
    label: str                       # agent | human | bot
    source: str                      # zenodo | asciinema | script | cowrie
    commands: list[Command]
    # grouping keys for matched / leave-one-out splits
    model: str = "unknown"           # LLM identifier (agents) or "human"/"bot"
    model_family: str = "unknown"    # e.g. gpt, claude, llama, qwen ...
    environment: str = "unknown"     # e.g. real_ubuntu, cowrie_default ...
    task: str = "unknown"            # prompt_1..prompt_6 or task tag
    max_turns: Optional[int] = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @property
    def n_commands(self) -> int:
        return len(self.commands)


# --------------------------------------------------------------------------- #
# model-family normalisation
# --------------------------------------------------------------------------- #
_FAMILY_PATTERNS = [
    (r"gpt|o[1-4](-|$)|openai", "openai"),
    (r"claude|anthropic", "anthropic"),
    (r"gemini|gemma|google", "google"),
    (r"llama|meta", "meta"),
    (r"qwen|alibaba", "alibaba"),
    (r"mistral|mixtral", "mistral"),
    (r"deepseek", "deepseek"),
    (r"phi", "microsoft"),
]


def model_family(model_id: str) -> str:
    m = model_id.lower()
    for pat, fam in _FAMILY_PATTERNS:
        if re.search(pat, m):
            return fam
    return m.split("-")[0].split("_")[0] or "unknown"


# --------------------------------------------------------------------------- #
# Zenodo: Honey for the Agent
# --------------------------------------------------------------------------- #
def _parse_zenodo_turns(raw) -> list[Command]:
    """Turn 0 = [[system_prompt, start_ts], [banner, conn_latency_ms]]
    Turn i = [[llm_raw_output, response_ms], [shell_output, exec_ms], [raw_cmd, parsed_cmd]]
    Inter-command gap is approximated by the LLM response time of the turn
    plus the previous turn's execution round-trip (the agent cannot issue
    the next command until it has seen the previous output)."""
    cmds: list[Command] = []
    prev_exec = 0.0
    for i, turn in enumerate(raw):
        if i == 0:
            continue
        try:
            (llm_out, resp_ms), (shell_out, exec_ms), (raw_cmd, parsed_cmd) = turn
        except (ValueError, TypeError):
            continue
        text = (parsed_cmd if isinstance(parsed_cmd, str) and parsed_cmd.strip() else raw_cmd) or ""
        if not isinstance(text, str):
            text = str(text)
        gap = None if i == 1 else float(resp_ms or 0) + prev_exec
        cmds.append(Command(text=text.strip(), gap_ms=gap, output=str(shell_out or ""),
                            exec_ms=float(exec_ms) if exec_ms is not None else None))
        prev_exec = float(exec_ms or 0)
    return cmds


def load_zenodo(root: Path) -> Iterator[Session]:
    """Walk Logs_final/prompt_k/{20,30}/<environment>/<model>/sessionNN.json."""
    root = Path(root)
    base = root / "Logs_final" if (root / "Logs_final").exists() else root
    for p in sorted(base.rglob("*.json")):
        parts = p.relative_to(base).parts
        if len(parts) < 5:
            continue
        task, max_turns, env, model = parts[0], parts[1], parts[2], parts[3]
        try:
            raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, list) or len(raw) < 2:
            continue
        cmds = _parse_zenodo_turns(raw)
        if not cmds:
            continue
        sid = "zen::" + "/".join(parts)
        yield Session(session_id=sid, label="agent", source="zenodo", commands=cmds,
                      model=model, model_family=model_family(model),
                      environment=env, task=task,
                      max_turns=int(max_turns) if max_turns.isdigit() else None,
                      meta={"path": str(p)})


# --------------------------------------------------------------------------- #
# asciinema v2 (.cast) — human recordings
# --------------------------------------------------------------------------- #
_PROMPT_RE = re.compile(r"(\$|#|>)\s*$")


def _commands_from_keystream(events: list[tuple[float, str]]) -> list[Command]:
    """Reconstruct submitted command lines from input events.
    events: (t_seconds, text) for stdin ('i') events.  A command is
    'issued' when a carriage return is typed.  Backspaces are applied so
    we recover the command as executed, and the gap is measured from the
    previous Enter to this Enter (operator think + type time)."""
    cmds: list[Command] = []
    buf: list[str] = []
    last_enter: Optional[float] = None
    n_edits = 0
    for t, s in events:
        for ch in s:
            if ch in ("\r", "\n"):
                text = "".join(buf).strip()
                if text:
                    gap = None if last_enter is None else (t - last_enter) * 1000.0
                    c = Command(text=text, gap_ms=gap)
                    c.output = ""
                    cmds.append(c)
                    cmds[-1].exec_ms = None
                    cmds[-1].__dict__["_edits"] = n_edits
                last_enter = t
                buf, n_edits = [], 0
            elif ch in ("\x7f", "\b"):
                if buf:
                    buf.pop()
                n_edits += 1
            elif ch == "\x03":          # Ctrl-C
                buf, n_edits = [], 0
                last_enter = t
            elif ch == "\x1b":
                n_edits += 1            # escape sequences (arrows) count as edits
            elif ch.isprintable():
                buf.append(ch)
    return cmds


def load_asciinema(path: Path, label: str = "human", operator: str = "human",
                   environment: str = "unknown", task: str = "unknown") -> Optional[Session]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return None
    try:
        header = json.loads(lines[0])
    except json.JSONDecodeError:
        return None
    events = []
    for ln in lines[1:]:
        try:
            t, kind, data = json.loads(ln)
        except (json.JSONDecodeError, ValueError):
            continue
        if kind == "i":
            events.append((float(t), data))
    if not events:
        # fall back to output stream heuristics: treat text after a prompt as command
        return None
    cmds = _commands_from_keystream(events)
    if not cmds:
        return None
    return Session(session_id=f"cast::{Path(path).stem}", label=label, source="asciinema",
                   commands=cmds, model=operator, model_family=label,
                   environment=environment, task=task,
                   meta={"path": str(path), "header": header})


# --------------------------------------------------------------------------- #
# `script -t 2>timing.log typescript` — human recordings
# --------------------------------------------------------------------------- #
def load_script_typescript(typescript: Path, timing: Path, label: str = "human",
                           operator: str = "human", environment: str = "unknown",
                           task: str = "unknown") -> Optional[Session]:
    """Approximate: `script` records output only, so we recover command lines
    from echoed prompts and time them from the timing file byte offsets."""
    data = Path(typescript).read_bytes()
    tim = [ln.split() for ln in Path(timing).read_text().splitlines() if ln.strip()]
    # build cumulative time per byte offset
    offsets, times, pos, t = [], [], 0, 0.0
    for d, n in tim:
        t += float(d); pos += int(n)
        offsets.append(pos); times.append(t)
    text = data.decode("utf-8", errors="replace")
    cmds: list[Command] = []
    last_t = None
    for m in re.finditer(r"[^\r\n]*[\$#>]\s([^\r\n]+)\r?\n", text):
        cmd = m.group(1).strip()
        if not cmd:
            continue
        # time at this byte offset
        import bisect
        i = bisect.bisect_left(offsets, m.start(1))
        tt = times[min(i, len(times) - 1)] if times else 0.0
        gap = None if last_t is None else (tt - last_t) * 1000.0
        cmds.append(Command(text=cmd, gap_ms=gap))
        last_t = tt
    if not cmds:
        return None
    return Session(session_id=f"script::{Path(typescript).stem}", label=label, source="script",
                   commands=cmds, model=operator, model_family=label,
                   environment=environment, task=task, meta={"path": str(typescript)})


# --------------------------------------------------------------------------- #
# Cowrie JSON log — bots (and weakly-labelled humans)
# --------------------------------------------------------------------------- #
def load_cowrie(path: Path, label_fn=None, environment: str = "cowrie") -> Iterator[Session]:
    """Group cowrie.command.input events by session.  `label_fn(session_events)`
    returns 'bot' | 'human' | None (skip).  Default labels everything 'bot'."""
    from datetime import datetime
    by_sid: dict[str, list[dict]] = {}
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        sid = ev.get("session")
        if sid:
            by_sid.setdefault(sid, []).append(ev)

    def ts(ev):
        s = ev.get("timestamp", "")
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    for sid, evs in by_sid.items():
        evs.sort(key=lambda e: e.get("timestamp", ""))
        inputs = [e for e in evs if e.get("eventid") == "cowrie.command.input"]
        if not inputs:
            continue
        label = (label_fn(evs) if label_fn else "bot")
        if label is None:
            continue
        cmds, last = [], None
        for e in inputs:
            t = ts(e)
            gap = None if (last is None or t is None) else (t - last) * 1000.0
            cmds.append(Command(text=str(e.get("input", "")).strip(), gap_ms=gap))
            if t is not None:
                last = t
        tty = [e for e in evs if e.get("eventid") == "cowrie.client.size"]
        yield Session(session_id=f"cowrie::{sid}", label=label, source="cowrie", commands=cmds,
                      model=label, model_family=label, environment=environment,
                      task="wild", meta={"src_ip": evs[0].get("src_ip"), "tty_negotiated": bool(tty),
                                         "n_events": len(evs)})


def default_cowrie_label(evs: list[dict]) -> Optional[str]:
    """Conservative weak labeller for wild Cowrie sessions.
    bot   : no TTY size event AND (≤ 2 distinct gaps OR all gaps < 300 ms)
    human : TTY size negotiated AND ≥ 3 commands AND gap std > 1.5 s
    else  : None (ambiguous → skip)"""
    from datetime import datetime
    import statistics
    inputs = [e for e in evs if e.get("eventid") == "cowrie.command.input"]
    if len(inputs) < 2:
        return None
    ts = []
    for e in inputs:
        try:
            ts.append(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp())
        except (KeyError, ValueError):
            pass
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    tty = any(e.get("eventid") == "cowrie.client.size" for e in evs)
    if not gaps:
        return None
    if not tty and (len(set(round(g, 1) for g in gaps)) <= 2 or max(gaps) < 0.3):
        return "bot"
    if tty and len(inputs) >= 3 and len(gaps) >= 2 and statistics.pstdev(gaps) > 1.5:
        return "human"
    return None


# --------------------------------------------------------------------------- #
# JSONL round-trip
# --------------------------------------------------------------------------- #
def write_jsonl(sessions: Iterator[Session], out: Path) -> int:
    n = 0
    with Path(out).open("w", encoding="utf-8") as f:
        for s in sessions:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[Session]:
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        d["commands"] = [Command(**c) for c in d["commands"]]
        yield Session(**d)
