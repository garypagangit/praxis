# Validity plan: a controlled, outcome-verified stage mechanism test

**Design review, September 22, 2026. No executions or positive results are claimed by this document.**

## Decision: feasible, with a deliberately narrow claim

A small local or AWS-hosted lab can test whether observed telemetry and earlier context distinguish **a completed remote action, a completed dummy-file transfer, both, or neither**. It can verify those outcomes independently of the scenario that was requested. It cannot establish real APT detection, attacker intent, generalization to enterprise traffic, or algorithm novelty.

Three isolated processes using bounded HTTP RPC on loopback are sufficient for this mechanism test. They are not three independently administered enterprise machines, and an RPC computation is not evidence of unauthorized lateral movement. Label it a **remote-action analogue**, not a successful host compromise. If the implementation instead uses distinct containers or hosts, state that actual deployment topology without upgrading the security claim automatically.

This is worth executing to validate the pipeline, expose shortcuts, and obtain reproducible measurements. It is insufficient by itself to turn the previous developmental result into a positive, defensible APT praxis conclusion. The existing [novelty review](../host_auth_context/NOVELTY_REVIEW.md) already documents substantial overlap in role/context modeling. A clean experiment could support a later, externally validated contribution.

## 1. Separate behavior, outcome and authorization

Use two binary behavioral outcome labels per complete execution:

- **R:** a request from one process caused a different designated process to complete a fixed harmless computation, verified by the receiver's completion record. The operation is fixed in code, such as hashing a bounded dummy buffer; it accepts no shell command, executable path or arbitrary code.
- **T:** a designated receiver obtained the complete generated dummy object with matching byte count and SHA-256, verified independently at that receiver.

The four combinations are neither, R only, T only, and both. A scenario requesting both but completing only R has truth R only. A connection, authentication success, attempted upload, HTTP success code or orchestration command is not sufficient proof of completed transfer. Partial transfers and failed remote requests remain in the dataset with their actual outcomes.

Authorization is a separate label derived from a policy fixed before the execution. An authorized administrative action and a simulated unauthorized use of the same capability can have indistinguishable technical observations. Similarly, copying the same dummy object can represent an allowed backup or a policy-violating transfer. **A model without the relevant policy cannot reliably infer an invisible intent difference.** This is a required identifiability control, not an invitation to invent a behavioral cue.

If authorization is evaluated, provide the same action-independent policy context to every baseline and candidate, and include an explicit permission-lookup rule. Do not supply a precomputed `unauthorized` flag as a predictor or claim novelty for reproducing a rule that defines the label. A policy-defined violation in this lab is still an authorized test performed by the experimenter, not an actual intrusion.

## 2. Verification must be separate from model telemetry

Each worker should emit a bounded completion receipt containing the execution nonce, worker identity, monotonic completion time and operation-specific verification result. The transfer verifier reads the received file and independently computes its size and hash. The remote-action verifier checks the computation result against the nonce and fixed operation specification. Receipts use a separate control channel or artifact stream from the telemetry exported to models.

Keep these fields out of predictors: requested scenario, planned class, completion receipt, result hash, nonce, filename, command/path string, role-assignment schedule, worker identifier, run index and authorization label. Do not let the observation packet contain a conveniently renamed `remote_success` or `file_transfer_complete` label. Diagnostic logs and raw transport bodies remain private and excluded from features.

Receipt verification is automated, independently implemented arithmetic/provenance checking. It is not a blinded human audit. Collector and verifier bugs can still agree, so include negative controls: corrupt a received byte, truncate a transfer, deny a remote request, and stop a worker before completion. They must fail the corresponding outcome check while preserving usable observations where possible.

## 3. Prevent a script from becoming the label

The following are design goals for stronger confirmation. The concrete mechanism implementation is scoped in Sections 4 and 9: it randomizes endpoints, request order, short gaps and payload sizes, but does not generate realistic enterprise background traffic, multiple transport implementations or physically distinct organizational roles. Do not claim those broader controls were executed merely because they appear in this validity plan. The final model protocol determines which additional counterfactual and telemetry-availability tests are actually run.

