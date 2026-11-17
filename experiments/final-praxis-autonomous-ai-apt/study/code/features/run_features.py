"""Feature step with its checks (feature and trial design sections 3, 4 and 10).

    python3 -I -B code/features/run_features.py

1. Builds the feature table, the column file and the per-command table (step10_features.py).
2. Builds them a second time into a temporary folder outside the study folder and compares hashes.
3. Runs the preprocessing's leak-audit patterns (design 6.6) over the new files in data/features/.
4. Writes the review file a person reads before EDA Pass 2: five windows from each session beside
   their feature rows, and the undefined share of every column for each session. No label is read.

Nothing is scored and no label, split or stage is read anywhere in this step.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
ROOT = os.environ.get("S3_ROOT") or os.path.dirname(CODE)
sys.path.insert(0, HERE)
sys.path.insert(0, CODE)
import step10_features as F
import s3_clean as K

FILES = ["data/features/%s/%s" % (wl, n) for wl in ("w30", "w60")
         for n in ("features.csv", "feature_columns.json", "per_command.jsonl")] + ["reports/10_features_report.json"]
REVIEW_WINDOWS = 5
REVIEW_TEXT_CHARS = 300


def build(out_root=None):
    env = dict(os.environ)
    if out_root:
        env["S3_FEATURE_OUT"] = out_root
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(HERE, "step10_features.py")], env=env)
    if r.returncode != 0:
        raise SystemExit("STOP: the feature step failed")
    root = out_root or ROOT
    return {rel: F.sha256_file(os.path.join(root, *rel.split("/"))) for rel in FILES}


def leak_audit():
    hits, checked = [], dict(table_files=0, command_texts=0, program_names=0)

    def search(data, where, bare_uid=False):
        for name, rx in K.LEAK_PATTERNS:
            n = len(rx.findall(data))
            if n:
                hits.append(dict(pattern=name, count=n, where=where))
        if bare_uid and K.LEAK_UID_BARE.findall(data):
            hits.append(dict(pattern="user_number_bare", count=len(K.LEAK_UID_BARE.findall(data)), where=where))

    for wl in ("w30", "w60"):
        d = os.path.join(ROOT, "data", "features", wl)
        for n in ("features.csv", "feature_columns.json"):
            search(open(os.path.join(d, n), "rb").read(), "data/features/%s/%s" % (wl, n))
            checked["table_files"] += 1
        with open(os.path.join(d, "per_command.jsonl"), encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                search(o["text"].encode(), "data/features/%s/per_command.jsonl (text)" % wl, bare_uid=True)
                checked["command_texts"] += 1
                for p in o["programs_started"]:
                    search(p["program"].encode(), "data/features/%s/per_command.jsonl (program)" % wl)
                    checked["program_names"] += 1
    total = sum(h["count"] for h in hits)
    return dict(patterns=[n for n, _ in K.LEAK_PATTERNS] + ["user_number_bare (command text)"], checked=checked,
                hits=hits, total_hits=total, result="PASS" if total == 0 else "FAIL")


def review(wl="w30"):
    """Five windows from each session beside their feature rows. Holds command text: read in place."""
    d = os.path.join(ROOT, "data", "features", wl)
    feats = {r["window_id"]: r for r in csv.DictReader(open(os.path.join(d, "features.csv"), encoding="utf-8", newline=""))}
    cols = json.load(open(os.path.join(d, "feature_columns.json"), encoding="utf-8"))["columns"]
    cmds = {}
    with open(os.path.join(d, "per_command.jsonl"), encoding="utf-8") as f:
        for line in f:
            o = json.loads(line)
            cmds.setdefault(o["window_id"], []).append(o)
    sessions = {}
    with open(os.path.join(ROOT, "data", "windows", wl, "windows.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["keep"] == "1":
                sessions.setdefault(r["session_key"], []).append(r["window_id"])
    report = json.load(open(os.path.join(ROOT, "reports", "10_features_report.json"), encoding="utf-8"))
    out = ["# Feature table review, 30-second windows",
           "",
           "Written by `code/features/run_features.py`. **This file holds command text, which can include the lab's "
           "attack-account passwords. It stays in the study folder and is read by a person** (feature and trial design "
           "section 10). No label, split or stage was read to make it; sessions are shown by their key.",
           "",
           "## 1. Column list",
           "",
           "%d columns: %s. Equal to section 4 of the design (the step stops if it is not)."
           % (len(cols), ", ".join("%s %d" % (t, n) for t, n in sorted(report["tiers"].items()))),
           "",
           "## 2. Undefined share of each column, by session",
           "",
           "Columns that are never undefined are left out. Shares are of the session's kept windows.",
           ""]
    keys = sorted(sessions)
    und = report[wl]["undefined_share_by_session"]
    out.append("| Column | " + " | ".join(keys) + " |")
    out.append("|---|" + "---|" * len(keys))
    for c in [x["column"] for x in cols if x["column"] in und]:
        out.append("| `%s` | " % c + " | ".join("%.0f%%" % (100 * und[c].get(k, 0)) for k in keys) + " |")
    out += ["", "## 3. Five windows from each session", "",
            "The windows are the first, last and three evenly spaced kept windows that hold at least one command.", ""]
    for sk in keys:
        with_cmd = [w for w in sessions[sk] if w in cmds]
        picks = sorted(set(int(round(j * (len(with_cmd) - 1) / float(REVIEW_WINDOWS - 1))) for j in range(REVIEW_WINDOWS))) if with_cmd else []
        out.append("### Session %s (%d kept windows, %d with a command)" % (sk, len(sessions[sk]), len(with_cmd)))
        out.append("")
        for i in picks:
            w = with_cmd[i]
            out.append("**Window `%s`**" % w)
            out.append("")
            for c in cmds[w]:
                text = c["text"].replace("\n", " ⏎ ")
                if len(text) > REVIEW_TEXT_CHARS:
                    text = text[:REVIEW_TEXT_CHARS] + " … (%d characters)" % len(c["text"])
                progs = [p["program"] for p in c["programs_started"]]
                shown = ", ".join(progs[:12]) + (" … (%d)" % len(progs) if len(progs) > 12 else "")
                out.append("- command %d, %s, %s: `%s`" % (c["n"], c["entry_style"],
                                                          "at the shell prompt" if c["at_prompt"] else "typed into a program",
                                                          text.replace("`", "'")))
                out.append("  - output %d bytes%s; programs started: %s" % (c["output_bytes"], ", error line" if c["failed"] else "",
                                                                           shown or "none"))
            out.append("")
            for tier in ("behavior", "command_content", "context", "input_channel"):
                vals = ["%s=%s" % (x["column"], feats[w][x["column"]] if feats[w][x["column"]] != "" else "undefined")
                        for x in cols if x["tier"] == tier]
                out.append("- %s: %s" % (tier, ", ".join(vals)))
            out.append("")
    p = os.path.join(ROOT, "reports", "10_features_review_windows.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return F.sha256_file(p)


def main():
    first = build()
    with tempfile.TemporaryDirectory(prefix="s3_features_rerun_") as tmp:
        second = build(tmp)
    different = sorted(k for k in FILES if first[k] != second[k])
    audit = leak_audit()
    rep = json.load(open(os.path.join(ROOT, "reports", "10_features_report.json"), encoding="utf-8"))
    checks = dict(
        step="10_features_checks", feature_version=F.FEATURE_VERSION,
        column_list_equals_section_4=dict(columns=rep["columns"], tiers=rep["tiers"], result="PASS"),
        rows=dict(w30=rep["w30"]["rows"], w60=rep["w60"]["rows"]),
        window_counts_agree_with_window_table=dict(
            failed={wl: rep[wl]["stats"]["window_count_checks_failed"] for wl in ("w30", "w60")},
            result="PASS" if not any(rep[wl]["stats"]["window_count_checks_failed"] for wl in ("w30", "w60")) else "FAIL"),
        output_bytes_agree_with_command_list=dict(
            differ={wl: rep[wl]["stats"]["output_bytes_recount_differs"] for wl in ("w30", "w60")},
            result="PASS" if not any(rep[wl]["stats"]["output_bytes_recount_differs"] for wl in ("w30", "w60")) else "FAIL"),
        rerun=dict(files_compared=len(FILES), different=different, result="PASS" if not different else "FAIL"),
        leak_audit=audit,
        review_file=dict(path="reports/10_features_review_windows.md", sha256=review(),
                         note="holds command text; read by a person, in place"),
        outputs=first,
    )
    with open(os.path.join(ROOT, "reports", "10_features_checks.json"), "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    ok = all(checks[k]["result"] == "PASS" for k in ("window_counts_agree_with_window_table",
                                                     "output_bytes_agree_with_command_list", "rerun", "leak_audit"))
    print("rerun:", checks["rerun"]["result"], "| leak audit:", audit["result"], audit["total_hits"], audit["checked"])
    print("COMPLETE: feature step and checks" if ok else "STOP: a feature check failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
