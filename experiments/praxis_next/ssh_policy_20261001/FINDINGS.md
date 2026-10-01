# PX-096: A deterministic TCP/22 rule closes the observed episode-warning gap

## Result

Adding the user's blanket TCP destination-port 22 rule to the original OR warnings covers **18/18 exfiltration episode proxies**, compared with 6/18 for original OR alone. This recovers all twelve wholly missed proxies identified in PX-095. It also warns on one extra exfiltration flow in an already warned episode: thirteen additional exfiltration flows in total.

| Offline policy | Exfiltration flows warned / 3,442 | Exfiltration flow warning recall | Episodes warned / 18 | Benign-labeled warning flows | Grouped warning cases |
|---|---:|---:|---:|---:|---:|
| TCP/22 rule alone | 13 | 0.38% | 13 | 510 | 483 |
| Original OR | 3,400 | 98.78% | 6 | 196 | 1,057 |
| Original OR + TCP/22 rule | 3,413 | 99.16% | 18 | 706 | 1,517 |
| Full heterogeneous OR + TCP/22 rule | 3,429 | 99.62% | 18 | 2,501 | 3,067 |

Original OR plus rule adds **510 benign-labeled flow warnings and 460 grouped cases**. At an assumed 15 minutes per additional case this is 115 analyst-hours of service, not a measured operational cost or a new queue simulation. Its benign-flow warning rate rises from 0.1020% to 0.3673%. The full heterogeneous gate adds workload without additional episode coverage over original OR plus rule.

The rule alone is not an exfiltration detector: it misses five episodes covered by ML and nearly all exfiltration flows by volume. The combined policy retains both sources of warning. Twenty-nine exfiltration flows still pass without warnings under original OR plus rule, within episodes that have another warning. Do not interpret 18/18 as a zero-miss flow result.

## What the rule means

An enforceable policy is: **in the defined scope, TCP destination port 22 requires explicit approval; unapproved connections receive a deny recommendation and policy warning, regardless of the model's benign score.**

"Block SSH only when it is exfiltration" still requires identifying exfiltration, so it does not remove the original uncertainty. The policy must specify observable conditions and approvals. If the organization bans all TCP/22 in a particular scope, the exception list is empty. If administration is required, explicitly approved paths remain permitted by this rule. Approval never clears an independent ML warning.

The implementation in [gate.py](gate.py) returns a policy violation, warning and deny recommendation. It does not modify a firewall or relabel a flow as exfiltration. A real enforcement point would need to enforce this decision before the connection carries traffic. Completed-flow replay cannot demonstrate that behavior or count transfers prevented.

## Why training is not required

Keep a mandatory policy outside the learned classifier. Training examples, weights or a policy-compliance feature may influence a model but do not guarantee that every forbidden connection is caught. The deterministic combination is:

```text
policy_violation = in_scope AND TCP AND destination_port == 22 AND NOT approved
final_warning = model_warning OR policy_violation
deny_recommended = policy_violation
```

Maintain the model's stage classification separately from the policy reason. If training is later extended, use independently labeled legitimate and malicious administration sessions, causal host/session context, and a distinct policy-compliance target. Do not change benign truth labels to exfiltration merely because a new policy disallows the traffic.

## Recommended practice and sources checked

- **MITRE ATT&CK M1037:** restrict SSH access to authorized ranges and filter unauthorized outbound traffic. This supports a deterministic authorization rule and network enforcement. [Filter Network Traffic](https://attack.mitre.org/mitigations/M1037/).
- **CISA AA25-239A:** for network-device management, isolate management services and limit egress to required destinations. Its device-management scope matters; it is not a universal mandate to ban all organizational SSH. [Countering Chinese State-Sponsored Actors](https://www.cisa.gov/news-events/cybersecurity-advisories/aa25-239a).
- **NSA/CISA:** application allowlisting can avoid relying exclusively on generic port numbers. [Top Ten Cybersecurity Misconfigurations](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-278a).
- **CISA:** SSH can be tunneled over HTTPS/443. Thus TCP/22 filtering does not cover all SSH or all exfiltration; application-aware controls and endpoint/session evidence remain relevant. [StopRansomware Guide](https://www.cisa.gov/stopransomware/ransomware-guide).

Sources checked October 1, 2026. MITRE page was retrieved directly; CISA recommendations were available through indexed official-page extracts when direct page retrieval failed. These recommendations establish prior practice, not algorithmic novelty for this rule.

## Scope and verification

This replay assumes every monitored test connection is in scope, with no approved exceptions. There is no authoritative organizational allowlist or verified egress-boundary mapping in the data. Benign-labeled matches therefore quantify potential impact; they do not prove that an actual organization's policy would prohibit legitimate business traffic. Conversely, if traffic is truly forbidden, a benign attack label does not make the policy warning incorrect.

The TCP/22 rule was proposed after the twelve missed records were inspected. It is deterministic for future decisions, but it was **not predetermined in the original experiment**. This is an exposed-data repair, not independent confirmation. All twelve missed proxies relate to one endpoint pair, and none is independently adjudicated as a separate successful theft. Attacker adaptation or use of different ports is untested.

Protocol and code frozen in commit `4a8820e`. All 208,094 test rows were traced to source labels/endpoints/timestamps; native TCP and destination-port fields were restored. All 32 combinations of model warning, protocol match, port match, scope and approval passed gate checks. Full per-row gate equality and alternate grouped-case accounting passed. The validation receipt states its scope; it is not an independent end-to-end audit. Zero model fits, cloud spending or production changes.

**Recommendation:** retain original OR plus an explicit, separately enforced authorization policy as the candidate architecture. For a confirmatory Praxis, freeze the actual policy and exceptions before testing untouched executions, including legitimate SSH administration and exfiltration through other channels. Measure episode/session coverage, affected benign activity and grouped workload. Do not claim novelty for blocking a port.

[Protocol](PROTOCOL.md) · [Results CSV](RESULTS.csv) · [Validation receipt](VALIDATION.json) · [Decision component](gate.py)
