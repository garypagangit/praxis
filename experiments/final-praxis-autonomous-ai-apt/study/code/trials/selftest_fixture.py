"""Builds a synthetic study tree, so that the trial code can be run end to end
(plumbing run, Freeze 2, scored run, tables) before any real window is scored.

    python3 -I -B code/trials/selftest_fixture.py /tmp/s3_fixture

Everything in the tree is made up: sessions, windows, splits, labels and feature
values come from a random number generator. The only thing taken from the study is
the column list of the real column file (names, tiers and kinds), which holds no
data. The trial code is then pointed at the tree with S3_ROOT. With S3_ROOT set, and
only then, S3_TEST_CHANCE_PARTS shortens the chance baseline for the test.
"""
import csv
import hashlib
import json
import os
import sys

import random

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_ROOT = os.path.dirname(os.path.dirname(HERE))
LABELS = ["P001", "P002", "P003", "P004", "P005", "P006", "P009", "P010", "P011"]
AI = set(LABELS[:4])                      # made up; the first of the 126 labelings
STAGES = [("1", "1-4"), ("3", "1-4"), ("5", "5"), ("6", "6"), ("7", "7")]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    out = sys.argv[1]
    if os.path.exists(os.path.join(out, "AHIR Participant Evidence")) or os.path.abspath(out) == REAL_ROOT:
        raise SystemExit("REFUSED: the fixture is never written into the study folder")
    rng = random.Random(7)
    with open(os.path.join(REAL_ROOT, "data", "features", "w30", "feature_columns.json"), encoding="utf-8") as f:
        colfile = json.load(f)
    cols = colfile["columns"]
    keys = {lab: "s_fix%05d" % i for i, lab in enumerate(LABELS)}
    frozen = {}
    feature_hashes = {}
    for window, scale in (("w30", 1.0), ("w60", 0.5)):
        wrows, frows, srows, tv, te, drows = [], [], [], [], [], []
        for lab in LABELS:
            n_kept_target = int(rng.randint(40, 90) * scale)
            effect = [rng.gauss(0, 0.4) for _ in cols]
            for li in range(rng.randint(1, 2)):
                login = "l_fix%s%d" % (lab[1:], li)
                for wi in range(int(n_kept_target * 0.8)):
                    wid = "%s_w%04d" % (login, wi)
                    keep = 1 if rng.random() < 0.65 else 0
                    stage, group = STAGES[min(len(STAGES) - 1, wi * len(STAGES) // max(1, int(n_kept_target * 0.8)))]
                    n_input = 0 if rng.random() < 0.3 else rng.randint(1, 40)
                    wrows.append([wid, keys[lab], login, li + 1, wi, wi * 30, wi * 30 + 30, n_input,
                                  rng.randint(0, 50), rng.randint(0, 30), keep, "" if keep else "no_terminal_record",
                                  stage, group])
                    drows.append([wid, keys[lab], li + 1, wi * 30.0, stage, group, keep])
                    if not keep:
                        continue
                    row = [wid]
                    shift = 0.9 if lab in AI else 0.0
                    for j, c in enumerate(cols):
                        v = rng.gauss(shift * (1 if j % 3 else 0), 1.0) + effect[j]
                        if c["column"] == "cmd_count":
                            row.append(str(max(0, int(round(v + 1)))))
                        elif c["undefined_when"] != "never" and rng.random() < 0.35:
                            row.append("")
                        elif c["kind"] in ("count", "size", "time"):
                            row.append(repr(round(abs(v) * 10, 3)))
                        elif c["kind"] == "correlation":
                            row.append(repr(round(max(-1.0, min(1.0, v / 3)), 4)))
                        else:
                            row.append(repr(round(abs(v) / 3, 4)))
                    frows.append(row)
                    u = rng.random()
                    split = "train" if u < 0.6 else "val" if u < 0.75 else "test" if u < 0.9 else "unused"
                    srows.append([wid, keys[lab], split, stage, stage])
                    klass = "ai" if lab in AI else "human"
                    if split in ("train", "val"):
                        tv.append([wid, klass])
                    elif split == "test":
                        te.append([wid, klass])
        d = os.path.join(out, "data")
        write_csv(os.path.join(d, "windows", window, "windows.csv"),
                  ["window_id", "session_key", "login_key", "login_order", "w_index", "t_start", "t_end", "n_input",
                   "n_output", "n_exec", "keep", "drop_reason", "stage", "stage_group"], wrows)
        write_csv(os.path.join(d, "features", window, "features.csv"),
                  ["window_id"] + [c["column"] for c in cols], frows)
        os.makedirs(os.path.join(d, "features", window), exist_ok=True)
        with open(os.path.join(d, "features", window, "feature_columns.json"), "w", encoding="utf-8") as f:
            json.dump(dict(columns=cols, n_columns=len(cols), window=window, note="fixture"), f)
        with open(os.path.join(d, "features", window, "per_command.jsonl"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        write_csv(os.path.join(d, "splits", "splits_%s.csv" % window),
                  ["window_id", "session_key", "split", "split_group", "stage"], srows)
        write_csv(os.path.join(d, "labels", "labels_trainval_%s.csv" % window), ["window_id", "class"], tv)
        write_csv(os.path.join(d, "labels", "labels_test_%s.csv" % window), ["window_id", "class"], te)
        write_csv(os.path.join(d, "description", "window_description_%s.csv" % window),
                  ["window_id", "session_key", "login_order", "elapsed_working_s", "stage", "stage_group", "keep"],
                  drows)
        for name in ("features.csv", "feature_columns.json", "per_command.jsonl"):
            feature_hashes["data/features/%s/%s" % (window, name)] = sha(os.path.join(d, "features", window, name))
    write_csv(os.path.join(out, "data", "labels", "sessions.csv"),
              ["session_key", "class", "label_basis", "included", "logins_used"],
              [[keys[lab], "ai" if lab in AI else "human", "fixture", 1, 1] for lab in LABELS])
    rep = os.path.join(out, "reports")
    os.makedirs(os.path.join(rep, "eda", "tables"), exist_ok=True)
    with open(os.path.join(rep, "05_windows_report.json"), "w", encoding="utf-8") as f:
        json.dump(dict(sessions={lab: dict(session_key=keys[lab]) for lab in LABELS}), f)
    for name, text in (("10_features_report.json", "{}\n"), ("10_features_review_windows.md", "fixture\n"),
                       (os.path.join("eda", "tables", "T1.csv"), "fixture\n")):
        with open(os.path.join(rep, name), "w", encoding="utf-8") as f:
            f.write(text)
    with open(os.path.join(rep, "10_features_checks.json"), "w", encoding="utf-8") as f:
        json.dump(dict(outputs=feature_hashes), f)
    for dirpath, dirs, names in os.walk(os.path.join(out, "data")):
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            if not rel.startswith("data/features/"):
                frozen[rel] = dict(sha256=sha(p), bytes=os.path.getsize(p))
    p = os.path.join(rep, "05_windows_report.json")
    frozen["reports/05_windows_report.json"] = dict(sha256=sha(p), bytes=os.path.getsize(p))
    with open(os.path.join(rep, "FREEZE_1.json"), "w", encoding="utf-8") as f:
        json.dump(dict(freeze="fixture", files=frozen, n_files=len(frozen)), f)
    for doc in ("real_lab3_feature_trial_design.md", "real_lab3_eda_handoff.md"):
        with open(os.path.join(out, doc), "w", encoding="utf-8") as f:
            f.write("fixture copy of " + doc + "\n")
    print("fixture written:", out)


if __name__ == "__main__":
    main()
