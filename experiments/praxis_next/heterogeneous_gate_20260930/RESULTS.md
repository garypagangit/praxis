# PX-093: heterogeneous gates — results

| Hypothesis | Outcome |
|---|---|
| H1 | SUPPORTED_BY_CONSTRUCTION |
| H2 | NOT_SUPPORTED |
| H3 | NOT_SUPPORTED |

All metrics below are clean budget 2; UNRAVELED is four-class, AIT is the adapted three-class task. Counts refer to flows. The CSV retains all conditions, budgets, mean controls and oracle comparisons.

| Source | Set | Exfil warning recall | Exfil misses | Benign false alerts | OR overlap | Additional exfil warnings vs base OR | Additional false alerts vs base OR |
|---|---|---:|---:|---:|---:|---:|---:|
| UNRAVELED | base3 | 98.779779% | 42 | 196 | 0.363636 | 0 | 0 |
| UNRAVELED | plus_current | 98.779779% | 42 | 196 | 0.277620 | 0 | 0 |
| UNRAVELED | plus_lr | 99.244625% | 26 | 1991 | 0.792596 | 16 | 1795 |
| UNRAVELED | A6_full | 99.244625% | 26 | 1991 | 0.743188 | 16 | 1795 |
| UNRAVELED | heterogeneous3 | 99.244625% | 26 | 1982 | 0.852107 | 16 | 1786 |
| UNRAVELED | duplicate_control | 98.779779% | 42 | 196 | 0.270345 | 0 | 0 |
| UNRAVELED | lr_only | 67.576990% | 1116 | 1973 | 1.000000 | 16 | 1777 |
| UNRAVELED | current_only | 67.518884% | 1118 | 167 | 1.000000 | 0 | -29 |
| wilson | base3 | 99.985862% | 3 | 54 | 0.341772 | 0 | 0 |
| wilson | plus_current | 100.000000% | 0 | 104 | 0.468468 | 3 | 50 |
| wilson | plus_lr | 100.000000% | 0 | 1716 | 0.930586 | 3 | 1662 |
| wilson | A6_full | 100.000000% | 0 | 1751 | 0.917715 | 3 | 1697 |
| wilson | heterogeneous3 | 99.995287% | 1 | 1750 | 0.970605 | 3 | 1696 |
| wilson | duplicate_control | 99.985862% | 3 | 54 | 0.255924 | 0 | 0 |
| wilson | lr_only | 98.609737% | 295 | 1686 | 1.000000 | 3 | 1632 |
| wilson | current_only | 99.967011% | 7 | 64 | 1.000000 | 3 | 10 |
| harrison | base3 | 99.603530% | 93 | 1404 | 0.543554 | 0 | 0 |
| harrison | plus_current | 99.607793% | 92 | 13973 | 0.855717 | 1 | 12569 |
| harrison | plus_lr | 99.603530% | 93 | 3329 | 0.702914 | 0 | 1925 |
| harrison | A6_full | 99.607793% | 92 | 15420 | 0.834325 | 1 | 14016 |
| harrison | heterogeneous3 | 99.603530% | 93 | 15355 | 0.925837 | 1 | 13951 |
| harrison | duplicate_control | 99.603530% | 93 | 1404 | 0.429489 | 0 | 0 |
| harrison | lr_only | 0.000000% | 23457 | 2153 | 1.000000 | 0 | 749 |
| harrison | current_only | 99.437268% | 132 | 13746 | 1.000000 | 1 | 12342 |
| pooled | base3 | 99.785120% | 96 | 1458 | 0.531923 | 0 | 0 |
| pooled | plus_current | 99.794073% | 92 | 14077 | 0.850523 | 4 | 12619 |
| pooled | plus_lr | 99.791835% | 93 | 5045 | 0.766717 | 3 | 3587 |
| pooled | A6_full | 99.794073% | 92 | 17171 | 0.842128 | 4 | 15713 |
| pooled | heterogeneous3 | 99.789596% | 94 | 17105 | 0.930226 | 4 | 15647 |
| pooled | duplicate_control | 99.785120% | 96 | 1458 | 0.418966 | 0 | 0 |
| pooled | lr_only | 46.834990% | 23752 | 3839 | 1.000000 | 3 | 2381 |
| pooled | current_only | 99.688871% | 139 | 13810 | 1.000000 | 4 | 12352 |

Additional warnings count recovered rows, not net gain for non-superset arms such as LR alone. For the full A6 set, every base member is retained, so its additions cannot be offset by lost base warnings. The overlap column describes OR, not the mean gate.

## Frozen fixed-denominator workload guard

| Source | Full A6 false alerts | Maximum allowed (2 × original mean) | Best constituent exfil recall | Full A6 exfil recall |
|---|---:|---:|---:|---:|
| UNRAVELED | 1991 | 359.333 | 98.750726% | 99.244625% |
| wilson | 1751 | 105.333 | 99.985862% | 100.000000% |
| harrison | 15420 | 1722.000 | 99.599267% | 99.607793% |
| pooled | 17171 | 1827.333 | 99.773928% | 99.794073% |
