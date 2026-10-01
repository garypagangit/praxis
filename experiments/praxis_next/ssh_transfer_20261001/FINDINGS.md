# PX-097: Fixed SSH-port policy transfer results

## Conclusion

The unchanged TCP destination-port 22 rule adds **no exfiltration coverage** in AIT Wilson or Harrison. Every labeled exfiltration flow in these executions uses **UDP destination/server port 53**. The rule still enforces its declared port condition; it cannot address this different channel.

This limits the earlier PX-096 repair to matching traffic. It does not disprove deterministic policy enforcement, but it does reject treating a TCP/22 restriction as a general exfiltration repair. No DNS rule was added after inspecting these outcomes.

## Results: original OR versus original OR plus fixed rule

| Source | Exfiltration flow recall, before → after | Episode proxies warned, before → after | Additional exfiltration flows warned | Additional benign-labeled warnings | Additional grouped cases |
|---|---:|---:|---:|---:|---:|
| UNRAVELED (PX-096, development) | 98.7798% → 99.1575% | 6/18 → 18/18 | 13 | 510 | 460 |
| AIT Wilson (PX-097) | 99.9859% → 99.9859% | 1/1 → 1/1 | 0 | 30 | 15 |
| AIT Harrison (PX-097) | 99.6035% → 99.6035% | 1/1 → 1/1 | 0 | 0 | 0 |

Group definition remains source/client, destination/server and a 15-minute flow-end window within capture/execution. UNRAVELED is shown for context, not pooled as independent evidence with AIT. The original OR already warns on the single exfiltration episode proxy in each AIT execution; it still misses three Wilson and 93 Harrison exfiltration flows, all on UDP/53.

The rule matches 59 Wilson flows (42 benign, 17 other attack) and nine Harrison flows (four benign, five other attack). All matched attack flows were already warned by original OR. Thirty matched Wilson benign flows lacked an original warning, producing fifteen new grouped cases. Original OR already warned on all nine Harrison rule matches.

For the full heterogeneous OR, adding the rule also recovers no exfiltration flows. Wilson gains 29 benign warnings and fifteen cases; Harrison remains unchanged. The full gate's preexisting three-flow Wilson and one-flow Harrison advantage over original OR is from its models, not the rule. All five arms are retained in RESULTS.csv.

## What is established

- A deterministic policy overlay can preserve its own warnings despite a benign model prediction, and preserve the model's existing warnings.
- The TCP/22 overlay repaired the twelve exposed UNRAVELED singleton episode proxies under the blanket-rule assumption.
- A different exfiltration channel falls outside the rule. AIT supplies no positive exfiltration examples matching TCP/22, so it cannot validate the rule's ability to recognize malicious SSH on a new execution.
- The rule's business acceptability is unmeasured: the datasets contain no authoritative approved-destination lists or organizational SSH exceptions.

## Recommendation for the Praxis

Retain the primary warning-loss/audit Praxis. Treat policy overlays as a bounded engineering extension unless stronger evidence is obtained. Do not promote the TCP/22 rule as a novel or generally successful exfiltration detector.

The next confirmatory study needs an actual policy specified independently of test labels, legitimate permitted and prohibited activity, and untouched executions spanning more than one exfiltration channel. For example, SSH destination restrictions and approved DNS resolvers could be part of a genuine organizational policy; adding a blanket UDP/53 ban merely because this dataset's attack uses it would be another post-hoc shortcut and could disrupt normal service. No such new rule or allowlist is inferred here.

Maintain separate outputs for policy violations, ML attack warnings and stage predictions. Assess violations against authorization ground truth and attacks against attack ground truth. A benign-labeled prohibited connection can correctly trigger policy enforcement, while an approved connection can still carry an attack.

## Verification and limits

Frozen protocol/code commit: `a621a5f`. The existing PX-096 decision function was reused unchanged. Both execution ZIPs, prepared data and saved predictions/metadata were hash-checked against prior receipts. Full row identities, source labels, times and endpoints were aligned. Ports were independently read from native CSV columns and compared with the source reader; per-row policy output and alternate grouped-case accounting passed. See VALIDATION.json for the scope of checks; this is not an independent end-to-end audit.

Wilson and Harrison were excluded from model fitting but previously examined. Thus this is a fixed-rule transfer test, **not untouched confirmation**. One exfiltration episode proxy per execution is weak support for episode-level generalization. No prevented transfer, deployment, analyst effectiveness or attacker adaptation was measured. Zero new fits, cloud allocations or production changes.

[All results](RESULTS.csv) · [Channel diagnostics](DIAGNOSTICS.json) · [Validation](VALIDATION.json) · [Frozen protocol](PROTOCOL.md) · [PX-096 development result](../ssh_policy_20261001/FINDINGS.md)
