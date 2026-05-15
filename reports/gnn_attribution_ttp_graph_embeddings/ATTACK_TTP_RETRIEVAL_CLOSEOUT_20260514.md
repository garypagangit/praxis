# ATT&CK TTP-Set Retrieval Closeout

Generated: 2026-05-14

Status: **result #2 strengthened; selected as bounded profile-retrieval result**

## Bottom Line

The ATT&CK TTP-set branch now clears the main closeout objections for a second narrow result: simple retrieval is strong, it beats random and degree-prior floors, performance remains visible by degree bucket, and the failed GraphSAGE path stays explicitly negative.

This remains a profile-retrieval result, not CTI prose attribution or actor authorship.

## Graph And Evaluation

| Item | Value |
|---|---:|
| Groups | 174 |
| Techniques | 697 |
| Group-technique edges | 4546 |
| Eligible groups, degree >= 10 | 121 |
| SVD explained-variance ratio sum | 0.6535 |

## Main Results With Floor Baselines

The practical operating point is 5 observed TTPs. At that point, overlap and SVD strongly exceed both random ranking and a simple group-frequency prior.

| method | shot | top1 | top5 | top10 | mrr | median_rank | queries | top5_lift_vs_random |
|---|---|---|---|---|---|---|---|---|
| frequency_prior | 5 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 | 1.5 |
| overlap_cosine | 5 | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 | 34.2 |
| random_uniform | 5 | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 | 1.0 |
| svd32_graph_embedding | 5 | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 | 31.3 |

## All Shot Levels

| method | shot | top1 | top5 | top10 | mrr | median_rank | queries |
|---|---|---|---|---|---|---|---|
| frequency_prior | 1 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| overlap_cosine | 1 | 0.136 | 0.425 | 0.598 | 0.284 | 7.0 | 605 |
| random_uniform | 1 | 0.003 | 0.025 | 0.053 | 0.030 | 91.0 | 605 |
| svd32_graph_embedding | 1 | 0.093 | 0.286 | 0.468 | 0.209 | 12.0 | 605 |
| frequency_prior | 3 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| overlap_cosine | 3 | 0.425 | 0.846 | 0.942 | 0.602 | 2.0 | 605 |
| random_uniform | 3 | 0.005 | 0.018 | 0.035 | 0.028 | 90.0 | 605 |
| svd32_graph_embedding | 3 | 0.306 | 0.684 | 0.858 | 0.479 | 3.0 | 605 |
| frequency_prior | 5 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| overlap_cosine | 5 | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 |
| random_uniform | 5 | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| svd32_graph_embedding | 5 | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 |
| frequency_prior | 10 | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| overlap_cosine | 10 | 0.969 | 1.000 | 1.000 | 0.982 | 1.0 | 605 |
| random_uniform | 10 | 0.008 | 0.030 | 0.055 | 0.035 | 82.0 | 605 |
| svd32_graph_embedding | 10 | 0.931 | 0.993 | 1.000 | 0.959 | 1.0 | 605 |

## Five-Shot Degree-Bucket Check

Degree buckets are computed over eligible groups. Low degree is <= `20` techniques and mid degree is <= `41` techniques.

| method | degree_bucket | top5 | mrr | median_rank | median_degree | queries |
|---|---|---|---|---|---|---|
| frequency_prior | high-degree | 0.128 | 0.109 | 20.0 | 57.0 | 195 |
| frequency_prior | low-degree | 0.000 | 0.010 | 101.0 | 14.0 | 205 |
| frequency_prior | mid-degree | 0.000 | 0.017 | 60.0 | 29.0 | 205 |
| overlap_cosine | high-degree | 0.887 | 0.644 | 2.0 | 57.0 | 195 |
| overlap_cosine | low-degree | 0.995 | 0.953 | 1.0 | 14.0 | 205 |
| overlap_cosine | mid-degree | 0.995 | 0.866 | 1.0 | 29.0 | 205 |
| random_uniform | high-degree | 0.015 | 0.030 | 82.0 | 57.0 | 195 |
| random_uniform | low-degree | 0.024 | 0.030 | 83.0 | 14.0 | 205 |
| random_uniform | mid-degree | 0.044 | 0.039 | 86.0 | 29.0 | 205 |
| svd32_graph_embedding | high-degree | 0.831 | 0.659 | 1.0 | 57.0 | 195 |
| svd32_graph_embedding | low-degree | 0.951 | 0.866 | 1.0 | 14.0 | 205 |
| svd32_graph_embedding | mid-degree | 0.854 | 0.667 | 1.0 | 29.0 | 205 |

## Example Five-Shot Retrievals

| true_group | degree | observed_ttps | overlap_rank | svd_rank | frequency_rank |
|---|---|---|---|---|---|
| APT38 | 56 | T1036.006 Space after Filename; T1036.003 Rename Legitimate Utilities; T1135 Network Share Discovery; T1106 Native API; T1518.001 Security Software Discovery | 1 | 1 | 24 |
| Indrik Spider | 33 | T1685.005 Clear Windows Event Logs; T1552.001 Credentials In Files; T1486 Data Encrypted for Impact; T1112 Modify Registry; T1036.005 Match Legitimate Resource Name or Location | 1 | 3 | 53 |
| BlackByte | 48 | T1112 Modify Registry; T1068 Exploitation for Privilege Escalation; T1055 Process Injection; T1087.002 Domain Account; T1219 Remote Access Tools | 1 | 1 | 30 |
| SideCopy | 16 | T1608.001 Upload Malware; T1036.005 Match Legitimate Resource Name or Location; T1518 Software Discovery; T1204.002 Malicious File; T1106 Native API | 1 | 1 | 91 |
| GALLIUM | 31 | T1003.002 Security Account Manager; T1133 External Remote Services; T1027.005 Indicator Removal from Tools; T1136.002 Domain Account; T1560.001 Archive via Utility | 1 | 1 | 57 |
| APT3 | 44 | T1041 Exfiltration Over C2 Channel; T1021.001 Remote Desktop Protocol; T1027.005 Indicator Removal from Tools; T1018 Remote System Discovery; T1104 Multi-Stage Channels | 1 | 4 | 35 |
| Mustard Tempest | 12 | T1036.005 Match Legitimate Resource Name or Location; T1583.008 Malvertising; T1204.001 Malicious Link; T1608.001 Upload Malware; T1566.002 Spearphishing Link | 1 | 1 | 106 |
| Kimsuky | 130 | T1553.002 Code Signing; T1593.001 Social Media; T1678 Delay Execution; T1190 Exploit Public-Facing Application; T1684.001 Impersonation | 6 | 2 | 1 |

## Decision

Select this as the second portfolio result **only** under the bounded claim: ATT&CK group technique profiles support few-shot profile retrieval from observed TTP sets.

Do not claim CTI prose attribution, attacker authorship, or GNN superiority. The learned GraphSAGE pilot remains a negative result because simple overlap and SVD dominate it.

## What Is Now Closed

- Random and frequency-prior floors are present.
- Degree-bucket sensitivity is documented.
- Example retrieval rows are available for paper/slides.
- The claim boundary is explicit.

## Remaining Optional Polish

- Add a release-to-release ATT&CK drift split if historical ATT&CK versions are needed.
- Add a small analyst-facing visualization of query techniques to top candidates.
- Convert this report into a thesis subsection after Praxis 06 packaging.
