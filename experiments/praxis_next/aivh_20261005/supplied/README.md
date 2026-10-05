# PX-090 · AIVH — AI-agent vs. human operator classification from log dumps

Classify whether an interactive attacker session (shell/SSH command dump with
timestamps) was driven by an **LLM agent** or a **human**, from passive logs
alone — no honeypot prompt-injection trap required — and wrap the classifier
in a **conformal abstention gate** that certifies a bounded error rate on the
decisions it emits.

This is the detection-side experiment. It does **not** study attacker evasion.
Full protocol and pre-registered hypotheses: [`EXPERIMENT.md`](EXPERIMENT.md).

## Why this is novel

Every published method that separates AI from human attackers today relies on
an *active lure* — a honeypot that plants hidden instructions and watches
whether the attacker obeys. Nobody has published a passive classifier over
ordinary session telemetry, and no public corpus pairs labeled human and LLM
sessions on matched tasks. AIVH builds that classifier and the evaluation that
would make it defensible: generalization to **unseen model families** (LOLO)
and **unseen environments** (LOEO), plus a **timing-free ablation** so the
result can't be dismissed as "it just measures latency."

## Install

```bash
pip install -r requirements.txt   # scikit-learn, numpy, scipy, pandas
```

## Quick start — smoke test (no data download)

```bash
python scripts/run.py --synthetic --out results/synthetic
python scripts/test_pipeline.py
```

The synthetic corpus encodes the literature's behavioral priors as **stubs**.
Near-perfect AUROC on it proves only that the pipeline runs and that the
features carry the intended signal — it says nothing about whether real agents
and humans are actually separable. That is what the real data is for.

## Real run

1. **Positive class (agents) — ready now.** Honey for the Agent, DOI
   `10.5281/zenodo.20818246`, CC-BY-4.0:
   ```bash
   curl -L -o data/zenodo/Logs_final.zip "https://zenodo.org/records/20818246/files/Logs_final.zip?download=1"
   unzip -q data/zenodo/Logs_final.zip -d data/zenodo/
   ```
   (If outbound `curl` is blocked in your environment, download in a browser
   and drop the zip into `data/zenodo/`.)

2. **Negative class (humans) — you must collect.** See `EXPERIMENT.md` §3.2.
   Record operators with `asciinema rec` (`.cast`) or `script -t`; drop files
   in `data/human/`. The ingest layer reconstructs commands and per-command
   timing from either format.

3. Evaluate:
   ```bash
   python scripts/run.py --zenodo data/zenodo --human 'data/human/*.cast' --out results/real
   ```

## Package layout

```
aivh/
  ingest.py     unified loader: zenodo / asciinema / script / cowrie → Session
  features.py   4 feature families (T timing, C content, S sequence, E errors)
  models.py     GBM, logistic regression, verb-ngram baseline
  gate.py       split-conformal abstention gate + Clopper–Pearson bound
  evaluate.py   random / LOLO / LOEO splits, ablations, bootstrap CIs
  synth.py      synthetic corpus (smoke-test stubs only)
scripts/
  run.py        CLI runner
  test_pipeline.py  guard tests (feature determinism, gate coverage property)
EXPERIMENT.md   pre-registration
```

## What the gate guarantees

Under exchangeability, `P(true label ∉ prediction set) ≤ α`. A label is
emitted only when the prediction set is a singleton; otherwise the session is
abstained on and escalated to an analyst. The threshold is fixed from a
held-out calibration split **before** any test point is seen and never adapted
online — that pre-committed, deterministic threshold is the gate the praxis
argument rests on. The reported numbers are **coverage** (fraction decided) and
**decided-error with a 95% Clopper–Pearson upper bound**.

Note: LOLO/LOEO deliberately **break** exchangeability (train and test differ
by model family / environment). Reporting how far the guarantee degrades under
that shift is itself a result, not a bug.

## Status

- [x] Ingest, features, models, gate, evaluation, synthetic smoke test, tests
- [ ] Zenodo download + ingest of real agent sessions
- [ ] IRB filing + human session collection (the gating dependency)
- [ ] Real RQ1–RQ5 runs, figures, Appendix A commit-hash citation
