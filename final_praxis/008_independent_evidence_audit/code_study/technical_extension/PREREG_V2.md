# Version-two technical extension: Qwen schema-constrained review

Prospective amendment registered after development-format diagnosis and before
any extension call or researcher/agent inspection of heldout revision decisions,
effect sizes, statistical tests or model-policy comparisons. The original frozen
run at `162d2ab`, protocol `11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a`,
continues unmodified and remains a separate version-one result. Its automated
analysis may finish, but no heldout scientific summary will inform this amendment.

## Reason and smallest intervention

Original native-development Qwen reviews: 430/532 valid (80.83%), below the 95% gate.
All 102 failures had terminal `end_turn` and invalid JSON; missing braces and unescaped
quotes occur in the development-only diagnostic. There is no evidence supporting
a longer output-token cap. Devstral passed 530/532 (99.62%). The original stop rule
therefore withholds Qwen heldout reviews and heldout proposals.

AWS lists Qwen3 Coder Next support for schema-constrained output on bedrock-runtime:
https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-coder-next.html
and documents the Converse outputConfig.textFormat mechanism:
https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html .

The sole decision-generation change is a provider-enforced JSON schema on Qwen
review requests: exactly decision (accept/keep) and reason (string), both required,
no additional properties. System/user text, inputs, code, testimony, policies,
temperature 0, 1,024 review token cap and strict terminal/schema parser are unchanged.
Request IDs receive v2- prefixes and raw receipts have a separate directory.
No malformed version-one response is repaired or relabeled. Proposal generation
stays unchanged at 2,048 tokens without the new schema. Devstral's interface is unchanged.
The decoder constraint can affect behavior; this is an explicitly distinct Qwen
configuration, not an assertion that repaired-format responses equal original ones.

Before benchmark calls, make one separately logged, validator-authored synthetic
review request with the same schema/system and 1,024 token cap to compile/validate the
provider schema. Its transport read timeout is 600 seconds because AWS documents
first-use schema compilation latency; benchmark request timeout stays 120 seconds.
Require a terminal schema-valid response, not a particular substantive decision.
This warmup is excluded from experimental denominators and included in API costs.
If it fails, stop the extension as a technical failure; no schema or parser search.

## Retained research design and fresh access boundaries

All scientific RQ1/RQ2/secondary RQ3 and H1/H2, public source pins, 135 eligible pairs/101 heldout,
41/123 source-task split, W/A/H roles, supplier budgets, verification policies,
20 offline replicates, 33 stability tasks, 7/5 arms, useful-acceptance constraints,
missingness treatment and statistical rules remain as in MODEL_STUDY_PREREG.md.
No policy weight, task, success threshold, code proposal, prompt sentence or test
selection is chosen from heldout decisions. The two helper-only source exclusions
identified after the first freeze remain excluded; their compatibility limitation
is documented separately and does not change this cohort.

Version-two completion targets the same 9,456 assignment identities, 656 proposal
directions, 328 generated proposal assignments and 131,200 offline assignments.
Record reuse is fixed by model/cohort/split, never by correctness or accept/keep:

- Reuse all version-one development code proposals and their immutable isolated
  execution artifacts, including invalid/rejected/ineligible placeholders.
- Reuse all version-one Devstral native decisions (development and heldout) and all
  its generated-development decisions. Copy exact record bytes and source hashes,
  retain original raw-request provenance, and count these as reused calls, not new
  independent observations. No version-one Qwen decision is reused.
- Rerun every eligible Qwen native-development and generated-development review
  under the new schema; all ineligible assignments remain explicit placeholders.
- Require Qwen >=95% valid reviews on each development cohort before any version-two
  heldout Qwen review or heldout proposal generation. Existing Devstral gates still
  apply. If Qwen fails again, retain its new failure and do not search another prompt,
  token cap or parser on these outcomes within this protocol.
- If qualified, generate all previously unrun eligible heldout proposals once with
  the original proposer prompt/cap. Evaluate them in the unchanged isolated worker.
  Run both reviewers on generated-heldout proposals; these proposal outcomes and
  corresponding decisions were not generated in version one. Qwen native-heldout
  decisions are also previously unrun. Devstral native-heldout observations are
  reused observations, not a fresh replication.

## Analysis and interpretation

The completed version-two assembled dataset uses one observation per frozen identity:
Qwen schema reviews and the explicitly named Devstral records above. Run the unchanged
analysis with the original four-test Holm family (H1/H2 by reviewer), source-task
bootstrap, minimum 40 harmful/useful tasks, and 5 percentage point harm and usefulness gates. There is no
new family chosen from outcomes. Never pool the two configurations as independent
replications or increase sample size by counting version-one Qwen failures twice.
Keep original version-one analyses separately, labeling Qwen heldout inference as
not run rather than interpreting its abstention placeholders as measured safety.

Generated effects remain secondary; intentional corruptions are not natural errors.
A positive schema-format gate is not a scientific effect or a novel defense.
All constraints and nearest-prior boundaries in the original protocol still apply.
Report mixed interface lineage explicitly and do not claim an identical-interface
cross-model replication. Version-two changes were motivated only by development
serialization failures, before any heldout scientific-outcome inspection.

## Provenance, execution and costs

EXTENSION_SOURCE_FREEZE.json binds the new wrapper/runner/protocol and the original
MODEL_SOURCE_FREEZE.json. The parent core remains byte-identical to `162d2ab`. Copying
old records requires exact assignment hashes and an immutable reuse manifest with
source/destination hashes; new provider requests never use imported result files.
Raw lineage records distinguish original Devstral requests, reused proposals and new
v2-prefixed Qwen requests. Reference inputs/oracles remain outside model/selector APIs.

Wait for the original supervisor to finish and preserve its archive before importing
records. Use a separate $30 API ledger, leaving the original ledger immutable. Thus
the two phase ledgers have a combined maximum $60; the total authorized incremental
job envelope remains $100 including the original eight-hour host window. No new host,
disk or endpoint is required. Keep the external 08:18:30 UTC stop watchdog and a
supervisor timeout that fits that window; stop earlier on completion. Preserve durable
receipts/S3 snapshots and every gate/budget/invalid/missing assignment.

Independent automated review must verify the original and assembled datasets, exact
reuse, new-request/schema routing, cost accounting, selectors and final statistics.
Paper-development readiness and any positive novelty claim remain separate decisions.
