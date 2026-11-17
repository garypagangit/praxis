"""EDA run 3: shared pieces.

Implements `reports/eda_run3/RULE_BEFORE_RUN.md`. Run 3 re-cuts the feature EDA for the
research questions and hypotheses as they now stand. It is a description: no model is
fitted and no feature, score, split or frozen file is changed.

The Pass 1 and Pass 2 code in `code/eda/` is imported and never edited. Run 3 adds:
  * Inputs3: every input is on a fixed list and is checked before it is read, against
    Freeze 1 or Freeze 2 where a freeze lists it, otherwise against the hash recorded in
    `reports/eda/pass2_checks.json`. The evidence folder, `set_aside/`, the private key
    map and the test-label files are refused by name.
  * the names used in the paper: stage groups as in its Table 3-2, plain feature labels.
No command text and no recorder or audit record is opened by run 3.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("S3_ROOT") or os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "code", "eda"))          # Pass 1 and Pass 2 code: imported, never edited
_LIBS = os.environ.get("S3_LIBS")
if _LIBS and _LIBS not in sys.path:
    sys.path.append(_LIBS)

import pass2_common as C

E = C.E
np = C.np

RUN3_VERSION = "eda-run3-1.0"
OUT = os.environ.get("RUN3_OUT") or os.path.join(ROOT, "reports", "eda_run3")
TABLES = os.path.join(OUT, "tables")
FIGURES = os.path.join(OUT, "figures")
WL = "w30"
PASS2_CHECKS = "reports/eda/pass2_checks.json"
PASS2_CHECKS_SHA256 = "9a89d5a07ce45f4982f81e515c9dd6a40cbf7f5c53b2a198f37fd3a221482ee3"
EDA_TABLES = "reports/eda/tables/"

# Names used in the paper (its Table 3-2). The keys are the stage-group codes of the data.
STAGE_GROUPS = ["1-4", "5", "6", "7"]
STAGE_NAME = {"1-4": "Discovery", "5": "Execution", "6": "Account manipulation",
              "7": "Lateral movement and collection"}
STAGE_NAME_2L = {"1-4": "Discovery", "5": "Execution", "6": "Account\nmanipulation",
                 "7": "Lateral movement\nand collection"}
STAGE_ABBR = {"1-4": "Disc.", "5": "Exec.", "6": "Acct.", "7": "Lat."}
STAGES_OF = {"1-4": "stages 1 to 4", "5": "stage 5", "6": "stage 6", "7": "stage 7"}
TIERS_MAIN = ["behavior", "command_content", "context"]
TIER_NAME = {"behavior": "Behavior", "command_content": "Command content", "context": "Context"}

# The six columns that carry the features H1 names (rule file, section 3).
H1_COLUMNS = ["cmd_len_mean", "cmd_len_max", "flags_per_cmd", "pipes_per_cmd", "chain_ratio", "redirect_ratio"]
EXAMPLE_COLUMNS = ["cmd_count", "gap_median", "exec_count", "output_bytes", "cmd_len_mean", "flags_per_cmd",
                   "pipes_per_cmd", "chain_ratio", "redirect_ratio"]

# Plain labels for the 40 columns of the main configuration, worded as in the paper's tables.
LABEL = {
    "cmd_count": "Commands submitted",
    "gap_mean": "Mean gap between commands (s)",
    "gap_median": "Median gap between commands (s)",
    "gap_min": "Shortest gap between commands (s)",
    "gap_max": "Longest gap between commands (s)",
    "gap_std": "Spread of the gaps (s)",
    "gap_cv": "Variability of the gaps",
    "gap_autocorr": "Autocorrelation of the gaps",
    "exec_count": "Programs started",
    "exec_distinct": "Distinct programs started",
    "exec_per_cmd": "Programs started per command",
    "proc_depth_max": "Process depth",
    "output_bytes": "Program output (bytes)",
    "output_per_cmd_mean": "Mean output per command (bytes)",
    "output_per_cmd_cv": "Variability of output per command",
    "fail_ratio": "Share of commands that failed",
    "shell_error_count": "Shell errors",
    "retry_count": "Retries",
    "chars_submitted": "Command text (characters)",
    "cmd_len_mean": "Mean command length (characters)",
    "cmd_len_max": "Longest command (characters)",
    "cmd_unique": "Unique commands",
    "cmd_diversity": "Command diversity",
    "transition_entropy": "Transition entropy",
    "prog_distinct": "Distinct program names",
    "prog_entropy": "Entropy of program names",
    "flags_per_cmd": "Flags per command",
    "pipes_per_cmd": "Pipes per command",
    "chain_ratio": "Share of commands chained",
    "redirect_ratio": "Share of commands with a redirect",
    "help_count": "Help requests",
    "io_ratio": "Output per character submitted",
    "ctx_cmd_count": "Commands, look-back",
    "ctx_exec_count": "Programs started, look-back",
    "ctx_output_bytes": "Program output, look-back (bytes)",
    "ctx_active_windows": "Windows with a command, look-back",
    "ctx_chars_submitted": "Command text, look-back (characters)",
    "ctx_cmd_len_max": "Longest command, look-back (characters)",
    "ctx_cmd_diversity": "Command diversity, look-back",
    "ctx_transition_entropy": "Transition entropy, look-back",
}


def short_label(col):
    """The label without its unit, for tight places."""
    s = LABEL[col]
    return s[:s.index(" (")] if " (" in s else s


class Inputs3(C.Inputs2):
    """Inputs for run 3: allowlist, refusal by name, and a check of every file before it is read
    against Freeze 1, Freeze 2 or the hashes recorded by Pass 2."""

    def __init__(self, allow):
        super().__init__(allow)
        p = os.path.join(ROOT, *PASS2_CHECKS.split("/"))
        self.pass2_checks_sha256 = E.sha256_file(p)
        if self.pass2_checks_sha256 != PASS2_CHECKS_SHA256:
            raise SystemExit("STOP: pass2_checks.json does not hash as recorded")
        with open(p, encoding="utf-8") as f:
            self.pass2_outputs = json.load(f)["outputs"]

    def path(self, rel, columns=None):
        if any(part in rel for part in E.FORBIDDEN_PARTS):
            raise SystemExit("REFUSED: the EDA never opens " + rel)
        if rel not in self.allow:
            raise SystemExit("REFUSED: not in run 3's input list: " + rel)
        if not (rel.startswith("data/") or rel.startswith("reports/")):
            raise SystemExit("REFUSED: inputs come only from data/ and reports/: " + rel)
        p = os.path.join(ROOT, *rel.split("/"))
        digest, size = E.sha256_file(p), os.path.getsize(p)
        if rel in self.freeze:
            which, ok = "freeze_1", (self.freeze[rel]["sha256"] == digest and self.freeze[rel]["bytes"] == size)
        elif rel in self.freeze2:
            which, ok = "freeze_2", (self.freeze2[rel]["sha256"] == digest and self.freeze2[rel]["bytes"] == size)
        elif rel.startswith("reports/eda/") and rel[len("reports/eda/"):] in self.pass2_outputs:
            which, ok = "pass2_checks", self.pass2_outputs[rel[len("reports/eda/"):]] == digest
        else:
            raise SystemExit("STOP: input is in neither freeze nor the Pass 2 record: " + rel)
        if not ok:
            raise SystemExit("STOP: input does not match %s: %s" % (which, rel))
        entry = {"bytes": size, "sha256": digest, which: "match"}
        if columns is not None:
            entry["columns_read"] = list(columns)
        self.opened[rel] = entry
        return p

    def table(self, name):
        """A Pass 1 or Pass 2 table, checked, all columns."""
        with open(self.path(EDA_TABLES + name), encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.opened[EDA_TABLES + name]["rows"] = len(rows)
        return rows


def write_csv(name, header, rows):
    os.makedirs(TABLES, exist_ok=True)
    p = os.path.join(TABLES, name)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    return p


def read_run3(name):
    with open(os.path.join(TABLES, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(s):
    return None if s in ("", None) else float(s)


def f4(v):
    return "" if v is None else "%.4f" % v


def g6(v):
    return "" if v is None else "%.6g" % v


def quartiles(v):
    if not len(v):
        return None, None, None
    q1, q2, q3 = np.percentile(np.asarray(v, dtype=float), [25, 50, 75])       # linear interpolation
    return float(q1), float(q2), float(q3)
