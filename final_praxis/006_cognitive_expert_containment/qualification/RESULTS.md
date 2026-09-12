# Public checkpoint qualification result —12September2026

Frozen run `fp006-20260912-11227b8`, AWS CPU, completed08:30:39UTC. Process142seconds, no model API calls or training. Source commit11227b852c819cafa37b937a18e6a7658565382d; protocolSHA63a162841824fb65c080adbd3cdeeba206eb9b9bf15063d29d74ee13ddb5e02f. Full source, environment, loading diagnostics, generated answers and routing receipts are archived under the campaign S3 run prefix.

The pinned public checkpoint loaded with no missing, unexpected or mismatched learned tensors. Finite logits and repeated forward passes passed; exact repeat and ablation-reset maximum difference were0. Eager/SDPA maximum logit difference was2.10e-5; cached/full-prefix differences were1.38e-5 and1.43e-5. Social-ablation routing assertions passed. This qualifies the documented CPU adaptation and intervention plumbing, not paper-score reproduction.

**Capability gate did not pass.** Across eight questions in two conditions, all16 responses lacked the required terminal final-answer format;15hit the128-token cap. There were0correct and0validly wrong baseline answers. Thus neither preservation nor recovery is estimable. This is a generation-budget/formatting floor, not evidence that containment helps or fails. The small checkpoint is not yet a suitable basis for a correctness-preservation experiment under this configuration.

Preserve this result unchanged. Review the paper's actual evaluation protocol before a separately preregistered longer-budget or task-matched feasibility run. Do not count malformed outputs as ordinary wrong answers, select easier questions from observed results, or describe this ablation as a novel defense.
