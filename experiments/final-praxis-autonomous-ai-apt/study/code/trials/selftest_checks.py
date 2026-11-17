"""Checks of the trial code on the synthetic tree. Never run on the study data.

    S3_ROOT=/tmp/s3_fixture python3 -I -B code/trials/selftest_checks.py

1. The weights give each class half the total and each session an equal share of its class.
2. The threshold equals a brute-force search.
3. Leave one session out, written the long way (a fresh fit for every calibration fold of
   every held-out session), gives the same predictions as run_loso, which makes each
   shared fit once (T10).
4. The metrics equal scikit-learn's.
5. The plumbing run cannot open the test labels or the description files; a column with a
   forbidden name is refused.
6. Medians and scaling are fitted on training rows only.
"""
import os
import sys

if not os.environ.get("S3_ROOT"):
    raise SystemExit("REFUSED: the self-test runs on the synthetic tree only (set S3_ROOT)")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trial_common as T

np = T.np


def naive_loso(tab, cols, model):
    ci = [tab.columns.index(c) for c in cols]
    X = tab.X[:, ci]
    sess = tab.session
    y = np.array([tab.class_of[s] for s in sess])
    out = {}
    for s in tab.sessions:
        others = [t for t in tab.sessions if t != s]
        oof, yo, so = [], [], []
        for t in others:
            tr = np.where((sess != s) & (sess != t))[0]
            f = T.fit_model(model, cols, tab.info, X[tr], y[tr], T.session_weights(sess[tr], y[tr]))
            ix = np.where(sess == t)[0]
            oof.append(T.raw_score(f, X[ix]))
            yo.append(y[ix])
            so.append(sess[ix])
        oof, yo, so = np.concatenate(oof), np.concatenate(yo), np.concatenate(so)
        w = T.session_weights(so, yo)
        cal = T.platt_fit(oof, yo, w)
        thr = T.best_threshold(cal.predict(oof), yo)
        tr = np.where(sess != s)[0]
        final = T.fit_model(model, cols, tab.info, X[tr], y[tr], T.session_weights(sess[tr], y[tr]))
        ix = np.where(sess == s)[0]
        p = cal.predict(T.raw_score(final, X[ix]))
        for j, i in enumerate(ix):
            out[tab.window_id[i]] = (float(p[j]), int(p[j] >= thr))
    return out


def main():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print("PASS" if cond else "FAIL", name)

    inp = T.Inputs("scored")
    tab = T.load_table(inp, "w30")
    cols = T.config_columns(tab, "main")
    y = np.array([tab.class_of[s] for s in tab.session])

    w = T.session_weights(tab.session, y)
    shares = {s: w[tab.session == s].sum() / w.sum() for s in tab.sessions}
    check("1 weights: each class holds half", abs(sum(v for s, v in shares.items() if tab.class_of[s]) - 0.5) < 1e-12)
    check("1 weights: sessions equal within a class",
          all(abs(shares[s] - 0.5 / sum(1 for t in tab.sessions if tab.class_of[t] == tab.class_of[s])) < 1e-12
              for s in tab.sessions))
    check("1 weights: average 1", abs(w.mean() - 1.0) < 1e-12)

    rng = np.random.default_rng(1)
    good = True
    for _ in range(200):
        n = int(rng.integers(5, 60))
        p = np.round(rng.random(n), 2)
        yy = (rng.random(n) < 0.4).astype(int)
        thr = T.best_threshold(p, yy)
        f = lambda t: T.f1_parts(*T.confusion(yy, p >= t))["macro_f1"]
        d = np.unique(p)
        best = max([f(t) for t in (d[:-1] + d[1:]) / 2.0] or [f(0.5)])
        good = good and abs(f(thr) - best) < 1e-12
    check("2 threshold equals brute force (200 random cases)", good)

    for model in ("lr", "rf"):
        res = T.run_loso(tab, np.arange(len(tab.window_id)), cols, tab.class_of, model, True)
        naive = naive_loso(tab, cols, model)
        diff = max(abs(p["p_ai"] - naive[p["window_id"]][0]) for p in res["predictions"])
        same_calls = all(p["called_ai"] == naive[p["window_id"]][1] for p in res["predictions"])
        check("3 %s: shared fits equal the long way (largest difference %.2e)" % (model, diff),
              diff < 1e-9 and same_calls and len(naive) == len(res["predictions"]))
        plumb = T.run_loso(tab, np.arange(len(tab.window_id)), cols, tab.class_of, model, False)
        check("3 %s: the plumbing fit has the same hash and holds no prediction" % model,
              plumb["fit_hash"] == res["fit_hash"] and "predictions" not in plumb
              and not any("threshold" in f or "platt_a" in f for f in plumb["folds"]))

    from sklearn.metrics import balanced_accuracy_score, f1_score, precision_score, recall_score
    yy = np.array([p["y"] for p in res["predictions"]])
    cc = np.array([p["called_ai"] for p in res["predictions"]])
    m = T.f1_parts(*T.confusion(yy, cc))
    check("4 macro-F1, F1, precision, recall and balanced accuracy equal scikit-learn's",
          abs(m["macro_f1"] - f1_score(yy, cc, average="macro")) < 1e-12
          and abs(m["f1_ai"] - f1_score(yy, cc)) < 1e-12
          and abs(m["precision_ai"] - precision_score(yy, cc)) < 1e-12
          and abs(m["recall_ai"] - recall_score(yy, cc)) < 1e-12
          and abs(m["recall_human"] - recall_score(yy, cc, pos_label=0)) < 1e-12
          and abs(m["balanced_accuracy"] - balanced_accuracy_score(yy, cc)) < 1e-12)

    refused = 0
    for rel in ("data/labels/labels_test_w30.csv", "data/description/window_description_w30.csv",
                "data/labels/_private/key_map.csv", "set_aside/x"):
        try:
            T.Inputs("plumbing").path(rel)
        except SystemExit as e:
            refused += str(e).startswith("REFUSED")
    check("5 the plumbing run refuses test labels, description, key map and set-aside files", refused == 4)
    check("5 forbidden column names are caught",
          all(T.FORBIDDEN_NAME.search(c) for c in ("session_duration", "w_index", "stage_group", "login_order",
                                                   "elapsed_working_s", "class", "split"))
          and not any(T.FORBIDDEN_NAME.search(c) for c in tab.columns))

    ci = [tab.columns.index(c) for c in cols]
    Xtr = tab.X[tab.session != tab.sessions[0]][:, ci]
    prep = T.Prep("impute_scale", cols, tab.info).fit(Xtr)
    Z = prep.transform(Xtr)
    check("6 scaled training columns have mean 0 and sd 1; one extra column; nothing undefined",
          np.allclose(Z.mean(axis=0), 0, atol=1e-9) and np.allclose(Z.std(axis=0)[:-1], 1, atol=1e-9)
          and Z.shape[1] == len(cols) + 1 and not np.isnan(Z).any())
    med = [np.nanmedian(Xtr[:, j]) for j in range(Xtr.shape[1])]
    check("6 the medians are the training medians of the defined values", np.allclose(prep.med, med))
    check("6 models that take undefined values get them unchanged",
          T.Prep("native", cols, tab.info).fit(Xtr).transform(Xtr) is Xtr and all(T.nan_groups().values()))
    print("SELF-TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
