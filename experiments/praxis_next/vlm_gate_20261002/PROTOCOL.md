# PX-098 — Visual Host Windows as an Additional Warning-Gate Member

Registered 2026-10-02. Development pilot on previously examined data; novelty unconfirmed.

## Question and hypotheses

Can a frozen Qwen2.5-VL-7B-Instruct member recover exfiltration warnings missed by every member of the existing gate, at an acceptable added alert cost?

1. Adding a warning with OR cannot remove an existing warning on the same evaluated units. Its false-alert count is at most the sum of member false-alert counts. These are set identities, not novel empirical findings or guarantees of operational usefulness.
2. The visual member recovers at least one exfiltration-positive host window missed by the original three-member gate. Repeat against the five-member gate; do not call one seed's misses ensemble-unrecoverable.
3. Image input provides better recovery at the same added benign-window workload than matched numeric text. A small pilot cannot establish this hypothesis; a larger frozen comparison is required.

## Bounded first phase

Use the existing UNRAVELED prepared release and original predictions. Recompute the claimed seed-8103 miss count, original-three gate misses, and full-five misses. Build one-hour windows per capture and host from completed flows, with twelve five-minute bins. Include both endpoints and orient bytes with respect to the displayed host. Use bytes out, bytes in, flow count, DNS-associated flow count and distinct peers. DNS flow count is a proxy, not a DNS query rate. No raw addresses, labels, signatures, stage names, capture identifiers or absolute dates in model inputs.

Windows are nonoverlapping UTC-hour bins, indexed by flow completion. A window is available only when it closes. Flow bytes are completion-accounted totals, not packet timestamps. Empty intervals are rendered as zero; incomplete capture coverage is a limitation. Do not interpolate across captures or split partitions. Select 16 nonempty test windows by SHA256 rank of an opaque capture/host/hour identifier, without labels. Add up to eight windows containing previously established full-gate misses as a separately reported diagnostic cohort. This enrichment cannot estimate prevalence, recall or workload for the population.

For each selected window run the same frozen question on image and numeric-text representations of identical five-minute aggregates. One response per representation, greedy decoding, at most 192 output tokens, JSON yes/no/insufficient plus a short reason. Invalid or insufficient outputs abstain and add no warning; report their count. Preserve original outputs. Initial cloud allocation has a 30-minute worker deadline, 40-minute stop watchdog, 45-minute outer bound and a $2 planning reserve (price must be rechecked). No paid model API, no model training. Run at most 48 PX-098 responses in this allocation; smaller completion is an operational finding.

## Evaluation and later expansion

Primary unit: host-hour, positive if it contains a completed exfiltration-labeled source flow; benign only if all incident flows are benign. Other attack windows are neither benign controls nor exfiltration positives. Existing gate window warning means any source-flow warning in that host-hour; also report destination-only traffic separately if evaluating it later. Report confusion counts, warning recall, benign-window false-positive rate, marginal warnings, added host-hour cases, abstentions, latency and GPU memory. A VLM warning arrives at window close plus inference latency. Any flow projection is retrospective coverage, never an early warning claim.

Larger efficacy evaluation requires a separate freeze: all eligible windows or a probability sample with known inclusion probabilities, matched-information numeric LightGBM fitted only on training windows, calibration-only threshold/workload choice, clustered uncertainty, episode coverage and case grouping. Working expansion screen: positive marginal episode coverage with no more than one percentage-point increase in benign-window FPR; publish full tradeoff and do not represent this research bound as SOC approval. AIT Wilson/Harrison require a source adapter and identical time/direction semantics before transfer. They are execution-disjoint but previously exposed.

No test-driven prompt search. A change creates a new version with a fresh freeze. Do not infer that pictures contain information absent from tabular data: the aggregation and representation effects must be separated. Model reasons are not evidence of true attacker intent.

## Foundation and overlap

- [Qwen2.5-VL technical report](https://arxiv.org/abs/2502.13923) and [official model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct): model capability, not security efficacy.
- [Visual Semantics of NetFlow: Zero-Shot DoS Attack Detection with Vision–Language Models](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7315138): search-indexed author abstract describes traffic images and matched text. Direct conceptual overlap; full text was inaccessible during registration, so novelty review remains incomplete.
- [Harnessing Vision-Language Models for Time Series Anomaly Detection](https://ojs.aaai.org/index.php/AAAI/article/view/39319), AAAI 2026: visual temporal anomaly detection is established.
- [Kittler et al., On Combining Classifiers](https://doi.org/10.1109/34.667881): classifier combination is established. PX-092 through PX-097 provide our local warning-loss and workload evidence.

Potential contribution: a controlled residual-warning recovery study, including failed repairs and actual workload. No claim of first visual intrusion detector.
