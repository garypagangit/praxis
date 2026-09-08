# Reproduction and current build

The complete build contains a deterministic 400-case generated corpus, eight-round real-inference collector, four frozen policies, paired statistical analysis and a separately implemented verifier. The 80 artificial trace fixtures exercise eight trajectory families and cannot receive a scientific classification.

From repository root, using an environment with NumPy and SciPy:

```powershell
.\.venv\Scripts\python.exe final_praxis/003_adaptive_investigation_stopping/harness/validate_fixtures.py
.\.venv\Scripts\python.exe final_praxis/003_adaptive_investigation_stopping/harness/run_traces.py --preflight-only
```

The corpus and protocol are already frozen. Do not rerun their generators to overwrite the sealed inputs. A changed fixture-tested harness requires a dated amendment before any corresponding inference.

Actual discovery, after the shared pinned Qwen server is ready:

First use the same three commands below with run directory `artifacts/pilot/qwen_20260908` and add `--pilot` to `run_traces.py`. The two-case pilot must produce an independent PASS for 16 records and classification INFRASTRUCTURE_PILOT_ONLY before discovery. Its model correctness is not an infrastructure gate.

```powershell
.\.venv\Scripts\python.exe final_praxis/003_adaptive_investigation_stopping/harness/run_traces.py --base-url http://127.0.0.1:8765 --run-dir final_praxis/003_adaptive_investigation_stopping/artifacts/discovery/qwen_20260908
.\.venv\Scripts\python.exe final_praxis/003_adaptive_investigation_stopping/harness/evaluate_policies.py final_praxis/003_adaptive_investigation_stopping/artifacts/discovery/qwen_20260908
.\.venv\Scripts\python.exe final_praxis/003_adaptive_investigation_stopping/harness/independent_verify.py final_praxis/003_adaptive_investigation_stopping/artifacts/discovery/qwen_20260908
```

On Linux substitute the appropriate Python executable; paths and arguments are otherwise the same. Each of sixteen worker traces is sequential across rounds; the shared server may microbatch independent calls. No pilot outcome is used to tune the protocol. An unrelated adapter smoke test is infrastructure evidence only.

A transient infrastructure failure leaves append-only raw records. The same command with `--resume` reuses completed per-case prefixes under an identical frozen contract, with at most two infrastructure retries. Existing completed scientific runs and analysis files cannot be overwritten. Outcome-aware corpus, prompt or threshold changes require a new experiment rather than a retry.

The collector records every round even if a evaluated policy already stopped. The `policy_decisions` field reports the latest decision in that policy's prefix, so its embedded round may precede the collection round after an absorbing STOP. Policy cost is the counterfactual measured sum through its selected endpoint; the full scientific collection consumes all eight rounds. REVIEW continues investigation and unresolved terminal review counts as abstain, with no invented human correction.

The benchmark's eight families share an authorization-matching construct. Case-level bootstrap and binomial intervals are conditional on these generated cases and cannot be read as uncertainty over independent real incidents. See `PREREGISTRATION_v1.md` for exact denominator and claim boundaries.
