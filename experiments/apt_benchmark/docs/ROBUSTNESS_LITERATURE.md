# Literature basis: attack-step recognition with missing or delayed logs

Checked September 20, 2026. This is a bounded primary-source review and design audit, not a claim that a novel method has been established. Publication date, collection date, and artifact release date are different facts.

## Research question

Can a detector retain useful recognition of dangerous attack steps when some supporting observations disappear or arrive late, at a declared decision deadline and alert burden?

The immediate experiments should establish where information is lost, whether ordinary context and robust-training controls help, and which failures remain. An architecture change or a positive development result alone does not establish a praxis contribution.

## Seven nearest primary sources

| Source and verified status | What it already establishes | Consequence for this experiment |
|---|---|---|
| [Landauer et al., CAM-LDS, International Journal of Information Security, August 26, 2026](https://doi.org/10.1007/s10207-026-01318-x) | A recent Linux attack-manifestation dataset with multiple host/network sources and technique annotations. The published evaluation already includes GPT-5.5, GPT-5.2, Llama 4, Qwen3-32B, and Ministral. | A useful independent scenario source; applying Qwen or another LLM to its logs is already covered. Our potential distinction concerns evidence available by a deadline and controlled information loss. |
| [Kilian et al., CasinoLimit, RAID 2025](https://doi.org/10.1109/RAID67961.2025.00039); [author project](https://casinolimit.inria.fr/) | System and network traces from 114 executions of one pentest challenge, with shell-session-based semi-automatic technique labeling and expert review. | Supports execution-held-out technique recognition. Repeated challenge structure limits generalization claims; the number of executions is not the number of distinct attack families. |
| [Phan and Bauschert, StageFinder, arXiv v2, May 5, 2026](https://arxiv.org/abs/2603.07560v2) | Graph encoders plus LSTM history for attack-stage estimation. Authors report acceptance to IEEE GLOBECOM 2026; a separate publisher proceedings entry was not verified here. | Graph-plus-history stage recognition is not a novel claim. Compare equal observable histories before attributing a gain to architecture. |
| [Kimm, Mishra, and Sekar, IMPROV, PRISM 2026](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) | Addresses missing/spurious provenance links and out-of-order events by adding operating-system context during collection; DOI 10.14722/prism.2026.23023. | Generic missing-context repair and ordering are established problems. A frozen-log experiment cannot claim to reproduce collection-time recovery or infer unavailable facts as observed evidence. |
| [Bilot et al., Sometimes Simpler is Better, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) | Unified evaluation of eight provenance IDS designs identifies practical shortcomings and shows strong performance from a simpler neural baseline. | Retain a strong simple classifier, common calibration, resource measurements, and useful alarm metrics. Complexity is not evidence of contribution. |
| [Reza, Prater-Bennette, and Asif, Robust Multimodal Learning With Missing Modalities via Parameter-Efficient Adaptation, IEEE TPAMI 47(2), 742-754, 2025; online 2024](https://doi.org/10.1109/TPAMI.2024.3476487); [author manuscript](https://arxiv.org/abs/2310.03986) | Missing-input adaptation and comparisons against dedicated available-modality models are established beyond cybersecurity. | Ordinary channel-dropout training and available-source specialist controls are baselines, not a newly invented mechanism. This paper is not evidence of APT performance. |
| [MirGuard, author preprint, August 2025](https://arxiv.org/html/2508.10639v1) | Uses provenance node, edge, and feature augmentation with contrastive learning against graph-manipulation attacks. A peer-reviewed venue was not verified. | Graph augmentation for robust intrusion detection is prior art. Sensor loss/delay differs from adversarial graph manipulation, but that difference alone does not prove novelty. |

The existing [next-experiment decision](NEXT_EXPERIMENT.md) also identifies TREC (CCS 2024) as direct prior work on tactic/technique recognition. Reported F1 values from those papers cannot be compared directly with our scores without matched targets, data, and prediction units.

## Dataset priority and access

### CAM-LDS: strongest next scenario-diversity check

[Pinned public artifact: Zenodo 18861762](https://zenodo.org/records/18861762). Its metadata describes seven scenario families and 34 variants, 81 techniques and 13 tactics, with raw logs across 18 sources. It provides `manifestations_raw.zip` (535.9 MB), `manifestations_filtered.zip` (213.8 MB), and complete per-scenario archives; the listed collection is 7.4 GB. The dataset has idle-system activity but no simulated ordinary-user workload. Technique/sequence exports can duplicate the same records across labels.

Prefer per-scenario raw logs for causal replay. Keep families together across splits; assess technique support before freezing targets. The smaller manifestations archive can support initial parsing, but attack-step directory names and attacker execution logs belong to the evaluator, never the classifier. Do not concatenate technique exports into independent examples. [Artifact organization and ground-truth route](https://zenodo.org/records/18861762).

The published paper uses temporally extracted attack steps and notes that delayed events can be mislabeled across step boundaries. It also inserts pauses between actions. Therefore actual collection delay is not directly measured by our later artificial delay injection. Missingness experiments must retain the author label interpretation and disclose this limitation. [Publisher limitations](https://doi.org/10.1007/s10207-026-01318-x).

### CasinoLimit: strongest immediate execution-variation check

[Pinned artifact: Zenodo 17256954](https://zenodo.org/records/17256954). Source and label acquisition are handled by the dataset adapter. Freeze complete execution groups; where repeat-player identity is available, group those executions together. Preserve original syscall/event identifiers only for event reconstruction and joins, never as memorized actor features. Process caches containing later aggregates must not become earlier prediction inputs.

CasinoLimit is appropriate for distinguishing labeled techniques within offensive traces. Other attack techniques are useful negatives for a particular technique, but they are not benign traffic. Neither it nor CAM-LDS alone demonstrates acceptable false-alert rates in an ordinary working enterprise. [Author dataset and challenge description](https://casinolimit.inria.fr/challenge.html).

### AIT-LDS: development control

Use already qualified AIT source logs to verify the pipeline and compare against the earlier representation. Its underlying capture is from 2022; new packaging does not make it a new attack capture. Previously inspected test runs are development evidence. Do not pool AIT, CasinoLimit, and CAM-LDS scores as though their labels and prediction units were identical.

## Three executable questions and one confirmation gate

These are design requirements; the operative protocol and run receipts determine which arms actually ran.

| Experiment | Matched comparisons | Required interpretation |
|---|---|---|
| 1. Does earlier activity supply missing meaning? | Meaning-preserving event-only classifier versus the same classifier with strictly earlier process/session context; the operative first protocol fixes a 120-second history view. | A gain establishes usefulness of context, not a novel architecture. Recompute the event-level baseline; do not compare directly to the old line-level F1. |
| 2. Can ordinary training reduce the damage? | Clean-trained context model versus identical model trained with record/channel loss; include observed-source indicators as an ablation. Test independent random record loss, named record-type removal, contiguous outages, and delay separately. | Report clean performance and absolute degraded performance, not only percentage retained. A weak clean model can appear artificially robust. |
| 3. Does waiting help enough to justify its cost? | Immediate partial-evidence decisions versus bounded buffering at the same declared evaluation deadlines. | A later decision may recover evidence at a latency cost. It is not a same-time gain; count deadline misses and unavailable evidence. |
| Confirmation gate | Freeze the useful mechanism and validate on execution/family groups not used to select it, preferably qualified CAM-LDS scenarios. | A positive pilot warrants confirmation; a new method still requires a precise contribution and appropriate nearest-method comparisons. |

## Design checks that can invalidate the result

1. **Freeze the target roster.** Removing an observation cannot remove its target from recall denominators. A hidden target can receive a no-evidence/abstain output; it remains a miss for timely recognition unless a valid alternative observation identifies it. Report coverage separately.
2. **Separate event time and availability time.** A delayed record is eligible only when its availability time is at or before the decision deadline. Reassembled events cannot contain later fragments. Test that adding future observations leaves previous predictions unchanged.
3. **Do not leak evaluator identity.** A hidden target's known process/session identifier cannot be passed to the model to select otherwise unrelated context. Fixed windows or an actually observed event must provide a deployable query unit.
4. **Distinguish source inactivity from a known outage.** Observed-source counts are valid inputs. An injected deletion mask is an oracle unless a real heartbeat/configuration would expose that state. Name any oracle arm explicitly and keep it out of deployment claims.
5. **Make perturbations paired and label-blind.** Use the same frozen loss schedules for all methods. Burst start times must not depend on attack labels. Describe record-type removal separately from whole-sensor outages; they remove different evidence.
6. **Hold thresholds fixed.** Calibrate with separate development/calibration groups. Do not retune per test corruption to manufacture a stable alert rate. A separately calibrated degraded-policy arm must be disclosed and trained without test labels.
7. **Count executions, not fragments.** Report per-technique F1, precision, recall, continuous-score AP/ROC-AUC where defined, support per execution, deadline recall, no-evidence coverage, and flags per negative-labeled event. Bootstrap execution groups for paired uncertainty; perturbation seeds are not independent attack campaigns.
8. **Keep the claim attainable.** Alarm burden on author-unannotated AIT rows and other-technique CasinoLimit rows is not independently adjudicated benign FPR. Rare/unsupported techniques require explicit reporting, not omission from a favorable macro average.

## Decision boundary

A useful positive result is better recognition under specified losses or delays without an unacceptable increase in incorrect step assignments, delay, or clean-data error. A null result is also informative: it can show that the absent evidence is not recoverable from remaining observations. Neither outcome justifies inventing observations, treating confidence as proof, or declaring novelty before reviewing the exact successful mechanism.
