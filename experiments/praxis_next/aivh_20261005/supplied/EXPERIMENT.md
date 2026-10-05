# PX-090 — AIVH: Classifying AI-Agent vs. Human Operators from Shell-Session Log Dumps

**Status:** Pre-registration v0.1 (2026-10-04)
**Owner:** Gary Pagan, D.Eng. candidate, GWU
**Thesis fit:** deterministic gate + external verification wrapped around an ML component (same spine as PX-001 and cert-gate)
**Scope:** detection only. This experiment builds and certifies a *defender-side* classifier. It does not study how an attacker could evade it.

---

## 1. Summary

Given a passive log dump of an interactive attacker session (command sequence with timestamps, no honeypot trap planted), can a classifier tell whether the operator was an LLM agent or a human? We build a session-level classifier over timing, command-content, and sequence features; wrap it in a **conformal abstention gate** that certifies a bounded error rate on the decisions it emits; and test whether it generalizes to **unseen LLM families** and **unseen environments** — the only setting that matters, because a defender never knows which model an adversary is running.

The positive-by-construction result is the gate: even if the raw classifier is mediocre, the sessions it does label carry a certified error ceiling, and the contribution is *how much coverage is achievable under that ceiling*.

---

## 2. Research questions

| ID | Question | Pre-registered hypothesis | Falsifier |
|---|---|---|---|
| RQ1 | Do session features separate LLM-agent from human sessions under a random split? | AUROC ≥ 0.90 | AUROC < 0.80 |
| RQ2 | Does separation survive **leave-one-LLM-family-out** (LOLO)? | AUROC drop ≤ 0.10 vs. random split | drop > 0.15 on any held-out family |
| RQ3 | Does separation survive **leave-one-environment-out** (LOEO)? | AUROC drop ≤ 0.10 | drop > 0.15 |
| RQ4 | How much depends on **timing** features alone? | timing-free AUROC ≥ 0.80 | timing-free AUROC < 0.70 → result is "just latency" |
| RQ5 | Under a conformal gate at α = 0.05, what **coverage** is achievable and does held-out error stay ≤ α? | coverage ≥ 0.60 at certified error ≤ 0.05 | empirical error > α on ≥ 2 of 5 folds |

**Primary endpoint:** RQ2. A classifier that only recognizes one model family is a signature, not a detector.
**Secondary:** RQ4, RQ5.

---

## 3. Data

### 3.1 Positive class — LLM-agent sessions (public, available now)

**Honey for the Agent** (Maddaloni, Safargalieva, Vasilomanolakis — Technical University of Denmark)
Zenodo DOI 10.5281/zenodo.20818246 · published 2026-06-23 · CC-BY-4.0
https://zenodo.org/records/20818246

- `Logs_final.zip` (157.7 MB, md5 `4f3b30538e6e4c492716f87f184dd816`), ~16,200 session JSON files
- Design: 6 system prompts × {20, 30} max turns × 5 SSH environments (1 real Ubuntu + 4 Cowrie variants) × several LLM models × 30 sessions per cell
- Per turn: `[llm_raw_output, response_time_ms]`, `[shell_output, execution_time_ms]`, `[raw_command, parsed_command]`
- Turn 0: `[system_prompt, start_ts]`, `[banner, connection_latency_ms]`

```
curl -L -o data/zenodo/Logs_final.zip "https://zenodo.org/records/20818246/files/Logs_final.zip?download=1"
curl -L -o data/zenodo/inputs.json   "https://zenodo.org/records/20818246/files/inputs.json?download=1"
md5sum data/zenodo/Logs_final.zip
unzip -q data/zenodo/Logs_final.zip -d data/zenodo/
```

### 3.2 Negative class — human sessions (must be assembled)

No public corpus has labeled human and LLM interactive shell sessions side by side. Sources, in priority order:

**(a) Controlled collection — primary.** Recruit N ≥ 20 authorized operators (GWU cyber-course students, CyberQRT staff, red-team colleagues) to perform the **same six task prompts** from `inputs.json` against **the same five lab environments** (reproduce the DTU Cowrie configurations on an isolated range). Record with `script -t` or `asciinema rec` for per-command timestamps. Target ≥ 600 sessions. This is the only design that removes task and environment confounds. **IRB review before recruiting** — likely exempt (no PII in logs; operator ID only), but file it.

**(b) Public honeypot dumps — secondary, weakly labeled.** Research Cowrie logs on Zenodo/GitHub. Most are bots; interactive human sessions are identifiable by TTY negotiation, editing keystrokes, high-variance gaps, and correction patterns. Label "human-likely" and **use only for robustness checks, never for training the headline model.**

**(c) CTF / training recordings — tertiary.** Public asciinema casts of CTF solves. Human by construction but a different task distribution. Out-of-distribution human test set only.

### 3.3 Control class — scripted bots

From the same honeypot dumps: sessions with near-zero timing variance and identical command strings across many sources. Required to show the classifier is not simply "fast = AI". Reported as a secondary three-way table.

### 3.4 Matching rule

Positive and negative sessions are **matched on task prompt and environment** wherever possible. Anything that can't be matched is labeled OOD and reported separately.

---

## 4. Feature families (all computed from the dump alone)

