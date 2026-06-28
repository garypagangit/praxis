# PX-009 AI Supply-Chain LoRA Multi-Strength Trace Gate

Generated: 2026-06-28T20:51:45.114519+00:00

Status: **FAIL - TRACE SIGNAL NOT USEFUL AT 5PCT**

## Scope

This gate reruns PX-009 as the registered multi-strength cloud test rather than another proxy. It trained `18` short LoRA conditions from `9` paired clean/poison specs across three seeds and three poison strengths.

| Field | Value |
|---|---:|
| Model | `meta-llama/Llama-3.2-3B-Instruct` |
| Paired run specs | `9` |
| Condition trainings | `18` |
| Max steps per condition | `150` |
| Trace rows | `2700` |
| AWS instance | `i-07178e293e8df2a60` |
| AWS final state | `stopped` |

## Promotion Checks

| Check | Pass |
|---|---:|
| 5% trace classifier ROC-AUC >= `0.7000` | `False` |
| 5% trace classifier AP >= `0.7000` | `False` |
| 5% cross-seed sign stability | `True` |
| 5% trigger behavior separation | `False` |
| Clean task degradation reported | `True` |

## Strength Results

| Poison strength | ROC-AUC | AP | Trace rows | Stable features | Trigger delta | Validation-loss delta |
|---:|---:|---:|---:|---:|---:|---:|
| `0.01` | `0.5020` | `0.5061` | `900` | `6` | `0.0000` | `0.0004` |
| `0.05` | `0.5266` | `0.5415` | `900` | `6` | `0.0000` | `0.1039` |
| `0.10` | `0.5542` | `0.5684` | `900` | `6` | `0.0000` | `0.1516` |

## Decision

Archive PX-009 as a negative for this dissertation cycle. The trace shifts are directionally stable, but the 5% poison condition does not approach the pre-registered ROC-AUC/AP threshold of `0.7000`, and trigger behavior separation is `0.0000` across all strengths and seeds.

This is useful evidence, not a publishable positive claim. The current LoRA training-trace features are not enough to identify the controlled poison condition reliably.

## Evidence

- Run report: `runs/ai-supply-chain-multistrength-lora-20260628/report.md`
- Run summary: `runs/ai-supply-chain-multistrength-lora-20260628/summary.json`
- Full trace rows: generated as `runs/ai-supply-chain-multistrength-lora-20260628/provenance_traces.jsonl` (`2700` rows, about 56 MB); summarized in the committed run report and summary JSON.
- Cloud runner: `cloud_jobs/ai_supply_chain_multistrength_20260628/run_multistrength_lora_cloud.py`
- Launcher: `cloud_jobs/ai_supply_chain_multistrength_20260628/run_on_instance.sh`

## Claim Boundary

This result does not prove that training-provenance signals are impossible. It closes this PX-009 formulation: short LoRA trace summaries over the current controlled-poison construction are not useful enough at 5% poison to support a Praxis claim.
