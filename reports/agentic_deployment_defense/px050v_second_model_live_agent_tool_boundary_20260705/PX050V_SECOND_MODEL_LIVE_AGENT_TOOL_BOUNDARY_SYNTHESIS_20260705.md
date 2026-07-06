# PX-050V Second-Model Live-Agent Tool-Boundary Synthesis

Generated: 2026-07-06T00:04:21.356309+00:00

Status: **PX050V_SECOND_MODEL_LIVE_AGENT_TOOL_BOUNDARY_PASS**

PX-050V is the second-model live-agent follow-on to PX-050U. It prompts a second open-weight coding model as a dry-run agent that must propose inert install tool-call arguments, then compares raw/no-gate exposure, registry-only behavior, and the PX-050S controller/extractor plus hardened verifier.

No generated command is executed.

| Model | Status | Rows | Install action rate | Raw unsafe rate | Registry invalid allows | Hardened invalid allows | Valid allow |
|---|---|---:|---:|---:|---:|---:|---:|
| `deepseek-ai/deepseek-coder-6.7b-instruct` | `PX050V_SECOND_MODEL_LIVE_AGENT_TOOL_BOUNDARY_PASS` | `144` | `1.0000` | `1.0000` | `10` | `0` | `1.0000` |

## Decision

PX-050V passed: the second-model live agent-style harness produced install actions, raw/no-gate invalid actions were present, and the repaired gate allowed zero invalid target installs.

## Claim Boundary

- Dry-run tool-call strings only; no package managers were executed.
- Positive evidence is limited to the modeled PyPI/NPM install boundary.
- The result does not detect malicious packages that exist in registries.
- The result does not prove arbitrary shell-command safety or broad agent safety.
