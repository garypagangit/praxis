# Praxis 06 Related Work Notes

Generated: 2026-05-12

## Purpose

This is a structured related-work scaffold for the Praxis 06 paper. It is not a final citation-complete literature review. The goal is to pin down how the paper should position its contribution without overclaiming.

## 1. APT Stage Detection And Deployment Shift

The paper should open the APT-detection related work around the gap between benchmark classification and deployment-realistic shift. The Praxis 04 negative result is important internal evidence: stage-conditioned routing did not work when stage predictions were made under held-out source-file shift. This motivates adaptation rather than more routing.

Positioning sentence:

> Prior APT-stage detectors usually optimize static supervised performance, but the Praxis 04 failure suggests that deployment shift can erase the usefulness of predicted stage labels before routing or ensemble selection can help.

Use in paper:

- Background/motivation.
- Threats to validity.
- Discussion bridge from negative to positive result.

## 2. Test-Time Adaptation

Anchor the method to test-time adaptation and test-time training literature:

- TENT-style entropy-minimization adaptation.
- Batch-normalization statistics adaptation.
- Test-time training with self-supervised objectives.

Praxis 06 should emphasize that it uses a conservative security-specific variant: the main intervention is not unconstrained adaptation but selective adaptation with a Data Exfiltration guard.

Positioning sentence:

> Unlike generic TTA settings where global accuracy is the main objective, streaming APT detection needs asymmetric safety constraints because improving a rare stage is not acceptable if it damages high-consequence Data Exfiltration behavior.

## 3. Confidence Rejection And Abstention

The matched-rate frozen confidence-rejection baseline is a key differentiator. Related work often treats confidence as a way to abstain or defer; Praxis 06 needs to show the result is not just abstention.

Positioning sentence:

> A matched-rate reject baseline controls the simplest explanation that TTA merely filters uncertain examples; it rejects the same fraction of rows but leaves Reconnaissance F1 at `0.0000`.

Use in paper:

- Results.
- Discussion.
- Defense Q&A.

## 4. Class Imbalance And Rare-Stage Recovery

The paper is adjacent to class-imbalance work, but the Plan 02 negative result matters: simple stage-aware weighting did not solve the rare-stage problem and damaged benign behavior. This lets Praxis 06 argue that deployment-time shift, not only static imbalance, is central.

Positioning sentence:

> The result complements class-imbalance methods but does not reduce to them: a separate stage-aware weighting pilot failed to recover rare-stage behavior without collateral damage.

## 5. Security-Specific Adaptation Risks

TTA is riskier in security than in ordinary domain adaptation because an attacker may influence the adaptation stream. The paper should acknowledge adaptation poisoning and adversarial stream manipulation explicitly.

Positioning sentence:

> The selective gate is a first safety mechanism, not a complete defense against adversarial adaptation-stream manipulation.

Use in paper:

- Threats to validity.
- Future work.

## 6. External Validity

DAPT2020 is useful as a detector-recipe transfer check, not as a TTA replication. A true DAPT TTA feasibility gate has now been run and is negative, so the paper should keep DAPT in the appendix as a boundary on generality.

Positioning sentence:

> As an appendix check, the same MLP recipe transfers to DAPT2020 with Macro F1 `0.6353 +/- 0.0043`, but a follow-up DAPT TTA feasibility gate was negative. The result should therefore not be interpreted as cross-dataset selective-TTA evidence, and Data Exfiltration support is only two test examples.

## Citation Targets To Fill

| Area | Candidate anchors already tracked |
|---|---|
| TTA / entropy minimization | Wang et al., TENT, ICLR 2021 |
| Test-time training | Sun et al., ICML 2020 |
| Class imbalance | Lin et al., Focal Loss, ICCV 2017; Chawla et al., SMOTE, JAIR 2002 |
| CIC-IDS2018 dataset | Sharafaldin, Lashkari, and Ghorbani, ICISSP 2018 |
| APT stage/routing baseline | TSE-APT, Electronics 2025 |
| Provenance graph context | MAGIC, USENIX Security 2024; Kairos, IEEE S&P 2024 |

## What Not To Claim

- Do not claim TTA is generally safe in adversarial settings.
- Do not claim DAPT2020 proves cross-dataset TTA.
- Do not claim provenance graph results are positive; the graph line is currently label-blocked.
- Do not present confidence rejection as equivalent to selective TTA; it is a failed explanation baseline.
