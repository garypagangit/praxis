# PX-062 Provenance and Existence Gate for Coding-Agent Skills

Date: 2026-07-24
Status: Gate 0 passed; public-corpus Gate 1 completed negative for provenance-only defense; live-model hallucination Gate 2 benchmark frozen and awaiting model outputs.

## Literature basis

Qu et al., *Supply-Chain Poisoning Attacks Against LLM Coding Agent Skill Ecosystems* (arXiv:2604.03081), demonstrate Document-Driven Implicit Payload Execution across coding-agent frameworks. The paper evaluates the post-loading phase and explicitly assumes retrieval succeeds; end-to-end retrieval validation is left to future work. Its defense evaluation covers SkillScan, while dynamic sandboxing and LLM-based auditing remain untested.

Original paper: https://arxiv.org/abs/2604.03081

## Praxis extension

PX-062 tests whether a deterministic admission gate can prevent an agent from loading a skill unless all of the following are true:

1. The requested skill name and version exist in a frozen registry.
2. The local manifest exists.
3. The local content hash matches the registry-pinned hash.
4. The registry record has a valid signature from the expected registry authority.
5. The requested version exactly matches the pinned version.

This is an inferred defense extension. The source paper demonstrates the attack surface but does not evaluate hash pinning or signed-registry admission.

## Research questions

- RQ1: Does the full gate block nonexistent, tampered, unsigned, wrong-signer, wrong-version, and missing-manifest cases without rejecting more than 5% of legitimate pinned skills?
- RQ2: Which deterministic control is necessary? Compare existence-only, hash-only, signature-only, and full provenance policies.
- RQ3: Do coding models invent nonexistent skill names when asked to solve tasks using an agent skill registry?
- RQ4: Does existence-constrained decoding or post-generation verification reduce invented-skill actions without materially reducing legitimate task completion?

## Frozen Gate 0 hypotheses

| ID | Hypothesis | Pass criterion |
|---|---|---|
| H1 | Full provenance admission blocks all inert attack cases. | Attack escape rate = 0. |
| H2 | Full provenance admission preserves clean utility. | Clean false-reject rate <= 5%. |
| H3 | Every decision is auditable. | Decision-trace completeness = 100%. |

Gate 0 validates software logic only. It cannot establish the effectiveness of a production signing system or a scientific defense result.

## Planned live gates

### Gate 1 - public registry and tamper corpus

Freeze a public set of legitimate skills, their exact repository commits, manifests, and file hashes. Create inert copies containing harmless marker-only modifications. Test legitimate false rejects, tampered-file escapes, rollback/version attacks, missing files, and registry equivocation. Use real public-key signatures or Sigstore-style attestations rather than the Gate 0 fixture authenticator.

### Gate 2 - skill-name hallucination

Freeze tasks that require no skill, one known skill, or an unavailable capability. Run at least two models under:

1. open-ended skill recommendation;
2. registry-constrained recommendation;
3. open-ended recommendation plus deterministic existence verification.

Primary metrics: nonexistent-name rate, attempted-load rate, corrected-after-verification rate, legitimate task success, and abstention rate. Names must be checked against a timestamped registry snapshot. Model outputs and registry evidence are sealed before scoring.

### Gate 3 - isolated agent execution

Use marker-only payloads in a network-disabled container. Compare no gate, static scan, provenance gate, and combined controls. Record load, code-generation, and marker-execution outcomes separately. No destructive, exfiltration, persistence, or credential payloads are permitted.

## Claim boundary

The source paper establishes that poisoned skills can be an action-space supply-chain channel. PX-062 tests a preventive admission control and a separate registry-hallucination hypothesis. A Gate 0 pass is only an implementation result; scientific claims require frozen public-registry and live-model gates.
