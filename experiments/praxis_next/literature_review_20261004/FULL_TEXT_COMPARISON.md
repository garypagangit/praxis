# Full-text comparison: CyberShapley and AlertPro

Reviewed October 4, 2026, using the user's local PDFs. Both access blockers are resolved. This addendum supersedes the unavailable-full-text statements in the historical PX-103/PX-105 reports. It changes the literature assessment, not experiment results. Source PDF hashes and page counts are in SOURCES.json. Copyrighted PDFs and extracted full texts remain local, outside Git.

## Decision

Do not claim that explainable alert triage on APT data, bot-assisted explanation evaluation, budgeted recovery of low-ranked attack alerts, or the broad F1-up/recall-down pattern is new. These papers already provide directly relevant evidence. Our narrower controlled audit of stage-specific warning destinations remains a possible applied contribution; novelty and publishability are not established by that difference alone.

## CyberShapley

Malach et al., *CyberShapley: Explanation, prioritization, and triage of cybersecurity alerts using informative graph representation*, Computers & Security150 (2025),104270. Available online December21,2024. DOI: [10.1016/j.cose.2024.104270](https://doi.org/10.1016/j.cose.2024.104270). Local PDF:12 pages.

### Method and evidence

- Sections3.1-3.4, pages4-6: builds connected event subgraphs using analyst-defined correlation rules. Entities include processes, files and sockets. Computes Shapley-based importance for these event groups through model evaluations on masked sequences, then highlights the contributing groups for review.
- Sections3.5-3.7, page6: assumes the detector can handle masked/subset input or requires a replacement sampling strategy. Exact subset enumeration grows exponentially with the number of groups. Do not assume these event-deletion operations transfer directly to correlated network-flow features.
- Sections4.1-4.3, pages6-7: uses PublicArena and DARPA E3 CADETS/Theia. KRYSTAL filters suspicious events; an LSTM models ten-event windows. CyberShapley receives sequences flagged as anomalous. The reported evaluation concerns this selected stream, not every raw event or every undetected attack.
- Section5.1, pages8-9: tests importance by removing highly ranked subgraphs and observing whether the anomaly decision disappears. This already provides an intervention-based explanation check; our generic idea of checking an explanation by changing its supposed cause is not new.
- Section5.2, pages10-11:12 participants, three groups of four, each reviewing six sequences (three true positives and three false positives), comparing CyberShapley, SHAP and LEMNA. The authors report faster and more accurate decisions for CyberShapley. It is a small task-specific study; it is not evidence that our explanations help analysts.
- Figure9/page10 and text/page11: already uses ChatGPT-4 as a virtual analyst with and without explanations. This is an illustrative example; the paper does not present it as a large controlled bot benchmark. Nonetheless, using a bot reviewer is not a first contribution for us.

### Relation to our work

CyberShapley explains why an existing alert was raised and which connected events deserve attention. I did not find an evaluated comparison of stage-classifier update-induced warning demotion, ensemble averaging suppression versus OR, or recovery cost measured with our episode-proxy definitions. This distinguishes the evaluated questions, but does not prove those questions are absent from all literature.

## AlertPro

Wang et al., *Combating alert fatigue with AlertPro: Context-aware alert prioritization using reinforcement learning for multi-step attack detection*, Computers & Security137 (2024),103583. DOI: [10.1016/j.cose.2023.103583](https://doi.org/10.1016/j.cose.2023.103583). Local PDF:17 pages.

### Method and evidence

- Sections4.1-4.4, pages6-8: Isolation Forest initially ranks alerts using four basic and seven context features. An active-learning policy implemented with reinforcement learning reranks using the anomaly score and eight features derived from prior feedback. Evaluated variants include D3QN, A2C and PPO2.
- Section5.1, page9: uses LLDOS, ISCX and three CPTC2018 teams, with MAWI background traffic added for CPTC. Aggregates alerts sharing source, destination and signature within a ten-minute window. Ground-truth-derived binary labels supply the feedback in the evaluation. This is relevant precedent for automated label-oracle evaluation, not proof that an arbitrary reviewer bot substitutes for humans.
- Sections5.2/5.5, pages10-12: evaluates cumulative precision/recall and attack alerts found within a query budget. Budgets are set near known attack-alert totals. These differ from our fixed supplemental case slots per window; do not compare their reported percentages directly with ours.
- Section5.3, page10: discusses recovering attack-related alerts initially ranked1438th and1622nd. We therefore cannot claim that recovering important low-ranked attack signs is an unexplored concept.
- Section6.1, page14: discusses both feature importance and a decision-path explanation of how feedback can elevate an initially low-scoring alert. Decision-path explanation in IDS is not absent from prior work.
- Section6.3, page15: explicitly assumes reliable expert feedback and identifies limited feedback types and one-at-a-time output as limitations. Section6.2 says it has not been used in an actual enterprise network. Its evidence is not a deployment outcome study.

### Direct prior evidence of F1 up while recall falls

Table4, page11, visually checked against the PDF:

| LLDOS features | F1 | Attack recall |
|---|---:|---:|
| Basic features |0.6188|90.78%|
| Context features |0.8370|82.50%|
| Basic plus context |0.8151|73.75%|

Basic plus context raises F1 by0.1963 while recall falls17.03 percentage points. Section5.4 also discusses the lower LLDOS recall. Thus the general phenomenon is already reported, not hidden in unexamined numbers. Our macro-F1/stage-specific warning-destination analysis, paired rows, acquisition conditions and repair auditing are additional details that must carry the contribution. They do not make the broad phenomenon newly discovered.

## Claim-by-claim disposition

| Proposed claim | Assessment after full-text review |
|---|---|
| First XAI triage study on APT data | Ruled out by CyberShapley. |
| First bot review with versus without security explanations | Ruled out as a broad claim by CyberShapley's ChatGPT-4 example. |
| First importance-removal test for IDS explanations | Ruled out by CyberShapley and other attribution literature. |
| First budgeted recovery of overlooked attack alerts | Ruled out as a broad claim by AlertPro. |
| First observation of F1 improving while attack recall falls | Ruled out by AlertPro Table4. |
| New diagnosis algorithm better than ordinary traces | Not supported: PX-105 tied the ordinary trace baseline. |
| New prioritizer better than confidence | Not supported: PX-103 selected identical cases in all nine comparisons. |
| Reproducible audit of stage-specific warning demotion with explicit repair limits | Still a candidate applied contribution. Requires a broader literature comparison and committee assessment; these PDFs do not establish its novelty. |

## Consequence for the Praxis

The primary title can still accurately describe the studied problem, but any first-discovery language about score-up/warning-down must be removed or narrowed. Treat AlertPro as prior evidence motivating the audit, and CyberShapley as an established XAI/SOC comparator. Emphasize exactly what our paired stage-level accounting measures, how it is reproducible, and what the tested repairs fail to solve.

The literature comparison is complete for the requested access blockers. We have not implemented either published system or shown empirical superiority over it. The current follow-ups do not establish a novel XAI algorithm or actual analyst benefit. No new experiment, model training, paid compute or manuscript rewrite was performed during this review.
