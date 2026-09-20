# APT-final development protocol

## Scope and scientific status

This branch preserves both user attachments exactly. It maintains three candidate topics and implements the separate E0-E4 telemetry-quality program supplied in the second attachment. That sequence does not by itself test local-LLM noninferiority, retraining stability mitigation, or the full structural/semantic/hybrid comparison. Those tracks remain candidates with explicit prerequisites in `candidates.json`.

All currently available, previously inspected Unraveled/DAPT records are development evidence. No new method is declared novel and no new confirmation result is claimed. E0 is an infrastructure audit, not a hypothesis test. Synthetic tests qualify software only. The initial configuration is a development specification; registration and real-data releases must precede model experiments.

## Contract and partitions

Normalized records and edges follow [the data contract](../data/DATA_CONTRACT.md). Distinct independently justified groups are assigned to train, gate_train, calibration, development, and confirmation. Base models fit train only. Gate policies fit gate_train only. Thresholds fit calibration only. Development is used for engineering interpretation, not later called untouched confirmation. Confirmation uses separate files rejected by E1-E3. No graph crosses split or group boundaries; source time and edge availability must not exceed the target's time. Scaling uses train rows only.

An E0 PASS must bind normalized row/edge hashes, supported labels, and evidence for groups. The current raw inventory cannot establish such a PASS merely by matching filenames. No normalized-data evidence validator has qualified yet, so `readiness.py` deliberately blocks real-data model runs through both the CLI and engine. A future adapter must validate completed mapping and review artifacts; hand-editing a receipt into PASS is insufficient. A group is an independently justified campaign/host-time unit, not a new ID assigned to correlated rows. Sharing hosts across groups must be disclosed; held-out-host claims require host separation independently checked.

## E0: verify data before model claims

Inventory and hash available source metadata, count stage support and distinct groups, inspect timestamp units/time zones, and assess possible host/flow joins. Report join success and skew only when correspondence is independently grounded. A bounded sample's candidate overlap is not verified linkage. Missing authoritative identity/campaign mapping yields HOLD_DATA_CONTRACT and a documented remediation packet.

Thirty positive evaluation rows per stage and five independent evaluation groups are screening floors only. Neither supplies statistical power. Do not delete unsupported classes silently: amend the declared scope and config before evaluation. Keep unsupported/unknown records accounted for. A different dataset requires its own schema, label, license, and split audit; a community framework does not bypass E0.

## E1: edge-information ablation

Primary graph encoder: GIN, selected from the fair prior comparison rather than the older borrowed-baseline headline. GATv2 is a planned secondary model, not implemented by the initial engine. Compare MLP, GIN real edges, the same GIN with degree-preserving time-valid rewiring, and self-loop-only GIN. All use identical features, train-only preprocessing, seed lists, training steps, and hidden widths. Equal training steps do not guarantee equal compute; record cost separately.

E1 reports per-stage and macro F1, probability-quality metrics where defined, paired predictions, and uncertainty over independent groups. Retraining-seed spread is a separate statistic. A non-significant real-versus-shuffled result is inconclusive; it does not prove that edges contain no information. If real edges beat shuffled edges but not MLP, the result establishes only that the graph arm has not beaten the simpler comparator. Also measure complementary corrected/introduced errors before assuming there is useful gate opportunity.

Rewiring must preserve directed degree, relation counts, permitted group/split membership, and causal availability. For a replaced synthetic relationship, retain the original edge's relative availability lead time and recompute availability at the new target; reject any edge unavailable within the source-to-target time interval. An old absolute arrival timestamp cannot be attached blindly to a different relationship. The heuristic swap chain is not claimed to sample uniformly from all admissible graphs. The provisional changed-edge floor is 50%, a mixing screen rather than a theorem or literature-derived threshold. Insufficient feasible swaps make that control unqualified; do not claim a valid randomized graph from unchanged edges.

## E2: characterize telemetry degradation on development material

The initial engine implements edge loss, relation loss, and delayed edge availability with node features fixed. It does not simulate loss of an entire source whose measurements also populate node features. Such a claim requires a source-to-feature provenance contract and a separate implementation. Degradation rate is an intervention label for reporting, never a gate input available only to the experimenter.

Generate paired predictions on gate_train/calibration/development using fixed base models. Learn no detector from development labels. Keep the E4 confirmation set out of this process. Describe a crossover if observed; its existence is a hypothesis, not guaranteed. If delay is evaluated only as edges unavailable at the original decision time, do not call it complete late-arrival replay or measure first-alert delay from it.

## E3: test quality-based routing

Actual arms: MLP, GNN, static quality rule, frozen learned quality rule, confidence rule, and a random routing control with a development-frozen rate. Add a label-informed oracle strictly as a descriptive upper bound. No deployed or random policy uses oracle/test labels. The supplied proposal's 'five arms' actually named six before adding the confidence control.

Compare corrections and induced errors, stage outcomes, macro F1, and attacks detected at a calibrated alert threshold. Report alerts/day only with verified monitored exposure. No arbitrary max-minus-min timestamp denominator. A fixed threshold calibrated to a budget may exceed that budget after shift; report the exceedance, do not silently recalibrate the evaluation set.

The per-record correctness oracle bounds accuracy, not the non-additive macro-F1 metric. Report an accuracy-oracle gap fraction only when that gap is positive; any macro-F1 oracle outcome is descriptive. Report static/learned benefit ratio only when the learned benefit over the same comparator is positive. Otherwise mark undefined. Proposed 50% and 80% targets are development design choices, not proven feasibility or confirmatory success criteria.

The first implementation replays saved predictions from both models. Its routed-cost estimate is a proxy. It cannot establish end-to-end compute savings or the full H3a cost claim. A deployable gate must run before graph work it purports to avoid, and measured cost must include telemetry summaries, construction, loading, inference, and routing. Actual online execution and the closest published gate baseline are later qualification gates; the simple confidence control is not a full Mowst reproduction.

## E4: frozen transfer

Freeze base-model weights, feature order, labels, preprocessing, gate parameters, and alert thresholds before evaluation. Bind hashes in the policy/readiness record. Read confirmation only after a separate data-readiness receipt authorizes its schema/group/exposure provenance. No transfer claim from relabeling an already examined development partition. Do not silently refit or remap incompatible dataset fields. A recalibrated result, if later added, must be a separately named arm.

The noninferiority margin remains unset until the target outcome, independent-unit support, and operational tolerance are defensible. Thus the initial branch cannot declare H4 success. A completed replay is not a scientific gate PASS.

## Statistics, cost, and stopping

Use paired group resampling for shared cases; summarize seed variability separately. Sparse groups or undefined PR-AUC must remain visible. Register one primary contrast or apply the specified multiplicity correction before confirmatory testing. Do not select thresholds or favorable stages from confirmation results. Accuracy, false-alert burden, and cost are separate outcomes; none is a substitute for another.

Stop advancement when E0 cannot justify the data contract, graph information lacks a useful opportunity, gates fail strong simple controls, label/exposure support is inadequate, or operational cost cannot be measured. A null result should be reported with its uncertainty and scope; publication or academic acceptance is not guaranteed.
