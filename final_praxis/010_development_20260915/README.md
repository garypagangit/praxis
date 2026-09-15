# What happens next

Internal AI-assisted research planning, September 15, 2026 UTC. No new model run or dataset analysis was performed for this handoff.

**Primary work: develop CTI's completed empirical contribution. Next experimental work: a small 010 mechanism screen. Keep 008 as the completed alternative and hold 009 scale-up.**

The [CTI next actions](CTI_NEXT_ACTIONS.md) identify what the author should read and understand, and what remains unresolved about the applied contribution. Automated verification supports the evidence; it cannot supply academic approval or the author's own research argument.

For 010, the next question is simple: **can corrupting one sensor's history make the model predict the other, unchanged sensors incorrectly?** If that effect is negligible, there is little reason to build a defense around it. If simple clipping or separate forecasts solve it, a more elaborate method needs a different justification.

The [D0 mechanism-screen protocol](D0_PROTOCOL.md) fixes the public-data base, transformations, comparisons, measurements and stopping criteria. Its machine-readable companion is [D0_SPEC.json](D0_SPEC.json). This is a prospective development plan, not a completed experiment or a frozen executable runtime. Implementation, source-bound controls and a separate runtime freeze remain required before any GPU processing.

Two findings narrowed this plan:

- [GITCO](https://arxiv.org/html/2606.05332v1) already gates, routes and smooths harmful input context in TimesFM 2.5. Generic context cleaning is insufficient as the proposed novelty.
- Our completed native TimesFM 3 run used a joint three-channel input with variate attention. TimesFM 2.5 used independent channel forecasts. The three-channel shift in qualification did not isolate influence from one channel to another. [Pinned worker](https://github.com/garypagangit/praxis/blob/cdf59507b588972b9a0f6879daa1184eadcf08e6/final_praxis/010_attack_aware_forecasting/code/gpu_qualification.py), [pinned TimesFM source](https://github.com/google-research/timesfm/tree/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch).

The protocol uses the already examined public NAB/TSB-AD series from the qualified adaptive-calibration example. Its three-channel construction is deliberately semisynthetic. A later cyber claim still requires natural multivariate telemetry and defensible trust assumptions. HAI remains outside this next screen; its prior timestamp-access deviation remains part of the record.

The [completed qualification](https://github.com/garypagangit/praxis/tree/e059f7017bd24c0caa12f69defa8137c96d2471c/final_praxis/qualification_20260914) and original results are preserved. The prospective screen has a 30-minute host cap and a $10 total reserve, conditional on its technical launch checks. No AWS resources were started to prepare this plan.

[Plan review](PLAN_REVIEW.json) records two independent design reviews and their resolved clarifications. Run `python verify_plan.py` to check the sealed files, local links, origins and evaluation accounting. Its PASS applies to the plan; it does not release an unfrozen worker or establish a scientific result.
