# Option 006: qualify a useful logic expert

This study determines whether the pinned MiCRo-Llama-1B logic expert offers enough reproducible GSM8K capability to justify developing a new corruption-containment method. It compares intact, logic ablation and social ablation on256 previously unused public test questions. Sixteen disjoint training questions validate the pipeline. No new defense or publishable contribution is claimed by this qualification.

Read [PREREGISTRATION.md](PREREGISTRATION.md) for the question, hypotheses, fixed methods and decision rule; [LITERATURE.md](LITERATURE.md) for primary sources; [SOURCE_CONTRACT.md](SOURCE_CONTRACT.md) for exact artifact pins and architecture checks. [protocol.json](protocol.json) and [data.json](data.json) are frozen before processing. The study remains on `Final-Praxis-006-Cognitive-Expert-Containment`.

## Reproduce and launch

Use the committed data cohort directly; `prepare_data.py` documents how it was selected from original GSM8K sources after earlier campaign exposures. The data retains GSM8K's MIT license in GSM8K_LICENSE.txt. `data_receipt.json` records source SHA256s and exclusions.

The following preparation uses no model inference. The official gated tokenizer requires normal authorized Hugging Face access. Keep tokenizer/code bundles in private artifact storage; credentials are never bundled.

```text
python prepare_artifacts.py --out /private/path/logic-artifacts
python run_study.py --artifacts /private/path/logic-artifacts --out /private/path/preflight --preflight-only
python -m unittest discover -s . -p "test_*.py" -v
```

`launch.py` packages only the committed study, shared supervisor and verified private artifacts. In the existing campaign environment with the authorized `praxis-build` AWS profile, run:

```text
python launch.py --artifacts /private/path/logic-artifacts --execution-dir /private/path/new-execution --execute
```

The launcher installs an8-hour AWS stop watchdog before starting the existing stopped g5.xlarge host. A detached systemd job builds an isolated environment, validates exact checkpoints and numerical behavior, runs816 fixed generations, and audits the results. It saves atomic cells and synchronizes to `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/<run-id>/`. Early completion/failure schedules host shutdown; the independent watchdog remains a backstop. An active host is never taken over. `--execute` omitted only builds the package and does not start AWS.

The launcher prints and saves the run ID, Git commit, S3 key, bundle/protocol hashes and SSM command ID. Inspect an existing run before retrying a launch; packages and remote run directories cannot be silently reused. Execution receipts belong outside tracked source. The bound is$75 total, with g5 compute at most approximately$8.05 for8 hours at the campaign's verified price.

## Automatic review

`audit.py` reads saved cells and independently reconstructs strict/flexible exact answers, validates identities and completion, and calculates paired confidence intervals. It writes `outputs/audit/audit.json` and `outputs/audit/RESULTS.md`, including on a failed setup/inference attempt where possible. No manual review or external judge call is required.

```text
python audit.py --run-dir /downloaded/outputs --data data.json --protocol protocol.json --technical /downloaded/outputs/technical.json --report-dir /downloaded/independent-audit
```

`collect.py --run-id <run-id> --out <private-folder> --wait --publish` monitors the private S3 lifecycle, downloads terminal evidence, verifies its frozen audit inputs, recomputes the audit locally, and commits only derived completion reports and STATUS.md to this numbered branch. It retries connectivity without launching compute or changing an experiment. Raw outputs stay in private artifact storage. Publication refuses unrelated staged edits; an unavailable Git connection leaves results committed locally for a later push. The collector needs the local machine and AWS session, while cloud inference, its first audit, S3 persistence and shutdown run independently.

A complete technical/scientific pass advances only the useful-specialist prerequisite. The next separate study must introduce and test a literature-defensible containment modification against permanent ablation, random routing and ordinary verification across held-out fault families. Incomplete or failed runs cannot pass, and the automated process does not start a different paid scientific experiment on failure.
