# Praxis Defense Brief

## When Better APT Scores Hide Missed Attack Warnings

**The problem in plain language.** A security model can earn a better overall score while calling more attack records normal. A team using that score to choose a model could lose warnings it would have wanted an analyst to investigate.

## What this praxis contributes

This is a measurement study with reusable audit software. It shows how training composition and historical evidence affect three different outcomes: naming the right attack stage, raising some attack warning, and creating false alerts on normal traffic. It also tests whether proposed datasets can support the evaluation being claimed.

The metrics already exist. The contribution is the controlled evidence, the error-destination analysis and the executable audit of actual benchmark artifacts. The closest literature and the remaining overlap are addressed in the manuscript.

## Three results to explain first

| Result | Plain-language meaning |
|---|---|
| Time-mixed fitting: macro-F1 +0.0632 on identical evaluation rows | A substantial score improvement came from changing which time periods supplied training data, while keeping the model and class budgets fixed. |
| Clean acquisition comparison: F1 .7148 to .7379, exfiltration warnings 85.18% to 76.25% | A better headline score came with fewer exfiltration-labeled records receiving any attack label. The size varies greatly by fitting seed. |
| Chronological history: F1 .7365 to .7582, benign alerts 24.0 to 14.3 | History gave useful gains under earlier-to-later evaluation, alongside a smaller loss of exfiltration warnings. |

The data are one previously examined UNRAVELED campaign. Its movement labels describe author-annotated discovery, and the features describe completed flows. This paper does not claim verified theft, early forecasting or independent-campaign generalization.

## What the extra reviewer checks established

{{SENSITIVITY_BRIEF}}

{{REPRODUCTION_BRIEF}}

## Answers to the likely objections

**Is this just another classifier comparison?** The controlled temporal comparison holds the classifier, evaluation rows and class counts fixed. The question is how evaluation and evidence choices change what a score means.

**Did you invent warning recall?** No. It is ordinary attack recall conditioned on a stage. The contribution is the measured tradeoff and transparent evaluation, with existing prior work cited.

**Are 27 comparisons 27 independent experiments?** No. They reuse one campaign, models and sometimes equivalent outcomes. The paper reports the complete inventory; the new sensitivity appendix makes that dependence even more explicit.

**Why not claim four more dataset replications?** The audit found different limits: DAPT's stages cannot all straddle one cutoff; SCVIC's physical chronology is unresolved; DSRL derives from DAPT; no qualified S-DAPT release was acquired. Those are source-qualification results, not four detector tests.

**What is the practical deliverable?** A working procedure and code that check source support, compare the same records, separate wrong-stage warnings from missed warnings, and report benign workload and uncertainty.

**What remains for a broader claim?** Independent repeated executions with reliable labels, event times and legitimate-background activity. Current candidate releases do not remove those requirements merely by adding more files.

## Review decision requested

Assess whether the bounded measurement contribution is sufficient for the intended praxis, and whether independent-execution replication is required for the institution or target venue. The complete paper, source-linked evidence, sensitivity results and reproduction receipts accompany this brief. This is a request for substantive human review, not a record that approval has occurred.
