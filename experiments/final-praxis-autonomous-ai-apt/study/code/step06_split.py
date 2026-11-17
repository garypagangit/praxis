"""Step 6: the split file (design section 8).

One split file per window length, written per session: train, validation,
test or unused for every kept window.
  - inside each session, windows are grouped by stage; a group under 7 windows
    is merged with the previous stage's group in the same session (the next if
    there is none), smallest first
  - within each group, in time order: the last 15% are test, the 15% before
    them validation, the rest train; 15% is rounded to the nearest whole
    window (halves up), never fewer than one
  - one unused window at every block boundary, and where one group's test
    block meets the next group's training block
Written once: existing rows never change, a session added later is appended,
and the writer refuses to overwrite. Before Freeze 1 a run may be repeated
with --before-freeze; that is refused once reports/FREEZE_1.json exists.
"""
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_config as C
import s3_io as IO

STEP = "06_split"
COLS = ["window_id", "session_key", "split", "split_group", "stage"]


def k_of(n):
    return max(1, int(math.floor(C.SPLIT_FRACTION * n + 0.5)))


def split_session(rows):
    """rows: kept windows of one session in time order (login order, window index)."""
    groups = {}
    for r in rows:
        groups.setdefault(int(r["stage"]), []).append(r)
    merged = [dict(stages=[s], rows=groups[s]) for s in sorted(groups)]
    while len(merged) > 1:
        small = [g for g in merged if len(g["rows"]) < C.MIN_GROUP]
        if not small:
            break
        g = min(small, key=lambda g: (len(g["rows"]), g["stages"][0]))
        i = merged.index(g)
        j = i - 1 if i > 0 else i + 1
        tgt = merged[j]
        tgt["stages"] = sorted(tgt["stages"] + g["stages"])
        tgt["rows"] = sorted(tgt["rows"] + g["rows"], key=lambda r: (int(r["login_order"]), int(r["w_index"])))
        del merged[i]
    out = {}
    prev_test_last = None
    for g in merged:
        rs = g["rows"]
        n = len(rs)
        k = k_of(n)
        lab = ["train"] * n
        pos = n
        for name, size in (("test", k), ("unused", 1), ("val", k), ("unused", 1)):
            for _ in range(size):
                if pos <= 0:
                    break
                pos -= 1
                lab[pos] = name
        # where the previous group's test block meets this group's training block
        if prev_test_last is not None and n and lab[0] == "train":
            lab[0] = "unused"
        name = "+".join(str(s) for s in g["stages"])
        for r, l in zip(rs, lab):
            out[r["window_id"]] = (l, name)
        prev_test_last = rs[-1]["window_id"] if n else prev_test_last
    return out


def main():
    force = "--before-freeze" in sys.argv
    if force and os.path.exists(os.path.join(C.out_root(), "reports", "FREEZE_1.json")):
        raise SystemExit("Freeze 1 exists: the split file cannot be rewritten")
    rep = dict(step=STEP, code_version=C.CODE_VERSION, lengths={})
    cls_of = {}
    for r in csv.DictReader(open(IO.out("data", "labels", "sessions.csv"), encoding="utf-8")):
        cls_of[r["session_key"]] = r["class"]
    for L in C.WINDOW_LENGTHS:
        win_path = IO.out("data", "windows", "w%d" % L, "windows.csv")
        rows = [r for r in csv.DictReader(open(win_path, encoding="utf-8")) if r["keep"] == "1"]
        by_sess = {}
        for r in rows:
            by_sess.setdefault(r["session_key"], []).append(r)
        new_rows = []
        for sk in by_sess:
            rs = sorted(by_sess[sk], key=lambda r: (int(r["login_order"]), int(r["w_index"])))
            res = split_session(rs)
            for r in rs:
                new_rows.append(dict(window_id=r["window_id"], session_key=sk, split=res[r["window_id"]][0],
                                     split_group=res[r["window_id"]][1], stage=r["stage"]))
        path = IO.out("data", "splits", "splits_w%d.csv" % L)
        appended = []
        if os.path.exists(path) and not force:
            old = list(csv.DictReader(open(path, encoding="utf-8")))
            old_by = {}
            for r in old:
                old_by.setdefault(r["session_key"], []).append(r)
            new_by = {}
            for r in new_rows:
                new_by.setdefault(r["session_key"], []).append(r)
            for sk, rs in old_by.items():
                if [dict(r) for r in rs] != [{k: str(v) for k, v in r.items()} for r in new_by.get(sk, [])]:
                    raise SystemExit("splits_w%d.csv: rows of session %s would change; refusing to overwrite" % (L, sk))
            final = old + [r for sk, rs in new_by.items() if sk not in old_by for r in rs]
            appended = [sk for sk in new_by if sk not in old_by]
        else:
            final = new_rows
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(final)
        # label files: train and validation labels apart from test labels (only the scorer reads those)
        tv = IO.out("data", "labels", "labels_trainval_w%d.csv" % L)
        te = IO.out("data", "labels", "labels_test_w%d.csv" % L)
        with open(tv, "w", newline="", encoding="utf-8") as f1, open(te, "w", newline="", encoding="utf-8") as f2:
            w1, w2 = csv.writer(f1), csv.writer(f2)
            w1.writerow(["window_id", "class"])
            w2.writerow(["window_id", "class"])
            for r in final:
                if r["split"] in ("train", "val"):
                    w1.writerow([r["window_id"], cls_of[r["session_key"]]])
                elif r["split"] == "test":
                    w2.writerow([r["window_id"], cls_of[r["session_key"]]])
        counts = {}
        groups = {}
        for r in final:
            c = counts.setdefault(r["session_key"], dict(train=0, val=0, test=0, unused=0))
            c[r["split"]] += 1
            g = groups.setdefault(r["session_key"], {})
            g[r["split_group"]] = g.get(r["split_group"], 0) + 1
        by_class = {}
        for sk, c in counts.items():
            d = by_class.setdefault(cls_of[sk], dict(train=0, val=0, test=0, unused=0))
            for k, v in c.items():
                d[k] += v
        rep["lengths"]["w%d" % L] = dict(
            input_sha256=IO.sha256_file(win_path)[0], kept_windows=len(final),
            by_session=counts, groups_by_session=groups, by_class=by_class, sessions_appended=appended,
            output_sha256={"splits": IO.sha256_file(path)[0], "labels_trainval": IO.sha256_file(tv)[0],
                           "labels_test": IO.sha256_file(te)[0]})
        print("w%d" % L, len(final), "kept windows;", json.dumps(by_class))
        for sk in counts:
            print("   ", sk, counts[sk], groups[sk])
    IO.write_json(IO.out("reports", "06_split_report.json"), rep)
    print("COMPLETE: split")
    return 0


if __name__ == "__main__":
    sys.exit(main())
