# Room to improve CRAG or Ahlert

Reviewed September 18, 2026. Literature and proposal review only; no implementation, inference, or efficacy result. This supersedes any implication that adding a relevance check or version rule is itself a novel algorithm.

## Decision

There is a concrete improvement target: determining whether a proposed security investigation is feasible when the available description of the defender's systems is incomplete. The most plausible current contribution is an empirical method/evaluation study. Algorithmic novelty is not established.

This would extend the current CTI multiple-choice study into hunt-lead verification. Existing CTI gains and mismatch losses motivate the question but do not validate this new task or checker.

## Observed limitations

- [CRAG, sections 4.2-4.3](https://arxiv.org/html/2401.15884v3): evaluates question/document pairs individually and selects its Correct branch if any document exceeds the upper threshold. This decision does not itself establish joint support for every condition in a multi-part task. The complete pipeline includes further knowledge refinement; do not characterize CRAG as having no filtering.
- [Ahlert, sections II-D and IV](https://arxiv.org/html/2609.08790v1): restores unfiltered candidates if environment filtering would remove everything, citing incomplete inventories. Its grounding measure requires at least one mentioned entity to appear in the inventory. Its evaluation does not establish that every prerequisite of every proposed hunt is jointly satisfied. These are specific method/measurement limitations, not an independent reproduction of failure rates.
- [SURE-RAG, section VII-B](https://arxiv.org/html/2605.03534v2): identifies remaining limits in joint passage reasoning and long-form evidence coverage. Its supported/refuted/insufficient framework already covers generic uncertainty-aware verification.

## Proposed question

Can checking the linked requirements of a hunt, and resolving consequential unknowns about the environment, reduce infeasible recommendations without discarding useful investigations when inventory information is incomplete?

Illustrative example: a lead requires a Windows server, a specific logging facility, and retained logs for a specified period. Evidence that the company has a Windows server and collects logs somewhere does not establish that those logs exist for that server and period. Individually true facts may fail to support the proposed combination.

The candidate process records each necessary condition as supported, contradicted, or unknown, with source evidence and entity/time bindings. It checks the conditions together, then requests or looks up a missing fact when that fact can change the decision. Missing inventory data must not automatically mean the required resource is absent. The extracted requirements may themselves be wrong, so end-to-end evaluation must include extraction errors.

This process is a proposal assembled from known techniques. It is not a proven solution or a newly certified formal method.

## Closest prior work that prevents broad novelty claims

- [CF-RAG, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1c078897dc08d46091d0d361d9955c6b-Abstract-Conference.html): discriminative evidence selection through counterfactual questions.
- [CoRM-RAG, May 2026](https://arxiv.org/html/2605.01302v1): evidence utility critic, robustness training, and abstention. Its conclusion identifies multi-hop perturbation propagation as future work.
- [GPS, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1f49b7fbd7c7afc52c1db0d4ed1a338d-Abstract-Conference.html): conditional reasoning graphs and efficient clarification. Asking for missing prerequisites is not a new general technique.
- [HunterAgent, May 2026](https://arxiv.org/html/2605.29269v1): separates generated hypotheses from deterministic telemetry verification and handles missing evidence in attack-trace reconstruction. Independent checking and prerequisite enforcement are already established.
- [PAVE, March 2026, sections 3.2-3.3](https://arxiv.org/html/2603.20673v1): extracts claims while retaining conditions and exceptions, then scores support and missing conditions. Extracting prerequisites before checking them is not by itself new; this is another required comparator for the proposed joint-binding study.
- [Beyond RAG for CTI, April 2026](https://arxiv.org/html/2604.11419v1): examines unanswerable CTI questions and schema gaps. A generic CTI abstention benchmark would overlap.

## Discriminating experiment

Start from independently specified test environments with known assets, services, log availability, and retention periods. Expose controlled incomplete or stale descriptions to the system. Include present-but-undocumented resources, genuinely absent resources, and evidence whose required facts refer to different hosts or times. Hold out entire incident/source/environment families.

Compare the same generator and task under: published Ahlert behavior; a simple removal of its fallback; explicit prerequisite rules; a strong published sufficiency checker; and the candidate with targeted missing-fact recovery. If CRAG is included, use it as a retrieval component within the same task, not a raw comparison of unrelated QA and hunt-generation scores.

Measure independently whether recommended investigations can be executed and address the intended behavior, how many useful investigations survive, recovery of viable leads hidden by incomplete inventory, and total checking/lookup cost. Successful query execution alone does not establish a correct investigation. Preserve inconclusive cases and assess extraction mistakes.

The candidate must outperform simple fixes and strong prior methods at comparable useful coverage and cost. Reject an efficacy claim if its apparent gain comes only from rejecting more recommendations, having extra environment information, or fixing a trivial fallback. Reject an algorithm-novelty claim if the distinction is only a renamed combination of existing components.

## Current status

Room for improvement: supported by explicit published limitations. A precise follow-up question: identified. Better checker on our data: untested. Defensible new algorithm: not established. A positive, independently validated result could support an applied Praxis; academic eligibility and originality still require assessment of the actual contribution.
