# PX-092 findings

H1: **SUPPORTED_BY_CONSTRUCTION**; H2: **SUPPORTED_KNOWN_RESULT**; H3: **NOT_SUPPORTED**; H4: **SUPPORTED**; H5: **SUPPORTED**; H6: **VACUOUS_NO_QUALIFYING_CELL**. H1 is structural; H2 repeats an already observed result. H4 and H5 primary decisions use the prespecified primary slice, with all secondary outcomes retained.

## Clean seed-count curve

| Seeds | OR exfil warning recall | Mean exfil warning recall | OR false alerts | Mean false alerts | OR overlap |
|---:|---:|---:|---:|---:|---:|
| 1 | 98.751% | 98.751% | 186 | 186 | 1.0000 |
| 2 | 98.751% | 98.402% | 196 | 178 | 0.5506 |
| 3 | 98.780% | 68.042% | 196 | 182 | 0.3636 |
| 5 | 98.780% | 68.216% | 238 | 180 | 0.2659 |
| 7 | 98.867% | 68.303% | 258 | 179 | 0.2163 |
| 10 | 98.867% | 68.303% | 259 | 177 | 0.1548 |

## Adapted AIT execution validation

| Execution | OR exfil warning recall | Best single seed | Overlap | Strict recall improvement |
|---|---:|---:|---:|---|
| wilson | 99.985862% | 99.985862% | 0.34177215189873417 | False |
| harrison | 99.603530% | 99.599267% | 0.5435540069686411 | True |
| pooled | 99.785120% | 99.773928% | 0.5319226559649762 | True |

## Adversity

| Budget | Condition | Clean recall | Adverse recall | Fraction retained | Pass |
|---:|---|---:|---:|---:|---|
| 1 | delayed_unavailable | 98.780% | 89.309% | 0.9041 | True |
| 1 | wrong_host_history | 98.780% | 98.780% | 1.0000 | True |
| 2 | delayed_unavailable | 98.780% | 89.309% | 0.9041 | True |
| 2 | wrong_host_history | 98.780% | 98.780% | 1.0000 | True |
| 3 | delayed_unavailable | 98.780% | 89.309% | 0.9041 | True |
| 3 | wrong_host_history | 98.780% | 98.780% | 1.0000 | True |

## Interpretation

**The strongest result is warning preservation relative to averaging, not a large gain over a strong single model.** The first seed alone reached 98.751% clean exfiltration warning recall with 186 false alerts. Three-seed OR added one exfiltration-flow warning and ten false alerts; ten-seed OR added four exfiltration-flow warnings and 73 false alerts relative to that seed. The best seed is a retrospective comparison, not a method for choosing a deployment model without labels.

On AIT, current+history OR produced 54 false alerts on Wilson versus 52 for its exfiltration-best seed, without improving exfiltration warning recall. On Harrison it recovered one additional exfiltration-flow warning over that execution's best seed, while false alerts increased from 686 to 1,404. The pooled best seed can differ from either execution's best seed. False-alert overlap met the proposed criterion but did not establish an acceptable operational workload. H3's requirement of improvement on both executions was not met.

These counts refer to labeled flows, not distinct attack campaigns or independently confirmed adversaries. The results support a reproducible evaluation of warning loss, seed sensitivity and alert workload. They do not establish OR as a novel algorithm or a broadly superior APT detector.

OR retention guarantees that combining the same warning decisions cannot remove a constituent warning. It does not guarantee extra attack coverage, a small false-alert burden, or useful independence among seeds. The empirical parts of H3 and H4 test those additional claims.

The gain from five to ten seeds is 0.087159 percentage points in the clean primary slice. Saturation below 1 pp: True; strictly decreasing overlap: True. Non-decreasing recall alone is mathematical, not evidence of improved learning.

Across all 120 triples, OR exfiltration warning recall ranges from 68.216% to 98.867% (median 98.518%). False-alert counts range from 182 to 254 (median 218.0). These are sensitivity summaries, not independent confidence intervals.

The original 8101–8103 triple had recall at least as high as 99 of the 120 triples, counting ties and itself. Its high result should not be assumed representative of every three-seed choice. [Full subset distribution](partB/SUBSETS_3.csv) and [seed-curve figure](partB/SEED_CURVE.png) retain the weaker combinations.

H6 has 0 qualifying cells. With none, its implication is vacuously true and provides no empirical aggregator-contrast evidence.

The delayed experiment shares the original seed-8101 acquisition schedule across every member; seven new roles seeds use the seed-8101 current model as fallback. Wrong-host history is unchanged input for roles-only experts. A4 is an acquisition-unconstrained reference, clearly excluded from budget-feasibility claims. No roles-corruption experiment was performed.

Audit: 140,354 checks passed over 228 cells / 684 reported rows. Every saved OR/mean decision was recomputed independently from source probability arrays, and all seven new models' full test predictions were reproduced. No cloud allocation or model API was used.

## Required scope statements

- UNRAVELED remains one previously examined campaign; the test rows were exposed in PX-081 and PX-086. Part A and Part B are development results, not fresh validation.
- Exfiltration training rows (1,740) are identical across seeds; seed diversity arises from benign/other-stage sampling and tree randomness. Ensemble diversity is therefore not attack-coverage diversity.
- The OR-gate multiplies inference cost by |M| and does not reduce evidence-acquisition cost.
- Roles are eight coarse static-topology indicators from one campaign; transfer of the roles-expert result to other networks is not established.
- AIT uses the adapted three-class, history-only contract. A Part C result is execution-disjoint evidence for the OR-gate mechanism, not a replication of the four-class result.
- A warning is a non-benign model label; no analyst outcome is measured.

## Evidence

[Protocol](PROTOCOL.md) | [Execution clarifications](EXECUTION_NOTES.md) | [Freeze](FREEZE.json) | [Audit](AUDIT.json) | [Hypothesis details](HYPOTHESES.json) | [Part A](partA/RESULTS.md) | [Part B](partB/RESULTS.md) | [Part C](partC/RESULTS.md)
