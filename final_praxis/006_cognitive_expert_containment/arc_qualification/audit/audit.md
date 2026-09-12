# FP006 ARC intervention audit

Downloaded and audited all 64 cells from the completed 32-question run, plus its manifest and summary.

- Largest absolute candidate log-likelihood change: 0.665376902.
- Questions with any changed score: 32/32.
- Questions with a score change above 1e-6: 32/32.
- Candidate scores changed: 128/128.
- Raw prediction changes: 0; normalized prediction changes: 0.
- Baseline social selection appeared on 32/32 questions, 128/128 candidate forwards.
- Baseline routing totals, logic/social/world/language: [9339, 5501, 17923, 71817].
- Ablation routing totals, same order: [10959, 0, 19662, 73959].
- Baseline social selection fraction: 5.260088%; ablated social selections: zero.

All cell identities match the manifest cohort. All 64 cells share the actual manifest file SHA-256. Candidate token IDs, labels, lengths, and gold answers agree across conditions. Stored predictions and correctness were recomputed successfully.

Routing totals sum per-layer token selections over candidate forwards; repeated question prefixes are counted repeatedly. These counts are not independent task observations. Candidate likelihood changes demonstrate an intervention effect on scoring when present; unchanged accuracy does not establish useful answer protection. This remains a capability/implementation qualification, with no new containment policy tested.

Source: s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp006-arc-20260912-6372d09/
Manifest SHA-256: 07727e6ed396a5bc512e74547c3bca0277c112eb26ffc400b8e91eaf39531a22
See audit.json for every paired score delta and download_receipts.json for exact object hashes.
