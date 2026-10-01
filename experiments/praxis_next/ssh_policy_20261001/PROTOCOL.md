# PX-096: Deterministic TCP/22 policy overlay

User-proposed policy after PX-095 showed all twelve missed singleton episode proxies use TCP destination port 22. This is explicitly a post-hoc repair on exposed data, not a predetermined policy in the original experiments and not a novel filtering algorithm.

Operational rule: for an in-scope connection, TCP destination port 22 requires explicit approval. A violation produces a policy warning and deny recommendation that ML cannot suppress. A legitimate approval exempts only the policy rule, not an independent ML warning. Preserve the stage prediction separately; policy violations do not establish exfiltration. This offline software returns decisions and does not modify a firewall.

Dataset scenario: all monitored UNRAVELED test flows are in scope, with no approved exceptions. The data lack an organizational allowlist and verified perimeter-egress designation. Thus this is a blanket destination-port restriction scenario, not a measured unauthorized-egress policy. Do not infer external status from OTHER_ADDRESS. Recover native destination ports from source CSV row pointers and verify identities and original source hashes.

Freeze before replay. Compare rule alone, original OR, original OR plus rule, and full OR plus rule. Retain native attack/benign labels. Report exfiltration warning flows and all 18 PX-094 episode proxies; benign-labeled matched flows and grouped cases; additional warnings and grouped cases relative to original OR. Group by capture/source/destination/15-minute completed-flow window exactly as PX-094. Grouping is workload accounting, not simulated packet blocking. No inference about prevented transfers, modified sessions, attacker adaptation or analyst decisions.

The offline gate must preserve ML warnings, flag every in-scope unapproved TCP/22 connection, allow policy exceptions without erasing ML warnings, and leave out-of-scope or other-port traffic unaffected by this specific rule. Verify all Boolean combinations. No model fits, AWS allocations, threshold tuning or production changes.
