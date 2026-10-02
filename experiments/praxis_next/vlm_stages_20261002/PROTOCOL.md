# PX-099 — Visual Reconstruction of APT Stages and Transitions

Registered 2026-10-02. Feasibility study; possible separate Praxis, not yet a qualified thesis.

## Question

Can a frozen VLM reconstruct source-supported stages and their timing from host-by-time traffic panels more accurately than matched numeric text and a simple temporal baseline?

## First phase

Reuse PX-098's label-free five-minute aggregates. Render a capture timeline with separate panels for bytes out/in, flow count, DNS-associated flows and distinct peers, with opaque host identifiers. Start with the first two test captures in source order and at most eight hosts per page, ordered by total flow count, with opaque-hash tie breaks, without attack labels. Record coverage and excluded hosts. No stage colors, annotations or raw identities in inputs. Do not describe capture slices as a whole-campaign result.

Qualify author labels before scoring. The existing prepared data collapses reconnaissance, foothold and cover-up into other attack, so it cannot establish full kill-chain reconstruction. Initial smoke outputs can use benign, other attack, movement and exfiltration only, and must be labeled coarse-stage feasibility. Recover native labels through verified capture/source-row mapping before any full-stage experiment. Keep simultaneous stages as sets; do not force a universal kill-chain order or invent transitions during gaps.

Initial cloud inference: at most two timeline images plus their matched numeric representations, the same pinned Qwen2.5-VL model as PX-098, greedy decoding, at most 512 output tokens. Request host ID, five-minute bin interval, a supported coarse stage and reason; permit insufficient evidence. Validate host/time bounds and schema. Generated intervals are unverified until source alignment and scoring pass.

## Hypotheses for a later frozen evaluation

1. Images improve macro stage F1 over matched text on supported host-time cells.
2. Images improve transition precision/recall over a persistence baseline, matching the same host and ordered stage pair within one five-minute bin, one-to-one. Multiple matches cannot inflate recall.
3. The direction persists on a second qualified execution without changing prompts or stage mapping.

Report per-stage support, multilabel precision/recall/F1, transition precision/recall/F1, timing error, unsupported stage assertions, abstentions, token count and runtime. Score only supported labels; explicitly report unevaluable stages. Large campaigns need paginated timelines and a coverage audit before model comparison. Freeze label mapping, pagination, scoring and baselines before efficacy inference. Bootstrap executions/episodes when enough independent units exist; a handful of pages does not justify significance claims.

Full timelines are retrospective reconstruction and contain future information relative to intermediate bins. Online warning claims require a separately evaluated causal-prefix experiment. Native flow labels do not independently establish attacker intent or incident boundaries.

## Foundation and novelty boundary

[MM-AttacKG](https://arxiv.org/abs/2506.16968) constructs attack graphs from text and images in threat-intelligence reports. It is related but does not, by itself, establish performance on our label-free traffic timelines. [VLM4TS](https://ojs.aaai.org/index.php/AAAI/article/view/39319) and [Visual Semantics of NetFlow](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7315138) overlap with the visual representation idea. A full literature comparison remains open.

Proceed to a Praxis proposal only if native stage labels, temporal alignment, baseline comparison and transfer are practical. Until then PX-098 is the simpler candidate.
