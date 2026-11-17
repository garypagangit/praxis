"""Study 3 trials: runner (design section 10).

    python3 -I -B code/trials/run_trials.py plumbing --shard 0/4     fit everything, score nothing
    python3 -I -B code/trials/run_trials.py plumbing-log             assemble reports/plumbing/PLUMBING_LOG.json
    python3 -I -B code/trials/run_trials.py freeze2 --confirm        write reports/FREEZE_2.json
    python3 -I -B code/trials/run_trials.py score --shard 0/4        each trial scored once, into results/
    python3 -I -B code/trials/run_trials.py status plumbing|score

The shell this was built in stops every command after three minutes, so a run works
through its tasks in slices and is repeated until it prints COMPLETE. The tasks are
numbered parts: one model of one trial, or one model of one relabeling of the chance
baseline. A stopped part leaves nothing behind and is simply run again. Shards split
the task list by position so that several processes can work side by side; the result
is the same however the work is sliced.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import trial_common as T

np = T.np
EST = {"lr": 4.0, "rf": 22.0, "gb": 40.0, "hgb": 20.0, "xgb": 18.0}   # seconds a task until measured
N_PARTS = 126                                  # every way of calling 4 of 9 sessions AI
if os.environ.get("S3_ROOT") and os.environ.get("S3_TEST_CHANCE_PARTS"):
    N_PARTS = int(os.environ["S3_TEST_CHANCE_PARTS"])     # self-test on the synthetic tree only


def all_tasks():
    tasks = []
    for name in T.LOSO_TRIALS:
        for m in T.MODELS:
            tasks.append(("loso", name, -1, m))
    for name in T.INSIDE_TRIALS:
        for m in T.MODELS:
            tasks.append(("inside", name, -1, m))
    for cfg in T.CHANCE_CONFIGS:
        for part in range(N_PARTS):
            for m in T.MODELS:
                tasks.append(("chance", cfg, part, m))
    return tasks


def key(task):
    return "%s|%s|%d|%s" % task


def parts_dir(mode):
    return os.path.join(T.PLUMB if mode == "plumbing" else T.RESULTS, "parts")


def read_log(path):
    recs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    pass                      # a line cut short by a stopped command
    return recs


def all_records(mode):
    d = parts_dir(mode)
    recs = {}
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if name.endswith(".jsonl"):
                for r in read_log(os.path.join(d, name)):
                    recs[r["key"]] = r
    return recs


def result_path(name, model):
    return os.path.join(T.RESULTS, "trials", "%s__%s.json" % (name, model))


class Context:
    def __init__(self, mode):
        self.mode = mode
        self.inp = T.Inputs(mode)
        self._tables = {}
        self._cache = {}
        self.freeze_2_sha256 = T.check_freeze_2() if mode == "scored" else None
        self.plumbed = None
        if mode == "scored":
            log = T.read_json(os.path.join(T.PLUMB, "PLUMBING_LOG.json"))
            self.plumbed = {r["key"]: r["fit_hash"] for r in log["tasks"]}

    def table(self, window):
        if window not in self._tables:
            self._tables[window] = T.load_table(self.inp, window)
        return self._tables[window]

    def once(self, name, fn):
        if name not in self._cache:
            self._cache[name] = fn()
        return self._cache[name]

    def splits(self, window):
        return self.once("split" + window, lambda: {
            r["window_id"]: r["split"] for r in
            self.inp.rows("data/splits/splits_%s.csv" % window, ["window_id", "split"])})

    def trainval(self, window):
        return self.once("tv" + window, lambda: T.class_map_from_label_file(
            self.inp, "data/labels/labels_trainval_%s.csv" % window))

    def test(self, window):          # scored mode only; the plumbing run refuses the file by name
        return self.once("te" + window, lambda: T.class_map_from_label_file(
            self.inp, "data/labels/labels_test_%s.csv" % window))


def run_task(task, ctx):
    kind, name, part, model = task
    scored = ctx.mode == "scored"
    t0 = time.time()
    rec = dict(key=key(task), kind=kind, name=name, part=part, model=model)
    if kind in ("loso", "chance"):
        window, config, subset = T.LOSO_TRIALS[name] if kind == "loso" else ("w30", name, None)
        tab = ctx.table(window)
        cols = T.config_columns(tab, config)
        rows = T.subset_rows(tab, subset)
        if kind == "loso":
            class_of = tab.class_of
        else:
            combo = T.chance_labelings(tab.sessions)[part]
            class_of = {s: int(s in combo) for s in tab.sessions}
            rec["ai_sessions"] = list(combo)
            rec["is_true_labeling"] = class_of == tab.class_of
        res = T.run_loso(tab, rows, cols, class_of, model, scored)
    else:
        window, config = T.INSIDE_TRIALS[name]
        subset = None
        tab = ctx.table(window)
        cols = T.config_columns(tab, config)
        res = T.run_inside(tab, cols, model, ctx.splits(window), ctx.trainval(window),
                           ctx.test(window) if scored else None, scored)
    rec.update(window=window, configuration=config, n_columns=res["n_columns"], n_fits=res["n_fits"],
               fit_hash=res["fit_hash"], prep_group=res["prep_group"])
    for k in ("n_rows", "n_train_rows", "n_val_rows", "n_test_rows", "n_embargoed_rows"):
        if k in res:
            rec[k] = res[k]
    if kind != "inside":
        rec["fold_train_rows"] = [f["n_train_rows"] for f in res["folds"]]
        rec["fold_calibration_predictions"] = [f["n_calibration_predictions"] for f in res["folds"]]
    if scored:
        rec["matches_plumbing"] = ctx.plumbed.get(rec["key"]) == res["fit_hash"]
        preds = res["predictions"]
        tp, fp, fn, tn = T.confusion([p["y"] for p in preds], [p["called_ai"] for p in preds])
        rec.update(tp=tp, fp=fp, fn=fn, tn=tn, macro_f1=T.f1_parts(tp, fp, fn, tn)["macro_f1"])
        if kind != "chance":
            doc = dict(trial=name, kind=kind, model=model, window=window, configuration=config,
                       subset=subset, columns=cols, trial_version=T.TRIAL_VERSION,
                       freeze_2_sha256=ctx.freeze_2_sha256, matches_plumbing=rec["matches_plumbing"])
            doc.update(res)
            T.write_once(result_path(name, model), T.dump_json(doc))
    rec["seconds"] = round(time.time() - t0, 2)
    return rec


def estimates():
    est = {}
    for mode in ("plumbing", "scored"):
        for r in all_records(mode).values():
            k = (r["kind"], r["model"])
            est[k] = max(est.get(k, 0.0), r.get("seconds", 0.0) * 1.25 + 1.0)
    return est


def run(mode, shard, nshards, budget):
    t0 = time.time()
    if mode == "plumbing" and os.path.exists(T.FREEZE_2):
        raise SystemExit("REFUSED: Freeze 2 is written; the plumbing run is closed")
    ctx = Context(mode)
    done = set(all_records(mode))
    if mode == "scored":
        for task in all_tasks():
            if task[0] != "chance" and os.path.exists(result_path(task[1], task[3])):
                done.add(key(task))
    mine = [t for i, t in enumerate(all_tasks()) if i % nshards == shard and key(t) not in done]
    est = estimates()
    os.makedirs(parts_dir(mode), exist_ok=True)
    log = os.path.join(parts_dir(mode), "shard_%d_of_%d.jsonl" % (shard, nshards))
    if os.path.exists(log) and os.path.getsize(log):
        with open(log, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(log, "a", encoding="utf-8") as g:
                    g.write("\n")
    n = 0
    for task in mine:
        need = est.get((task[0], task[3]), EST[task[3]])
        if time.time() - t0 + need > budget:
            continue                          # too long for what is left of this slice; a shorter one may fit
        rec = run_task(task, ctx)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        n += 1
    print("shard %d/%d: ran %d, %d left, %.0f s" % (shard, nshards, n, len(mine) - n, time.time() - t0))


def status(mode):
    recs = all_records(mode)
    tasks = all_tasks()
    done = set(recs)
    if mode == "scored":
        for task in tasks:
            if task[0] != "chance" and os.path.exists(result_path(task[1], task[3])):
                done.add(key(task))
    by = {}
    for t in tasks:
        d = by.setdefault(t[0], [0, 0])
        d[1] += 1
        d[0] += key(t) in done
    secs = sum(r.get("seconds", 0.0) for r in recs.values())
    left = sum(1 for t in tasks if key(t) not in done)
    print(" ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in by.items()),
          "| compute so far %.0f s |" % secs, "COMPLETE" if left == 0 else "INCOMPLETE (%d left)" % left)
    return left


def plumbing_log():
    """Counts and hashes only. Times go to their own file so that the log is the same
    on a rerun."""
    recs = all_records("plumbing")
    tasks = all_tasks()
    missing = [key(t) for t in tasks if key(t) not in recs]
    if missing:
        raise SystemExit("INCOMPLETE: %d plumbing tasks left" % len(missing))
    inp = T.Inputs("plumbing")
    opened = {}
    for w in ("w30", "w60"):
        tab = T.load_table(inp, w)
        for cfg in T.CONFIG_SIZE:
            T.config_columns(tab, cfg)
    for w in ("w30",):
        inp.rows("data/splits/splits_%s.csv" % w, ["window_id", "split"])
        T.class_map_from_label_file(inp, "data/labels/labels_trainval_%s.csv" % w)
    opened.update(inp.opened)
    keep = lambda r: {k: v for k, v in r.items() if k != "seconds"}
    doc = dict(step="plumbing run", trial_version=T.TRIAL_VERSION, design="real_lab3_feature_trial_design.md",
               freeze_1_sha256=inp.freeze1_sha256, libraries=T.library_versions(),
               model_settings=T.model_settings(), takes_undefined_values=T.nan_groups(),
               seed=T.SEED, threads_per_process=1, n_tasks=len(tasks),
               n_fits=sum(recs[key(t)]["n_fits"] for t in tasks),
               inputs_opened=opened, never_opened=["data/labels/labels_test_*", "data/description/*",
                                                   "data/labels/_private/*", "set_aside/*",
                                                   "AHIR Participant Evidence/*"],
               scores_written=0, held_out_sessions_predicted=0, test_rows_predicted=0,
               tasks=[keep(recs[key(t)]) for t in tasks])
    T.write_once(os.path.join(T.PLUMB, "PLUMBING_LOG.json"), T.dump_json(doc), overwrite=True)
    by = {}
    for t in tasks:
        r = recs[key(t)]
        d = by.setdefault("%s|%s" % (r["kind"], r["model"]), dict(tasks=0, seconds=0.0, longest=0.0))
        d["tasks"] += 1
        d["seconds"] = round(d["seconds"] + r["seconds"], 2)
        d["longest"] = max(d["longest"], r["seconds"])
    chance = sum(v["seconds"] for k, v in by.items() if k.startswith("chance"))
    T.write_once(os.path.join(T.PLUMB, "plumbing_timing.json"), T.dump_json(dict(
        by_kind_and_model=by, total_seconds=round(sum(v["seconds"] for v in by.values()), 1),
        chance_baseline_seconds=round(chance, 1),
        note="single-thread compute seconds, summed over tasks")), overwrite=True)
    print("plumbing log written: %d tasks, %d fits" % (len(tasks), doc["n_fits"]))


def freeze2():
    if "--confirm" not in sys.argv:
        raise SystemExit("Freeze 2 is written only on the user's word: run with --confirm")
    if os.path.exists(T.FREEZE_2):
        raise SystemExit("FREEZE_2.json exists; it is never overwritten")
    if os.path.exists(T.RESULTS):
        raise SystemExit("STOP: results/ exists before Freeze 2")
    log_path = os.path.join(T.PLUMB, "PLUMBING_LOG.json")
    log = T.read_json(log_path)
    if log["n_tasks"] != len(all_tasks()) or log["trial_version"] != T.TRIAL_VERSION:
        raise SystemExit("STOP: the plumbing log is not complete for this code")
    files = {}

    def add(rel, kind, base=T.ROOT):
        p = os.path.join(base, *rel.split("/"))
        files[rel] = dict(kind=kind, sha256=T.sha256_file(p), bytes=os.path.getsize(p))

    def walk(rel_dir, kind, base=T.ROOT, rel_prefix=None):
        top = os.path.join(base, *rel_dir.split("/"))
        if not os.path.isdir(top):
            raise SystemExit("STOP: missing " + rel_dir)
        for dirpath, dirs, names in os.walk(top):
            dirs.sort()
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(names):
                if name.endswith((".pyc", ".part", ".tmp")) or name == ".DS_Store":
                    continue
                p = os.path.join(dirpath, name)
                rel = (rel_prefix or rel_dir) + "/" + os.path.relpath(p, top).replace(os.sep, "/")
                files[rel] = dict(kind=kind, sha256=T.sha256_file(p), bytes=os.path.getsize(p))

    # the design, as it stands at the freeze: a byte copy is kept so that later status
    # lines in the living documents do not touch what was frozen
    design_at_freeze = {}
    for doc in ("real_lab3_feature_trial_design.md", "real_lab3_eda_handoff.md"):
        src = os.path.join(T.ROOT, doc)
        with open(src, "rb") as f:
            data = f.read()
        design_at_freeze[doc] = T.sha256_bytes(data)
        dst = os.path.join(T.REPORTS, "freeze2", doc)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            raise SystemExit("STOP: a frozen copy already exists: " + dst)
        with open(dst, "wb") as f:
            f.write(data)
        add("reports/freeze2/" + doc, "design")
    walk("trials", "trial_code", base=T.CODE, rel_prefix="code/trials")
    walk("features", "feature_code", base=T.CODE, rel_prefix="code/features")
    walk("eda", "eda_code", base=T.CODE, rel_prefix="code/eda")
    walk("data/features", "feature_table")
    for rel in ("reports/10_features_report.json", "reports/10_features_checks.json",
                "reports/10_features_review_windows.md"):
        add(rel, "feature_report")
    walk("reports/eda", "eda_output")
    walk("reports/plumbing", "plumbing_parts")
    files["reports/plumbing/PLUMBING_LOG.json"]["kind"] = "plumbing"
    doc = dict(freeze="Freeze 2", trial_version=T.TRIAL_VERSION,
               design="real_lab3_feature_trial_design.md",
               design_documents_at_freeze=design_at_freeze,
               freeze_1_sha256=T.sha256_file(os.path.join(T.REPORTS, "FREEZE_1.json")),
               libraries=log["libraries"], model_settings=log["model_settings"],
               takes_undefined_values=log["takes_undefined_values"],
               files=files, n_files=len(files))
    T.write_once(T.FREEZE_2, T.dump_json(doc))
    print("Freeze 2 written:", len(files), "files, sha256", T.sha256_file(T.FREEZE_2))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("plumbing", "score"):
        shard, nshards, budget = 0, 1, 150.0
        for i, a in enumerate(sys.argv):
            if a == "--shard":
                shard, nshards = [int(x) for x in sys.argv[i + 1].split("/")]
            if a == "--budget":
                budget = float(sys.argv[i + 1])
        run("plumbing" if cmd == "plumbing" else "scored", shard, nshards, budget)
    elif cmd == "status":
        status("plumbing" if sys.argv[2] == "plumbing" else "scored")
    elif cmd == "plumbing-log":
        plumbing_log()
    elif cmd == "freeze2":
        freeze2()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
