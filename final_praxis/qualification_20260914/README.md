# Praxis development and new-experiment qualification

September 14, 2026. The new protocols were committed before GPU execution. This campaign qualifies reproducibility and measurement; it does not establish a new algorithm's efficacy or academic acceptance.

**Progress at 14:24 UTC:** CTI's internal handoff and 009 qualification are published. SOUP passes numerical checks but prefetch takes 6.32% longer in the tiny warm-cache workload. TimesFM 3 passes hardware feasibility and its saved synthetic probe has been independently reconciled; original TimesFM 2.5 replay is running and the public NAB calibration run remains pending. Overall 010 qualification is still pending. Cloud teardown has not yet occurred.

| Workstream | Purpose | Evidence |
|---|---|---|
| CTI development | Navigate the completed CTI evidence, understand its limits and prepare for independent authorship. | [Internal guide, Word/PDF, evidence index and automated checks](https://github.com/garypagangit/praxis/tree/Final-Praxis-CTI-Development-20260914/final_praxis/cti_development_20260914) |
| Final-Praxis-009 | Check whether a bounded CPU staging modification preserves SOUP's actual model outputs, gradients and updates before considering a larger training experiment. | [Protocol and qualification package](https://github.com/garypagangit/praxis/tree/Final-Praxis-009-SOUP-Streaming/final_praxis/009_soup_streaming) |
| Final-Praxis-010 | Reproduce attack-detection and conformal-score implementations, separate an oracle baseline from deployable policies, and test current forecasting-model feasibility. | [Protocol and qualification package](https://github.com/garypagangit/praxis/tree/Final-Praxis-010-Attack-Aware-Forecasting/final_praxis/010_attack_aware_forecasting) |

The [three existing research drafts and evidence packages](https://github.com/garypagangit/praxis/tree/Final-Praxis-Top-Three-Papers-20260914/final_praxis/papers/20260914) remain available. CTI has the strongest completed cybersecurity evidence, 008 is the decision-manipulation alternative, and PX055 supports a narrower geometric measurement claim.

## Academic authorship status

The current [GW doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links an [AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) that restricts AI-written submitted Praxis work. These AI-assisted documents are internal research materials. No applicable written exception has been verified, and human editing alone does not establish compliance. Source identification and coding are permitted under the policy's conditions, including attribution and the author's ability to explain the code. This package preserves provenance and makes no submission or approval claim.

## Compute controls

One existing AWS g5.xlarge was authorized for at most two hours under a $25 combined reserve, with an external stop schedule installed before startup. The verified Linux instance rate was $1.006/hour. This reserve is not a billing invoice. No paid model API calls, additional GPU instances, held-out HAI scoring or full efficacy campaign are part of this qualification.

`cloud_ops.py` implements profile-based control and keeps account/resource identifiers and operational logs in a separate private settings directory. It accepts no embedded credentials. The public campaign record will identify protocol hashes, runtime environments, actual outcomes and verified shutdown.
