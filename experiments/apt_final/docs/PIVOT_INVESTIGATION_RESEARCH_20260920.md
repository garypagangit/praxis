# Research pivot: preventing false links in APT investigations

> Final access and decision update: the [consolidated shortlist](APT_PIVOT_SHORTLIST_20260920.md) supersedes provisional artifact status below. Full OCR acquisition failed; public OTRF APT29 day-one logs were acquired and qualified instead. Stable IDs and ordinary joins are mandatory baselines, not a new algorithm. The narrower evidence-selection idea remains conditional on a natural failure beyond those baselines. No new positive efficacy result is claimed.

Reviewed September 20, 2026. **Recommendation: one conditional investigation candidate merits a small artifact and mechanism pilot. No positive experiment or established novelty is claimed.** This memo does not change the failed MAGIC study or its results.

## Plain-language opportunity

An investigator can see two programs called `python` or two files called `update.exe` and accidentally combine their actions into one attack story. The same problem occurs when a summary hides a network port, a process identity, or the order of events. A useful system must preserve which actual object performed each action, and admit when several explanations still fit the evidence.

**Candidate title:** *Preserving System Identity and Uncertainty in Automated APT Investigations.*

**Question:** Can a compact evidence representation and an ambiguity-aware query layer reduce incorrectly joined attack steps while retaining as many correct answers as strong deterministic methods, at the same evidence and computation budget?

This is incident investigation after an alert. It is not a new attack detector, attacker-group attribution method, or recovery of telemetry that was never recorded.

## What current literature already does

