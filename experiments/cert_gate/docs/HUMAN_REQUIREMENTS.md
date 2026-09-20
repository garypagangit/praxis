# Completing the outstanding human and data work

**Prepared; no review or author correspondence completed.** These study requirements come from the supplied proposal and [registration](../REGISTRATION.json). They do not prevent the completed software and artifact checks.

## 1. Resolve data availability first

SecAlertBench's processed records omit the full raw evidence, capture time, severity and incident context required by this gate. Label review cannot supply missing fields. Its 2,496 attack-labeled rows also do not establish 2,496 independent attack episodes.

Use this draft through a contact channel listed by the [authors](https://github.com/Dxsssu/SecAlertBench), or with an organization authorized to supply equivalent deidentified SOC data. **This request has not been sent.** No contact address has been invented.

> Subject: Research access and provenance questions for SecAlertBench
>
> I am evaluating offline security-alert triage for a doctoral praxis. Could you clarify the research-use terms and whether an authorized deidentified release can include:
>
> 1. Capture times and enterprise/incident/campaign groups, including how related or duplicate attack alerts were identified;
> 2. Trusted severity/rule identifiers and references joining alerts to independent raw events;
> 3. Incident membership as known at decision time, distinguishing unclustered from unavailable context;
> 4. Labeling guidance and sufficient evidence to review a blinded sample?
>
> The study will not suppress live alerts. It needs separate fitting, model-selection, risk-calibration and evaluation data. Its 1% attack-suppression target at 95% calibration confidence requires at least 299 independent attack calibration units for one nontrivial certificate, plus separate evaluation data. Repeated alerts from one attack would not count as independent attacks. If some fields cannot be released, a statement of those limitations would help us scope the study accurately.

The [CORTEX paper](https://arxiv.org/abs/2510.00311) is another source to ask about using these questions; also request exact actionable-label and FPR definitions. We did not locate an actual dataset download and do not assume access will be granted.

**If supported data are available:** document terms/provenance, reconstruct fields without inventing values, finish G0, and register the exact model-specific study. **If not:** narrow or stop the full-gate claim. Treating missing context as safe, copying processed rows as raw evidence, or repeating one capture cannot resolve G0. Any exploratory score-only study needs an explicitly amended scope and weaker claims.

## 2. Complete the prepared review when useful

Final local packet: [Open the 50-alert review form](C:/w/cert_gate_data_20260920/human_review_v2/REVIEW.html).

1. Use a reviewer with relevant SOC/security-analysis experience. Open only `human_review_v2/REVIEW.html`; do not give the reviewer `ANSWER_KEY.json`.
2. Enter a name or study ID and experience. For every alert choose **Attack**, **Non-attack**, or **Unable to verify**, with the visible supporting facts or missing evidence.
3. Click **Download review responses**. The page sends nothing to a server. Complete it in one sitting; it does not save drafts automatically.
4. Save the downloaded JSON in the private review directory and score the actual submission:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' experiments/cert_gate/score_review.py --answer-key 'C:/w/cert_gate_data_20260920/human_review_v2/ANSWER_KEY.json' --responses 'C:/w/cert_gate_data_20260920/human_review_v2/soc_label_review_responses.json' --output 'C:/w/cert_gate_data_20260920/human_review_v2/SCORED_REVIEW.json'
```

The proposal requires point agreement of at least **45/50**. Unable-to-verify cases remain in the denominator and do not count as agreement. The tool also reports an uncertainty interval. Passing the point threshold does not establish population agreement of at least 90%, authenticate the reviewer, prove independent ground truth, or release other G0 requirements.

V2 hides the released label and derived attack/kill-chain annotations. Rule names and recorded request/response evidence remain visible. Missing full logs can make a label unverifiable; record that result instead of replacing it with AI assessment or fabricated initials. V1 is retained only for audit history. **No human result exists for either packet.**

## 3. Review the contribution before a larger run

Give an adviser the [literature review](LITERATURE_REVIEW.md), [startup report](STARTUP_REPORT.md), and [statistical contract](STATISTICAL_CONTRACT.md). The open question is whether supported evidence predicates improve useful automation or resilience beyond an existing risk-controlled score-only gate at comparable utility. Generic certified closure, a Qwen substitution, and the standard PAC bound are established ideas. No adviser approval or demonstrated novelty is being claimed.
