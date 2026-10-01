## 4.12 Preserving Model Warnings: PX-092 and PX-093

On the clean UNRAVELED comparison at budget two, the original three-member OR gate warns on 98.7798% of exfiltration flows, compared with 68.0418% for probability averaging. Benign flow warnings rise from 182 to 196. The models are the same; only their combination changes. This is a warning-preservation result on previously examined records.

The benefit is not uniform across model selections or sources. The OR recall across three-member subsets ranges from about 68.22% to 98.87%. Adding seeds to reach ten members raises clean recall to 98.8669% and benign warnings to 259. PX-092's requirement to improve strictly over the best individual member in both AIT executions fails: Wilson ties its best member, while Harrison improves slightly. That failed criterion remains failed.

PX-093 adds a current-only model and logistic regression. The full five-member OR recovers more exfiltration flows but adds many benign warnings. Its fixed combined benefit-and-workload criteria fail.

**Table 4-18. Original versus full heterogeneous OR.** These are flow warnings; neither column establishes an incident was detected.

| Source | Original OR exfil. recall | Full OR exfil. recall | Original benign warnings | Full benign warnings |
|---|---|---|---|---|
| UNRAVELED | 98.7798% | 99.2446% | 196 | 1,991 |
| AIT Wilson | 99.9859% | 100.0000% | 54 | 1,751 |
| AIT Harrison | 99.6035% | 99.6078% | 1,404 | 15,420 |

The added exfiltration warnings are sixteen UNRAVELED flows, three Wilson flows and one Harrison flow. Other attack warnings also increase. The next test asks whether those extra flows cover another exfiltration episode rather than adding warnings to activity already flagged.

## 4.13 Episode Coverage and Review Workload: PX-094

Additional models produce no extra exfiltration episode coverage under any tested episode definition. On UNRAVELED, averaging warns on four of eighteen primary episode proxies; original OR warns on six; full OR also warns on six. Both AIT executions contain one primary episode proxy, which all these policies already warn on. Full OR warns earlier on the Harrison episode, but the current-only addition already supplies that earlier warning.

**Table 4-19. Primary episode coverage and extra grouped cases.** Cases use 15-minute source/destination windows. Extra cases compare full OR with original OR.

| Source | Averaging episodes | Original OR episodes | Full OR episodes | Extra cases | Extra hours at 15 min/case |
|---|---|---|---|---|---|
| UNRAVELED | 4/18 | 6/18 | 6/18 | 1,550 | 387.50 |
| AIT Wilson | 1/1 | 1/1 | 1/1 | 151 | 37.75 |
| AIT Harrison | 1/1 | 1/1 | 1/1 | 758 | 189.50 |

The hours are assumed service effort, not measured analyst workload. The reference queue becomes heavily overloaded under all policies; no exfiltration-linked review slot finishes within 60 minutes of its episode's earliest completed flow. These queue outcomes depend on the stated schedule, grouping and handling time. They are not production forecasts.

The important measurement lesson is that 98.78% flow recall can coexist with only 6/18 episode coverage. Large episodes contribute many flows and dominate the flow score. Episode counts weight each defined group once. The next diagnostic shows why those groups must also be checked before calling them incidents.

## 4.14 What the Twelve Missed Proxies Represent: PX-095

All twelve completely missed UNRAVELED episode proxies contain a single flow. They use the same source and destination and TCP destination port 22. Eleven are two-packet exchanges totaling 121 bytes and lasting 0-1 milliseconds. The remaining flow contains 73 packets, 14,823 bytes and lasts 120.254 seconds. The native source labels each as Data Exfiltration with an APT signature.

These are twelve time-defined proxies, not twelve independently confirmed thefts. The grouping rule separates repeated activity from one endpoint pair across two captures. Port 22 does not by itself verify an SSH application or stolen-file transfer.

All five members predict benign on these flows. The lowest benign score across the members and missed flows is 99.8775%; this is a model score, not calibrated certainty. Their shared protocol, host-role and service category contains no exfiltration training examples. It contains seven eligible benign training rows, two retained by capped fitting. The absence of positive examples therefore predates subsampling.

No missed flow has an exactly identical current-plus-roles input among the checked benign fitting or test rows. No earlier same-source warning exists within the tested 5-, 30- or 60-minute windows. These findings are consistent with a shared information or training limitation, but do not isolate its cause. They do show that rearranging the existing members' hard warnings cannot recover these flows.

## 4.15 What a TCP/22 Rule Repairs, and What It Does Not: PX-096 and PX-097

The blanket TCP/22 rule adds a warning even when the models predict benign. Combined with original OR, it warns on all eighteen UNRAVELED episode proxies. It recovers thirteen exfiltration flows: the twelve completely missed proxies plus one flow in an already warned episode. The price is 510 additional benign-labeled flow warnings and 460 additional grouped cases. Twenty-nine exfiltration flows still receive no warning, within episodes that have another warning.

**Table 4-20. Unchanged TCP/22 overlay on original OR.** UNRAVELED is the exposed development result; AIT is an already-examined transfer test. Episode counts are proxies.

| Source | Exfil. flow recall before/after | Episodes before/after | Extra exfil. flows | Extra benign flows | Extra cases |
|---|---|---|---|---|---|
| UNRAVELED | 98.7798% / 99.1575% | 6/18 / 18/18 | 13 | 510 | 460 |
| AIT Wilson | 99.9859% / 99.9859% | 1/1 / 1/1 | 0 | 30 | 15 |
| AIT Harrison | 99.6035% / 99.6035% | 1/1 / 1/1 | 0 | 0 | 0 |

Every labeled exfiltration flow in Wilson and Harrison uses UDP destination/server port 53. The TCP/22 rule therefore recovers none of the three Wilson or 93 Harrison exfiltration flows missed by original OR. AIT supplies no matching exfiltration examples with which to validate the rule's benefit on new SSH activity. The protocol was not widened after this result.

The rule alone is also insufficient on UNRAVELED: it warns on only thirteen of eighteen episode proxies and thirteen of 3,442 exfiltration flows. The combined result comes from retaining both model and policy warnings.

This is a successful warning repair for the inspected matching traffic, with a demonstrated boundary on another channel. It is not evidence that the model learned exfiltration, that every data transfer was blocked, or that port filtering is novel. Because the rule was selected after inspecting misses, a future confirmatory test must fix the actual organizational policy and exceptions before examining untouched executions.
