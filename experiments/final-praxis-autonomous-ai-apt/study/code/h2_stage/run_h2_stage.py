"""Study 3, H2 (ATT&CK stage groups): the frozen chance baseline, split by stage group.

    python3 -I -B code/h2_stage/run_h2_stage.py run --shard 0/4      the 1,260 chance tasks, in slices
    python3 -I -B code/h2_stage/run_h2_stage.py status

Post hoc (2026-11-14); the rule is in results_h2_stage/H2_RULE_BEFORE_RUN.md and was
written before this code was run.

What this does and does not do:
- The frozen trial code (code/trials/trial_common.py) is imported and run unchanged. No
  model, weight, calibration, threshold, seed or column list is set here.
- Each of the 126 relabelings is run through run_loso exactly as the frozen scored run
  ran it. The frozen run kept one confusion count per relabeling; this run keeps the
  same count and, beside it, the count within each stage group and each session.
- The stage group is joined to the predictions after they are made (reading T13).
- Nothing in results/, data/, reports/ or the frozen code is written. Outputs go to
  results_h2_stage/.

The shell stops every command after three minutes, so the run works in slices, as the
frozen runner does: repeat until status prints COMPLETE.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CODE, "trials"))            # the frozen trial code, read only
import trial_common as T

np = T.np
VERSION = "study3-h2-stage-1.0"
OUT = os.path.join(T.ROOT, "results_h2_stage")
PARTS = os.path.join(OUT, "parts")
RULE = os.path.join(OUT, "H2_RULE_BEFORE_RUN.md")
CONFIGS = list(T.CHANCE_CONFIGS)                             # main, no_command_content
N_PARTS = 126
ALL_KINDS = ("trial_code", "feature_table", "design", "plumbing", "feature_code", "eda_code",
             "feature_report", "eda_output", "plumbing_parts")
EST = {"lr": 3.0, "rf": 12.0, "gb": 18.0, "hgb": 14.0, "xgb": 8.0}    # seconds a task until measured


def all_tasks():
    return [("chance", cfg, part, m) for cfg in CONFIGS for part in range(N_PARTS) for m in T.MODELS]


def key(task):
    return "%s|%s|%d|%s" % task                              # the frozen runner's key


def read_log(path):
    recs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    pass                                     # a line cut short by a stopped command
    return recs


def all_records():
    recs = {}
    if os.path.isdir(PARTS):
        for name in sorted(os.listdir(PARTS)):
            if name.endswith(".jsonl"):
                for r in read_log(os.path.join(PARTS, name)):
                    recs[r["key"]] = r
    return recs


class Context:
    def __init__(self):
        if not os.path.exists(RULE):
            raise SystemExit("REFUSED: the rule file is written before the run")
        self.rule_sha256 = T.sha256_file(RULE)
        self.freeze_2_sha256 = T.check_freeze_2(kinds=ALL_KINDS)
        self.inp = T.Inputs("scored")
        self.tab = T.load_table(self.inp, "w30")
        stage = {}
        for r in self.inp.rows("data/description/window_description_w30.csv",
                               ["window_id", "stage_group", "keep"]):
            if r["keep"] == "1":
                stage[r["window_id"]] = r["stage_group"]
        if sorted(stage) != sorted(self.tab.window_id):
            raise SystemExit("STOP: the described windows are not the kept windows")
        self.stage = stage
        log = T.read_json(os.path.join(T.PLUMB, "PLUMBING_LOG.json"))
        self.plumbed = {r["key"]: r["fit_hash"] for r in log["tasks"]}
        if T.library_versions() != log["libraries"]:
            raise SystemExit("STOP: the libraries are not those of the plumbing run")


def run_task(task, ctx):
    kind, cfg, part, model = task
    t0 = time.time()
    tab = ctx.tab
    cols = T.config_columns(tab, cfg)
    rows = T.subset_rows(tab, None)
    combo = T.chance_labelings(tab.sessions)[part]
    class_of = {s: int(s in combo) for s in tab.sessions}
    res = T.run_loso(tab, rows, cols, class_of, model, True)          # the frozen procedure
    preds = res["predictions"]
    tp, fp, fn, tn = T.confusion([p["y"] for p in preds], [p["called_ai"] for p in preds])
    by_stage, by_session_stage = {}, {}
    for g in T.STAGE_GROUPS:
        sub = [p for p in preds if ctx.stage[p["window_id"]] == g]
        by_stage[g] = list(T.confusion([p["y"] for p in sub], [p["called_ai"] for p in sub]))
    for p in preds:
        d = by_session_stage.setdefault(p["session"], {})
        e = d.setdefault(ctx.stage[p["window_id"]], [0, 0])           # windows, windows called AI
        e[0] += 1
        e[1] += p["called_ai"]
    return dict(key=key(task), kind=kind, configuration=cfg, part=part, model=model,
                ai_sessions=list(combo), is_true_labeling=class_of == tab.class_of,
                n_rows=res["n_rows"], n_columns=res["n_columns"], n_fits=res["n_fits"],
                fit_hash=res["fit_hash"], matches_plumbing=ctx.plumbed.get(key(task)) == res["fit_hash"],
                tp=tp, fp=fp, fn=fn, tn=tn, macro_f1=T.f1_parts(tp, fp, fn, tn)["macro_f1"],
                stage=by_stage, session_stage=by_session_stage,
                rule_sha256=ctx.rule_sha256, freeze_2_sha256=ctx.freeze_2_sha256, version=VERSION,
                seconds=round(time.time() - t0, 2))


def run(shard, nshards, budget):
    t0 = time.time()
    ctx = Context()
    recs = all_records()
    est = {}
    for r in recs.values():
        est[r["model"]] = max(est.get(r["model"], 0.0), r.get("seconds", 0.0) * 1.25 + 1.0)
    mine = [t for i, t in enumerate(all_tasks()) if i % nshards == shard and key(t) not in recs]
    os.makedirs(PARTS, exist_ok=True)
    log = os.path.join(PARTS, "shard_%d_of_%d.jsonl" % (shard, nshards))
    if os.path.exists(log) and os.path.getsize(log):
        with open(log, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(log, "a", encoding="utf-8") as g:
                    g.write("\n")
    n = 0
    for task in mine:
        need = est.get(task[3], EST[task[3]])
        if time.time() - t0 + need > budget:
            continue                                         # a shorter task may still fit
        rec = run_task(task, ctx)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        n += 1
    print("shard %d/%d: ran %d, %d left, %.0f s" % (shard, nshards, n, len(mine) - n, time.time() - t0))


def status():
    recs = all_records()
    tasks = all_tasks()
    left = sum(1 for t in tasks if key(t) not in recs)
    by = {}
    for t in tasks:
        d = by.setdefault(t[1], [0, 0])
        d[1] += 1
        d[0] += key(t) in recs
    secs = sum(r.get("seconds", 0.0) for r in recs.values())
    print(" ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in by.items()),
          "| compute so far %.0f s |" % secs, "COMPLETE" if left == 0 else "INCOMPLETE (%d left)" % left)
    return left


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        shard, nshards, budget = 0, 1, 140.0
        for i, a in enumerate(sys.argv):
            if a == "--shard":
                shard, nshards = [int(x) for x in sys.argv[i + 1].split("/")]
            if a == "--budget":
                budget = float(sys.argv[i + 1])
        run(shard, nshards, budget)
    elif cmd == "status":
        status()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
