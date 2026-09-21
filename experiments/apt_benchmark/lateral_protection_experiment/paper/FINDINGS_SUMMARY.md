# What the completed experiments actually found

**Yes: the work shows measured improvements that can support an applied praxis.** The contribution is to explain the benefits and detection costs of training and alert choices. It has not established a new algorithm or a production protection guarantee.

## 1. More examples of harmless traffic made the detector much quieter

In the earlier ten-paired-seed comparison, increasing benign fitting examples from 32 to 1,024 while retaining the same 160 attack fitting examples reduced false-positive rate from **10.04% to 0.40%**: a **96.02% relative reduction**. Overall six-class macro-F1 improved from **0.4421 to 0.6543**.

The cost was lower lateral-flow detection: **94.24% to 83.06%**. The improvement therefore concerns false alarms and overall classification; it does not establish that every attack stage improved. [Earlier audited evidence](../../results/strong_benign_controls_v1/SUMMARY.json).

## 2. The later policy comparison improved false alarms and alert precision

On the same six supports with selected policies, the candidate produced **33.3% fewer false positives** than the lateral-sensitive reference. Attack precision rose **79.78% to 86.03%**, and binary attack F1 rose **0.8770 to 0.9044**. Lateral-flow detection declined **88.19% to 84.49%**.

These are favorable alert measures with a measured recall cost. The other four primary supports had no qualifying policy under the original requirements. [Audited source results](../../results/lateral_protection_v1/REPORT.md).

## 3. One additional comparison improved both averages, modestly

Against the ordinary source-normal 1% threshold, the lateral-sensitive reference had **25.9% fewer false positives** and lateral recall of **88.19% instead of 87.73%** on those same six supports.

This was an exploratory comparison. Only two of the six supports improved both measures; some other attack stages declined. The reference also used lateral-labeled selection data, whereas the ordinary threshold used normal selection data only. The result is promising descriptive evidence about this comparison, not proof of consistent superiority. [Exact comparisons and seed counts](FINDINGS_ACTUALS.md).

## 4. Why this is connected to a literature gap

Revell et al. (2026, Section 6.5) explicitly proposes larger benign support to reduce benign/attack ambiguity. This praxis measures the related idea's benefit and attack-stage cost in supervised trees, with fixed attack fitting identities and comparisons of weighting and threshold effects. [Primary paper](https://www.techscience.com/CMES/v147n1/67129/html).

**The contribution:** reproducible evidence about how much false-alarm improvement additional benign information buys, which attack stages change, and how much benefit is available from the alert threshold alone. Existing research already uses these component methods. The study adds a bounded empirical evaluation; it does not claim first use. [Current literature review](FINDINGS_LITERATURE_GAP.md).

## What the original 90% rule means

The 90% recall floor and the other numerical requirements were investigator-selected engineering targets. The original joint screen remains **INFEASIBLE**. That result does not erase the improvements above; those improvements also do not turn the original screen into a pass. The revised paper reports both clearly.

The full paper retains all 152 final model cells, all 19 support groups, stage results, the controls-only DEDALE stress test, label costs, and limitations. Whether the empirical contribution meets a particular institution's praxis requirements remains an academic assessment.

[Complete paper](FINDINGS_PRAXIS.md) · [Word](FINDINGS_PRAXIS.docx) · [PDF](FINDINGS_PRAXIS.pdf)
