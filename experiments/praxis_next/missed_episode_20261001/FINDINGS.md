# PX-095: Why the existing gate misses these exfiltration episode proxies

## Main finding

The 12 missed episode proxies are **12 individual flows between the same source and destination, all using TCP destination port 22**. Eleven contain only two packets totaling 121 bytes and last 0–1 milliseconds. The remaining flow contains 73 packets, 14,823 bytes and lasts 120.254 seconds. The source labels all twelve as Data Exfiltration with an APT signature.

These are not evidence of twelve independent successful thefts. The 60-minute gap rule separated repeated activity from one endpoint pair across two captures into twelve episode proxies. This materially qualifies the operational interpretation of PX-094's 6/18 coverage. Do not remove these records from the benchmark, but do not call them confirmed incidents either. Port 22 alone does not verify application identity or file transfer; stage annotations do not establish stolen content.

## Evidence

| Diagnostic | Result | Interpretation |
|---|---|---|
| Primary episodes | 18 total; 12 completely unwarned | All 12 missed episodes contain one flow each |
| Missed endpoint pairs | 1 | Repeated related activity, not 12 independent attack samples |
| Traffic size | 11 two-packet flows; 1 larger flow | Small exchanges dominate episode misses |
| Five-member predictions | Every member predicts benign on all 12 | Rearranging those existing hard warnings cannot recover them |
| Lowest benign probability across members/flows | 99.8775% | Strong model scores, not calibrated certainty; these are not near argmax ties |
| Training exfiltration in shared protocol/role/service stratum | 0, before and after training subsampling | No positive examples in this specific category |
| Benign training rows in that stratum | 7 eligible; 2 retained by capped fitting | Sparse support, entirely benign; capping did not remove positive examples |
| Exact current-plus-roles input match with benign rows | 0 in capped training; 0 in test | No demonstrated exact-input contradiction; benign resemblance is not an impossibility proof |
| Prior same-source base-OR warnings, within capture | 0/12 at 5, 30 and 60 minutes | A simple bounded carry-forward of existing source warnings would not rescue these episodes |
| Source-label trace | All 3,442 test exfiltration rows verified against native CSV | Prepared labels and row mapping agree with source annotations |

The shared stratum is department source to OTHER_ADDRESS destination, TCP, remote-administration service category, without the web/DNS service categories. OTHER_ADDRESS is an unknown topology category, not proof that the destination is on the Internet.

The full OR gate misses 26 exfiltration flows overall: these twelve plus fourteen inside episodes that already have another warned exfiltration flow. The diagnostic distinguishes wholly missed episode proxies from unwarned flows in already warned episodes.

## Why this happens: evidence versus explanation

The observed combination is sparse, entirely benign training support in this traffic category, tiny exchanges in eleven cases, and confident benign predictions across every existing member. This is consistent with a shared feature/training limitation. It does not isolate which feature or training choice caused the predictions. The models share much of their training information; adding another seed does not introduce missing evidence about the activity.

The earlier-warning diagnostic also has a substantial benign background: 53,746/192,193 benign test rows have a prior source warning within five minutes, 82,258 within thirty minutes, and 95,735 within sixty minutes. These are context prevalences, not new false-alert counts or a fitted rule's workload. The test uses source orientation and capture boundaries; it does not rule out longer-lived, destination-oriented or session-level context.

## Recommended next work

1. **Qualify the underlying activity before another model experiment.** Link these source rows to any available packet/session records or attack execution narrative. Determine whether the tiny records are fragments or maintenance traffic associated with an attack session, and whether the larger record contains an independently documented transfer. Keep unknowns unknown. This determines whether a flow, session or documented transfer is the right target.
2. **Test new information if source qualification supports it.** Candidate signals include completed-session byte history and recurrence, host/process identity, file-access or transfer evidence, and destination behavior relative to a host's prior activity. Current data already include flow byte counts and coarse roles; simply renaming those features adds no information. No benefit from these additional signals is established here.
3. **Evaluate on untouched executions with matching benign administration traffic.** If new labeled training examples are acquired, include legitimate traffic in the same category. Choose the alert-cost policy using training/calibration only. Report both flow and session/episode coverage plus grouped workload. These twelve inspected records cannot serve as independent validation of a fix designed from them.

Do not spend on a larger ensemble based on this diagnosis. The immediate need is stronger source qualification and potentially different evidence, rather than another vote over the same confidently benign decisions. No new detector or operational improvement is claimed.

## Reproducibility and scope

Frozen diagnostic protocol and runner: commit `9d0bca3`. Zero new fits, cloud calls or model API calls. Independent post-run audit passed 376 checks for episode reconstruction, member warning counts, probability minima, training support, exact input matches and source trace. Additional endpoint-pair/port summaries are explicitly marked post-hoc in SOURCE_DETAIL.json. All data were previously examined; this is diagnosis, not a new confirmatory evaluation or a novelty finding.

[Episode table](EPISODES.csv) · [Twelve missed flow records](MISSED_FLOWS.csv) · [All feature profiles](FEATURE_PROFILES.csv) · [Summary](SUMMARY.json) · [Source detail](SOURCE_DETAIL.json) · [Audit](AUDIT.json) · [Protocol](PROTOCOL.md)
