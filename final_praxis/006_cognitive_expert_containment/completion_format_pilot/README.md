# Fixed MiCRo completion-format pilot

This 64-response train-split pilot tests one source-supported serialization change after a completed raw-format qualification failed its truncation gate. The [preregistration](PREREGISTRATION.md) fixes the research question, hypotheses, source/data identities, gates and two-hour/$15 execution bounds. [Completion diagnosis](COMPLETION_DIAGNOSIS.md) preserves the previous negative result and explains this single follow-up. [STATUS.md](STATUS.md) links the latest automatic review when available.

The model loader and environment are byte-identical to the working FP32 predecessor. Obtain the pinned source/tokenizer artifacts under their original access terms described in [SOURCE_CONTRACT.md](SOURCE_CONTRACT.md). The runtime cache fetches the pinned model weights; third-party weights and tokenizer files are not included in Git. Dataset rows and rendered prompt/token identities are committed, with the [GSM8K license](GSM8K_LICENSE.txt).

From an environment with the declared dependencies, reconstruct the cohort and exact prompt manifest without model inference:

```text
python reproduce_data.py --sources-dir /path/to/gsm8k-cache --tokenizer-dir /path/to/pinned/tokenizer
python run_study.py --out /path/to/preflight --artifacts /path/to/private-artifacts --preflight-only
python -m unittest discover -s . -p "test_*.py"
```

The reproduction command downloads only the pinned public source files if missing, verifies their hashes, rerenders all 64 inputs, and requires byte-identical data.json. It never overwrites the frozen study data or invokes a model. The runtime independently requires the cloud tokenizer to reproduce every saved token sequence before pilot inference.

The authorized AWS launcher requires the entire study to be committed, bundles exact files with hashes, installs the stop schedule, starts the stopped campaign GPU host, and verifies an S3 supervisor heartbeat. Use a new execution directory for each committed run; do not duplicate an existing bundle or take over an active host:

```text
python launch.py --artifacts /path/to/private-artifacts --execution-dir /path/to/new-execution --execute
python collect.py --run-id fp006-format-COMMIT10 --out /path/to/new-collection --wait --publish
```

The collector requires a stable terminal S3 snapshot and matching source hashes. It runs the independent audit locally before publishing its derived review on branch `Final-Praxis-006-Cognitive-Expert-Containment`. Interrupted and failed runs retain a negative or incomplete review. The cloud host stops independently of the local collector.

To recompute the review from collected raw cells without AWS or inference:

```text
python audit.py --run-dir /path/to/outputs --data data.json --protocol protocol.json --technical /path/to/outputs/technical.json --report-dir /path/to/recomputed-review
```

Only chat performance determines the prospective feasibility gate. Raw is diagnostic. A pass permits a separately preregistered held-out qualification; this process never launches another study automatically, and neither outcome establishes a novel containment method.
