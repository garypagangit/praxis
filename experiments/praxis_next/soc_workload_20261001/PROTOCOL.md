# PX-094: Exfiltration episode coverage and grouped SOC workload

Freeze before producing results. This is a local CPU replay of existing PX-093 decisions; zero fits, cloud allocations or model API calls. All source data have previously been examined. No confirmed real incident or analyst outcome is inferred from simulation.

## Question and source qualification

Do additional flow warnings identify an exfiltration episode previously missed, or mainly add warnings to already detected episodes? What additional grouped cases and review time result? UNRAVELED provides source/destination, capture and time; AIT provides native flow labels, execution identity and source-row pointers, from which original client/server endpoints can be recovered. Neither prepared source supplies independently adjudicated SOC incident IDs or handling times. Thus the measured units are **label-defined exfiltration episodes** and **simulated investigation cases**, not confirmed incidents.

Use UNRAVELED clean budget 2 and AIT Wilson/Harrison, separately. Policies: original three-member probability mean; three-member OR; three-member OR plus existing current-only model; full heterogeneous OR. Preserve all policies; do not tune or select a favorable grouping after seeing results. Native labels remain four-class UNRAVELED and three-class AIT. Host addresses stay private.

## Fixed grouping and timing

1. Predictions become available at recorded flow **end**, because features describe completed flows. Convert UNRAVELED milliseconds to seconds; AIT prepared times are already seconds. Verify labels and identities against prior artifacts before replay.
2. Primary investigation case: capture/execution + source/client + destination/server + a fixed 15-minute UTC window of flow-end time. Aggregate only warned flows. Release a case at the end of its window, so no future alert is available early. Sensitivity: 5 and 60 minutes, and source-only grouping (capture/execution + source/client + window). Windows are half-open; an end exactly on a boundary belongs to the following window. Case IDs depend only on endpoint/time metadata, never labels or policy.
3. A benign-only-warning case contains no warned true attack flow. A case containing any warned attack is counted separately. Unwarned exfiltration flows in the same group are reported as context but never credited as detected. No rule assumes an analyst discovers every hidden attack.
4. Primary exfiltration episode: consecutive true-exfiltration flows from the same source/client within one capture/execution, with a new episode when consecutive **start** times differ by more than 60 minutes. Sensitivity: 30 and 120 minutes. Labels define evaluation truth only, not case construction or queue order. These are operational proxies, not independent campaigns. Also report native capture/execution coverage.
5. An episode is warned only when at least one of its true-exfiltration flows receives any non-benign prediction. Report first warning relative to episode first start and earliest completed flow. Correct exfiltration stage naming is not required. All-zero support is undefined, never zero recall. Compare recovered and lost episodes with base-three OR, including earlier warning times where both detect.

## Workload and queue scenarios

Report total cases, benign-only-warning cases, attack-warning cases, exfil-warning cases, deduplication factor, and additional cases per additional episode (undefined if no new episode). Raw warning counts remain visible. Include all-stage attack gains.

Simulate 5, 15 and 30 minutes per investigation; 1, 2 and 4 analysts; fixed daily 09:00–17:00 **UTC** shifts, all calendar days, FIFO and no dropped cases. No breaks, weekends, variable complexity or measured staff productivity are claimed. One case occupies one analyst; a case that will not finish before shift end starts next shift. Serve ties by stable case ID, without labels. Scenario reference is one analyst at 15 minutes, unless the user selects a different reference before the freeze; all nine scenarios remain reported. User selection of no preferred staffing leaves all scenarios unranked.

Report total analyst-hours, cases whose service finishes by the final observed case-release boundary, unresolved cases at that boundary, waiting-time median/p95, and backlog clearance time. Preserve simulated service start/finish per case. Report episodes with a linked exfil-warning case served within 60 and 240 minutes of earliest completed exfil flow and by observation end. This is **review-slot completion**, not analyst detection success. Stronger OR can preserve flow warnings while delaying review through added workload; do not assume queue outcomes are monotone.

## Frozen checks and interpretation rules

- Structural: case membership and release respect endpoints, blocks and windows; no future row is released early. OR supersets retain base flow warnings and directly warned episodes. Base cases are a subset of OR-superset cases for the same grouping. Case count and alert conservation must hold. Duplicate endpoint/time rows are not extra incidents.
- Empirical: report whether full OR adds **any** primary exfiltration episode on each source, and whether primary review-slot completion improves. No positive direction is required; all sensitivity outcomes are retained. No new practical-utility threshold or novel theorem is claimed.
- Audit independently reconstructs endpoint mappings, grouping, episode boundaries, case counts, structural invariants and selected/full queue accounting from private per-row artifacts, without importing the runner. Preserve all source and decision hashes, raw aggregate results, private case/queue ledgers and report the remaining inability to establish true incident or analyst effectiveness.

The requested incident-level recommendation can be completed only to this qualified proxy/scenario scope with existing data. Additional true incident IDs and measured investigation records would be required for a stronger operational claim.
