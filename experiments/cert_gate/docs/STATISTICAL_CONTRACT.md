# Statistical contract for offline alert-suppression research

## What is controlled

The target is **R = P(suppress an incoming alert | that alert is a true attack)**. It is not the proportion of suppressed alerts that are attacks, and it does not measure attacks that never generated an alert. The primary settings are alpha = 0.01 and delta = 0.05. The intended statement is: over repeated independent calibration samples, at least 95% of resulting policies have population attack-alert suppression risk at most 1%, under the assumptions below. This is not a posterior probability that a particular certificate is correct.

Standard **Conformal Risk Control** gives an expected-risk guarantee averaged over calibration and future examples; its main theorem is not this high-probability guarantee. [Angelopoulos et al., ICLR 2024, sections 1.2 and 2](https://arxiv.org/html/2208.02814v4). **Risk-controlling prediction sets** explicitly target population risk with high probability. [Bates et al., 2021, Definition 1 and Theorem 1](https://arxiv.org/html/2101.02703v3). The implementation uses the existing **Neyman-Pearson order-statistic method**, adapted by protecting the attack class. It is not new certification mathematics. [Tong, Feng, and Li, 2018, Proposition 1](https://arxiv.org/pdf/1608.03109).

## Implemented rule

Before calibration, freeze the benignness scorer s, score direction, preprocessing, model/prompt/version, eligibility predicate e, target population, alpha and delta. Larger finite scores mean more benign. An alert is suppressed only if `e(x) and s(x) > t`.

Use **all n attack calibration units**, including ineligible ones. Set the effective score Z to s for eligible units and negative infinity otherwise. Write Z_(k) for the k-th ascending score, with one-based rank k. Compute:

```text
r = largest j in {0,...,n-1} such that BinomialCDF(j; n, alpha) <= delta
k = n - r
t = Z_(k)
```

If no such j exists, return explicit `KEEP_ALL_INSUFFICIENT_ATTACKS`: nothing is suppressed and its suppression risk is deterministically zero. Otherwise the certificate records

```text
P_calibration(R(t) > alpha) <= BinomialCDF(r; n, alpha) <= delta.
```

The rank depends only on n, alpha and delta. It does not search observed score values or select the best scorer. Strict `>` is essential: ties at the threshold are kept. An all-constant eligible score therefore suppresses nothing at that score.

At the primary settings:

| Attack calibration units | Allowed strict exceedances r | Ascending rank k |
|---:|---:|---:|
| 200 | No nontrivial certificate; keep all | — |
| 298 | No nontrivial certificate; keep all | — |
| 299 | 0 | 299 |
| 500 | 1 | 499 |
| 1,000 | 4 | 996 |
| 2,000 | 12 | 1,988 |

The zero-exceedance minimum is `ceil(log(delta)/log(1-alpha)) = 299`. With 200 attack units the best such order-statistic bound is `0.99^200 = 0.134`, not 0.05. These counts concern attack calibration units, not total labeled alerts or attack test examples. Even 299 units do not ensure useful suppression.

### Why the rule works, including ties

Condition on the independently fitted, frozen scorer and eligibility predicate. Let F be the attack-class CDF of Z and let q be its lower `(1-alpha)` quantile. Strict suppression gives `R(t)=1-F(t)`. If `R(Z_(k))>alpha`, then `Z_(k)<q`; therefore at least k calibration scores fall below q. Each has probability `F(q-)<=1-alpha` of doing so. Independence and the monotonicity of a binomial upper tail give

```text
P(R(Z_(k)) > alpha)
  <= P(Binomial(n,1-alpha) >= k)
   = P(Binomial(n,alpha) <= n-k).
```

If q is negative infinity, that failure event is empty. Thus the same argument covers atoms, ties and ineligible scores. The bound is exact for continuous effective scores. With ties it can be conservative. **All calibration examples being ineligible does not establish deterministic zero future risk**: a future eligible example may still be suppressed. The binomial guarantee remains conditional on the same sampling assumptions.

## Assumptions and selection restrictions

1. **Correct labels and a defined population.** Calibration examples are true attack alerts from the target incoming-alert population. Using actionability, an approximate attack time window, or noisy proxy labels instead changes what is controlled. A 50-case, 90%-agreement label review is an engineering gate; it does not establish label error below 1%.
2. **Independent and identically distributed attack units.** Replayed packets, many alerts from one incident and duplicated scenarios cannot be counted as independent evidence without justification. Group-separated splits prevent some leakage but do not create independent alerts. One-hour gaps do not prove independence or stationarity. Calibrating incident maxima would control a different incident-level endpoint, not automatically the alert-volume-weighted risk above.
3. **Separate fit, development/selection, risk calibration and locked evaluation roles.** Scorer training, fusion fitting, feature learning, predicate changes and prompt/model selection must finish without using risk-calibration outcomes. External fixed models can omit local fitting but still require independent calibration. Class-conditional sampling must not select attack examples by their score.
4. **One certificate is not a family-wide guarantee.** For M prespecified candidates, one sufficient option is delta/M per candidate; a union bound then permits selection among them. At M=3, the zero-exceedance minimum becomes 408. Alternatively select one candidate using independent development data before fresh calibration. Do not pick the best of several 95% certificates and claim simultaneous 95% validity. Learn Then Test supplies a broader multiple-testing framework for such selection. [Angelopoulos et al., Theorem 1](https://arxiv.org/html/2110.01052v5).
5. **Same frozen decision rule and deployment distribution.** New model randomness, changed eligibility, time drift, another SOC or adversarially changed scores require additional assumptions or a new study. A predicate that uses incident context must use context actually available at decision time and account for shared-context dependence. This code does not verify these assumptions.

## What empirical checks can establish

For a policy with true risk exactly 0.01, a 200-attack test exceeds 1% whenever at least three alerts are suppressed. That happens with probability **32.3321%**, not 5%. The draft's proposed fraction of test sets exceeding alpha is therefore not a valid direct test of the theorem. Report independent test counts and suitable one-sided binomial uncertainty when IID assumptions are defensible; describe dependence limitations otherwise. An ordinary bootstrap with zero observed misses cannot establish a zero population risk.

Repeated splits of one fixed pool are a sensitivity analysis, not 100 independent experiments. The software qualification instead uses fresh independent synthetic Uniform(0,1) calibration samples; true risk is analytically `1-t`. The threshold follows a Beta(k,n+1-k) distribution, which independently checks the binomial formula. Exact enumeration on a discrete population checks ties and ineligibility. Further tests cover minimum sizes, strict comparisons, conservative subsets, JSON round trips, invalid inputs and certificate consistency.

Source-field agreement proves consistency, not harmlessness: attacker-controlled text can appear in both the alert and its genuine source log. The gate has no general prompt-injection guarantee. Clean-to-attacked miss-rate ratios are undefined when denominators are zero. A future adversarial study needs a frozen threat model and absolute error/utility endpoints; it must not reinterpret an arbitrary distribution shift as covered by this certificate. No positive suppression benefit or new-method novelty follows from the theorem.

## Code and reproducible qualification

Import `experiments.cert_gate.calibration`:

```python
certificate = calibrate(attack_scores, eligible, alpha=0.01, delta=0.05,
                        metadata={"scorer_sha256": "...", "predicate_sha256": "..."})
suppressed = apply_certificate(certificate, evaluation_scores, evaluation_eligible)
document = certificate.to_dict()  # safe for json.dumps(..., allow_nan=False)
restored = Certificate.from_dict(document)
```

`tolerance_rank(n, alpha, delta)` returns the one-based rank or `None`. `gate_decision(certificate, score, eligible=True)` is the scalar application; `True` means suppress. Nonfinite scores, malformed masks and invalid parameters raise `ValueError`; a caller must retain alerts after any such validation failure. Missing eligibility defaults to all eligible, so a production wrapper must explicitly provide its checked predicate outputs. Inputs are not mutated.

Thresholds use `{kind: finite|negative_infinity|positive_infinity, value: number|null}` in JSON; no NaN or numeric infinity is serialized. Negative infinity is an internal representation of ineligibility, never an accepted scorer output. The frozen certificate stores a detached JSON copy of metadata. Schema/rank/count checks detect internal inconsistencies; they do not authenticate data, labels or provenance. In particular, loading a certificate cannot establish that its finite threshold equals the actual calibration order statistic without the original inputs. The experiment harness must separately bind the calibration inputs, scorer and predicate hashes and verify the threshold against those inputs.

Run from the repository root:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m unittest discover -s experiments/cert_gate/tests -p test_calibration.py -v
```

This module has an import API, not a standalone data-processing CLI. No real-data scorer fitting, scoring, calibration or live suppression was performed to qualify it.
