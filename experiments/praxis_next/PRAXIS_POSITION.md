# When Better APT Scores Hide Missed Attack Warnings

Praxis position for review - September 24, 2026.

## The problem in ordinary language

A security team can choose a model because its overall score is higher, even though that model calls more attack activity normal. A score alone can therefore hide a tradeoff the team needs to see.

## The research question

**When do better APT model scores come with more missed attack warnings?**

The study examines this question using matched evaluation records and explicit accounting of correct stage labels, wrong-stage attack labels, attacks classified as benign, and false alarms on benign records. Training chronology and source qualification are supporting checks.

## The thesis and practical contribution

APT model comparisons should report correct-stage recognition, stage-specific missed warnings, and benign false alerts alongside overall scores, using a justified temporal evaluation design.

The praxis contributes measured evidence of the tradeoff and a reproducible procedure for revealing it. Its practical use is to make model-selection tradeoffs visible. The experiments measure classification outcomes; they do not measure improvements in analyst decisions, prevented attacks, or field deployment.

## Evidence already obtained

| Finding | Actual evidence | What it establishes |
|---|---|---|
| A higher overall score can accompany more missed warnings | In the clean budget-three acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379, while exfiltration-labeled records receiving any attack label fell from 85.18% to 76.25%. Mean benign false alerts also rose from 111.3 to 122.3. | This specified comparison improved the headline score while losing warnings and increasing false alerts on the same records. |
| The direction survives the specified single-unit omissions, while magnitude varies | All nine group means with higher F1 and lower exfiltration warning recall retain that direction after each individual seed or capture omission. Removing seed 8101 from the headline comparison reduces warning loss from 8.93 to 0.36 percentage points. | The observed mean-direction example is not eliminated by one specified deletion; the magnitude is strongly seed-sensitive. |
| Evaluation composition changes the reported score | Time-mixed fitting raised macro-F1 by 0.0632 on identical anchor records with the classifier architecture and per-class fitting counts fixed. | Training-pool composition materially affected the reported result on this evaluation population. |
| Historical evidence also produced useful improvements | Under chronological fitting, history raised macro-F1 from 0.7365 to 0.7582 and reduced mean benign false alerts from 24.0 to 14.3, alongside a smaller exfiltration warning loss. | Useful gains and stage-specific warning loss can coexist and should be reported together. |
| The public calculations are reproducible | A fresh local Python environment reproduced 36 comparisons and 720 metric intervals; the review bundle passed its extraction and integrity checks. | Reviewers can verify the public aggregate arithmetic without private prediction files. |

These rows summarize related measurements from one campaign. They are not independent campaign replications or evidence that analyst outcomes improved.

## Contribution relative to the literature

Prior studies already recognize attacks misclassified as normal, temporal evaluation concerns, and attack-stage modelling. This paper adds controlled flow-level observations about their interaction, a complete account of the declared comparison outcomes, and executable checks of whether proposed benchmark releases support the intended evaluation. The [closest-work audit](measurement_praxis/LITERATURE_AND_CLAIMS.md) documents both overlap and the narrow contribution.

The paired quantities use established confusion-matrix measures. The scholarly claim is the empirical contribution and its reproducible application. Reviewers must assess whether that contribution is sufficient for the intended venue.

## Scope and submission position

The central results concern one previously examined UNRAVELED campaign. The movement target refers to author-annotated discovery, and completed-flow features do not establish early prediction. Warning loss was examined retrospectively. The paper includes these qualifications, seed variation and the full reported comparisons.

The completed [paper](submission_readiness/apt_praxis_review_edition.pdf), [editable manuscript](submission_readiness/apt_praxis_review_edition.docx), and [evidence bundle](submission_readiness/praxis_review_bundle.zip) support review as an empirical cybersecurity evaluation praxis. A new detector is not an outstanding deliverable. The remaining review concerns are the sufficiency of the empirical contribution, institutional presentation, and whether a particular venue requires broader replication. The [adviser handoff](submission_readiness/ADVISER_HANDOFF.md) is prepared and unsent.
