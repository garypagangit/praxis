# Feature dictionary template

**Status:** candidate families; definitions must be finalized before freeze. Keep only information available to a defender under the declared observation window. Internal prompts, model names, labels and collection IDs are not substantive features.

| Family / candidate | Source | Unit and exact definition | Timing-derived? | Tool-derived? | Missingness policy | Leakage check |
| --- | --- | --- | --- | --- | --- | --- |
| Host behavior / command diversity | Validated process/script logs | TBD: normalized vocabulary and denominator | Depends on rate normalization | Audit | TBD | Strip identifiers; fit vocabulary in training |
| Sequence / transition entropy | Target-side event ordering | TBD: event categories, estimator and minimum length | No if using order alone | Audit categories | TBD | Do not use future events beyond window |
| Breadth / entities accessed | Host + network | TBD: identity-free count and opportunity normalization | Yes if per-time rate | Audit | TBD | Use identities for joins, not predictors |
| Retry/error behavior | Verified outcome fields | TBD: event rule and denominator | Depends on formulation | Audit | TBD | Do not infer error solely from missing output |
| Network protocol mix | Validated sensor logs | TBD: per-trial protocol proportions | No for proportions alone | Audit | TBD | Remove address/banner identity |
| Timing / bursts / concurrency | Synchronized sensor timestamps | TBD: windows and aggregation | Yes | Audit | TBD | Remove entire proxy family in timing ablation |

For every implemented feature add its stable ID, extraction version, allowed availability time and whether it enters full, no-timing and no-timing/no-tool sets. Any learned thresholds/encodings are fitted only on training data.
