# Appendix F: Follow-up Repair Studies and Evidence

## F.1 Experiment map

**Table F-1. Follow-up studies included in this revision.** Each folder preserves its protocol, source hashes, outputs and validation scope.

| Experiment | Question | Main finding | Evidence folder |
|---|---|---|---|
| PX-092 | Does OR preserve warnings across seeds and AIT? | Preserves member warnings; required improvement in both AIT executions fails | or_gate_20260930 |
| PX-093 | Do different model types add useful coverage? | Additional flow warnings; combined benefit/workload criteria fail | heterogeneous_gate_20260930 |
| PX-094 | Do extra flows mean additional episodes? | No extra episode coverage from full OR; more grouped cases | soc_workload_20261001 |
| PX-095 | What are the twelve wholly missed proxies? | Twelve singleton flows from one endpoint pair; no positive training support in shared stratum | missed_episode_20261001 |
| PX-096 | Does a TCP/22 policy cover those misses? | Original OR plus rule warns on 18/18 proxies; adds 510 benign flows and 460 cases | ssh_policy_20261001 |
| PX-097 | Does the unchanged rule help AIT? | No extra exfiltration coverage; labeled exfiltration uses UDP/53 | ssh_transfer_20261001 |

Folders are under experiments/praxis_next in the project repository. The public reports contain aggregate results; private row-linked arrays are identified by local paths and hashes. Source access remains necessary for full recomputation.

## F.2 Validation scope

PX-092 and PX-093 preserve their independent audit reports and original success criteria. PX-094 passes 15,496 independent checks across 72 case cells, 216 episode-result rows and 648 queue scenarios. PX-095 passes 376 post-run checks of episode reconstruction, member predictions, training support, input matches and source details. All 3,442 UNRAVELED exfiltration test rows are traced to their native source records.

PX-096 verifies all 208,094 test rows and all 32 Boolean combinations of model warning, protocol match, port match, scope and approval. PX-097 checks source identities, labels, times and endpoints, independently recovers native ports, and verifies the unchanged policy output and grouped-case counts. Their validation receipts do not claim an independent end-to-end audit. Computational agreement does not establish incident truth or deployment effectiveness.

## F.3 Reproduction and claim boundaries

Run each recorded runner with its existing frozen sources in a fresh output location. Do not overwrite prior results, refit on inspected test records or relabel failed criteria as successful. The dated revision changes the paper's explanation and adds completed evidence; it does not change experimental predictions.

PX-093's LITERATURE_AND_CLAIMS.md records classifier-combination and error-diversity precedents. PX-096's FINDINGS.md records official network-filtering guidance and its retrieval limitations. These checks prevent claiming novelty for OR combination or a TCP/22 restriction. The recommendation is to assess warning preservation, coverage and workload together under an independently specified policy.
