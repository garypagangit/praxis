# PX-009 AI Supply-Chain LoRA Multi-Strength Trace Gate

Generated: 2026-06-28T20:51:45.114519+00:00

Status: **FAIL - TRACE SIGNAL NOT USEFUL AT 5PCT**

## Scope

- Model: `meta-llama/Llama-3.2-3B-Instruct`
- Paired run specs: `9`
- Condition trainings: `18`
- Max steps per condition: `150`
- Trace rows: `2700`

## Promotion checks

| Check | Pass |
|---|---:|
| `five_pct_trace_classifier_roc_auc` | `False` |
| `five_pct_trace_classifier_average_precision` | `False` |
| `five_pct_cross_seed_sign_stability` | `True` |
| `five_pct_trigger_behavior_separation` | `False` |
| `clean_task_degradation_reported` | `True` |

## Strength results

| Poison strength | ROC-AUC | AP | Trace rows | Stable features | Trigger delta | Validation-loss delta |
|---:|---:|---:|---:|---:|---:|---:|
| `0.01` | `0.5020` | `0.5061` | `900` | `6` | `0.0000` | `0.0004` |
| `0.05` | `0.5266` | `0.5415` | `900` | `6` | `0.0000` | `0.1039` |
| `0.10` | `0.5542` | `0.5684` | `900` | `6` | `0.0000` | `0.1516` |

## Condition summary

| Run | Condition | Mean loss | Mean grad norm | Mean update norm | Final val loss | Final trigger success |
|---|---|---:|---:|---:|---:|---:|
| `seed_41_01pct` | `clean` | `2.5630` | `0.2052` | `0.2499` | `1.9881` | `0.0000` |
| `seed_41_01pct` | `poison` | `2.5683` | `0.2059` | `0.2500` | `1.9892` | `0.0000` |
| `seed_41_05pct` | `clean` | `2.5630` | `0.2052` | `0.2499` | `1.9881` | `0.0000` |
| `seed_41_05pct` | `poison` | `2.6141` | `0.2060` | `0.2498` | `1.9891` | `0.0000` |
| `seed_41_10pct` | `clean` | `2.5630` | `0.2052` | `0.2499` | `1.9881` | `0.0000` |
| `seed_41_10pct` | `poison` | `2.6656` | `0.2097` | `0.2495` | `1.9888` | `0.0000` |
| `seed_42_01pct` | `clean` | `2.5356` | `0.1922` | `0.2519` | `1.9842` | `0.0000` |
| `seed_42_01pct` | `poison` | `2.5458` | `0.1935` | `0.2519` | `1.9845` | `0.0000` |
| `seed_42_05pct` | `clean` | `2.5355` | `0.1922` | `0.2519` | `1.9842` | `0.0000` |
| `seed_42_05pct` | `poison` | `2.5738` | `0.1951` | `0.2519` | `2.1139` | `0.0000` |
| `seed_42_10pct` | `clean` | `2.5356` | `0.1921` | `0.2519` | `1.9843` | `0.0000` |
| `seed_42_10pct` | `poison` | `2.6154` | `0.1962` | `0.2519` | `2.3654` | `0.0000` |
| `seed_43_01pct` | `clean` | `2.5680` | `0.1937` | `0.2585` | `1.9486` | `0.0000` |
| `seed_43_01pct` | `poison` | `2.5748` | `0.1937` | `0.2585` | `1.9485` | `0.0000` |
| `seed_43_05pct` | `clean` | `2.5680` | `0.1936` | `0.2585` | `1.9485` | `0.0000` |
| `seed_43_05pct` | `poison` | `2.6201` | `0.1973` | `0.2585` | `2.1295` | `0.0000` |
| `seed_43_10pct` | `clean` | `2.5680` | `0.1935` | `0.2586` | `1.9484` | `0.0000` |
| `seed_43_10pct` | `poison` | `2.6667` | `0.1964` | `0.2560` | `2.0214` | `0.0000` |

## Claim boundary

This gate tests whether short LoRA training traces separate clean and controlled-poison conditions at 5 percent poison across three seeds. A pass would support a bounded training-trace provenance claim; a fail means this PX-009 formulation should be archived for this dissertation cycle.