| Primary source | Relevant overlap and consequence |
|---|---|
| [Jiang et al., ORTHRUS, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/jiang-baoxiang) | Reconstructs attack paths using dependency analysis and evaluates analyst investigation burden. Merely adding graph reconstruction or smaller analyst output is established. |
| [Aly et al., OCR-APT, CCS 2025](https://doi.org/10.1145/3719027.3765219) and [author source](https://github.com/CoDS-GCS/OCR-APT/tree/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3) | Combines anomalous subgraphs with LLM narratives; local-model comparisons already exist. Replacing its language model with Qwen is insufficient novelty. Actual code inspection exposes a narrower information-preservation question below. |
| [Mukherjee & Kantarcioglu, PROVSEEK, v2 November 2025](https://arxiv.org/abs/2508.21323) and [author full text](https://www.kunmukh.com/docs/provseek.pdf) | Already provides typed artifact lookup, follow-up queries, verification and inconclusive answers. Section 6.7 reports incorrect correlations and artifact-recognition failures; an example confuses the Metasploit command `elevate` with a system artifact. Its file/process lookup uses full paths and basenames, and IP lookup can fall back from IP:port to IP. Thus a generic verifier, NER layer, or follow-up agent is too broad a claim. |
| [Zhao et al., HunterAgent, May 2026 preprint](https://arxiv.org/html/2605.29269v1) | Already separates LLM hypotheses from a deterministic identity/temporal verifier, distinguishes grounded evidence from leads, and halts on insufficient evidence. Its Section III-B3 resolves multiple satisfying telemetry matches by minimum semantic distance. Maintaining unresolved alternatives rather than forcing that choice is a narrower possible distinction; it requires direct testing. No runnable author artifact was located in this bounded search. |
| [Kimm et al., Minding the Gap / Improv, PRISM 2026](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) | Already addresses stable identity under descriptor/name reuse and event reordering, by querying live OS state before finalizing logs. Our possible scope is offline preservation and ambiguity handling when live kernel state is unavailable. Claiming to invent stable identifiers or reconstruct missing identity with certainty would conflict with this work. |
| [Sun et al., HIDBench, May 2026 preprint](https://arxiv.org/abs/2605.21773) | Evaluates modern LLMs on host intrusion detection and reports substantial variation with noisy data. A new model comparison alone is weak differentiation. Detection and investigation endpoints must remain separate. |
| [How Benchmarks and Evaluation Protocols Shape Conclusions, August 2026 preprint](https://arxiv.org/html/2608.01454v2) | Reports strong lexical-novelty effects on several E3 subsets and richer semantic support on THEIA. The paper also documents benchmark limitations. Use natural identifiers and renamed controls, and verify joins before assuming a prepared benchmark supports forensic claims. |
| [Gheerbrant et al., Querying Incomplete Data, TPLP 2024](https://doi.org/10.1017/S1471068423000364) | Answers that hold across possible interpretations of incomplete data are established database theory. An intersection over alternative bindings is not new mathematics. A defensible contribution would need an APT-specific representation, scalable implementation and measured improvement beyond ordinary database baselines. |

Other screened primary work includes [ProvX](https://arxiv.org/html/2508.06073v1), which already uses counterfactual explanations, and [Weaver](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6826531), a May 2026 preprint on intent-aware interactive investigation. Neither generic counterfactual explanation nor interactive evidence-grounded Q&A is an unoccupied contribution. Search absence is not proof of novelty.

## Concrete implementation evidence

The actual [OCR-APT investigator file](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/src/ocrapt_llm_investigator.py) was downloaded and read, not merely inferred from its abstract:

- `parse_name_from_attr`, around line 203, reduces file/process paths to their final component and removes ports from some flow formats.
- `get_attack_description_from_df`, around line 245, retains descriptions and timestamps, rather than the original subject/object UUIDs.
- `prepare_document`, around line 266, aggregates descriptions within minutes.
- The IOC hallucination filter around line 505 checks substring presence. Presence of a name alone does not establish a particular relationship between two uniquely identified objects.

For example, `/usr/bin/python` and `/tmp/python` can acquire the same displayed name. Two actions within the same minute can lose their precise order. These are verified properties of the conversion code, **not measured frequencies of mistakes in published reports**. They do not prove OCR-APT's reported findings are wrong.

Downloaded file: 39,665 bytes; SHA-256 `429a76d687d0f2f975c3e4a9134b9a46d4b3bf4f5fdaf4ba5858b35fc8a5ea10`. Repository commit: `d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3`. No author model, checkpoint or pipeline was executed during this research audit.

## Two implementable mechanisms within one candidate

### 1. Preserve identity through the LLM interface — first pilot

Build an immutable event table. Assign compact aliases to existing full identities, such as `P17`, `F32`, and `E81`; keep the alias-to-UUID mapping, full path, host and exact recorded timestamp outside the prompt. Never turn a basename into a unique identity. Serialization may aggregate repeated equivalent actions only while retaining their event references and order constraints. The language model returns event references and typed relationships; a deterministic renderer resolves display names.

This alone may be a valuable engineering repair rather than a doctoral contribution. The pilot must establish a measurable problem on real released events, and an improvement over simply retaining UUIDs in ordinary JSON. If ordinary JSON resolves the issue equally well at comparable cost, stop the claimed method contribution.

### 2. Preserve competing matches and select a resolving query — optional extension

When a report artifact matches several objects, keep the candidate set. Apply available host, lifetime, type, parent and event constraints without filling absent fields by guesswork. Return a relationship as supported only when every still-feasible binding supports it; otherwise display the ambiguity. Inconsistent constraints produce an inconsistency result, not a vacuously true claim.

For ambiguity that the archive can resolve, choose a bounded follow-up lookup that partitions the candidate set most effectively per measured query cost. Examples are process start time, parent UUID or a full file path. A CPU implementation can use indexed tables and small candidate-set intersections. Compare this policy to fixed-order and random valid queries. No query can reveal unavailable live OS state. Cap candidate-set growth, and report unresolved cases explicitly.

This extension is a hypothesis about useful investigation efficiency. Generic active querying, certain-answer semantics and abstention are established techniques. Its novelty case is **conditional and moderate at best** until tested against those strong baselines and checked more broadly.

## Accessible artifacts and remaining gate

The [OCR-APT release](https://zenodo.org/records/17254415) exposes a `dataset.tar.xz` archive of 2,940,005,988 bytes, with published MD5 `bd6aa111af451e9bee44bc69dcab710b`. A prior project audit verified a 64-byte HTTP range response and XZ signature. The parent investigation is attempting full download, checksum and safe inventory separately. **This memo does not count that archive as acquired or inspected.**

The downloaded [author schema](https://github.com/CoDS-GCS/OCR-APT/blob/d927daf6057c80a46bdc5e44d7aa373d4a3ad5d3/datasets_Documentation.md) describes edge IDs through source/destination identifiers, entity types, timestamps and separate node attributes, plus malicious UUID files. It does not establish that every host preserves all fields needed here. Required checks are UUID uniqueness, host separation, timestamp units, path preservation, edge/node joins and attack-scenario grouping. The current normalized MAGIC arrays are insufficient for this task.

Additional actual downloads:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| OCR-APT schema documentation | 2,705 | `734cea1c246da0cb06a911e19260eed8a6e099caafe30d127c3d69e671c4d031` |
| OCR-APT prompt source | 7,062 | `1d05ae4c7a21751cc609e46e918cf41d48a39e479d1a9f82c787cea869509ecf` |
| CADETS published report | 5,690 | `09e9d19f9758a087977831767718ae42e25956b9fafb51ea1cf20b025d8a5070` |
| CADETS IOC annotation | 261 | `5f40aa40367f396f958a97c65222eeb7320b4cb7420ba650726a6980d6f8b063` |

The [ORTHRUS repository](https://github.com/ubc-provenance/orthrus/tree/e7f25dfee1ddd182a955b88f8a90a8cbd4a8e543) and its current README were also verified. It links prepared data and weights, but those large artifacts were not downloaded here. Its README warns that a missing `PYTHONHASHSEED` prevented exact replication of original results. An available repository is not proof of successful reproduction. OCR-APT code is Apache-2.0; dataset redistribution rights require their own verification.

## Small, fair pilot

### Stage A: CPU artifact and failure audit

1. Safely inventory the archive and load only inspected CSV/JSON tables. Do not load executable checkpoint or pickle formats for this stage.
2. Audit one E3 host and one genuinely separate supported host/scenario. Count where distinct UUID pairs collapse to the same serialized description, and where compression erases event-order distinctions.
3. Separate harmless naming collisions from collisions that change the answer to a registered investigation query. A high raw collision count alone is not a benefit result.
4. Build approximately 100 source-grounded query cases if enough eligible cases exist. Include actual unambiguous and ambiguous events, benign lookalikes, and unanswerable requests. All claims concern observable events; malicious node labels alone do not prove a causal attack edge.
5. Use deterministic questions with answers derived from the original event table: which exact process accessed a file, whether two steps involved the same process, and whether a recorded order is supported. Human review is needed for claims of malicious intent or attack-stage interpretation, which this first pilot omits.

### Stage B: paired comparison

Use identical source events, question sets and one fixed local language model. No fine-tuning or new GNN is required.

Required baselines:

- OCR-APT-style displayed descriptions and substring checks, clearly labeled as an isolated interface reproduction rather than its full system.
- UUID/full-path preserving JSON at the same token ceiling.
- Exact compound-identity SQL joins with recorded temporal constraints.
- The same deterministic joins with abstention when matches are not unique.
- Semantic top-match selection among schema-valid candidates, explicitly a reconstructed component baseline, not a reproduced HunterAgent system.
- The proposed representation alone; proposed ambiguity handling; and optional resolving queries, as separate ablations.

Evaluate natural cases and controlled perturbations separately. Perturbations should include same basenames across directories, same names on different hosts, repeated process instances, reordered same-minute events, omitted fields and absent evidence. Keep the untouched original available only to the scorer. Renaming must be identity-consistent and preserve the observable behavior. Include easy cases, because refusing every difficult question must not count as success.

Split by underlying host/scenario and original connected evidence component, with every transformed sibling kept in its parent's split. Nearby events, paraphrases and repeated seeds are not independent attacks. Use held-out scenarios for the decision; if there are too few scenario groups, report descriptive paired results without a population-generalization claim.

Primary metrics are incorrect entity links per answered query and exact supported relationship recovery at **matched answered coverage**. Also report abstention, answerability classification, full-path correctness, source-reference validity, retrieved event count, tokens, wall time and query count. Compare resolving-query policies at identical maximum query counts. Bootstrap by independent scenario when enough groups exist; never bootstrap dependent event rows as if they were independent campaigns.

### Proposed go / stop rules, to freeze before scoring

- Artifact hold if source identity/time joins cannot be verified, or if no independent scenario grouping is available for the intended claim.
- Mechanism stop if natural harmful ambiguities are too rare to support a meaningful paired study; synthetic examples alone support only a stress-test claim.
- Go to broader evaluation only if the method reduces wrong relationship bindings by at least 30% relative to the strongest available baseline at matched coverage, while correct relationship recovery falls by no more than 2 percentage points. Require a material gain on natural cases as well as perturbations.
- For the optional query policy, require at least 20% fewer inspected events or lookup calls at matched correctness and coverage than the strongest deterministic query order.
- Stop the novel-method claim if full-identity JSON or ordinary compound-ID joins match the method, or if improvement comes only from answering fewer questions.
- A small pilot that passes these engineering gates is a reason to continue, not a final praxis result. Widen the literature and independent-data review before claiming novelty.

## Recommendation

Proceed first with the CPU artifact audit and source-to-summary collision measurement. This directly tests a concrete implementation weakness and avoids another broad model search. If that gate succeeds, test identity-preserving evidence and competing-match handling in one bounded investigation study. Do not launch another detector-training sweep or market a new checker before establishing this narrower failure and an improvement over strong deterministic controls.
