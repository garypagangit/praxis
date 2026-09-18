# Five Praxis directions worth considering

**Research-priority review: September 18, 2026.** These are five directions supported by positive observations, with different levels of readiness. The evidence does not establish five novel, successful solutions. The first two are the strongest completed empirical foundations; the fifth is a reserve.

| Rank | Idea | Problem in everyday language | Positive result | Pursuit judgment |
|---|---|---|---|---|
| 1 | **Reliable review of AI code changes** | An AI can show real passing tests while hiding the tests that expose a broken change. | One reviewer accepted 12/101 harmful changes with selected test evidence, versus 4/101 with uniformly selected evidence. | Best completed risk finding. A successful defense remains to be demonstrated; the tested hybrid defense failed. |
| 2 | **Security evidence that actually applies** | A true security fact can be about the wrong situation and make an AI answer worse. | On 1,578 source-compatible questions, question-based retrieval improved Llama/Qwen accuracy by 18.19/13.88 percentage points. | Strong applied problem. The first checker failed external validation; the revised checker also produced no reliable gain across both models. |
| 3 | **Verifying software references** | Coding assistants can recommend packages, versions, repositories, or tags that do not exist. | In a small strict holdout, fabricated references accepted fell from 6/7 to 0/7; all 8 valid references were retained. | Clearest small working safeguard. Needs a larger independent test and added value beyond a full-metadata prompt, which tied it on the main model. |
| 4 | **Checking model and dataset references before use** | An AI setup assistant can name a resource that is missing, private, inaccessible, or the wrong version. | A live pilot blocked 232 occurrences labeled missing, with zero known-missing allows. | Early pilot, closely related to rank 3. Only two missing occurrences concerned physical-model registries; ambiguous lookups and extraction errors need review. |
| 5 | **Auditing behavior after model compression** | A cheaper model may retain an internal pattern while changing the behavior people need. | Across nine model/precision cells, the measured refusal-style geometry remained stable; minimum directed transfer ratio was .975. | Reserve only. Geometry is not independently verified safety, restoration did not improve the measured proxy, and close prior work limits novelty. |

## How I would allocate effort

Focus the main Praxis discussion on **rank 1 or rank 2**, depending on whether the adviser accepts a carefully controlled failure analysis or requires a successful new intervention. Keep **rank 3** as the most concrete small engineering alternative. Develop **rank 4** within the same broader verification program rather than claiming it is an independent methodological breakthrough. Do not fund rank 5 further until a distinct question and valid behavioral measure are established.

The completed [checker revision](../cti_checker_revision_20260918/REPORT.md) changed Llama from **86.53% to 86.77%** and Qwen from **87.09% to 87.01%** on 1,247 SecEval questions. Its mean gain was **+0.08 percentage points**, with a 95% interval of **[-0.24, +0.40]**. It accepted eight answer changes per model, recovered eight correct answers across the two model runs, and introduced six errors. It still rejected 89 of the 97 available useful corrections. This is an unsuccessful development attempt at establishing a reliable overall improvement, not fresh confirmation or proof of novelty. Complete the prepared independent human review before choosing another checker design; improved source retrieval has not yet been tested.

## Evidence, prior work, and exclusions

- [Evidence audit and exact limitations](EVIDENCE_AUDIT.md), [machine-readable recount](EVIDENCE_AUDIT.json), and [portable source snapshots](EVIDENCE_SOURCE_MANIFEST.json).
- [Primary-literature comparison](PRIOR_WORK_SCREEN.md), including recent direct overlaps. A topic or larger score alone does not establish an original contribution.
- Requested one-page summary of the frozen CTI external test: [PDF](../../output/pdf/cti_evidence_checker_one_page/Choosing_the_Right_Evidence_for_Cybersecurity_AI.pdf) and [editable Word](../../output/doc/cti_evidence_checker_one_page/Choosing_the_Right_Evidence_for_Cybersecurity_AI.docx). The subsequent development revision is reported separately.
- Larger follow-ups failed the main criteria for adaptive stopping, external streaming-intrusion adaptation, and cross-channel forecast harm. Their old positive headlines do not override those outcomes.
- A new post hoc check found the source-locked citation verifier's 90.4% accuracy was below a simple metadata comparator's 100% on the constructed labels. This is a diagnostic limitation, not a replacement for the original recorded result.

Independent human review and academic acceptance are not recorded as complete. These priorities concern which practical research question is most worth resolving next.