The same source/target pair, port family, RPC endpoint and transport implementation must be capable of all four behavioral outcomes. Use a fixed endpoint such as `/rpc`, with operation details excluded from predictors. Match response-envelope size and omit string payloads. Vary dummy sizes across outcomes and give harmless administrative work comparable traffic volume. Do not make all transfers large, all remote actions tiny, or all positive operations use a unique port or process.

Cross both target outcomes with:

- source and destination role assignments;
- low and higher background activity;
- short and longer payloads, with overlapping sizes;
- valid and failed/partial attempts;
- short and longer gaps, with overlapping timing;
- authorized and simulated unauthorized policy twins;
- differing operation order when an execution includes both outcomes.

All hosts must generate benign administration and authorized transfers as well as the simulated policy-violation cases. Keep an activity on the same host pair under both policy conditions. Swap host-to-role assignments between held-out deployments; never use a known victim address as a role feature.

**History must not be a label encoded earlier.** Do not inject an authentication-failure burst before every positive, a special token before every transfer, or a deterministic stage sequence. Background authentication, connection failures and prior transfer attempts must occur in negative and positive cases. Legitimately informative history may come from earlier portions of the actual measured workflow, especially when a later supporting record is unavailable. It must still survive history-only and wrong-linkage controls and a held-out ordering test.

## 4. Agreed bounded collection roster

**The following concrete roster supersedes the initial 160-execution design suggestion before collection.** Collect 48 blocks, each with 48 current transactions: four prior-operation patterns × four requested current-operation patterns × three modes (success, authentication denied, operation failed). This yields **2,304 fresh current transactions**. Each has one separate, successfully completed prelude RPC, including a no-op prelude for pattern neither, for 4,608 measured peer RPCs overall.

Current attempts are fully crossed with prior patterns. Modes are service gates used to create actual denied or incomplete outcomes; they are private truth-side information, not predictors. HTTP status is a legitimate current observation. Completed outcomes still come from disk verification rather than the requested pattern or mode.

| Predeclared use | Blocks | Transactions used |
|---|---:|---:|
| Fit: linked prior/requested pattern only | 24 | 288 |
| Calibration: linked prior/requested pattern only | 8 | 96 |
| Linked-pattern held-out test | 16 | 192 |
| Crossed-history held-out stress: prior pattern differs from requested pattern | The same 16 held-out blocks | 576 |

The other crossed transactions in fitting/calibration blocks remain preserved but unused for model fitting, feature selection or calibration. All views of a transaction stay within its block. History includes only the corresponding episode's actually observed prelude. Workers may persist across blocks, but nonce-isolated artifacts prevent accidental job/file state reuse; this is not a cold-restart test.

**The linked subset deliberately creates workflow dependence by selecting `prior_mask == requested_mask`.** Prior successful activity plus the current success/failure status can strongly predict that subset's outcome. A gain there is a mechanism/shortcut demonstration, not evidence that real attack history determines the next action. The crossed-history test is essential paired evidence, not an optional unfavorable sensitivity to omit. Neither subset is a genuine enterprise distribution.

The controller randomizes transaction order, choice of distinct source/receiver workers, and 512/2,048-byte dummy payload size independently of the requested pattern. Request body lengths are identical across masks/modes within each payload bucket; response bodies are always 256 bytes. Timing is retained for provenance and availability diagnostics, not as a primary predictor. Worker roles are nominal metadata assigned by the separate frozen model protocol. A test-time role permutation is a counterfactual metadata stress, not a physical change to real server roles or proof of role-domain generalization.

Authorization twins are **counterfactual opposite-label views of the exact same recorded observation packet**, generated only as a held-out diagnostic. They are not separate physical runs and must not double the fitting sample, test execution count or statistical support. Without policy information, identical packets must produce identical predictions.

Requested combinations define collection balance, **not the actual outcome labels**. Publish verified completion counts and all denied/partial cases. The 48 blocks, their repeated script patterns and their fitting seeds are not independent APT campaigns. Calibration support should be stated from its verified outcomes, with no claim of a small population false-alarm guarantee.

## 5. Define when observations are available

Use one OS `perf_counter_ns` clock for this local multi-process lab, with each source-worker RPC interval checked inside its controller dispatch interval. Windows' coarser `monotonic_ns` clock was rejected in synthetic tests because distinct events could share a tick. Preserve worker event time and the controller's actual observation-arrival time. For multiple machines, measure uncertainty through explicit synchronization/control exchanges and preserve interval bounds. Do not select an offset to fit attack labels. This directly avoids the unqualified seven-hour Windows clock shifts encountered in the [authentication experiment](../host_auth_context/DESIGN.md).

