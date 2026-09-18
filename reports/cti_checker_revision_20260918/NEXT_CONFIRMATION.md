# What would count as a completed better-checker claim?

The current revision is a bounded development test. It checks the answer-selection component while reusing the same six retrieved facts and previously generated answers. A higher development score would justify further testing, not establish a new practical solution or novelty.

## Human step already prepared

Two independent cybersecurity reviewers must complete the existing [50-item blinded form](../cti_external_validation_20260918/human_review.html) under the [handoff instructions](../cti_external_validation_20260918/REVIEW_HANDOFF.md). Preserve both original judgments and use a third reviewer for disagreements. No real reviewer responses have been received in this session. Do not substitute generated explanations for their work or overwrite the original released labels.

The balanced packet is a quality diagnostic. It does not estimate population accuracy and may not contain every answer-changing error. Any additional outcome-targeted error review must be marked diagnostic and kept separate from the preselected packet.

## Follow-up experiment, subject to the diagnostic findings

Freeze four conditions on previously unused questions: original evidence and original checker; original evidence and revised checker; improved evidence and original checker; improved evidence and revised checker. These comparisons separate the effect of better retrieval from the effect of better checking. Keep the generator, question/options, information access, and cost accounting explicit.

Build the improved evidence corpus from authoritative sources appropriate to the actual question types, including the relevant security framework or platform documentation. Pin source versions, licenses, retrieval parameters, and time cutoffs. Do not retrieve using answer keys or source pointers available only in benchmark labels. Retain difficult, unsupported, and ambiguous questions rather than removing failures after seeing outcomes.

Include plain relevance and a strong published support verifier. A generic NLI adaptation is not a complete CoRM-RAG, PAVE, or SURE-RAG reproduction. The proposed condition checks for platform, version, entity, and time should be evaluated separately; none is established by the present maximum-support policy.

Set new success criteria before confirmation, covering net additional correct answers, evidence-induced errors, retained useful corrections, all-question performance, source groups, and total tokens/latency. Separate evidence rejection from refusing to answer. For any abstaining system, report answer coverage alongside accuracy; unanswered items cannot disappear from the denominator.

SecEval has been inspected and is development data for this revision. A confirmatory set must be untouched by threshold selection, prompt changes, and error-based design. Hold out source/document families where possible, audit exposure, and document the remaining public-data/pretraining limitations. The previous external failure remains unchanged regardless of a later result.

## Stop rules

Stop or narrow the claim when the revised method fails to beat a simple comparator at comparable cost, gains arise only from rejecting more questions, the supporting passages fail human review, or novelty reduces to renaming an existing technique. Keep failed attempts and the reasons for design changes in the record.
