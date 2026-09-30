# PX-092 — Warning-Preserving OR-Gate: Generalization, Seed-Count and Adversity

**Status:** Frozen before execution. No numeric value in the Results section of this file may be written until FREEZE.json exists.
**Depends on:** PX-081 saved predictions and replay code; PX-086 seed-union implementation; AIT campaign-validation artifacts (36 classifiers, seeds 8101–8103, Wilson/Harrison held-out probabilities).
**Compute:** Local CPU only. No cloud, no API charges. Refitting is limited to Part B (roles expert, ≤ 10 seeds, PX-081 configuration).
**Evidence root:** `experiments/praxis_next/or_gate_20260930/`

---

## 0. One-paragraph rationale

Across PX-085–090, every intervention that adjusted a single model's probability (threshold calibration, recalibration, monotone constraints, probability averaging) left exfiltration warning recall at ≈67–68% or purchased recall with unusable workload. The two interventions that raised recall at small alert cost both added an independent view and retained any warning it produced (PX-090 retention gate: 88.41%; PX-086 seed-union of roles-model warnings: 98.78% at 196 alerts vs. 68.04% at 182 for averaging). PX-092 tests whether that mechanism — a deterministic OR-gate over independently fitted experts — generalizes beyond the single clean budget-2 setting in which it was observed.

## 1. Definitions (fixed)

- **Warning:** any non-benign predicted label. A row's warning under a single model *m* is `w_m(x) = 1[argmax_k p_m(x)_k ≠ benign]`.
- **OR-gate over a model set M:** `w_OR(x) = max_{m∈M} w_m(x)`. A row is called benign only if *every* model in M calls it benign.
- **Stage label under OR-gate** (for macro-F1 reporting only): among models that warn, take the non-benign class with the highest summed probability; ties → lowest class index. If none warn, benign. The stage label is secondary; the primary outcomes are warning-level.
- **Mean-gate (control):** `w_MEAN(x) = 1[argmax_k (1/|M|) Σ_m p_m(x)_k ≠ benign]`.
- **Warning recall for stage s:** `1 − C(s, benign)/N(s)`, on the declared test rows.
- **Benign false alerts:** count of true-benign test rows with `w = 1`; also reported as a rate.
- **Overlap ratio:** `FA_OR / Σ_m FA_m`. Value 1 means benign false alerts never coincide across models (worst case); value 1/|M| means they coincide perfectly.
- **Recovered warnings:** true-attack rows with `w_OR = 1` and `w_ref = 0`, where ref is the named reference policy.

## 2. Hypotheses (stated before execution; all retained regardless of outcome)

**H1 (inequalities; must hold by construction — a violation is a bug):**
H1a `WR_OR(s) ≥ max_m WR_m(s)` for every stage *s*.
H1b `FA_OR ≤ Σ_m FA_m`.

**H2 (empirical, primary):** On the clean budget-2 UNRAVELED replay, the OR-gate over the three PX-081 roles experts (seeds 8101–8103) achieves exfiltration warning recall ≥ 95% with benign false alerts ≤ 2 × the mean single-seed count. (PX-086 observed 98.78% / 196; this restates it as a pre-registered target, not a new fit.)

**H3 (generalization, primary):** On the AIT held-out executions, the OR-gate over the three seeds of the *current+history* AIT classifier raises pooled exfiltration warning recall over the best single seed **and** the overlap ratio is < 0.75 (i.e., false alerts coincide substantially). Reported separately for Wilson and Harrison; the direction must hold in both to count as supported.

**H4 (seed count):** Exfiltration warning recall under the OR-gate is non-decreasing in |M| for |M| ∈ {1,2,3,5,7,10} and the marginal recall gain from 5→10 seeds is < 1 pp, while false alerts grow sub-linearly (overlap ratio decreases with |M|).

**H5 (adversity):** Under delayed/unavailable and wrong-host history conditions, the OR-gate over roles experts retains ≥ 90% of its clean-condition exfiltration warning recall.

**H6 (aggregator contrast):** Mean-gate over the same model set does not exceed the best single-seed warning recall by more than 2 pp in any setting where the OR-gate exceeds it by more than 10 pp.

Directional expectations are recorded above; results in either direction are reported. No threshold in this section may be revised after execution.

## 3. Parts

### Part A — Replay on existing UNRAVELED predictions (no fitting)

Inputs: PX-081 saved per-row probability vectors for the four subset experts (current, current+roles, current+history, all) for seeds 8101, 8102, 8103; clean, delayed_unavailable, wrong_host_history conditions; budgets 1, 2, 3.

Model sets evaluated:
- A1 `roles × {8101,8102,8103}` (the PX-086 set)
- A2 `current × {3 seeds}`
- A3 `history × {3 seeds}`
- A4 `all-evidence × {3 seeds}` (reference only; exceeds budget 2)
- A5 `{current, roles} × {3 seeds}` = 6 models (mixed-evidence OR)

Aggregators: OR-gate, mean-gate, best-single-seed (oracle upper bound for single models; label-informed, reported as a bound only).

