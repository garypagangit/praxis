# PX-104 — Automated review of warning-loss explanations

This is a deterministic software-bot pilot, not an LLM evaluation or human participant study. PX-102 human results remain unmeasured. The cases have been exposed; this is not blinded or independent validation.

Use all 12 PX-102 cases. Freeze source, protocol and case/answer-key hashes before running. The reviewer cannot access answer keys; a separate scoring step reads the key. Check for identical score vectors and report unique counts. Do not treat duplicate cases as independent evidence.

Bots: (1) score calculator reconstructs each member argmax and mean argmax; (2) explanation follower parses the supplied sentence and answers from it; (3) verifying bot reconstructs the scores and verifies all three explanation claims, returning a contradiction or abstaining when data are missing. Ties use first class, matching saved decision semantics. Successful score calculations are an engineering baseline, not a new detection result.

Fixed conditions on every case: scores only; valid explanation; incorrect member-warning count; inverted mean-warning claim; inverted OR-warning claim; missing first member vector. False explanations are deliberate integrity challenges, not naturally occurring error rates. Verifying bot must reject contradictions and abstain with missing vectors. On contradictions retain the numeric answer separately for diagnosis, but do not authorize accepting the explanation. On incomplete evidence do not infer a complete-ensemble decision.

Metrics: answer accuracy over all 12 assigned cases (abstentions count as nonanswers); answered-case accuracy; valid explanation acceptance; contradiction rejection; incomplete evidence abstention; informational correctness of claims. Use exact counts without population confidence claims. Measure neither simulated analyst time nor human trust. Existing warning/case/episode performance is unchanged by this review experiment.

Hypotheses: the verifier reproduces every complete-evidence gold answer, accepts every valid explanation, rejects every deliberately contradictory explanation, and abstains on every incomplete-evidence case. The explanation follower is a naive control, not a stand-in for an analyst or a competent LLM. Additional independent review cases and real participants are required for broader claims.
