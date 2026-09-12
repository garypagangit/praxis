# Empathy qualification result

Independent artifact audit: **PASS**. All 128 cells cover the same 64 validation IDs, balanced 32 per label.

Baseline and permanent social ablation both scored **32/64 (50%)**, equal to the constant-label baseline. Both predicted `empathy` on every item: empathy recall 100%, not-empathy recall 0%. There were 0 changed predictions, 0 correct-to-wrong changes, and 0 wrong-to-correct changes.

The preregistered qualification failed: baseline needed at least 39/64, a net advantage of two, and at least two answers harmed by ablation. This is a retained zero-harm null result. Do not promote this checkpoint/task configuration to the primary preservation benchmark or use held-out test performance to rescue it. No held-out test inference was run.

The null is not an inactive-ablation artifact: baseline had 292,177 social selections and ablation had zero. Likelihoods changed on 64/64 questions; maximum candidate log-likelihood change was 1.357750103. These routing counts include repeated candidate prefixes and do not represent independent observations. Baseline→ablation→baseline reset difference was 0.

Both candidates used identical context hashes; context/candidate token boundaries and shared-prefix scores agree. Per-token log probabilities sum to stored candidate scores with maximum absolute error 0. All cohort/manifest hashes, winners, correctness, route totals and zero-social-ablation checks passed. The run reports CPU float32, four threads, 259 candidate forwards and 357.1 seconds after loading.

This is a capability/measurement failure for the small checkpoint under the fixed three-demonstration likelihood adaptation. It does not establish that every social expert is useless, reject the entire brain-inspired idea, or reproduce a reported empathy accuracy. The labels are a binary proxy for authors' self-reported empathic concern; the prompt asks whether text expresses empathy. That construct mismatch and unresolved training overlap limit any publication claim. A larger model or different validated measurement would require a new prospective qualification, with this null preserved.
