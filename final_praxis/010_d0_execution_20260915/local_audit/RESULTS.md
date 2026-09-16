# D0 mechanism screen: audited results

**Audit: PASS. Decision: HOLD_CROSS_CHANNEL_HARM_SCALE_UP.**

Qualifying raw-joint variants: none.
Clean-repeat maximum: 0; numerical floor: 1e-05.
Independent maximum spillover: 0.

| Pipeline | Clean off-channel MAE | Change from raw joint |
|---|---:|---:|
| joint_native3 | 0.491926097 | 0 |
| independent_native3 | 0.483921733 | -0.00800436356 |
| joint_channel0_clip_minus3_plus3 | 0.491074874 | -0.000851223245 |
| joint_channel0_causal_sma5 | 0.486856572 | -0.00506952483 |

| Pipeline | Variant | Contexts with spillover >=0.05 and above floor | Mean error inflation (all 32) |
|---|---|---:|---:|
| joint_native3 | step1 | 6 | -0.00794224788 |
| joint_native3 | step3 | 8 | -0.00608382017 |
| joint_native3 | step6 | 11 | -0.00708394773 |
| joint_native3 | ramp1 | 22 | -0.0178157474 |
| joint_native3 | ramp3 | 23 | -0.0134136963 |
| joint_native3 | ramp6 | 23 | -0.00898588793 |
| independent_native3 | step1 | 0 | 0 |
| independent_native3 | step3 | 0 | 0 |
| independent_native3 | step6 | 0 | 0 |
| independent_native3 | ramp1 | 0 | 0 |
| independent_native3 | ramp3 | 0 | 0 |
| independent_native3 | ramp6 | 0 | 0 |
| joint_channel0_clip_minus3_plus3 | step1 | 5 | -0.00624304921 |
| joint_channel0_clip_minus3_plus3 | step3 | 14 | -0.0049966802 |
| joint_channel0_clip_minus3_plus3 | step6 | 22 | 0.00146780361 |
| joint_channel0_clip_minus3_plus3 | ramp1 | 23 | -0.0154266262 |
| joint_channel0_clip_minus3_plus3 | ramp3 | 19 | -0.00101895698 |
| joint_channel0_clip_minus3_plus3 | ramp6 | 17 | 0.000186564665 |
| joint_channel0_causal_sma5 | step1 | 7 | 0.00678035316 |
| joint_channel0_causal_sma5 | step3 | 12 | -0.000733038192 |
| joint_channel0_causal_sma5 | step6 | 14 | 0.00096388462 |
| joint_channel0_causal_sma5 | ramp1 | 8 | -0.0107049533 |
| joint_channel0_causal_sma5 | ramp3 | 20 | -0.00240130928 |
| joint_channel0_causal_sma5 | ramp6 | 19 | 0.00444540023 |

Adequate simple controls: none.

Accounting: 1024 evaluations; 1536 native forward calls; 1536 tensor batch sequences; 3072 tensor channel sequences.

## Scope

This is a descriptive mechanism screen using 32 overlapping origins from one previously inspected public series with semisynthetic channels. It does not establish independent incident replication, a novel defense, attack detection, persistent retention, or recovery. A positive mechanism result only permits a separately frozen D1 design.
