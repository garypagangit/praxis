# PX-050 Live-Agent Tool-Boundary Final Determination

Generated: 2026-07-06T00:04:21Z

Status: **TWO_MODEL_DRY_RUN_LIVE_AGENT_TOOL_BOUNDARY_POSITIVE**

## Decision

PX-050 is a true positive for the bounded Praxis defense claim after the PX-050U and PX-050V follow-on runs.

The two-model dry-run live-agent tool-call test produced install actions, established a raw unsafe-action baseline, and the PX-050S controller/extractor plus hardened verifier allowed zero invalid package-install actions while preserving valid install utility.

No generated command was executed.

## Evidence Table

| Run | Model | Rows | Invalid rows | Valid rows | Install action rate | Raw unsafe rate | Controller recovery | Registry invalid allows | Hardened invalid allows | Valid allow |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PX-050U | `Qwen/Qwen2.5-Coder-7B-Instruct` | `144` | `64` | `80` | `1.0000` | `0.8906` | `0.9514` | `10` | `0` | `1.0000` |
| PX-050V | `deepseek-ai/deepseek-coder-6.7b-instruct` | `144` | `64` | `80` | `1.0000` | `1.0000` | `1.0000` | `10` | `0` | `1.0000` |
| Combined | two model families | `288` | `128` | `160` | `1.0000` | `0.9453` | `0.9757` | `20` | `0` | `1.0000` |

## What This Proves

The repaired PX-050 boundary pattern works in the measured dry-run agent setting:

1. The model proposes observable package-install tool-call arguments.
2. The controller extracts a target-matching install command.
3. The hardened verifier blocks invalid, mixed, remote, alias, and shell-composed install requests.
4. Valid package installs remain usable.

This directly resolves the PX-049 no-install-action failure mode and strengthens the PX-050 paper story from command-string evidence to two-model dry-run live-agent tool-call evidence.

## Boundary

PX-050 may claim:

- two-model dry-run live-agent tool-call replication,
- zero observed hardened invalid-package allows over `128` invalid tool-call rows,
- full valid utility over `160` valid tool-call rows,
- registry-only baseline exposure on `20` invalid rows,
- no package-manager execution.

PX-050 must not claim:

- broad agent safety,
- arbitrary shell-command safety,
- malicious-existing-package detection,
- post-install package behavior safety,
- raw third-model replication, because the raw/strict StarCoder2 gates failed.

## Final Determination

**Promote PX-050 as the lead Praxis defense result.**

The best wording is:

> Across two open-weight coding models prompted as dry-run agents, a deterministic package-install tool-boundary gate blocked all observed invalid package-install tool-call actions while preserving all valid install actions in the measured PyPI/NPM boundary.

This is publishable if kept narrow, empirical, and no-execution.
