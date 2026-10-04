# Review assessment — October 4, 2026

## Recommendation

Revise the original Praxis as an applied auditable-AI study. Keep its title, **When Better APT Scores Hide Missed Attack Warnings**. State the research product more precisely: a reproducible audit of stage decisions, lost warnings and repair costs in an APT flow pipeline.

The evidence does not support starting a fresh manuscript claiming a new XAI algorithm. PX-103 tied confidence ranking, and PX-105 tied ordinary trace diagnosis. CyberShapley already evaluates explainable APT triage; AlertPro already reports higher F1 with lower attack recall. Model-update regression also has direct prior work in computer vision and malware detection.

## What the new experiment adds

PX-106 compares exact-stage regression with warning regression on all 27 saved PX-081 policy pairs. In the clean, budget-three comparison, seed 8101 loses 901 exfiltration warnings. Only eight had a previously correct stage label; 893 were wrong-stage warnings that became benign. Seeds 8102 and 8103 lose four and 25 warnings, respectively. All are reported.

The result supports explicit binary warning accounting beside stage accounting. Ordinary binary negative flips already capture it. The study does not introduce a new mathematical metric or outperform that baseline. The independent reconstruction passes 945 checks. No new model training or paid compute was needed.

## Academic assessment

| Requirement | Evidence available | Remaining limit |
|---|---|---|
| Specific problem | Stage correctness and retained warnings can diverge on identical records | Broad regression problem is established |
| Research product | Audit procedure, code, protocols, saved results and verified calculations | Operational benefit not measured |
| Literature differentiation | Full-text CyberShapley/AlertPro review and explicit negative-flip comparison | Not a systematic proof of first use |
| Controlled evidence | Fixed rows, per-seed results, capture sensitivity and source checks | One exposed UNRAVELED campaign |
| External test | Adapted AIT Wilson/Harrison test, excluded from original fitting | Original policy ordering failed to replicate; related laboratory scenarios |
| Positive repair | OR preserves available warnings; local policy adds coverage | No universal detection gain; extra cases and channel limits |
| Explainability | Recorded actions and outputs support verifiable decision explanations | No causal attack explanation or completed human study |
| Reproducibility | Frozen input hashes and independent arithmetic reconstructions | Some complete reruns require private source/prediction artifacts |
| Defense readiness | Complete review manuscript and evidence map | Adviser must assess contribution sufficiency; no acceptance guarantee |

This is a defensible description of completed evidence. It is not a certification that the contribution meets the committee's novelty threshold. A more ambitious method or analyst-benefit claim requires evidence the completed work does not provide.

## How the two example Praxes shaped the format

Reviewed the user-provided Date and Okhankhuele PDFs. Both organize the research in five chapters with formal front matter, numbered sections, figures/tables, an abstract and references. This edition follows that structure and keeps the original detailed appendices. The executive summary and Appendix G explain the work in everyday language. Technical definitions remain available for examination.

The review edition uses a review-status page because an approved certification page requires actual institutional confirmation. No committee names, degrees, approvals or defense dates were copied from the examples. The author's existing degree information is preserved from the prior manuscript.

The layout uses US letter pages, Times New Roman 12-point main text, double-spaced body paragraphs, portrait side margins of 1.25 inches and top/bottom margins of 1 inch. Front matter uses Roman numbering; main chapters use Arabic numbering. These follow the inspected [GW ETD formatting guidance](https://gradpostdoc.gwu.edu/gw-etd-formatting). Final institutional acceptance of the submission format is still a university decision.

## AI assistance and evaluation

This edition discloses AI help with planning, code, analysis, literature summaries, drafting and editing. It does not claim that AI was used only for proofreading. No writing-detector service was run and no detector outcome is guaranteed. The paper should be evaluated through its sources, reproducible results and the author's ability to explain its choices and limitations.

GW's current default rules require explicit instructor permission for submitting AI-generated content for evaluation; instructors may set their own permitted scope. The applicable Praxis direction and disclosure requirements must be confirmed before submission. Disclosure alone does not establish permission. See the [Provost's AI guidelines, default rules](https://provost.gwu.edu/guidelines-using-artificial-intelligence).

## Closest additional precedent checked October 4

- [Yan et al., Positive-Congruent Training (CVPR 2021)](https://openaccess.thecvf.com/content/CVPR2021/papers/Yan_Positive-Congruent_Training_Towards_Regression-Free_Model_Updates_CVPR_2021_paper.pdf): negative flips and mitigation across model versions. This rules out claiming general warning-preservation across updates as an unexplored idea.
- [Ghiani et al., Regression-Aware Continual Learning for Android Malware Detection (2026)](https://doi.org/10.1109/TIFS.2026.3714132), [inspected author text](https://arxiv.org/html/2507.18313v2): directly addresses harmful prediction changes in security. It does not serve as an implemented baseline in our experiment.

Search terms included intrusion detection model-update regression, negative flips and APT warning audits. This was a targeted follow-up, not a systematic review or proof of novelty. The supplied PDFs remain local and are not redistributed in Git.
