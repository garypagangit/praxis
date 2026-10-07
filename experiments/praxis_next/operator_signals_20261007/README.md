# Operator signals: choosing an existing-data Praxis

This is an exploratory study of command fingerprints, incomplete logs, recovery behavior, unknown models, early decisions, and human-versus-AI correction proxies. It uses saved public data. No new attack sessions, paid model inference, or human recruitment were used.

**Start with the [Praxis recommendation](DIRECTION_DECISION.md).** Full evidence: [findings](FINDINGS.txt), [HTML report](REPORT.html), [flat result table](evidence/RESULTS.csv), [measurement audit](evidence/MEASUREMENT_DIAGNOSTICS.json), [validation](evidence/VALIDATION.json). The HTML report is self-contained and can be downloaded and opened locally. [Sources and prior-work boundaries](SOURCES.md) explain which ideas already exist.

Family identification and human-versus-AI attribution are different tasks. A high score on the four-family Honey benchmark is not evidence that an unknown session is AI-operated, malicious, or part of an autonomous APT campaign.

## Experiments

| Study | Question | Evidence |
|---|---|---|
| S1 | Does family identification survive unseen environments, prompts, and combinations? | 17 predefined partitions; six representations, prior baseline, shuffled-label checks |
| S1A | Does recovery add information beyond command length/shape and simple edit/retry proxies? | 51 follow-up fits; explicitly specified after initial results |
| S2 | What happens when logs lose commands, arguments, or outputs? | Fixed-cohort stress tests, with and without retraining |
| S3 | Are timing and correction measurements suitable for operator attribution? | Clock/coverage audit and correction/recovery representations |
| S4 | Do unfamiliar families get incorrectly assigned a known identity? | Four held-out families; known-only threshold calibration |
| S5 | Can a stable identity be emitted early? | Prefix replay and an agreement-based stopping rule |
| B1 | Do correction features improve human-versus-AI flags on shared tasks? | Five expert-and-task holdouts using the prior Lyptus extraction |

The APT missing-telemetry proposal remains a separate fallback and was not executed as part of this shell-attribution study.

## Reproduce

Use Python 3.11 and the pinned dependencies in [requirements.txt](requirements.txt). Run commands from the repository root, with this folder substituted for `STUDY` below. Allow several GB of RAM and disk for the uncompressed ignored cache; fitting uses local CPU.

1. Obtain `Logs_final.zip` from [Honey dataset version 1](https://zenodo.org/records/20818246). Our archived copy matches the release MD5 `4f3b30538e6e4c492716f87f184dd816`; its SHA256 is `2b5410d5fa6d9aed5218bcaa925686af639b50f4922c13131f746d14798daeb4`.
2. Install requirements and extract deterministic records:

```text
python -m pip install -r STUDY/requirements.txt
python STUDY/prepare.py --archive /path/to/Logs_final.zip
```

The optional `--human /path/to/gambit/commands.json` reproduces the supplementary timestamp-availability audit using the archived GAMBiT export whose SHA256 is in `evidence/DATA_AUDIT.json`. It does not change fitted models. If omitted, the report identifies the missing supplementary audit.

3. Run the studies:

```text
python STUDY/experiment.py
python STUDY/binary.py --records experiments/praxis_next/aivh_lyptus_20261007/results/PX121_records.json
python STUDY/ablation.py
python STUDY/audit.py
python STUDY/solver_compare.py
python STUDY/report.py
```

Replace `STUDY` with `experiments/praxis_next/operator_signals_20261007`. `experiment.py` from scratch does not require a feature cache or checkpoint. The B1 records and their original extraction code/source manifest are in the inherited [PX120/PX121 directory](../aivh_lyptus_20261007/). Commands from source logs are treated as inert strings and never executed.

The initial run used checkpoint resumes, with six exact reconstruction fits. Its convergence warnings triggered a complete numerical recheck using the equivalent primal SVC solver. Final results come from that uninterrupted recheck; the original results are preserved under `initial_solver/`. [Solver correction](SOLVER_CORRECTION.txt) and [execution note](EXECUTION_NOTE.txt) document both phases. The unmodified initial runner remains available at Git commit `2f46972`. Protocols were committed before their respective fits: [main](PROTOCOL.txt), [binary](BINARY_PROTOCOL.txt), [post-initial-results ablation](ABLATION_PROTOCOL.txt).

For the optional standalone figure, install matplotlib in a plotting environment and run `python STUDY/plot.py`, then rerun `report.py` to embed it. Plotting dependencies do not participate in model fitting. `package.py` compresses predictions and produces the integrity manifest.

## Evidence and interpretation

* `RESULTS.json` and `PREDICTIONS.json.gz`: all primary aggregate scores and hashed-session predictions. Local runs write uncompressed JSON; the audit reads either form.
* `SPLITS.json` and `SESSION_INDEX.json`: session partitions and source-condition metadata, without raw Honey command/output text.
* `ABLATION_*`: separate post-initial-results mechanism checks.
* `BINARY_*`: calibration scores, held-out predictions, expert/task isolation, and raw denominators.
* `PAIRED_COMPARISONS.json`: conditional session-bootstrap intervals for the combined representation's accuracy change. These do not account for all collector/template dependence or establish population-level significance.
* `VALIDATION.json`: developer checks of saved arithmetic, split isolation, feature observability and provenance. This is not independent ground-truth or terminal-extraction certification.

Session selection, incomplete human reconstruction, model/collector dependencies, unverified clock semantics, and tiny human calibration sets constrain the conclusions. Negative results are preserved. None of these pilots validates a deployable binary AI flag or proves research originality.

Representation detail: the structural baseline uses first-token verbs, shell-word counts and adjacent first-token pairs, not a full shell AST. Its word tokenizer collapses punctuation in the operator tokens, so that channel measures aggregate operator occurrences rather than distinguishing each operator type. Correction features are lexical proxies, not verified keyboard mistakes.
