# Verify the public evidence without private flow records

Requirements: Python 3.10+ and NumPy (the recorded run used NumPy 2.2.6). From this folder:

```text
python verify_public.py
```

The default command verifies the files and prints a receipt without modifying them. To save a **new** receipt:

```text
python verify_public.py --receipt my_verification.json
```

Existing receipts are never overwritten. `--directory PATH` can identify a different intact copy of this evidence folder. The verifier imports only the Python standard library and NumPy, and does not import the experiment runner, D1 metric library, publisher, or any other project analysis code.

## What it verifies

- Hashes against the previously issued arithmetic and publication receipts.
- The complete fixed inventory of 27 acquisition-policy and nine temporal/history comparisons.
- All 66 public per-capture confusion tables and their paired capture-stage support marginals.
- Regeneration of the exact 2,000 five-capture draws from seed 20260923.
- All published points, paired differences, error-destination counts, stage direction flags, and 720 paired metric intervals.
- Undefined bootstrap support, all 12 three-seed mean groups, and all six study/stage direction summaries.

It recomputes confusion-matrix formulas directly. Repeated captures repeat their full confusion counts; both methods use the same multiplicities. This is sufficient for the reported capture-bootstrap statistics. The saved [public verification receipt](PUBLIC_VERIFICATION.json) records the exact input and verifier hashes and a PASS outcome.

## What public aggregate verification cannot establish

Matching capture-stage support counts is necessary but cannot prove that each original row was paired correctly. This verifier cannot recover row identities, independently reproduce the probability-to-decision conversion, validate the author's ground-truth labels, establish model-fitting provenance, or turn one campaign into independent replications. The earlier [private-input audit](AUDIT.json) checked original hashes and row pairing; it remains a separate evidentiary step. Public recomputability verifies the arithmetic of the released sufficient statistics, with these boundaries intact.

The reanalysis was retrospective. Verification does not make it prospective, confirm its novelty, or guarantee interval coverage beyond the five observed capture fragments.
