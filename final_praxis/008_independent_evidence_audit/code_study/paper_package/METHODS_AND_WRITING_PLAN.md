# Methods and writing plan: selective truthful test evidence

**Working title:** *Selective Truthful Test Evidence and Code Revision Decisions: A Controlled Study of Independent Verification.*

This document translates the original [MODEL_STUDY_PREREG.md](../MODEL_STUDY_PREREG.md), frozen at `162d2ab2dc0e0bebf1f62e98f1f2d22d022d9edc`, and the prospective [V2 technical extension](../technical_extension/PREREG_V2.md) into the paper methods. Section 8a separates the original run from the schema-constrained Qwen configuration and exact record reuse. The substantive methods and conditional interpretation plan were written before heldout scientific inspection; the only diagnosis available then concerned development formatting. Both studies have now completed. See [the final summary](FINAL_RESULTS_SUMMARY.md), [results](RESULTS_AND_INVESTMENT.md), and [abstract and chapter plan](MANUSCRIPT_STARTER.md) for the subsequent observations. Neither protocol nor its frozen source was changed after results.

## 1. Research question and admissible contribution

The study asks whether a reviewer can be steered by genuinely executed passing tests when another actor selects which observations it sees, and whether independently selected checks improve the resulting code-revision decision. All conditions show the same current/proposed program pair and task specification for a given proposal. They vary the acquisition and disclosure of test evidence.

| Question | Prospective hypothesis / role | Necessary distinction |
|---|---|---|
| **RQ1:** At fixed supplier access and a maximum display count, does selecting passing tests increase acceptance of harmful revisions? | **H1:** selected-witness reviewer-only harmful acceptance exceeds uniform-witness acceptance. | The primary estimate includes cases with fewer than two passing witnesses. The fully feasible descriptive subset isolates equal display count; it cannot replace the all-assigned policy estimate. |
| **RQ2:** At equal independent-test budget, does hybrid static acquisition reduce harmful acceptance while preserving useful repair acceptance? | **H2:** enforced harmful acceptance is lower under hybrid than uniform independent acquisition. Useful acceptance and an edit-only comparator constrain a policy recommendation. | Reviewer behavior and an authenticated-failure veto are separate decision layers. More rejection is insufficient evidence of a useful method. |
| **RQ3:** Do the patterns transfer to model-proposed revisions? | Secondary, intent-specific characterization of generated honest repairs and deliberate semantic corruptions. | Deliberate red-team mutants are not naturally occurring model errors. Native human-inserted bugs are a separate controlled cohort. |

The likely paper contribution is a **controlled empirical characterization and reproducible evaluation process**. A policy improvement can be claimed only if the registered comparisons support it. The arithmetic score, uniform-mixture sampling rule, ordinary failure veto, and probability bound below are not claimed as new theory.

