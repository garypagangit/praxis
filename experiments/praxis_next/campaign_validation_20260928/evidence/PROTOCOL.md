# AIT external-execution validation attempt

Frozen design written 28 September 2026, before fitting or inspecting model results on AIT.

## Question and scope

Can the praxis's comparison of aggregate classification scores, exfiltration warnings, and benign false alerts be evaluated on a different source with whole executions held out? Does selecting a prior-history feature group by predicted entropy reduction versus predicted stage-weighted error reduction show the same trade-off?

This is an adapted external-source test, not an exact replication of PX-081. The source has eight independently executed laboratory testbeds produced by a common scenario generator, not eight unrelated real-world APT campaigns. Its native flow labels support benign, other attack, and exfiltration; no movement class will be invented. The original two optional groups become one prior-history group because publisher role/topology fields participate in label construction and should not be offered to the model. This limits how strongly results can confirm or contradict the original two-group experiment. Costs, latency, and collection remain offline simulations.

## Source and qualification

Acquire all eight archives of Zenodo record 13168643, verify publisher MD5, calculate SHA256, and check every ZIP member's CRC. Use all three native CSV members per execution. Preserve publisher labeling scripts and label dictionary. Unknown labels are excluded and counted, never silently treated as benign. Flow labeling relies on topology/ports and attack timing. In particular, the UDP notebook assigns remaining unlabeled traffic to data exfiltration. These are publisher labels, not new payload verification or forensic confirmation of every transfer. The earlier exfiltration/later intrusion scenario does not support claiming within-run chronological replication of the original four-class task.

## Partition and information boundaries

Order executions by earliest observed start time, breaking ties alphabetically. Reserve the last two whole executions as final evaluation. Use the first six for development. Generate forward predictions by training on preceding development executions and predicting the next execution (five folds). Never randomly divide rows of one execution between fit and evaluation. This partition tests disjoint executions; any overlap in their calendar intervals is reported and precludes a strict future-calendar claim. Qualification counts and timing may be inspected before freezing model fits; held-out predictions may not be used to change this design.

Use every eligible row without class sampling or row caps. Remove exact duplicate observable flow records within an execution, retain one if labels agree, and exclude all rows in any duplicate group with conflicting native labels. Observable identity consists of protocol, endpoint addresses and ports, start/end times, directional packet and byte counts. Check identities across executions and exclude shared identities from final evaluation if any occur. Report every exclusion. Aggregated probes have lost sensor identifiers; near-duplicate multi-probe observations may remain, so rows are not independent replications.

Current features: TCP/UDP flag; log(1+x) of nonnegative duration, directional packets and bytes; directional byte and packet fractions; and log(1+x) of mean bytes per packet for each direction. No IP strings, ports, FQDNs, absolute time, execution ID, publisher roles, networks, or labels enter model features.

Prior-history features: for the same initiating endpoint within its own execution, aggregate only flows that ended strictly before current start and no more than one hour earlier. Features are log prior count, log total bytes, log total packets, log mean bytes, log mean packets, mean log duration, UDP fraction, and log seconds since latest eligible completion (zero when no history). Raw endpoint identity only keys grouping; it is not a predictor. No labels enter history. Empty histories are all zeros. Every history endpoint and strict time boundary must be audited. History is available after current-flow completion; this measures classification of completed flows, not early warning.

## Fixed models and policies

Seeds 8101, 8102, 8103. Two LightGBM classifiers (current; current + history), 150 boosting iterations, 15 leaves, learning rate .05, minimum child count 10, L2=1, four threads, no class weights, tuning, or early stopping. Default full-row fitting with seed-controlled feature bin sampling. Treat seed agreement as fitting stability, not three independent campaigns. Explicit constant predictor for any one-class training fold.

Train two regressors on development forward predictions, 100 boosting iterations, nine leaves, minimum child count 20, learning rate .05, L2=1. Inputs are current features and current-model probabilities only. Targets: (a) Shannon entropy before minus after history; (b) weighted hard-classification error before minus after history, with weights [1,1,4] for benign, other attack, exfiltration. Negative targets retained. No optional-history values or post-acquisition probabilities enter the selector. Final classifiers use all six development executions; selectors use all eligible development OOF rows.

Evaluate no acquisition; acquire history always; acquire history if predicted entropy reduction >0; acquire history if predicted weighted error reduction >0. All acquiring policies have the same per-row budget 2, history cost 2, nominal latency .75 and deadline 1.0. Clean delivery only, no post-hoc thresholds or budget selection. Equal available budget does not imply equal realized spending: publish acquisition fractions. The always-history model is also the full-context reference for this one-group design. Freeze code and prepared-data hashes before fitting.

## Outcomes and reporting

Publish all seeds and both held-out executions separately plus pooled and execution-macro summaries: macro-F1 across three fixed classes, per-class precision/recall/F1, full confusion matrix, exfiltration missed count, exfiltration warning recall (any attack prediction for true exfiltration), exact exfiltration recall, benign false-alert count/rate, unweighted and stage-weighted error, acquisition count/fraction and mean spend. Distinguish warning recall from exact-stage recall throughout. Primary comparison: error-focused minus entropy-focused acquisition. Direction analogous to the earlier result is macro-F1 increasing while exfiltration warning recall decreases; size and consistency must be reported, not just direction. No row-level significance claims, no invented pass threshold, no selective omission of null or opposite results.

Write probabilities/actions and true labels for independent recomputation, fitted models, software versions, per-file hashes, and audited feature/split boundaries. Report source limitations and whether this qualifies as an adapted validation, exact replication, or only feasibility. Do not modify original paper claims to assert broader validation until evidence is audited.

Sources: https://zenodo.org/records/13168643 ; https://arxiv.org/abs/2203.08580 ; publisher labeling notebook preserved next to this protocol.
