# PX-104 — Automated review of warning-loss explanations

## Result

Built and ran three deterministic bots on 12 prepared PX-102 cases under six conditions: 216 bot reviews. There are only 11 unique score vectors. These are software checks on exposed cases, not 216 independent attacks, human reviews, or language-model assessments.

| Condition | Scores-only calculator | Explanation follower | Verifying bot |
|---|---|---|---|
| Scores only | 12/12 correct | 12 abstentions | 12/12 correct |
| Correct explanation | 12/12 correct | 12/12 correct | 12/12 verified and correct |
| Wrong member-warning count | 12/12 correct | 12/12 final answers correct, false count unchecked | 12/12 contradictions rejected |
| Wrong mean-warning claim | 12/12 correct | 4/12 correct | 12/12 contradictions rejected |
| Wrong OR-warning claim | 12/12 correct | 4/12 correct | 12/12 contradictions rejected |
| Missing member scores | 12 abstentions | 12/12 answers match original key, unsupported by complete evidence | 12 abstentions |

For rejected explanations, the verifier also retains the correct independently calculated answer as diagnostic evidence. Its public accepted answer is null. RESULTS.json deliberately counts abstention/rejection as a nonanswer in all-case answer accuracy, while reporting fault rejection separately. A correct final answer can accompany a false explanation, as the wrong-count condition illustrates.

## What the bot does

1. Checks for three complete, finite class-score vectors with valid probability ranges and sums.
2. Reconstructs member decisions and the mean decision, matching first-class tie handling.
3. Determines whether an available member warning was discarded by the mean.
4. Parses the fixed explanation format and verifies its warning count, mean decision and OR decision.
5. Rejects contradictions; abstains when complete evidence is unavailable.

The scorer reads the answer key after generating bot responses. The reviewer module never reads the key. A separate NumPy audit reconstructs the correct answers and checks the specified response behavior. Freeze commit: e4df97a.

## What this establishes for the Praxis

The deterministic review layer can verify these explanations and detect the deliberate faults tested here. It provides an executable auditable-AI component. The calculator already achieves 12/12, so there is no measured answer-accuracy improvement from explanations for this bot. The follower is intentionally naive; its errors do not estimate how a human or competent LLM would behave.

This is engineering validation, not a new scientific explanation method or a publishability result. Faults were inserted deliberately and do not estimate natural error rates. The narrow parser does not evaluate arbitrary prose, attack causality, evidence authenticity, missing-evidence partial bounds or adversarial tampering. Score integrity itself is assumed. No stronger attack detector was trained and no new attack coverage was gained.

PX-102 remains **no human results**. No people were simulated or enrolled. There were no LLM calls, AWS jobs or paid inference. A bot cannot establish whether explanations improve human accuracy, speed, confidence or SOC outcomes. The current automated tests can support a future reviewer experiment, and the duplicate case should be removed before that study is finalized.

## Use the bot

From this directory with the Praxis Python environment:

```
python cli.py ../explanation_trials_20261003/PX102_CASES.json --bot verifier
python audit.py
```

Input is a JSON case or list of cases with `case_id`, `member_probabilities` and optional `explanation`. Accepted explanation format is demonstrated in PX102_CASES.json. Responses contain a status, answer and, for contradictions, diagnostic numeric answer and reason.

All assigned cases and negative outcomes are retained in RESPONSES.json and RESULTS.json. This bot pilot is separate from PX-102's human-study records.