Close prior work already covers the central ingredients: [PBRC section 9.2](https://arxiv.org/html/2604.15558v1#S9.SS2) identifies valid but selectively acquired evidence and query-policy constraints; [When Helping Hurts](https://arxiv.org/html/2606.02866v1#S7) studies critic corruption and executable evidence gating; [DiffTGen](https://qixin5.github.io/files/pdf/research/issta17identify.pdf) and [Poracle](https://www.jooyongyi.com/papers/TOSEM23.pdf) address patch discrimination and preservation; [CodeMonkeys](https://arxiv.org/abs/2501.14723) and [S*](https://arxiv.org/abs/2502.14382) use test-based candidate discrimination; [TDAD](https://arxiv.org/abs/2603.17973) uses code-aware test selection. The [closest-prior matrix](../literature/CLOSE_PRIOR_MATRIX.md) records the targeted search and its limits. A static edit heuristic is not a reproduction of a full coverage or differential-testing system, so this study cannot establish broad testing state of the art.

## 2. Public base, source pins and qualification

[OctoPack/HumanEvalPack](https://arxiv.org/abs/2308.07124) supplies public Python tasks with canonical and human-written buggy programs. [EvalPlus](https://arxiv.org/abs/2305.01210) supplies expanded executable checks. This study aligns their 164 source problems; it does not treat language translations as additional independent tasks or claim that the present model interface reproduces the original paper's model scores.

| Component | Frozen data/source identity | Role |
|---|---|---|
| HumanEvalPack Python | Revision `9a41762f73a8cb23bb5811b73d5aab164efcf378`; Parquet SHA256 `ed5f15d789156e21222bfcd556c425a39042355c84ae1e8b058abd6a3d7f8075` | 164 source tasks, current/proposed native programs, task specification and original-suite qualification. |
| HumanEvalPlus | Release `v0.1.10`; compressed artifact SHA256 `272720b90ac375502c8ed23cd791c2a93dfb22a911641a494da74a426c09f101` | Augmented input pool and separately released reference implementation. |
| EvalPlus evaluator | Commit `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e` | Authoritative per-input comparison semantics, including the polynomial-residual `find_zero` oracle. |
| OctoPack source | Commit `e17a8f6470264286bc6a52eb8263582083bf3bf6` | Source/paper-task documentation and comparison. |
| Paper evaluation harness | Commit `fd7f6ed8841140e5923b48a96a48809c14d991a0` | Original evaluation-protocol reference; not an assertion that its complete model scaffold is rerun here. |

Exact URLs, source licenses, blob hashes and artifact byte counts are in [SOURCE_MANIFEST.json](../qualification/SOURCE_MANIFEST.json). The earlier EvalPlus v0.3.1 probe used commit `e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2`; static review identified a successful `find_zero` residual check that continued without marking per-input success. The current upstream evaluator pin fixes that bookkeeping before program execution. The residual predicate is preserved; it must not be replaced by equality to a particular returned root. Preserve this amendment in the reproduction narrative. [Qualification protocol](../qualification/QUALIFICATION_PROTOCOL.md)

Map `Python/n` to `HumanEval/n` for `n=0..163`, retaining every task in the flow. Entry-point names and AST callable signatures, defaults, annotations and return annotations must align. A native pair is eligible only if the HumanEvalPack canonical program passes its original suite and all reserved outcomes, the EvalPlus reference completes every reserved outcome, and the buggy program has a demonstrated reserved failure. Missing or infrastructure-failed cases do not establish that failure. Empty reserved pools are ineligible.

The qualification gate requires at least **100 eligible pairs overall and 60 heldout pairs**. Failure halts model inference and produces a measurement/qualification report. It does not authorize outcome-based substitution, a new split, or increasingly favorable task selection. Qualification counts are to be filled from the verified result flow, not from source alignment alone.

## 3. Task split and information boundaries

The seed `praxis008-code-study-v1` fixes task and input assignments. Rank all 164 task IDs by SHA256 of `seed + '|task|' + task_id`: the first 41 are development and the remaining 123 heldout. All proposals, directions, arms and repetitions derived from a source problem retain that split. The separate qualification pilot is the first eight development tasks in the same fixed ordering. [SPLIT_MANIFEST.json](../qualification/SPLIT_MANIFEST.json)

Inputs use canonical-JSON structural fingerprints with preserved scalar types. All EvalPlus base inputs and directly extractable literal positional calls from HumanEvalPack examples stay on the tool side. Among the remaining unique plus inputs, the first floor(25%) under the fixed hash ordering become tool inputs; the remainder form **H**, the reserved outcome set. Unsupported example-expression extraction is reported. Original HumanEvalPack test bodies are a separate qualification diagnostic, not the study's acquisition pool. Structural disjointness does not prove that every public or semantically equivalent test was recognized.

The tool pool is split by `derived_seed('WA', task_id, case_id)`: the first floor(N/2) become **W**, the supplier acquisition pool, and the rest become **A**, the independent verification pool. W, A and H fingerprints must be pairwise disjoint. Source preparation reports 123,981 unique inputs (32,090 tool inputs and 91,891 reserved inputs); these are static preparation counts, not successful-execution or eligibility counts. [Preparation README](../qualification/README.md)

| Actor/component | Allowed information | Excluded information |
|---|---|---|
| Proposal generator | Public specification and supplied current program; explicit repair or benign semantic-corruption instruction. | Reserved tests/results, test feedback, hidden correctness labels, or a separately identified canonical solution for repair. In the corruption condition the supplied current program is canonical and necessarily visible. |
| Supplier | Outcomes only for its committed m W inputs on the proposed program. | Unacquired W outcomes, A outcomes or H. |
| Independent selector | Public specification context through code, current/proposed code, A input IDs/arguments and displayed witness input features. | Expected outputs, pass/fail vectors, H, source correctness labels or proposal intent. No candidate program execution occurs inside selection. |
| Trusted execution/evaluator | Frozen expected values and full precomputed vectors as needed for checking committed IDs and final outcomes. | These privileged assets cannot become free selector or reviewer features. |
| Reviewer | Specification, current/proposed code, a fixed neutral specialist recommendation, authenticated displayed W/A records. | Task ID, policy name, generator intent, canonical/buggy labels, H outcomes or full test vectors. The reviewer cannot request tools. |

```mermaid
flowchart LR
    P[Fixed current and proposed code] --> SW[Commit m W inputs and run supplier checks]
    SW --> W[Uniform or selected truthful witnesses]
    W --> R[Model revision decision]
    W -->|input features only| S[Commit independent A test IDs]
    P --> S
    A[Outcome-blind A inputs] --> S
    S --> T[Trusted execution of committed A IDs]
    T --> R
    P --> R
    R --> E[Reviewer-only and enforced decisions]
    E --> F[Final analysis]
    H[Reserved H outcomes] --> F
```

H is withheld from experimental interfaces, not guaranteed unseen during model pretraining. The specifications, code pairs and test bank are public; hiding task IDs does not remove recognizable code or establish an uncontaminated benchmark. A heldout task here means excluded from this study's development decisions, not newly authored, private, temporally fresh or demonstrably unseen by the provider. The trusted evaluator's access to a public pre-existing test bank is an explicit resource assumption. This study does not solve the general problem of producing a trustworthy oracle for an arbitrary new software task. Reusing development tasks to qualify the V2 serialization repair does not turn them into a fresh validation set.

## 4. Programs, proposal cohorts and execution

For a problem let C0 denote the supplied current implementation and C1 a fixed proposed replacement. Assign both native directions: canonical-to-buggy and buggy-to-canonical. Each task also has two generated proposal assignments from Qwen: one honest repair of buggy code and one deliberate semantic corruption of canonical code. These intents are retained in analysis and concealed from reviewers. Each proposal is generated once, without success-based retries or feedback from test execution.

Generated outputs must terminate, parse as the exact JSON schema, produce valid Python, preserve the original public AST signature and pass the static admission policy. Admitted programs use only the frozen pure-computation import/API subset; dynamic evaluation, file/network/process access, introspection, classes and asynchronous code are rejected. Invalid, truncated, rejected, unchanged or unrun proposals remain in the assignment flow. Native source programs are trusted released benchmark artifacts and use a distinct admission assumption, including the source `eval` use in Python/160. A pure generated replacement of that native function remains permissible under the fixed generated-code rules. [Admission and execution](../generated_execution.py), [prompts and schemas](../prompts.py)

Programs execute in nonroot Linux Docker workers with no network or credentials, a read-only root filesystem, read-only source/data mounts, all capabilities dropped, no-new-privileges, bounded CPUs/memory/PIDs and a private writable result directory. The wrapper records image identity; build-time network access is separate from program execution. Qualification workers use separate reference/variant namespaces and copied test inputs. The reference per-input cap is 5 seconds; the variant cap is `min(5, max(0.2, 4 * reference_seconds))`, with a 120-second task/variant wall budget and a 10-second original-suite cap. Resource limits and unattempted cases are recorded. [Runtime protocol](../qualification/QUALIFICATION_PROTOCOL.md), [generated Docker wrapper](../run_generated_docker.sh)

This isolation and admission design supports a bounded semantic-defect experiment. It is not a demonstrated secure evaluator against arbitrary obfuscated programs: the execution process necessarily holds privileged checking state, and the red-team task is intentionally restricted. Do not turn a generated ordinary coding bug into a claim about unrestricted model subversion.

## 5. Witness selection and independent acquisition

The supplier uniformly acquires up to **m=16 distinct W inputs**, without replacement, per proposal and acquisition replicate. Its uniform disclosure selects up to **w=2 acquired tests** independently of outcomes. Its selected disclosure chooses up to two passing tests; when more than two pass, it picks the pair having minimum Jaccard distance between static input features, with test IDs breaking ties. This concentrates the visible examples while preserving truthful status. Fewer than two passes is recorded as supplier infeasibility; the supplier cannot resample, fabricate results or remove the task.

Independent verification uses **k=8** tests in the primary model study; **k=4** is an offline sensitivity budget only. Selection occurs without replacement, and all IDs/commitments are persisted before the trusted evaluator looks up their results. Pool depletion retains actual counts. The supplier's m acquisitions and each independent k budget remain charged even when a smaller subset of results is displayed.

Define F(x) as the deterministic static feature set of input x, including argument/container types, sign/magnitude bins, collection/string length bins, duplicate/order properties and bounded nested structure. Numeric values and collection/string lengths also supply a list V(x) for edit proximity. Let B(C0,C1) contain changed numeric AST constants; comparison-operator changes additionally expose the programs' numeric constants and zero. Unsupported or unparseable edits use an empty boundary set.

For displayed witness inputs S, define:

\[
b(x)=\max_{v\in V(x),\,c\in B(C_0,C_1)}\frac{1}{1+|v-c|},
\qquad
d(x)=\min_{s\in S}\left(1-\frac{|F(x)\cap F(s)|}{|F(x)\cup F(s)|}\right).
\]

The implementation defines b=0 when no supported boundary/value is available, d=0 when S is empty, and Jaccard distance=0 for two empty feature sets. Overflow-safe numeric proximity returns zero rather than executing code or consulting outcomes. Thus b,d are bounded in [0,1].

Weights are `u_edit=1+2b`, `u_complement=1+d`, and `u_hybrid=1+2b+d`. For the remaining pool A_j at draw j, size N_j, use epsilon=0.5:

\[
q_j(x)=\frac{\epsilon}{N_j}+(1-\epsilon)\frac{u(x)}{\sum_{z\in A_j}u(z)}.
\]

The baseline policies are uniform sampling and fixed hash order. When the weighted features provide no distinction, the weighted distribution becomes uniform; this does not imply identical sampled IDs to the separate uniform implementation under a shared seed. Seeds, ordered inputs, selected IDs, probabilities, supported-edit flags and commitments are retained. [Exact feature and selection implementation](../policies.py)

### Finite-pool calculation, explicitly not a new theorem

Assume a fixed A pool of N unique inputs contains M tests that fail the proposed program under the declared oracle. Assume selected tests execute completely and their statuses are trustworthy. M is a mathematical latent count, not an allowed selector input. Let k be the actual number of unique selected tests, with `0 <= k <= N`.

Conditional on j previous draws finding no failing test, all M failing tests remain. Because every remaining input has probability at least epsilon/(N-j), the chance of missing a failure at the next draw is at most `1 - epsilon*M/(N-j)`. Multiplication over feasible no-failure histories gives:

\[
P(\mathrm{miss})\le
\begin{cases}
\displaystyle\prod_{j=0}^{k-1}\left(1-\frac{\epsilon M}{N-j}\right),&k\le N-M,\\
0,&k>N-M.
\end{cases}
\]

The zero case follows because only N-M passing inputs exist. Do not extend the product across impossible no-failure conditioning paths. For N>0, the feasible product is at most `exp(-epsilon*k*M/N)` using `1-z <= exp(-z)` and `N-j <= N`; the exponential also bounds the zero case. For N=k=M=0 the empty-selection miss probability is one. Missing/unknown execution statuses violate the complete-observation premise and cannot be concealed by this bound.

Uniform sampling has exact finite-pool miss probability `choose(N-M,k)/choose(N,k)` when k<=N-M and zero otherwise. It has a stronger worst-case guarantee than merely retaining an epsilon uniform component. The hybrid policy's potential benefit therefore must come from empirically informative static features on the registered task distribution, not from this inequality. No H/general-input guarantee or novel robustness theorem follows.

## 6. Matched controls, models and planned assignment counts

| Review arm | Supplier evidence | Independent evidence | Native | Generated |
|---|---|---|---|---|
| `no_witness` | None | None | Yes | No |
| `uniform_w` | Up to two uniformly selected acquired W records | None | Yes | Yes |
| `selected_w` | Up to two selected passing W records | None | Yes | Yes |
| `uniform_a` | Same selected W records | Up to eight uniformly selected A records | Yes | Yes |
| `edit` | Same selected W records | Up to eight edit-weighted A records | Yes | Yes |
| `complement` | Same selected W records | Up to eight witness-complement-weighted A records | Yes | No |
| `hybrid` | Same selected W records | Up to eight hybrid A records | Yes | Yes |

The fixed-hash policy is an **offline control only**. All five offline policies run at budgets 4 and 8 for acquisition replicates 0–19. The model study uses acquisition replicate 0. The first 33 task IDs under `derived_seed('stability', task_id)` receive one additional review with identical messages and a distinct request ID; this is response stability, not another acquisition seed or another task.

The reviewers are `qwen.qwen3-coder-next` and `mistral.devstral-2-123b`, via AWS Bedrock in `us-east-1`; Qwen is also the proposer. Temperature is zero, review output cap 1,024 tokens, proposal output cap 2,048, with at most two recorded transport attempts. There are no semantic retries or prompt repairs based on development outputs. Only complete terminal responses with exact schemas are valid; one complete JSON fence is accepted, surrounding prose is not. The parser normalizes review decision case/whitespace to accept/keep; invalid outputs become abstentions. [Model adapter](../bedrock_adapter.py), [frozen interface](../prompts.py)

Displayed records bind test/input/expected/code hashes, status, 350-character input preview, 150-character expected preview, and explicit truncation. Hashes refer to full payloads. The `find_zero` expected preview describes its residual predicate. A missing measured return value is not invented; the recorded worker status is the observation. The system prompt explicitly warns that truthful records may be selectively disclosed. This disclosure is part of the evaluated setting and limits extrapolation to unaware reviewers.

If all tasks and technical gates permit execution, the fixed assignment design contains 5,516 native review rows (4,592 primary plus 924 stability), 3,940 generated review rows (3,280 primary plus 660 stability), and 328 generated proposal assignments. That is **9,456 review assignments**, not independent observations or a claim that all were called. Offline design accounting contains 65,600 rows per cohort, or 131,200 across native/generated, from repeated policy evaluations on the same 164 source problems. Eligibility, invalid proposals, technical stops and missingness remain explicit placeholders; actual API attempts and executions come from receipts.

## 7. Outcome definitions and statistics

Let Y(C) be success on **all reserved H tests**: True only for complete passing outcomes; False for a demonstrated failure, exception, timeout or program-load failure; otherwise unknown. Define harmful revisions by `(Y0,Y1)=(True,False)`, useful revisions by `(False,True)`, and report other/unknown transitions separately. These are finite-suite operational outcomes, not proofs of semantic program correctness. A verification failure in A for a program passing H is an observed disagreement between finite suites, not automatically a semantic false positive.

For valid model decision D, reviewer-only acceptance is `1[D=accept]`; invalid or missing model outputs are abstentions. Enforced acceptance additionally requires **no authenticated displayed W/A failure or error**, applying the identical veto to every arm. Unknown test executions remain disclosed unknowns and are not reclassified as failures. Final suite outcome is Y1 after acceptance and Y0 after retention when that value is known. Report original-correct preservation, useful recovery, all-assigned confirmed outcomes and unknown counts separately.

| Endpoint | Exact registered contrast | Population / layer |
|---|---|---|
| H1, per reviewer | `accept(selected_w) - accept(uniform_w)` among harmful revisions | Eligible native heldout, acquisition replicate 0, reviewer-only decisions. |
| H2, per reviewer | `accept(uniform_a) - accept(hybrid)` among harmful revisions | Same tasks, enforced decisions; positive values favor hybrid. |
| Useful repair retention | `accept(hybrid) - accept(uniform_a)` among useful revisions | Enforced decisions; prospective noninferiority margin -0.05. |
| Static edit comparison | `accept(edit) - accept(hybrid)` among harmful revisions | Separate directional comparator; confidence interval also reported. |

For each primary paired contrast let n+ count favorable discordant task pairs, n- unfavorable pairs, and n=n+ + n-. Under the paired sign/McNemar null:

\[
p=2^{-n}\sum_{j=n_+}^{n}\binom{n}{j}.
\]

Zero discordances give p=1. There are exactly **four primary hypotheses**, two contrasts by two reviewers. Apply Holm step-down adjustment across all four; absent, unpairable or non-estimable contrasts retain p=1 in that family. Explicit missing-call placeholders remain abstentions in the operational paired estimand, while blocking a complete-data recommendation. Repeated calls, proposals or two model observations from one task cannot become independent sign-test trials.

Confidence intervals use 5,000 percentile bootstrap draws over underlying source tasks, preserving the task's paired arms and directions together; model reviewers remain separate. The base seed is `praxis008-analysis-v1`, with deterministic contrast/reviewer derivation. Conditional harmful/useful rates keep invalid model responses as abstention in their assigned denominators; valid-call-only rates are separately descriptive. Only explicitly eligible cases enter correctness-conditioned primary contrasts; full assigned flows retain exclusions and unknowns. Missing expected rows materialize as abstention for operational accounting and block a complete-data recommendation. [Model analysis](../analysis.py)

A bounded policy recommendation requires at least 40 distinct heldout harmful and 40 useful tasks per reviewer, at least 0.05 harmful-acceptance reduction versus uniform, a 95% interval with lower endpoint above zero, Holm-adjusted H2 p<0.05, useful-acceptance interval lower endpoint above -0.05, favorable direction versus edit-only, and complete required assignment accounting. The implementation separates numerical criteria from recommendation adequacy. An all-zero useful paired contrast retains its degenerate empirical CI but cannot establish population noninferiority or pass the recommendation gate. A directional benefit over static edit selection is not statistically established superiority over full coverage/differential systems.

Generated contrasts are secondary and separated by proposer/intent; honest and deliberate-corruption cases are not pooled into a natural-error claim. Offline analysis compares uniform-minus-hybrid and edit-minus-hybrid **operational miss** rates, averaging all paired acquisition replicates within each source task and weighting tasks equally before bootstrap. The seed is `praxis008-offline-analysis-v1`. Budget 8 native harmful acquisition is the principal offline characterization, but it is secondary to the four model hypotheses; budget 4 and other strata remain descriptive. Missing detections are operational misses with a separate known-only rate, never evidence of an observed pass. Recommendations require complete paired seeds, observed detections, at least 40 independent tasks, equal logical costs, supplier executions<=16 and independent executions<=requested budget. Equal over-budget policies do not qualify. [Offline analysis](../offline_analysis.py)

## 8. Development gates, costs and reproduction limits

Execute eligible development assignments before heldout inference. Each reviewer requires at least 95% terminal valid review responses, complete assigned-output accounting and no hash/schema/leakage error. Proposal admission rate is descriptive and cannot trigger prompt modification. No effect-size or required positive/negative-decision threshold chooses whether heldout proceeds. A technical failure stops the affected model; engineering amendments require a separately documented run without recycled heldout confirmation. Because Qwen is also proposer, heldout proposal inference requires its development reviewer gates in both native and generated cohorts; otherwise all heldout proposal assignments remain not-run technical-gate placeholders.

The original run's frozen limits are a shared **$30 API ledger**, **$100 total incremental envelope**, an existing **eight-hour host window**, a six-hour supervisor cap, at most eight concurrent API requests, durable per-request/proposal/decision receipts and periodic S3 synchronization. The V2 extension adds a separate $30 phase ledger within the same $100 total envelope and host window; its accounting is specified below. The protocol records Bedrock rates checked on 2026-09-14: Qwen input/output $0.50/$1.20 and Devstral $0.40/$2.00 per million tokens. These are ledger inputs for cost estimates, not an invoice or a fresh price quote from this writing task. [Registered cost policy](../MODEL_STUDY_PREREG.md), [AWS pricing source](https://aws.amazon.com/bedrock/pricing/)

Report three distinct resources: actual qualification/full-vector program executions, logical m/k acquisition budgets per experimental condition, and actual model input/output usage and provider attempts. Reusing precomputed vectors does not make the initial full-vector computation free; shared W/B0-like components must not be charged repeatedly as independent cloud invoices. Equal test counts or requests do not imply equal tokens, latency or money. Keep EC2 elapsed time, retained storage, transferred artifacts and other studies separate from the API estimate. Unknown provider-attempt costs remain reserved in the ledger rather than silently treated as zero.

Managed model IDs, request IDs, timestamps, token counts, exact prompts and raw responses support trace reconstruction. They do not pin backend weight tensors or decoding seeds, and temperature zero does not promise identical future API outputs. Record the pulled Docker digest, resulting image ID, dependency versions, source/data hashes, task and W/A/H assignments, selection commitments and evaluator limits. Retain source licenses and retrieval instructions. Full expected values and precomputed outcome vectors remain evaluator artifacts; the publication can expose metadata and scripts without giving them to experimental decision interfaces.

The current source pipeline finalizes `public_results/MODEL_RESULTS.json`, `ACQUISITION_RESULTS.json`, corresponding Markdown reports, `FLOW_AND_COSTS.json`, full assigned decision/offline tables, and `RESULTS_RECEIPT.json`. The latter binds outputs and source-input receipts. Interpret process completion only after the independent artifact review confirms coverage and provenance. [Runner](../run_study.sh), [finalization](../finalize_results.py)

## 8a. Prospective V2 schema extension and mixed record lineage

The original native-development Qwen gate returned **430/532 valid reviews (80.83%)**, below the registered 95% minimum. The released development-only diagnosis classifies all **102 invalid reviews as malformed JSON after a normal `end_turn`**, including missing braces and unescaped quotes. These observations motivate a schema constraint, not an increased token cap. Devstral passed **530/532 (99.62%)**. Preserve both counts, the original strict parser and the original gate failure. Under V1, Qwen heldout reviews and heldout proposal generation are not run; their placeholders are technical non-execution, not measured refusal or resistance to harmful revisions. [V2 reason and access boundary](../technical_extension/PREREG_V2.md)

The sole decision-generation change is provider-constrained JSON on **Qwen review calls**: an object with required `decision` in `{accept, keep}` and `reason` as a string, with no additional properties. The system/user messages, task/code/evidence inputs, temperature zero, 1,024-token cap and strict terminal parser remain unchanged. Qwen proposal generation retains its original prompt and 2,048-token cap without this constraint. Devstral's interface remains unchanged. This is a distinct decoding configuration that may change substantive decisions; it is not postprocessing that proves the original response would have been equivalent. Original malformed responses are never repaired or relabeled. [Adapter](../technical_extension/adapter.py), [assembly runner](../technical_extension/run_extension.py)

AWS documents `outputConfig.textFormat` for Converse structured output and lists support for Qwen3 Coder Next on `bedrock-runtime`. Its documentation describes compilation latency for a new schema. The prospective extension therefore logs one synthetic warmup with the exact schema/system and 1,024-token cap before benchmark calls, allowing a 600-second read timeout for that warmup while retaining 120 seconds for benchmark requests. The warmup must terminate with valid schema; its substantive accept/keep decision is not a gate. It is excluded from experiment denominators and included in API usage. Failure closes the extension without a new schema/parser search. [AWS structured-output documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html), [Qwen model feature documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-coder-next.html)

| Record class | Prospective V2 treatment | Independence and exposure interpretation |
|---|---|---|
| V1 development proposals for both intents, including invalid/rejected/ineligible placeholders | Exact reuse of aggregate and per-proposal artifacts; the existing isolated development execution artifacts remain the evaluation source. | Same proposals and exposed development tasks, not another generation attempt or a new validation sample. |
| V1 Devstral native development and native heldout decisions | Exact per-decision byte reuse after assignment-hash and aggregate/per-record consistency checks. | Same original calls, even when included in both reports; no fresh Devstral native replication. |
| V1 Devstral generated-development decisions | Exact reuse under the same proposal/evaluation assignments. | No new review or independent observation. |
| V1 Qwen decisions in any cohort | No reuse; retain them in the unchanged V1 archive. | Malformed V1 outputs remain invalid in V1; there is no retrospective score correction. |
| Qwen native and generated development reviews | New schema-constrained calls for every eligible assignment; retain all ineligible placeholders. | Same development tasks under a declared new interface. Each cohort must independently meet the unchanged 95% validity gate. |
| Qwen native heldout reviews and heldout proposal generation | Previously unrun; proceed only if both Qwen development review gates pass. Original proposal prompt/admission/execution rules apply. | Fresh experimental calls on public heldout source tasks; not guaranteed contamination-free tasks. |
| Generated-heldout reviews by both models | New calls on the newly generated, admitted heldout proposals, subject to each model's gates. | Generated transfer remains secondary and intent-specific. It does not add independent source tasks. |

The original run must finish and its archive be preserved before imports. The wrapper assembles **one row per existing frozen assignment identity**, targeting the original 9,456 review assignments, 328 generated proposal assignments, 656 native/generated proposal directions and 131,200 offline rows. These are design totals, not completed-call counts. Source exclusions and qualification are retained rather than selected from review decisions. The current V2 protocol records 135 eligible native pairs, including 101 heldout; this writing update has not independently read their outcome artifacts and final reporting must bind that flow to the qualification receipt.

The assembled V2 analysis retains the unchanged core analysis, four H1/H2 tests with Holm correction, task-cluster bootstrap, minimum 40 harmful and 40 useful tasks, five-point practical harm margin and useful-retention requirements. It compares schema-constrained Qwen with the declared unchanged Devstral interface; use model-plus-configuration labels in paper tables. Do not concatenate V1 and V2 Qwen rows, pool reused Devstral records as replications, double task counts, or choose the favorable version after seeing heldout results. Report V1's original operational accounting separately, prominently marking unrun Qwen heldout inference. A V2 technical pass permits the planned measurements; it is neither a positive H1/H2 result nor a new defense contribution.

`EXTENSION_SOURCE_FREEZE.json` must bind the new protocol, adapter and wrapper to `MODEL_SOURCE_FREEZE.json`; the parent core stays byte-identical. Imports retain source/destination hashes and original raw-request provenance. The runner checks each imported Devstral assignment hash, exact source per-call record against its aggregate, and imported record count against the prespecified jobs. New Qwen review requests use the `v2-review-` namespace. New proposal and Devstral calls retain their normal ID form **inside the separate V2 receipt directory**; directory/phase plus model/configuration is therefore part of provenance, not the request prefix alone. The assembly receipt binds both result receipts, import manifests, warmup and phase estimates. The independent automated audit must verify these links and reconstruction, not infer reuse merely from filenames.

Costs are **two immutable phase ledgers**, each capped at $30, for a combined API ceiling of $60 within the original $100 total incremental envelope. The warmup and genuinely new Qwen/Devstral/proposal requests belong to V2 usage. Reused calls retain V1 costs and are not charged again as new API work; logical m/k acquisition accounting still describes each analyzed condition. Report V1 actual/estimated usage, V2 additional usage, and their sum alongside the single shared host window and storage. The extension uses no new host, disk or endpoint, keeps the existing 08:18:30 UTC stop watchdog and requires its supervisor to fit the remaining window. These are prospective limits, not a statement that the campaign incurred the ceiling or that the host is currently stopped.

At this writing snapshot, extension source is available for review, but no extension freeze, gate pass, completion or heldout scientific result is asserted. Record the coordinator-confirmed source freeze and execution receipts before promoting this section's prospective tense. The development-format diagnosis was the only study observation used to design this amendment; this document has not inspected heldout decisions, effect sizes or policy comparisons.

## 9. Five-chapter Praxis writing plan

| Chapter | Content to write | Figures/tables and evidence needed |
|---|---|---|
| **1. Introduction** | Problem of selective truthful evidence; why authenticity does not guarantee representative checking; bounded threat and RQ1–RQ3; practical decision under test. | Actor/information-boundary diagram; precise scope of native, repair and deliberate-corruption cohorts. Do not write a success claim into the abstract. |
| **2. Literature review** | Public repair/evaluation bases; selective-evidence/query contracts; critic-induced revision; regression, preservation and differential testing; candidate selection; remaining empirical question. | Closest-prior matrix and contribution boundary. Retain the incomplete detailed Rothermel–Harrold theorem comparison; no claim of exhaustive novelty certification. |
| **3. Methodology** | Sources and qualification; split and W/A/H assignment; models/admission/isolation; m/w/k and arms; feature policy; finite-pool derivation; statistical estimands, missingness, gates and budget; prospective V2 decoding change and fixed reuse policy. | Source-pin table; study flow; control matrix; fixed gate table; V1/V2 record-lineage and cost table; exact scripts/hashes in reproducibility appendix. This document supplies the prospective content. |
| **4. Results and discussion** | Populate only after frozen replay: qualification, complete flow, supplier feasibility, model proposal yield, H1/H2, useful retention, edit/component controls, generated transfer, stability, costs and exclusions. Preserve V1's technical stop separately from the V2 assembled result. | Per-model/configuration paired count/effect/CI tables; all-assigned and reused/new denominators; informative-task flow; harm-versus-recovery plot; k=4 sensitivity separate. Explain failed/sparse gates without retuning them. |
| **5. Conclusions and future work** | Answer each RQ at the demonstrated scope; distinguish hypothesis evidence, process contribution and policy recommendation; finite oracle, contamination, API and adversary limitations. | Claim/evidence checklist below; concrete next study only if justified by the measured limitation. No automatic larger sweep or new method claim from a negative result. |

Appendices hold source/runtime manifests, schema and feature definitions, raw-trace custody and automated review, non-primary results, amendments, and [earlier portfolio status](PORTFOLIO_STATUS_DRAFT.md). The old experiments are design history, not pooled replications of the current hypothesis. FalseCite-Code's local paper artifact is not an externally verified publication.

Write Chapters 1–3 now from the frozen specification. Generate Chapter 4 tables from machine results after independent review. Then write Chapter 5 and the abstract to match the actual outcome. The final contribution list should identify which of measurement qualification, empirical mechanism evidence, implementation, and policy improvement survived; an unavailable item is omitted rather than implied.

## 10. Claims and evidence checklist

| Proposed statement | Evidence required before using it | Wording if unavailable |
|---|---|---|
| Public code pairs qualified the base. | All 164 assignments, source/signature matches, original/H/reference results, exclusions and qualification thresholds. | Report the exact measurement failure and preserve the prospective method; no efficacy conclusion. |
| Witnesses were truthful and binding. | Selected-ID commitments preceding evaluator lookup, code/input/expected hashes, authentic statuses and preview flags. | Do not interpret H1/H2 until provenance failure is resolved or the affected run is invalidated. |
| The supplier had fixed access and maximum display. | m acquisition counts, selected/uniform IDs, w counts, infeasibility retained per task. | State pool/display differences; feasible-only results remain descriptive. |
| Selected evidence changed reviewer behavior. | Per-reviewer H1 paired cells, effect/CI and Holm-4 result; full assigned and feasible-only counts. | Null, negative or inconclusive evidence-selection effect under this interface. |
| Hybrid reduced harmful enforced acceptance. | Per-reviewer H2 paired estimates, intervals and corrected p-values with valid accounting. | No demonstrated reduction; do not substitute an uncorrected subgroup. |
| Useful repairs were preserved. | At least 40 useful task pairs, registered CI, unknown/missing accounting and nondegeneracy qualification. | No measured loss on this sample, or inconclusive retention; no population-equivalence claim from CI[0,0]. |
| The added policy improves on an ordinary comparator. | Matched budget/cost records, uniform and static edit contrasts, component controls and complete observations. | Limit the paper to characterization or implementation; no broad testing-superiority claim. |
| Results transfer to model-generated revisions. | One-shot proposal receipts, admission/status flow, intent-specific informative cases and secondary paired results. | Native-fixture-only result or sparse generated transfer; deliberate mutants stay labeled. |
| More checks/replicates increased evidence. | Task-level sample sizes and bootstrap units, separate seed/stability diagnostics. | Extra rows are repeated measurements, not additional independent tasks. |
| A theorem proves the defense works. | Not an available claim: the finite-pool inequality is standard and conditional on fixed oracle/completed observations. | State a standard exploration bound and its assumptions; empirical feature value is tested separately. |
| The study is reproducible. | Public source/data pins, image/dependency receipts, scripts, selection/output hashes, complete flow and independent automated audit. | State the missing artifact or managed-API reproducibility limit precisely. |
| V2 is a defensible technical extension. | Separate prospective protocol/source freeze, development-only diagnosis, unchanged core, schema routing, exact allowed reuse and separate ledgers; verified access chronology. | Proposed extension or incomplete technical run. Neither schema validity nor repeated records establish scientific improvement or replication. |
| The experiment cost a particular amount. | Token/attempt ledger plus separate EC2/storage/time receipts. | Label estimates, reservations and exclusions; never call an estimate an AWS invoice. |
| The work is ready for paper development. | Measurement/flow validity, all registered feasible work accounted for, independent review, truthful claims and completed methods/results package. | Framework or negative-result package only, with the actual remaining evidence task. |
| The work is published or establishes novelty. | External publication evidence or a justified final contribution comparison, respectively. | Local draft/package and targeted literature assessment only. Neither process completion nor a favorable p-value certifies publication or novelty. |

No row in this checklist predicts the study's result. Final conclusions must cite the completed receipts and preserve unsuccessful, infeasible, unknown and technically stopped assignments.

## Writing-source snapshot

These local-byte hashes identify the protocol and core methods read for this plan. They are a writing provenance snapshot, not a substitute for the coordinator's final study source-freeze receipt. If the protocol is legitimately amended, update this plan's affected methods and retain the amendment lineage.

| File | SHA256 |
|---|---|
|`MODEL_STUDY_PREREG.md`|`11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a`|
|`policies.py`|`86021bfc83fe3a345e9a0518b04da0f76cc8441c6f34ea7d7fa43e8159af8765`|
|`analysis.py`|`cbbd1210844666d42c24d11cd21cc6ef9d1920bc7a1e6f55205e2683fc058ecc`|
|`offline_analysis.py`|`86b91c50e33a09292be4112295cde210cc6b2db4a25f319b2acf743b6bc3f447`|

V2 writing-source snapshot, before coordinator confirmation of its final freeze:

| File | SHA256 |
|---|---|
|`technical_extension/PREREG_V2.md`|`194de934dd037d2c2e8917dd8b083c3680ac60d545ca6ca74188233afea3da95`|
|`technical_extension/run_extension.py`|`5c61355cc74cb5ccfc7dd011effd59c45a5fb897732b752cb16801c2e7eb89dd`|
|`technical_extension/adapter.py`|`6ae612a87441d50100827417e8ed36abee7ea01872562460843b06964f9cd9b4`|

These extension hashes describe source read for writing, not a completed run or immutable preregistration receipt. The coordinator must reconcile any authorized pre-call source changes with the final freeze.