| Family | Features | Rationale |
|---|---|---|
| **T — Timing** | mean / median / std / CoV / IQR of inter-command gaps; lag-1 autocorrelation; fraction of gaps < 1 s; entropy of log-quantized gaps; KS distance from log-normal | Human think-time is heavy-tailed and bimodal; model latency clusters near generation time |
| **C — Content** | command length stats; flag density; pipe / `&&` / `;` rate; long one-liner rate; near-duplicate retry rate; `2>/dev/null` rate; token-type entropy; vocabulary richness | Models emit complete textbook-form commands; humans abbreviate and retry |
| **S — Sequence** | command-verb bigram entropy; recon→enumeration→action phase ordering score; repeat-after-error rate; fraction of commands that reference prior output tokens | Models follow a very regular phase structure and quote output verbatim |
| **E — Error handling** | rate of error-producing commands; mean commands until recovery; fraction of errors followed by an immediate alternative | Distinct recovery styles |

Timing-free ablation (RQ4) = families C + S + E only.

---

## 5. Models

1. **Logistic regression** on standardized features (interpretable baseline; coefficients reported)
2. **Gradient-boosted trees** (HistGradientBoosting; primary)
3. **Sequence baseline:** TF-IDF over command-verb n-grams → LR (checks whether hand features add anything)

No deep models in v1 — sample size (~16k positives, ~600 negatives) does not justify them, and interpretability matters for the praxis.

**Class imbalance:** downsample positives to match negatives per (prompt, environment) cell; report results on the balanced set and on full positives with class weights.

---

## 6. The gate (the praxis contribution)

Split conformal prediction, Mondrian (class-conditional):

1. Train classifier on train split.
2. On a disjoint **calibration** split, compute nonconformity score `s = 1 − p̂(y_true)`.
3. For risk level α, set threshold `q = ⌈(n+1)(1−α)⌉ / n` quantile of calibration scores (per class).
4. On test, the prediction set is `{y : 1 − p̂(y) ≤ q_y}`. **Emit a label only if the set is a singleton; otherwise ABSTAIN.**
5. Report **coverage** (fraction decided) and **empirical error among decided** with a Clopper–Pearson 95% upper bound.

Guarantee: P(true label ∉ set) ≤ α, marginally, under exchangeability. The deterministic part is step 4: the threshold is fixed before test data is seen and never adapted online. Exchangeability is *violated* under LOLO/LOEO by design — reporting how far the guarantee degrades under that shift is itself a result.

---

## 7. Evaluation protocol

| Split | Purpose |
|---|---|
| Stratified 5-fold random | RQ1, RQ5 |
| LOLO: hold out each LLM family in turn | RQ2 (primary) |
| LOEO: hold out each of 5 environments | RQ3 |
| Feature-family ablation (T only / C+S+E / all) | RQ4 |

Metrics: AUROC, AUPRC, balanced accuracy, F1 at τ = 0.5, and for the gate: coverage, decided-error, upper bound. All with 1,000-resample bootstrap 95% CIs. Seeds fixed: `[0, 1, 2, 3, 4]`.

Reported in the same paired style as PX-080–083: every headline number next to its ablation.

---

## 8. Threats to validity (pre-declared)

- **Confound: environment realism.** DTU agents ran against lab/honeypot shells; humans in source (a) run against the same shells, so this is controlled only for source (a).
- **Confound: task distribution.** Controlled only for source (a); (b)/(c) are reported as OOD.
- **Label noise in (b).** Addressed by excluding (b) from training.
- **Temporal leakage.** Sessions are independent; no cross-session temporal ordering is used. The TESSERACT-style audit from PX-080 is not required here, but we check that no model/prompt identifier leaks into features.
- **Model-family coverage.** Only families present in the DTU corpus are tested; LOLO measures within-corpus generalization, not generalization to future models. State this explicitly.
- **Timing fragility.** Timing features are a known weak signal; RQ4 exists to bound how much the result depends on them. The praxis claim will rest on the timing-free ablation.

---

## 9. Deliverables

- `aivh/` package: ingest, features, models, gate, evaluation
- `results/*.csv|json`: per-split metrics with CIs
- `results/figures/`: ROC per split, coverage-vs-α curves, feature importance
- Appendix A entry with commit hash (push to `paganpraxis` GitHub)

## 10. Timeline

| Week | Milestone |
|---|---|
| 1 | Download Zenodo; ingest; feature extraction; RQ1 on agents-vs-bots as a dry run |
| 1–2 | IRB filing; range reproduction of DTU environments |
| 3–5 | Human collection (source a) |
| 6 | Full RQ1–RQ5 runs; figures |
| 7 | Write-up; Appendix A |

---

## References

- Maddaloni, Safargalieva, Vasilomanolakis. *Honey for the Agent* dataset. Zenodo, 2026-06-23. https://doi.org/10.5281/zenodo.20818246
- Reworr & Volkov. *LLM Agent Honeypot*. arXiv 2410.13919, Oct 2024. https://arxiv.org/abs/2410.13919
- Beelzebub. *Catching AI Red Teamers in the Wild*. Feb 2026. https://beelzebub.ai/blog/catching-ai-red-teamers-in-the-wild/
- Anthropic. *Mapping AI-enabled cyber threats*. Sep 2026. https://www.anthropic.com/news/AI-enabled-cyber-threats-mitre-attack
- Vovk, Gammerman, Shafer. *Algorithmic Learning in a Random World*. Springer, 2005 (conformal prediction).
- Angelopoulos & Bates. *A Gentle Introduction to Conformal Prediction*. arXiv 2107.07511, 2021.
