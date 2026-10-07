# Praxis direction after the first exploration batch

**Leading candidate: determine when passive AI-agent fingerprinting has enough reliable evidence to support an attribution.** Develop the environment and incomplete-log studies together, with unknown-family rejection as a required limitation. Keep recovery features as an incremental experiment. The human-versus-AI typo idea has not earned a detector-success claim.

The figures below use the final primal-solver numerical recheck. The original solver results are retained for comparison; see [numerical correction](SOLVER_CORRECTION.txt) and [score comparison](evidence/SOLVER_COMPARISON.json).

Suggested working title:

> Evidence Requirements for Reliable Fingerprinting of AI Cyber Operators Under Environmental Change and Incomplete Logs

## What the experiments support

The four-family classifier has strong conditional performance on the existing Honey corpus. Command-only macro F1 averages 96.93% over three ordinary session splits, 89.82% over five held-out environments, 94.16% over six held-out prompts, and 95.23% over three unseen prompt/environment cell sets. These are averages over dependent exploratory settings, not population confidence bounds.

Adding command-shape/correction and recovery features changes the environment average to 91.44%, a gain of 1.62 percentage points. The largest environment gain is 81.51% to 86.77%. Follow-up ablations show that both command-only shape features and output-conditioned recovery contribute; a pure edit/retry addition does not explain that gain. The effect is small or negative on some other settings. This supports an incremental feature study, not a new universally superior detector.

Observation mismatch is larger. In the ordinary seed17 test, changing to verbs-only logs drops the frozen lexical model from 96.65% to 46.93% macro F1; fitting on the same reduced view recovers 90.14%. Removing the middle half of commands gives 83.89% frozen and 88.92% after adaptation. These are synthetic log reductions. Exact reduced-observation overlap is separately audited; the unchanged-cohort primary results must be read alongside that audit.

The predefined second stress setting, the held-out backend-pool Cowrie environment, has 92.31% complete-log macro F1. Verbs-only observations score 35.88% frozen and 81.49% with adaptation. Removing the middle half gives 75.62% frozen and 79.21% adapted. The mismatch effect repeats, but adaptation does not fully recover the complete-log score. Only this one held-out environment received the full masking suite.

Fast known-family decisions are feasible on this selected corpus. The simple two-prefix agreement rule emits by command 10 on 1,740 of 1,995 qualifying test sessions, with 98.28% accuracy among emitted identities. It emits 1,563 at command 5, 177 at command 10 and abstains on 255. There are 30 wrong emitted identities and 41 disagreements with the later ten-command classifier. A later disagreement is not necessarily a correction. This evaluation excludes sessions shorter than ten commands and does not test unknown families within the sequential rule.

High closed-set accuracy does not resolve unfamiliar agents. At a 10th-percentile known-calibration margin threshold, the lexical model accepts 25.5% to 65.2% of held-out-family sessions as known identities in the ordinary split. Adding recovery raises the DeepSeek held-out acceptance from 65.2% to 77.2%. A confidence margin is not a reliable universal unknown detector.

## What did not work, or cannot yet be measured

The matched-task human-versus-AI combined model flags 26 of 27 AI test appearances but also 9 of 16 human sessions. Those 27 appearances represent 26 distinct AI sessions; the 16 human sessions come from five experts. The narrower edit/retry representation detects 10 of 27 AI appearances while falsely flagging 5 of 16 humans. No model meets the exploratory recall/false-label target.

The extraction problem matters as much as those scores: 15 of 16 eligible human records contain excluded prompt lines. This can remove actual typing mistakes and create apparent adjacency between actions that were not consecutive. The pilot cannot estimate true human typo prevalence or rule out better recovery of the existing recordings.

Timing is not ready for a binary classifier. All 11,803 eligible Honey sessions have increasing values in both timing fields, despite the release describing durations. The archived GAMBiT export has only coarse command timestamps and lacks comparable output-completion times. Combining those fields would risk detecting the recorder or runtime instead of the operator. No binary timing classifier was fitted.

## Why this is a candidate, not a novelty claim

TRACE already evaluates command fingerprints, early prefixes, argument removal and transfer. LIDAR already uses recovery behavior for active agent fingerprinting. Other work evaluates timing, unknown agents and behavioral attribution. The present methods are established baselines. The potential contribution is the specific empirical evidence about which observations preserve attribution and where confidently assigning an identity becomes unjustified.

The novelty review remains incomplete, particularly against the full Honey paper. Existing-data exploration can identify a promising direction; it cannot establish priority from a few successful scores. A complete Praxis also needs an explicit engineering artifact, documented requirements, and evaluation against those requirements.

## Recommended next work using existing data

1. Turn the logging study into an explicit observation contract: available command fields, missingness patterns, minimum evidence and a fallback when requirements are unmet. Evaluate that rule against fixed classifiers and generic abstention.
2. Test the chosen contract on an independently collected public corpus whose collector, tasks and model labels can be qualified. Do not label simulated missingness an external replication.
3. Improve terminal reconstruction on existing Lyptus recordings if retaining the human-versus-AI question. Validate command order and timing equivalence before training a richer binary detector; reconstruction alone does not guarantee enough independent human experts.
4. Complete the closest-prior-work comparison before claiming a novel method or rewriting the manuscript around a successful detector.

No new participants or generated attacks are required by these proposed next steps. Existing sources may still prove insufficient. APT attack detection from provenance logs is a separate fallback, not a result of the experiments here.
