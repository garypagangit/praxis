# EXP-RQ2: stable attributes and generalization

**Status:** prospective matched-study experiment not run; wording approved October 24, 2026. Earlier archive/synthetic screens are exploratory only. **Tracker:** E02, with final confirmation in E04. **Development target:** Nov 6; locked evaluation Nov 7.

**RQ2:** Which classifiers retain useful behavioral attributes for classification performance on autonomous-AI APT data?

**H2:** Logistic regression retains useful behavioral attributes and achieves above-baseline classification performance on previously unseen autonomous-AI configurations and human operators.

| Element | Method |
| --- | --- |
| Independent variables | Held-out group type; full versus no-timing versus no-timing/no-tool representation; classifier |
| Group tests | Human operator, AI configuration; separate model-family/scaffold tests only if enough distinct groups exist |
| Primary responses | Unseen-group macro-F1 benefit over baseline; transfer loss relative to a predefined reference evaluation |
| Attribute stability | Predeclare family-rank correlation or top-k overlap across development holdouts; choose k and handling of ties before scoring |
| Shortcut controls | Exclude collection IDs and runner artifacts; remove timing proxies and tool-derived proxies together with explicit identifiers |
| Transfer comparison | Use a declared comparable reference population/protocol. Record changes in class mix or difficulty; a score difference across different populations alone is not pure overfitting |
| Confirmation | Frozen models, thresholds and features; reserved groups never used for selection; report each held-out group as well as aggregates |
| Acceptance | Supported positive logistic-regression baseline contrast on the declared unseen groups; attribute stability reported separately. Any transfer-loss gate must be explicitly frozen as an additional robustness criterion |
| Limitation | A held-out configuration using a known model family does not establish unseen-family transfer |

Deliver split membership audit, group counts, unseen-group predictions, full/reduced contrasts and stability tables. Report ordinary scripted-control outcomes separately to show whether the model confuses automation with AI; do not quietly relabel controls as humans. [Fillable experiment record](templates/EXPERIMENT_TEMPLATE.md) · [Results record](templates/RESULTS_TEMPLATE.md).

[October 24 hypothesis rationale and revision history](../../PRAXIS_RESEARCH_DESIGN.md#october-24-revision-and-evidentiary-basis). Freeze exact contrasts, baselines and practical margins before final evaluation.
