# CTI Praxis pursuit decision and second-opinion reconciliation

September 18, 2026. Decision support based on existing evidence and primary literature; no new inference or statistical rerun. No academic approval is claimed.

## Recommendation

Keep CTI as the leading candidate for focused Praxis development. The existing experiment is a substantial empirical foundation, while its contribution beyond prior work and its practical solution remain the decisive questions. Do not discard it solely because its components are established. Do not treat its failed applicability selector as a working defense.

This is a recommendation to pursue a precise applied contribution, not a finding that the current manuscript is already sufficient for the degree. A new foundational AI algorithm is not the only possible contribution. Conversely, relabeling an ordinary retrieval pipeline or reporting a large effect does not establish originality.

## The applicable standard

The project materials identify GW's D.Eng. Praxis. The October 6, 2025 guidelines, linked by the current doctoral policies page, describe an original practical resolution using existing tools or techniques (Appendix section 3, printed page 10). The proposal section (printed page 3) requires a new approach to a real issue; the defense section (printed page 5) retains quality and originality judgment by the committee. Thus an applied system/process contribution can qualify without a new base model, but a comparative benchmark alone is not automatically sufficient.

Primary sources: [current policies page](https://online.engineering.gwu.edu/policies-procedures-doctoral), [D.Eng. guidelines](https://online.engineering.gwu.edu/sites/g/files/zaxdzs5816/files/2025-10/deng-student-guidelinesOct6_2025.pdf). This review does not replace the student's actual approved proposal or faculty assessment.

## What the pasted second opinion gets right

There is a real bounded positive: selected source-compatible relationship evidence improves the tested models' CTI multiple-choice answers, and incompatible evidence can harm them. The controls and archived predictions make the study inspectable. Source identity, evidence selection and scope belong in the central research question. The failures must remain visible.

## Material corrections

| Pasted assessment | Current evidence and implication |
|---|---|
| Leads with 500 questions and a 106-question slice | The canonical September 17 paper analyzes 2,500 questions: 1,578 eligible and 922 mismatch. Earlier numbers concern different samples/conditions; they are historical results, not interchangeable headline estimates. |
| Says confidence intervals and paired significance tests are absent | They are complete. The package includes Wilson and paired bootstrap intervals, exact McNemar tests and multiplicity corrections. A historical full reproduction regenerated 156 intervals; September 17 reused those intervals while rechecking counts. No new statistics are needed to fill this claimed omission. |
| Says controls isolate the mechanism | They support the compound evidence treatment. Content, length and wording differ, source-known retrieval gets a source pointer, and query retrieval sees answer options. Relational reasoning or graph structure is not isolated as the cause. |
| Says contamination can only reduce the measured effect | That direction is unestablished. Public-benchmark training exposure is unmeasured. Separately, 500 questions had prior development exposure; post hoc exclusion is a sensitivity analysis. |
| Explains router failure through an older source-bucket anomaly | PX-068 is a separate trained source classifier. Its external precision is 46.26%, and its false-positive rate is 52.53%. The earlier bucket observation does not establish the cause of that failure. |
| Says only presentation issues remain | Originality, information-access differences, measurement limitations and failed generalization are scientific issues. They restrict claims even though the archived positive remains. |

The other AI's conclusion is directionally reasonable about continuing investigation, but too strong about readiness.

## Canonical result

Source-known eligible gains are +23.07 percentage points for Llama and +19.58 for Qwen. Query-only eligible gains are +18.19 and +13.88 points; mismatch losses are -14.97 and -17.46 points. The primary terminal state is PASS_SOURCE_KNOWN_ONLY. PX-068 is FAIL_ROUTER_CONFIRMATION; PX-071 supplies no completed efficacy result.

Sources: [current paper](C:/w/px_final_20260917/final_praxis/final_three_20260917/01_cti/PAPER.md), [evidence map](C:/w/px_final_20260917/final_praxis/final_three_20260917/01_cti/EVIDENCE.json), [prior comparison](C:/w/px_final_20260917/final_praxis/final_three_20260917/01_cti/PRIOR_WORK.md). These sources preserve answer-format defects, source metadata access, option-text access, public-data limits and the difference between offline reproduction and new model replication.

## Candidate contribution worth reviewing

Plain-language question: What happens to an AI security assistant's accuracy when it must choose supporting evidence itself, rather than being given the correct source, and what practical process can preserve the useful benefit while limiting mismatch harm?

The completed portion separates evidence form, source access, eligible benefit, mismatch harm and an unsuccessful external selector. Its potential additional value lies in that specific controlled comparison and the resulting engineering decision, not in a first claim that retrieval helps or harms.

The closest overlaps are [TechniqueRAG](https://aclanthology.org/2025.findings-acl.1076/), [Beyond RAG for CTI](https://arxiv.org/html/2604.11419v1), and [Ahlert](https://arxiv.org/html/2609.08790v1). They already cover CTI retrieval and important evidence-use failures. None was implemented head-to-head in this completed experiment, so superiority over them is unestablished. The companion [gap review](RESEARCH_GAP.md) documents possible follow-up questions and their substantial prior-art overlap.

## Concrete next decision

Present the existing controlled comparison as the proposed applied foundation and ask for a specific scope determination: whether it already supplies sufficient original practical value, or exactly which capability/comparison must be demonstrated. This is an academic fit decision, not permission needed to continue ordinary analysis.

If one extension is necessary, keep the original CTI answer task initially. Qualify outcome scoring on fresh, source-disjoint questions; compare the old selector, a strong published question-evidence checker, and the specific proposed improvement under equal information access. Freeze benefit, mismatch-harm, useful answer coverage and total cost criteria before confirmation. Do not automatically change the topic into a full threat-hunting platform merely because Ahlert is a useful comparator.

Advance a practical-solution claim only when its added value survives those comparisons. If existing methods already solve the scoped problem equally well, retain the empirical result and reject the claimed new method. If the program accepts the current bounded contribution, additional inference is not required merely to make the paper look more novel.

## Decision summary

- Worth continuing as a focused applied Praxis candidate: yes.
- Demonstrated source-compatible evidence benefit: yes, within the tested benchmark and access conditions.
- Demonstrated automatic safe evidence selection: no.
- Established new AI algorithm: no.
- Established sufficiency for the degree: not yet; the practical contribution and required scope remain to be settled.
