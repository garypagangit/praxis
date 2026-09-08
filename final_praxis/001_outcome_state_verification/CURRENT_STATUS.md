# Final Praxis 001 current execution status

Updated 2026-09-08. **Protocol v2 frozen; 16-case real model pilot independently verified; 400-case discovery running. No discovery result is claimed here.**

Active protocol SHA-256: `eb5f66c216cab7ca88660211c437a2ea366978fdaf32dc4e60ad6d87e89a58e1`.

The v2 Qwen agent and distinct Mistral judgment pilot completed all 16 planned cases on real CUDA endpoints. Independent verification passed both in the cloud and after local artifact transfer. The 400-case discovery agent phase launched at 21:52:15 UTC. The root orchestration controls cloud execution and authoritative run IDs.

The pilot exposed a model-output limitation: Mistral used numeric `success` values instead of required booleans in 10 of 16 primary judgments. Every response ended normally; the frozen parser retained these as malformed rejection outcomes. No prompt, parser, token budget, task, or threshold was changed in response. Final interpretation must distinguish protocol adherence from substantive evaluator accuracy.

Infrastructure evidence: all 140 preserved fixture records replay correctly; 18 focused tests pass, including negative tamper tests and independent reconstruction of all 400 planned controlled-state constructions. These checks are not scientific outcomes.

The earlier `README.md`, proposal documents, and Gate 3 notes are preserved historical design evidence; their older preparation/blocked status is superseded by this execution status and the dated amendments. The first-version protocol and every input are archived in `history/protocol_v1_20260908/`. Any v1 pilot output remains historical infrastructure evidence only.

The experiment explicitly separates real-model natural action states from imposed controlled-state outcomes. The primary scientific estimand is the learned judge's disagreement with outcome predicates under limited observations, with a 40-case full-state judge diagnostic. It is not a natural failure prevalence estimate or a proof that the deterministic oracle is universally correct.
