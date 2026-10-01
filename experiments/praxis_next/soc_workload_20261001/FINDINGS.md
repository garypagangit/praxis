# PX-094 interpretation: preserving warnings does not guarantee episode coverage

## Decision

Retain the original three-member OR gate as the warning-preservation baseline for further research. These results do not support adding both heterogeneous members to improve exfiltration episode coverage. They also do not establish that the original gate solves missed exfiltration: it still misses 12 of 18 UNRAVELED episodes under the primary definition.

The completed replay used saved PX-093 predictions, zero new fits and no cloud or model API calls. The independent audit passed 15,496 checks across 72 case cells, 216 episode-result rows and 648 queue scenarios. The protocol, runner and audit were frozen in commit `f65e41d` before replay.

## What improves, and what does not

Primary definitions: source/client episodes separated by more than 60 minutes between consecutive exfiltration flow starts, within a capture/execution; investigation cases grouped by source, destination and 15-minute flow-end windows.

| Source | Averaging: episodes warned | Original OR: episodes warned | Full heterogeneous OR: episodes warned | Full OR additional cases versus original OR | Additional service hours at 15 minutes per case |
|---|---:|---:|---:|---:|---:|
| UNRAVELED | 4 / 18 | 6 / 18 | 6 / 18 | 1,550 | 387.50 |
| AIT Wilson | 1 / 1 | 1 / 1 | 1 / 1 | 151 | 37.75 |
| AIT Harrison | 1 / 1 | 1 / 1 | 1 / 1 | 758 | 189.50 |

1. **Original OR versus averaging:** UNRAVELED gains two warned episodes. It also creates 332 additional grouped cases (83 service hours at 15 minutes per case); the increase includes attack-warning cases as well as benign-only cases. Wilson and Harrison gain no additional episode coverage.
2. **Full heterogeneous OR versus original OR:** none of the three sources gains an episode. This remains true across all declared 30/60/120-minute episode gaps and alert grouping/window variants. Full OR does warn earlier on the one Harrison episode; it does not discover a previously unwarned episode. The current-only addition already provides that earlier warning.
3. **More flow warnings do not necessarily mean more episodes caught.** PX-093 full OR recovered 16 additional UNRAVELED exfiltration flows, three Wilson flows and one Harrison flow. Here, all those gains occur within episodes already warned by original OR. Other attack-stage warnings also increase; this experiment does not establish their incident-level value.
4. **The flow denominator hides uneven coverage.** Original OR warned on about 98.78% of UNRAVELED exfiltration flows in PX-093, yet warns on only 6/18 episodes here. Full OR reaches about 99.24% of flows but remains at 6/18 episodes. Flow recall weights large episodes heavily; episode coverage gives each defined episode one count. Neither metric alone establishes campaign detection or operational safety.

## What the workload simulation says

Every grouped case receives a FIFO review slot. The reference scenario assumes one analyst, daily 09:00–17:00 UTC shifts and 15 minutes per case. These are explicit assumptions, not observed SOC staffing or handling times.

All four policies create substantial backlogs in the reference scenario. Original versus full OR median queue wait rises from 321.75 to 889.75 hours on UNRAVELED, 1,563.38 to 1,630.25 hours on Wilson, and 6,963.12 to 7,249.88 hours on Harrison. These large values describe an overloaded simulated queue; they are not forecasts of a production SOC. At this staffing level, none has an exfiltration-linked review slot completed within 60 minutes of its episode's earliest completed exfiltration flow. One UNRAVELED episode is served within 240 minutes under each policy; neither AIT episode is.

The practical lesson is conditional: willingness to investigate more helps only if cases can receive timely review. Extra warnings can consume capacity without expanding episode coverage. The complete one/two/four-analyst and 5/15/30-minute service grids remain in the results; no favorable scenario was selected to claim operational success.

## Implication for the Praxis

The defensible finding is that a deterministic OR gate preserves member warnings and can recover episodes lost by averaging, while flow-level gains from additional experts may provide no extra episode coverage and increase review demand. This supports evaluating warning preservation, episode coverage and workload together. It does not establish novelty or a generally superior deployed detector.

Use the original OR baseline for further investigation of the 12 missed UNRAVELED episode proxies. Because even full OR does not warn on them, rearranging these same members' existing hard warnings cannot recover them; recovery would require additional signals, changed model decisions or contextual detection. Any new intervention must be evaluated on untouched executions rather than optimized and validated on these same episodes.

## Boundaries of the evidence

- These are label-defined temporal episode proxies, not independently adjudicated SOC incidents. The AIT primary result has only one episode per execution, so 1/1 is weak evidence of generalization.
- A warning means any non-benign prediction on a true-exfiltration flow. Correct stage naming is not required.
- A completed review slot is not proof that an analyst would recognize or contain an attack. Service time is assumed constant, and priority triage is not modeled.
- Previously examined test data were replayed. This is a descriptive follow-up with frozen definitions, not a fresh confirmatory holdout or independent campaign trial.
- True incident identifiers and timed analyst reviews are needed to establish actual incidents rescued and operational benefit. Additional model tuning cannot replace that evidence.

[Full tables](RESULTS.md) · [Frozen protocol](PROTOCOL.md) · [Audit receipt](AUDIT.json) · [Episode results](RESULTS.csv) · [Queue scenarios](QUEUE_RESULTS.csv)
