# Corrections made before real-data model experiments

The user-supplied proposal is preserved byte-for-byte in [source/USER_PROPOSAL.txt](source/USER_PROPOSAL.txt). Its embedded `REGISTERED` heading is draft text, not evidence of an earlier registration. This new branch records its own actual commits. The user authorized building and starting the experiment; adviser review remains a later academic review, not an invented approval or a prerequisite for read-only G0 and software tests.

Version 1.1 registers G0 and software qualification after literature, schema and class-count inspection, before scorer fitting or efficacy evaluation. The following corrections are visible rather than silently incorporated into a purportedly untouched preregistration:

1. **No guaranteed positive result.** A safe gate can suppress nothing. Workload benefit and novelty must be demonstrated separately.
2. **Risk denominator fixed.** Attack-suppression risk means the fraction of all true attack alerts suppressed. It is not the fraction of suppressed alerts that are attacks.
3. **Expected risk is different from high-confidence risk.** The proposed 95%-confidence population statement uses an established binomial tolerance/NP construction, not an unspecified expected-risk CRC theorem. At the requested 1%/95% setting, even the most conservative nontrivial threshold needs at least299 IID attack calibration units. Two hundred test attacks do not establish the same statement.
4. **Finite-test noise accounted for.** A method whose population risk is1% can exceed1% on a small finite test sample much more often than5%. Repeated splits of one corpus are also dependent. Neither phenomenon is automatically an implementation bug.
5. **Training separated from certification.** A learned scorer needs fitting data; model/feature selection uses a separate development role. Risk calibration occurs after the scorer and predicates are fixed, followed by a locked test. A three-way calibration/validation/test design omitting training is incomplete for an SVM.
6. **No hidden selection benefit.** Selecting the best of several individually certified scorers needs fresh calibration or a prospective multiple-comparison allocation. Ten seeds are repeated models, not ten independent datasets.
7. **Predicates require actual evidence.** Missing raw logs, severity or incident context cause a retained alert. Repackaging a processed alert as its own raw evidence does not pass P1. Source-consistent hostile text can satisfy exact-match predicates, so P1 alone does not prove prompt-injection containment.
8. **H3 ratios replaced before use.** Ratios to a zero clean miss rate are undefined. A new attack-specific registration must use absolute rates/differences, fixed attack sets and explicit unchanged/changed fields. No adversarial protection theorem is asserted for an untested attack family.
9. **Data tiers are conditional.** Public availability, licensing, independent campaign support and ground-truth joins must be checked. Replaying one PCAP does not create unlimited independent labeled attacks. Flow labels do not automatically label generated alerts.
10. **Literature baseline added.** Current papers already study certified alert closure and nonvacuous security decision gates. A generic certified suppression wrapper is not an unoccupied contribution. The nearest methods are required comparisons; a difference between marginal and PAC guarantees alone is not new mathematics.
11. **Human review is real work.** A local blinded 50-case review packet can be prepared now. Agreement and reviewer identity remain pending until a human completes it; missing underlying evidence limits what such a review can validate.
12. **No unearned cross-paper comparisons.** A published average over16 LLMs is not a target for a newly trained SVM. FPR, attack miss rate, fraction of benign alerts suppressed and workload removed use different denominators. No alerts-per-analyst-day claim is derived from an unrelated SOC's volume.

No G1-G5 efficacy results existed when these changes were recorded. The original draft's H2 target remains the planned utility goal. A frozen model/data-specific release must resolve G0, the exact scorer and comparator, split roles, uncertainty units and attack specification before confirmatory runs.

## Qualification reporting correction after the first software run

The original `qualification_20260920` attempt is retained. Its four underpowered settings used an analytical keep-all result and one API check each, but the output misleadingly called the length of a placeholder array 10,000 independent calibration samples. The corrected runner reports zero Monte Carlo samples for those settings and null empirical frequencies/intervals. It records 40,000 actual independent simulated calibration sets across the four nontrivial settings. A second attempt uses the same seed and mathematical code; thresholds, risks and all substantive findings must remain identical. This is a reporting correction, not a changed hypothesis or a rerun to improve an outcome.

## Review blinding refinement before any human review

The first G0 packet hid the `Label` field but still showed derived `attack_type` and `kill_chain_all` annotations. The final packet also hides those annotations and common ground-truth aliases, reducing the risk of circular label agreement. The same 50 case IDs and answer key are retained; source counts and eligibility are unchanged. The original receipt remains archived and a v2 receipt binds the final packet. No human reviewed either packet before this correction. Use only `human_review_v2/REVIEW.html` for the study.

## Section 12 amendment: release a score-only exploratory pilot

**2026-09-20, before real-data scorer fitting or performance inspection.** The user's follow-up explicitly requested a workaround rather than holding all modeling for full evidence-gate acceptance. [PILOT_PROTOCOL.json](PILOT_PROTOCOL.json) now releases local SecAlertBench score-only exploration: fixed SVM, deterministic four-role split, one representative per IPv4-normalized feature family, reserved human-review families, and documented mixed-label exclusions. Exact/normalized grouping counts and split class counts were inspected; no model results informed the choices. Model text is unchanged by grouping-only address normalization. All outcomes will be retained.

The earlier registration remains an immutable record of the startup stage. This amendment changes which exploratory work can proceed; it does not mark missing terms, human review, independent attack support or raw-event provenance as resolved. It does not release original confirmatory H1-H3 or assert published-scorer reproduction. Empirical benefit may justify continued study but cannot establish an operational population certificate from unverified independent units.

Tier3 is separately opened for a small offline PCAP-to-alert provenance pilot. Published scenario labels stay at scenario level; they are not automatically labels for every derived alert. Network captures do not supply authenticated user identities or complete enterprise incident membership. A supported network-only predicate contract would be an explicit revised design, not silently described as the original full gate. No favorable or certified result is promised.

Gary may perform the proposal's real50-case audit himself with relevant experience disclosed; an external reviewer was not required. A single-rater result has that limitation and must actually meet45/50agreement. The audit remains pending and is not replaced by automated checks. External correspondence remains a prepared draft, not a prerequisite for this exploratory pilot or a message already sent.

## Packet-provenance diagnostic after the first replay

The first two compact captures replayed successfully through Suricata8.0.7 but produced **zero ET Open alerts**. The engine loaded52,302 rules; nine `file.magic` rules failed because this Windows build lacks libmagic. The full attempt, hashes and logs are preserved. This is not a successful detection or suppression evaluation, and a zero-alert linkage audit is vacuous.

A separately labeled instrumentation run now emits a diagnostic event for TCP/UDP packets solely to exercise packet-reference joins on real capture bytes. These explicit diagnostic rules make **no attack judgment** and are not a substitute detector, new ground truth or evidence of favorable suppression. A later efficacy corpus still needs suitable natural alerts and independently validated labels. The supplementary mode also records rule-load failures explicitly and removes the unused default threshold-file path from future generated configs. The original attempt is not overwritten.
