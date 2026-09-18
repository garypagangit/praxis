# CTI external validation status

**The frozen checker did not meet the combined external transport criteria. Individual benefits and harms remain visible below.**

Status: `EXTERNAL_TRANSPORT_CRITERIA_NOT_MET`. All 1,247 questions and 4,988 fresh outputs were analyzed.

- Llama 3.1 8B: 86.53% → 86.21%; change -0.32 [-0.88, +0.24] pp.
- Qwen 2.5 7B: 87.09% → 87.25%; change +0.16 [-0.40, +0.72] pp.
- Evidence used: 85/1247 (6.82%).
- Usefulness gates: FAIL; added-value gates: FAIL.
- Algorithmic novelty remains unproven; this uses public questions, shared ATT&CK sources, and released labels.

The blinded 50-item review packet is ready; zero human reviews are recorded as completed. Two independent security reviewers and a third adjudicator are required.

The earlier pilot remains part of the evidence. See [full report](REPORT.md), [updated decision](DECISION.md), and [ready-to-use human-review handoff](REVIEW_HANDOFF.md).

AWS connection was established and used. The full numerical audit passed; the GPU was verified stopped after the single completed run. Local archive recovery preserved every output byte. See [operational closeout](OPERATIONS.md). Estimated compute was approximately $0.59, not an invoice.