Outputs per set × aggregator × condition × budget: macro-F1 (fixed 4-class), exact and warning recall for Other/Movement/Exfiltration, benign FA count and rate, overlap ratio, recovered-warning count vs. entropy policy and vs. error-focused policy, evidence cost.

### Part B — Seed-count curve (fitting required)

Refit the PX-081 roles expert with seeds 8104–8110 (seven new fits) using the frozen PX-081 configuration: 150 iterations, 15 leaves, lr 0.05, min_child_samples 10, L2 = 1, caps 12,000 benign / 4,000 per other class, same forward-fold procedure, same final fitting captures. Nothing else changes. Record LightGBM version and hashes in FREEZE.json.

Evaluate the OR-gate and mean-gate for nested seed sets of size 1, 2, 3, 5, 7, 10 in seed order (8101…8110). Report the curve for clean budget 2 (primary) and all other conditions/budgets (secondary). For |M| = 3, additionally report all 120 three-subsets of the ten seeds as a sensitivity distribution (min/median/max warning recall and FA) so the original 8101–8103 triple can be located within it.

### Part C — AIT held-out replication (no fitting)

Inputs: saved held-out probabilities for the AIT current and current+history classifiers, seeds 8101–8103, Wilson and Harrison.

Model sets: C1 `current+history × 3 seeds`; C2 `current × 3 seeds`; C3 both experts × 3 seeds = 6 models.
Aggregators: OR-gate, mean-gate.
Report per execution and pooled: three-class macro-F1, exfiltration exact and warning recall, missed-warning count, benign FA count/rate, overlap ratio. Compare against the always-history and entropy policies from Table 4-15/4-16.

Note: AIT uses three classes and history-only evidence; this is the adapted contract, not the four-class/two-group one. Label the section accordingly.

## 4. Pass / fail criteria (frozen)

| Hypothesis | Supported if | Not supported if |
|---|---|---|
| H1 | Both inequalities hold in every cell | Any violation → halt, fix implementation, rerun; report the bug |
| H2 | Exfil WR_OR ≥ 95% and FA_OR ≤ 2 × mean single-seed FA (clean, B2) | Either fails |
| H3 | Pooled and both per-execution WR_OR > best single seed, and overlap ratio < 0.75 on both | Either execution fails, or overlap ≥ 0.75 |
| H4 | Non-decreasing WR in |M|; gain 5→10 < 1 pp; overlap ratio decreasing | Any of the three fails |
| H5 | Delayed and wrong-host WR_OR ≥ 0.9 × clean WR_OR | Either condition fails |
| H6 | Mean-gate gain ≤ 2 pp wherever OR-gate gain > 10 pp | Any setting violates |

Partial support is reported as partial; hypotheses are not merged or reweighted after results.

## 5. Audit (independent script, count-based)

`audit_px092.py` must recompute from saved per-row predictions, without importing the replay module:
1. Every OR/mean decision from raw probability vectors (exact match to reported decision files).
2. H1a and H1b in every cell.
3. Row-identity and label-hash equality against PX-081 and AIT source manifests.
4. Seed-set membership for every reported curve point.
5. Evidence cost accounting per row (roles = 1, history = 2; budget enforced).
6. FREEZE.json hash of this protocol, replay code, refit code, and LightGBM version before first Part B fit.

Report the check count and any failure verbatim.

## 6. Outputs

```
or_gate_20260930/
  PROTOCOL.md          (this file, byte-identical)
  FREEZE.json          (written before Part B fitting)
  partA/RESULTS.csv, RESULTS.md
  partB/FIT_LOG.json, RESULTS.csv, CURVE.csv, SUBSETS_3.csv, RESULTS.md
  partC/RESULTS.csv, RESULTS.md
  AUDIT.json
  FINDINGS.md          (interpretation; written last)
```

RESULTS.md files contain only tables and pass/fail per hypothesis. FINDINGS.md contains interpretation and must state, in its first paragraph, which hypotheses were supported, partially supported, or not supported.

## 7. Scope statements to carry into FINDINGS.md verbatim

- UNRAVELED remains one previously examined campaign; the test rows were exposed in PX-081 and PX-086. Part A and Part B are development results, not fresh validation.
- Exfiltration training rows (1,740) are identical across seeds; seed diversity arises from benign/other-stage sampling and tree randomness. Ensemble diversity is therefore not attack-coverage diversity.
- The OR-gate multiplies inference cost by |M| and does not reduce evidence-acquisition cost.
- Roles are eight coarse static-topology indicators from one campaign; transfer of the roles-expert result to other networks is not established.
- AIT uses the adapted three-class, history-only contract. A Part C result is execution-disjoint evidence for the OR-gate mechanism, not a replication of the four-class result.
- A warning is a non-benign model label; no analyst outcome is measured.

## 8. What this experiment does not do

No new architecture. No threshold tuning on test rows. No change to PX-081 or AIT frozen protocols. No pooling of UNRAVELED and AIT metrics. No claim of a universal effect size.