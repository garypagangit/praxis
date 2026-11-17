"""Study 3 EDA: shared pieces.

Implements `real_lab3_eda_handoff.md`. The EDA is separate from the preprocessing
code in `code/` and imports nothing from it except the leak-audit patterns, which
the checks reuse (handoff section 10, check 3).

Rules enforced here (handoff section 1):
  2. Inputs come only from `data/` and `reports/`. The evidence folder, `set_aside/`,
     the private key map and the test-label files can never be opened.
  8. Outputs go only to `reports/eda/`. Nothing is written to `data/`.
Every input is checked against Freeze 1 before it is read, and every file opened
is logged with its hash.
"""
import csv
import hashlib
import json
import os

EDA_VERSION = "study3-eda-1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("S3_ROOT") or os.path.dirname(os.path.dirname(HERE))
OUT = os.environ.get("EDA_OUT") or os.path.join(ROOT, "reports", "eda")
TABLES = os.path.join(OUT, "tables")
FIGURES = os.path.join(OUT, "figures")

FORBIDDEN_PARTS = ("AHIR Participant Evidence", "set_aside", "_private", "labels_test_")

STAGE_GROUPS = ["1-4", "5", "6", "7"]
STAGE_GROUP_LABEL = {"1-4": "Stages 1–4", "5": "Stage 5", "6": "Stage 6", "7": "Stage 7"}
CLASSES = ["human", "ai"]
CLASS_LABEL = {"human": "Human", "ai": "AI"}
SPLITS = ["train", "val", "test", "unused"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Inputs:
    """Opens inputs from an allowlist, checks each against Freeze 1, logs it."""

    def __init__(self, allow):
        self.allow = set(allow)
        self.opened = {}
        fz_path = os.path.join(ROOT, "reports", "FREEZE_1.json")
        self.freeze_sha256 = sha256_file(fz_path)
        with open(fz_path, encoding="utf-8") as f:
            self.freeze = json.load(f)["files"]

    def path(self, rel, columns=None):
        if any(part in rel for part in FORBIDDEN_PARTS):
            raise SystemExit("REFUSED: the EDA never opens " + rel)
        if rel not in self.allow:
            raise SystemExit("REFUSED: not in this pass's input list: " + rel)
        if not (rel.startswith("data/") or rel.startswith("reports/")):
            raise SystemExit("REFUSED: inputs come only from data/ and reports/: " + rel)
        p = os.path.join(ROOT, *rel.split("/"))
        digest = sha256_file(p)
        frozen = self.freeze.get(rel)
        if frozen is None:
            raise SystemExit("STOP: input is not listed in Freeze 1: " + rel)
        if frozen["sha256"] != digest or frozen["bytes"] != os.path.getsize(p):
            raise SystemExit("STOP: input does not match Freeze 1: " + rel)
        entry = {"bytes": os.path.getsize(p), "sha256": digest, "freeze_1": "match"}
        if columns is not None:
            entry["columns_read"] = list(columns)
        self.opened[rel] = entry
        return p

    def read_json(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return json.load(f)

    def read_csv(self, rel, columns):
        """Rows as dicts holding only the named columns. Other columns are never kept."""
        p = self.path(rel, columns)
        rows = []
        with open(p, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = [c for c in columns if c not in reader.fieldnames]
            if missing:
                raise SystemExit("STOP: %s lacks columns %s" % (rel, missing))
            for r in reader:
                rows.append({c: r[c] for c in columns})
        self.opened[rel]["rows"] = len(rows)
        return rows


def write_csv(name, header, rows):
    """Deterministic CSV in reports/eda/tables/. Returns the path."""
    os.makedirs(TABLES, exist_ok=True)
    p = os.path.join(TABLES, name)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    return p


def read_table(name):
    with open(os.path.join(TABLES, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def read_json_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pct(part, whole):
    return "" if not whole else "%.1f" % (100.0 * part / whole)


def session_table(inp):
    """Sessions in display order (humans first), labeled as in Table 4-1.

    The label (P001 ...) and the session key are both in the windows step report,
    so the private key map is not needed and is never opened.
    """
    rep = inp.read_json("reports/05_windows_report.json")
    label_of = {v["session_key"]: label for label, v in rep["sessions"].items()}
    cls_rows = inp.read_csv("data/labels/sessions.csv",
                            ["session_key", "class", "included", "logins_used"])
    desc_rows = inp.read_csv("data/description/sessions.csv",
                             ["session_key", "lab_range", "logins_recorded", "logins_used",
                              "working_time_s", "stages_accepted_by_operator",
                              "finished_stage_7"])
    desc = {r["session_key"]: r for r in desc_rows}
    sessions = []
    for r in cls_rows:
        if r["included"] != "1":
            continue
        k = r["session_key"]
        sessions.append({
            "session_key": k,
            "session": label_of[k],
            "class": r["class"],
            "lab_range": desc[k]["lab_range"],
            "logins_recorded": int(desc[k]["logins_recorded"]),
            "logins_used": int(desc[k]["logins_used"]),
            "working_time_s": float(desc[k]["working_time_s"]),
            "stages_accepted_by_operator": int(desc[k]["stages_accepted_by_operator"]),
            "finished_stage_7": int(desc[k]["finished_stage_7"]),
        })
    sessions.sort(key=lambda s: (CLASSES.index(s["class"]), s["session"]))
    return sessions, rep