The simplest endpoint is retrospective classification at a fixed execution cutoff after scheduled requests can finish. Ground truth includes only verified outcomes completed by that cutoff. Later receipts may confirm an earlier completion timestamp; later completion itself is not relabeled as an earlier outcome. Features include only telemetry actually available to the collector by the cutoff. Full-flow statistics are available only for completed flows.

Freeze an event-time/history rule separately. Historical records for a query must precede its declared cutoff; equal-time and future records are excluded. When testing delayed telemetry, **arrival time**, not just the original event timestamp, determines whether the record is available. Keep source time and arrival time so the auditor can verify the distinction.

This initial endpoint is not early warning. A later time-to-detection experiment would need separately specified action onset/completion times and an explicit cost of warnings issued before an outcome is knowable.

## 6. Minimal fair model and control comparison

Use fixed, small models; this dataset does not justify GPU training or a large search. Keep the fit examples, label budget, telemetry availability indicators, preprocessing and tuning budget identical within each comparison.

Primary contrast:

- **B:** current available traffic and host-observation summaries, including the same coverage and arrival-delay indicators given to the candidate.
- **C:** B plus legitimate coarse roles and strictly earlier host/network activity summaries.

Additional necessary controls:

1. **A simple observable-event rule** with the same permitted telemetry; the rule never reads completion receipts. A complex learner must not take credit for recognizing an operation that a direct rule already identifies.
2. **B plus roles**, and **B plus history**, to identify the useful component.
3. **Roles/history only**, as a shortcut diagnostic.
4. **Wrong-host history**, with matched roles, logging availability and decision time; preserve missingness and exclude future donors.
5. **Policy-free and policy-informed authorization twins**, reported separately from behavioral outcome discrimination. The direct policy baseline receives identical information.

Use two output scores for R and T. Do not force a single class when both actually occurred. Unlike UNRAVELED's single stage annotation, here both outcomes can be verified. If using four-class predictions instead, include the true both and neither classes rather than treat an ambiguous two-label answer as two correct detections.

Select each threshold using calibration data only under one fixed rule, such as calibration F1 with a documented tie rule. Freeze the rule before test collection or scoring. Report fixed-score results as well. Do not import the old 100-negative/20-positive role gate into this much smaller lab without acknowledging that it would make many groups unsupported. No 90% success floor or post-result preferred threshold is needed.

## 7. Missing and delayed evidence without a designed win

Collect a complete base trace first. Apply a frozen, label-blind telemetry schedule equally to every model. A bounded secondary comparison can include full telemetry, a fixed missing-event fraction, and a fixed positive arrival delay for one supporting sensor. Publish exactly which streams are affected and preserve the ground-truth receipt channel exclusively for evaluation.

These are paired views of the same execution, not new independent examples. Keep all degraded siblings in the same partition. Avoid a mask that always deletes the baseline's decisive signal while preserving an equivalent candidate-only truth bit; include the same sensor metadata and available current evidence in both B and C. Under complete direct evidence, both methods may hit a ceiling. That is a valid result, not a reason to tune the missingness schedule until C wins.

## 8. Primary measurements and required hard negatives

The primary descriptive endpoint is the change in **macro-F1 across the two verified behavioral outputs**, C minus B, on held-out execution blocks at thresholds fixed from calibration. Always report each output's precision, recall, F1, AP/prevalence and exact counts, plus exact two-output set accuracy. Separate familiar-role and held-out-role conditions. A pooled improvement that hides additional missed remote actions is not a stage-preservation success.

For every condition also publish:

- missed R, missed T, false R, false T and both/neither confusion;
- cases improved and worsened by C relative to B;
- false flags on authorized administration, authorized transfers, failed requests, partial transfers and high-volume background activity;
- unresolved/review outputs, automated correct decisions, wrong automatic decisions and unique review counts, if abstention is added;
- real verified completion rates versus planned scenarios, exclusions, missing receipts, and collection failures.

Three mandatory shortcut checks:

