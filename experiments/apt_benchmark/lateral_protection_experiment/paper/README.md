# Findings-led empirical praxis

## Current recommended manuscript

**Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs**

An empirical praxis on benign training coverage, alert policies, and attack-stage visibility.

- [Read the findings-led manuscript](FINDINGS_PRAXIS.md)
- [Current Word document](FINDINGS_PRAXIS.docx)
- [Current PDF](FINDINGS_PRAXIS.pdf)
- [Actual improvements, matched counts, and tradeoffs](FINDINGS_ACTUALS.md)
- [Literature gap and prior-art boundaries](FINDINGS_LITERATURE_GAP.md)
- [Unchanged audited numerical results](../../results/lateral_protection_v1/REPORT.md)
- [Frozen design and reproduction instructions](../README.md)

The earlier benign-label experiment reduced false positives by **96.02%** and raised macro-F1 from **0.4421 to 0.6543**, with lateral detection falling from **94.24% to 83.06%**. In the current experiment, the candidate achieved **33.3% fewer false positives** and attack F1 **0.8770 to 0.9044** on the same six feasible supports; lateral detection fell from **88.19% to 84.49%**.

An exploratory comparison on those six supports found **25.9% fewer false positives** and **0.46 percentage points higher mean lateral recall** for the lateral-sensitive reference than the ordinary source-normal threshold. Both measures improved in only **two of six supports**, and some other stages declined. This is a small aggregate improvement, not superiority across all seeds or stages.

The revised emphasis and additional descriptive comparisons were developed after completion. No fits, thresholds, source data, protocol, or original decision changed. All 152 final models and 19 groups completed; the original all-ten screen remains **INFEASIBLE**, with six feasible selections and four unavailable policies. DEDALE tested ordinary controls only on four lateral flows from one execution. The contribution is empirical evidence about useful improvements and their costs, not a novel validated algorithm or demonstrated deployment utility.

## Preserved earlier manuscripts and receipts

- [Prior screen-oriented manuscript](PRAXIS.md), [Word](PRAXIS.docx), [PDF](PRAXIS.pdf)
- [Prior manuscript review](MANUSCRIPT_REVIEW.json)
- [Prior document receipt](DOCUMENT_RECEIPT.json)
- [Earlier source draft](DRAFT_EMPIRICAL_PRAXIS.md)

The earlier manuscript and its document receipt remain intact. They describe the original screen-oriented presentation; they are not the receipt or page count for the findings-led revision. Software validation, scientific audit, numerical synthesis, and document rendering are separate checks.
