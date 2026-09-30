# What the first three experiments established

These are development results from an already examined UNRAVELED campaign. They do not establish novelty, independent-campaign performance, or deployment guarantees. See [all results](RESULTS.md), [all arms](results/ALL_ARMS.csv), [protocol](PROTOCOL.md), and [compute adjustment](TRANSPORT_ADDENDUM.md).

## PX-085: calibration did not fix the main warning failure

For the error-focused policy in the primary clean, budget-2 comparison, supported-stage target miss rates of 1%, 2%, 5% and 10% all left exfiltration warning recall at 67.33% averaged across seeds. The observed miss rate remained approximately 32.67%. Calibration attack examples were assigned very high attack probabilities, while many later attack examples received confident benign predictions. Consequently, the learned thresholds did not promote those missed attacks.

This is an empirical calibration-transfer failure, not a refutation of conformal theory. The theorem requires exchangeability and concerns a marginal expectation. The campaign's chronological, correlated flow split does not establish those assumptions. Movement has no calibration examples at all. A policy that insists on a bound for every stage therefore falls back to warning on everything in this implementation, with 192,193 benign false alerts. That is explicit infeasibility for useful workload control, not a useful detector result.

Some other arms did change under calibration, so this is not a claim that the gate never changes predictions. All 2,268 policy/alpha/scope rows and 144 gated ensemble rows are retained.

## PX-086: the mean ensemble can erase good seeds' warnings

With roles evidence, the three seeds missed 43, 61 and 1,100 of 3,442 exfiltration rows. The probability mean missed 1,100. It called 1,058 rows benign despite at least one seed warning on them. This directly disproves the supplied empirical expectation that mean averaging would necessarily stabilize warning retention.

The warning union missed 42 rows: 98.78% warning recall, with 196 benign false alerts. For comparison, the three individual roles experts averaged 88.34% warning recall and 179.67 false alerts; their warning recall ranged from 68.04% to 98.75%. The best individual seed is known only after evaluation, so it is not a valid deployable selection rule. Union retains every seed's warning by construction, but costs three model evaluations and may add false alerts. It is a candidate mitigation to validate, not a novel ensemble algorithm.

The recoverability partition is useful for explaining failure: it separates selector misses that another reachable fitted expert would warn about from misses shared by all reachable fitted experts. Its oracle sees hypothetical evidence outcomes; it cannot be presented as achievable detector recall. 'Unrecoverable' refers only to this expert set and budget.

## PX-087: early stopping reduced simulated acquisition cost

In the clean, budget-2 comparison, stopping roles-first acquisition when currently observed attack probability reached 90% reduced mean acquisition cost from 1.0000 to 0.9291, a 7.09% reduction. Exfiltration warning recall remained 88.34%, movement warning recall remained 85.71%, and mean benign false alerts remained 179.67. Macro-F1 changed from .713604 to .713508 because stage assignments can differ even when warning counts agree.

This is a narrow cost improvement relative to always acquiring roles. It does not resolve the 8103 seed failure or establish that cheapest-first is optimal. Costs and availability are inherited simulations; the result does not measure actual dollar or latency savings in a SOC. Other budgets and conditions must be read from the complete comparison rather than inferred from this primary case.

## Next experiment priorities

1. Keep warning union and fixed stopping as transparent comparators. Do not use the proposed mean-retention or cheapest-first optimality claims.
2. PX-089 needs qualified temporal windows and label availability before testing recalibration. Present-stage support and missing-stage handling are central requirements.
3. PX-088 needs an actual selective-risk construction and an explicit response when its risk and analyst-capacity requirements conflict. No analyst performance is assumed.
4. PX-090 requires justified monotone feature directions; PX-091 requires a new independently qualified execution. Both remain registered rather than falsely reported as tested.

The most useful result is that a risk-control formula does not repair unrepresentative calibration. The warning-preservation choice that helped here was explicit union, while ordinary probability averaging reproduced the weak seed's exfiltration failure. Both findings need independent replication before a stronger claim.