1. **Identical-observation authorization twins:** with policy hidden, a model must produce the same result for byte-identical observation packets that receive opposing authorization labels. A high intent score here indicates leakage. When policy is supplied, compare against the explicit policy rule.
2. **Held-out role/order:** reverse the role assignment and operation order in specified test cells without changing outcome definitions. A collapse exposes dependence on the scenario generator.
3. **Non-completion hard negatives:** a nearly full truncated copy and an authenticated but rejected remote request must not receive successful-outcome credit from the verifier. Models may still make false flags; those errors stay visible.

No confidence interval across model fitting seeds implies independence. Any optional uncertainty estimate must resample whole paired execution blocks and be labeled conditional on this small laboratory generator. Prefer exact counts and per-scenario differences for this first run.

## 9. Implemented collection and audit contract

The standard-library collector exposes `collect(output: Path, seed: int, blocks: int = 48, reps: int = 1)` and produces:

- `MANIFEST.json`: code hash, seed, crossed roster, bounded payloads and temporal/measurement assumptions;
- `WORKERS.json`: actual three worker processes and their private loopback ports;
- `FLOW.jsonl`: block/episode/phase, actual source and receiver worker, peer-request start/end, collector arrival, HTTP status and request/response body byte counts; excluded controller dispatch traffic is not a model flow;
- `TELEMETRY.jsonl`: actual service observations with event and collector-arrival times, host join key, generic event kind, success and byte count; planned outcomes, operation-mask integers, mode, secrets and receipt fields are absent;
- `TRUTH.jsonl`: requested and verified completed masks, prior mask, injected mode, private nonces and receiver receipt bindings;
- private `payloads/` and per-worker `receipts/`, `remote_results/` and `received/` evidence;
- `COLLECT_RECEIPT.json`: complete roster accounting, verified-outcome counts, elapsed time and artifact hashes;
- `COMPLETE.json` only after all planned transactions are accounted for, or `INCOMPLETE.json` on infrastructure interruption.

The source worker sends the actual peer RPC; the controller sends an excluded dispatch request to the source. All destinations are fixed loopback peers. A receiver permits only no-op, a fixed hash computation, and a bounded dummy file write. There is no arbitrary command or external network destination. Earlier telemetry is read and verified immediately after the prelude returns, before the current RPC starts. Delaying its collector arrival by a fixed 50 ms can therefore be evaluated honestly as an availability stress.

Remote verification computes SHA-256 over the ASCII bytes `FIXED_REMOTE_HASH_V1`, one NUL byte, the ASCII nonce, another NUL byte, and the original payload, in that order. Transfer verification compares the actual receiver file with the independent original bytes. Receipts bind the worker artifacts; incomplete files remain incomplete even if the scenario requested a transfer. A separate auditor must implement these checks without importing the collector's truth-classification function.

Keep telemetry input and allowed model features distinct. Current service event kinds could directly identify the fixed operations; a model using them needs a same-information deterministic-rule comparison and must not claim a difficult detection discovery. The parent model protocol, not this collector, determines which measured fields are permitted primary predictors and which are reserved diagnostics.

Preserve raw evidence privately; publish aggregate counts and sanitized receipts. A separate auditor verifies observed/truth separation, block-disjoint partitions, receipt failures, allowed feature names, arrival-time eligibility, model/protocol hashes and all saved-prediction metrics. It must not refit models or invent outcomes for failed collection.

Local processes can run the collector immediately when the required environment is available. The same bounded workload can run on an existing approved AWS CPU worker after the parent confirms access; GPU use is unnecessary for these small tabular comparisons. This review has not connected to AWS, provisioned a worker, acquired credits or executed the lab. Lack of AWS access does not prevent a local mechanism test, but it must not be reported as a cloud execution.

## What would justify a stronger praxis claim

A clean positive mechanism result establishes that the implementation can exploit specified observations under specified controlled conditions. A defensible cybersecurity claim additionally needs independently administered hosts, real authentication/remote-action/file-access telemetry, varied tools and personnel/workflows, independently verified outcomes, realistic benign activity, and held-out environments/executions not generated by the same scripted template. Literature positioning must identify a contribution beyond known context fusion and multi-output classification. This lab is a bridge to that evidence, not a substitute for it.
