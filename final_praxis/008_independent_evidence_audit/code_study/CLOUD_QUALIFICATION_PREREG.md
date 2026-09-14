# Prospective code-benchmark qualification and bounded cloud execution

Recorded before starting the AWS host or executing benchmark programs. This phase is a measurement prerequisite, not evidence that a novel defense works. The later model experiment requires its own committed protocol after this base qualifies.

## Literature basis and question

OctoPack introduces HumanEvalPack and code repair tasks with released evaluation artifacts and code variants (https://arxiv.org/abs/2308.07124). EvalPlus demonstrates that expanded executable tests find faults missed by small original suites (https://arxiv.org/abs/2305.01210). These motivate checking whether paired variants and disjoint test sets can expose selectively reported passing evidence without relying on a model judge.

Audit RQ: Do aligned public canonical/buggy HumanEvalFix pairs yield reproducible incorrect revisions that pass some truthful tests while failing separately reserved outcome checks?

Audit hypothesis: Such cases exist in the pinned release, but all assigned tasks, source incompatibilities, timeouts, canonical failures, and both-pass/both-fail cases must be reported. The existence of one case alone does not qualify a model study or establish novelty. No policies or model conditions are chosen from held-out experimental outcomes.

Source pins identified before execution: HumanEvalPack `9a41762f73a8cb23bb5811b73d5aab164efcf378`; OctoPack `e17a8f6470264286bc6a52eb8263582083bf3bf6`; paper evaluation branch `fd7f6ed8841140e5923b48a96a48809c14d991a0`; EvalPlus `e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2` and HumanEvalPlus release v0.1.10. The qualification manifest will bind the actual data and runtime hashes. Identity alignment must be checked before merging releases.

Use all 164 Python task IDs. Keep every variant of a problem in one source-problem split. Freeze test-role and development/evaluation partitions independently of verification-policy results. Candidate checking inputs and the separately reserved final outcome suite must be disjoint; no canonical code, unused expected outputs, pass/fail vectors or reserved outcomes enter a future selector prompt. Public pretraining exposure remains a limitation.

The artifact protocol under qualification/ will specify canonical-pass/buggy-fail eligibility and all exclusions before execution. Original variants are immutable. Any scorer or compatibility amendment gets a separate version and receipt. Every executed program runs in a nonroot container without network or credentials, with read-only input and bounded processes, CPU, memory and wall time. Trusted orchestration handles source download and result upload outside that container. Per-case failures remain explicit.

## Authorized cloud envelope

Reuse stopped campaign host `i-07178e293e8df2a60` in account272615233626/us-east-1 and its retained encrypted scratch storage. Confirm stopped state, guest shutdown behavior=stop and an enabled external stop schedule before start. Leave the other host stopped. No new persistent endpoint or disk is needed.

Host wall-time limit: eight hours. Supervisor execution limit: six hours. Conservative total incremental envelope for qualification, subsequent separately registered pilot, containers and API requests: $100, with a separate model ledger capped at $30 before any inference. The prior verified g5.xlarge rate is $1.006/hour; an eight-hour host reservation is about $8.05 at that rate, not an invoice. Existing retained storage is separate. No job may exceed the user's $1,000 threshold without explicit user authorization. The default action is to stop early once work completes; external shutdown protects against intermittent connectivity.

The host may be used for setup and source qualification under this document. No model calls are authorized by this qualification protocol alone; the user has authorized continuing automatically once a substantive model-study RQ, hypothesis, literature boundary, matched controls, budget and decision rules are frozen. All such calls must use a ledger and durable request/response receipts. Infrastructure setup failures are technical failures, not scientific negatives.

## Completion and reporting

Publish code, dependency/source hashes, denominators, artifact compatibility, outcome diagnostics and automated review. Distinguish canonical/oracle-built pairs from a demonstrated model repair baseline. Preserve this phase and all earlier failed studies separately. The final paper-development package must state what was tested, what the evidence supports and any remaining publication limitations; it must not recast audit completion as a successful novel method.
