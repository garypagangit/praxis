# Selective Disclosure of Executed Tests in Language-Model Code Revision

**Praxis 008 | Research report prepared for Gary Pagan | 17 September 2026**

**Review status:** Complete AI-assisted research report for human review. Author verification, academic eligibility, originality assessment, and advisor approval remain pending. This report consolidates completed experiments; it introduces no new model inference or retrospective change to the frozen protocols.

## Abstract

Genuine execution records can still be selectively disclosed. This study measures how that disclosure changes a language model's acceptance of a proposed code revision and tests an independent verification policy at a matched test budget. Qualification of 164 public HumanEvalPack problems yields 135 eligible canonical/buggy pairs, including 101 heldout source problems. A supplier acquires at most 16 observations and discloses at most two. Uniform disclosure samples acquired outcomes; selected disclosure withholds failures and chooses passing records when available, allowing fewer records or none. Under a prospectively frozen schema-constrained Qwen configuration, harmful native revisions are accepted in 12/101 cases with selected disclosure and 4/101 with uniform disclosure: +7.92 percentage points, with a 95% task-bootstrap interval of [2.97, 13.86] and Holm-adjusted one-sided p = .015625. Eight acceptances occur only under selected disclosure. Exploratory inspection finds that seven omit a failure visible in the uniform condition and two contain no selected tests. Devstral does not establish the same effect. The proposed hybrid independent-test policy fails its primary recommendation criteria for both reviewers. Neither reviewer exhibits a disclosure contrast among 34 harmful model-generated revisions. The contribution is a reproducible, bounded empirical characterization of a known evidence-selection threat, accompanied by a failed intervention and explicit transfer limits. Finite test labels, public-benchmark exposure, reused observations, and managed-model variability limit generalization.

**Keywords:** code revision; language models; selective disclosure; executable evidence; independent verification

## 1. Problem and research questions

A software assistant can propose replacing a working function and accompany that proposal with authentic test results. A receiving model then decides whether the evidence justifies accepting the replacement. Executing a test establishes what happened on that input. It does not establish that the supplier displayed an informative or representative sample of the observations it acquired. A harmful revision may pass several real tests while failing undisclosed ones.

This distinction matters in both directions. Preserving a correct program is useful, but refusing every change would also reject valid repairs. A meaningful evaluation must measure harmful canonical-to-buggy revisions and useful buggy-to-canonical repairs. It must also separate the model's judgment from any deterministic rule that overrides that judgment after a failed test.

Three questions organize the completed study:

1. **RQ1:** Does the complete passing-only disclosure policy increase harmful acceptance relative to uniform disclosure, with the code pair, supplier acquisition, prompt, and maximum display count fixed?
2. **RQ2:** Does an input- and edit-conditioned hybrid verification policy reduce harmful acceptance relative to equal-budget uniform independent testing while retaining useful repairs?
3. **RQ3:** Are comparable patterns observed for model-generated revisions, including explicitly requested semantic corruptions?

H1 tests the first contrast and H2 the second. Two reviewers contribute four primary tests. Generated-proposal comparisons are secondary. The supported result concerns one reviewer configuration and a compound disclosure intervention. It does not identify a new general defense or isolate why each individual decision changed.

### 1.1 Distinguishing the earlier artifact audit

Praxis 008 began with a narrower AutoDCWorkflow audit. That work examined released scoring functions, reference identities, negative fixtures, and selected queries; it was explicitly not a full pipeline or saved-model-performance reproduction. Its initial scorer credited only 111/142 identity fixtures. Subsequent offline repair passed 103 comparator controls, but source review retained only 40/142 tasks as provisionally purpose aligned. No new model calls occurred in that phase. Those findings motivated a different executable base. They do not reproduce or refute the complete data-cleaning debate study, and their denominators must not be merged with the code experiment. The evidence map preserves this lineage separately. [E01–E02]

## 2. Related work and contribution boundary

The closest conceptual prior is **Preregistered Belief Revision Contracts** (PBRC), which explicitly discusses query steering, selective evidence, and withholding in Section 9.2. Therefore, identifying selective truthful evidence as a threat is prior art. The present study measures a specific code-revision implementation. It does not instantiate PBRC's full router or nonempty-witness requirement; empty-disclosure acceptances consequently do not falsify its guarantees. [PBRC](https://arxiv.org/html/2604.15558v1#S9.SS2)

**When Helping Hurts and How to Fix It** studies harmful criticism in data cleaning and evaluates executable critics with evidence-gated revision. Evidence-grounded feedback is thus also established. Our manipulated variable is which genuine execution records accompany a fixed code replacement; our outcome is correctness under reserved executable tests. That differs from the data-cleaning paper's factual-consistency measure. Its published success should not be imported as a baseline score for this experiment. [Primary paper, Section 7](https://arxiv.org/html/2606.02866v1#S7)

**AI Control** already evaluates useful coding assistance under intentional subversion, including trusted monitoring and editing. Our instructed corruptions are bounded experimental proposals, not evidence of spontaneous strategic deception. [Primary paper](https://arxiv.org/abs/2312.06942) **DiffTGen** generates tests that expose overfitted patches, while **Poracle** tests preservation conditions. Both constrain claims that additional discriminating tests or behavior preservation are themselves novel. The hybrid here samples an existing input pool without executing candidates during selection and supplies neither system's full capabilities. [DiffTGen](https://qixin5.github.io/files/pdf/research/issta17identify.pdf), [Poracle](https://www.jooyongyi.com/papers/TOSEM23.pdf)

HumanEvalPack supplies public correct/buggy programs, and EvalPlus supplies expanded tests; neither benchmark's published model scores are a reproduction target. Expanded tests improve measurement while leaving correctness finite and conditional. [OctoPack](https://arxiv.org/abs/2308.07124), [EvalPlus](https://arxiv.org/abs/2305.01210) Test-based candidate selection and impact-guided testing also appear in CodeMonkeys, S*, and TDAD. The present static comparator does not establish superiority over those systems. [CodeMonkeys](https://arxiv.org/abs/2501.14723), [S*](https://arxiv.org/abs/2502.14382), [TDAD](https://arxiv.org/abs/2603.17973)

The bounded candidate contribution is a paired measurement with explicit acquisition/disclosure boundaries, both revision directions, complete assignment accounting, and a secondary generated-proposal cohort. A targeted primary-source check on 17 September 2026 supports this framing, not a claim of priority. The accompanying `PRIOR_WORK.md` records overlaps and what remains for human originality review.

## 3. Methods

### 3.1 Frozen design and version lineage

The original implementation was frozen at repository commit `162d2ab`; a prospective technical extension was frozen at `43b7d26`. The original source manifest remains unchanged. These are repository preregistrations, not externally certified registrations. The extension enabled provider-enforced JSON review output for Qwen after development-format failures, while retaining the scientific policies, review prompt, strict downstream parser, temperature, token cap, and statistical rules. [E03]

Original Qwen heldout reviews were gated and never executed. Its native development validity was 430/532; generated development validity was 308/370, both below the 95% threshold. The original native malformed responses included 102 cases after normal termination, rather than truncation. V2 contains new Qwen reviews and explicitly reuses designated Devstral native/generated-development observations and development proposals. It adds previously unrun generated-heldout work after development qualification. V1 and V2 must remain separate: reuse is neither a new trial nor independent replication, and these records cannot establish that schema enforcement caused a change in vulnerability. [E03–E04]

### 3.2 Tasks, finite outcome labels, and information separation

The sources are HumanEvalPack Python revision `9a41762f73a8cb23bb5811b73d5aab164efcf378`, HumanEvalPlus v0.1.10, and EvalPlus evaluator revision `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`. Qualification requires callable alignment, canonical success on original and reserved tests, reference completion, and an observed reserved failure for the buggy implementation. It admits 135/164 pairs: 34 development and 101 heldout. All 29 exclusions remain visible, including namespace-compatibility and reference-resource failures. The qualification audit passed 7,075 checks; this certifies faithful accounting rather than universal execution success. [E05]

Each qualified native pair is evaluated in both directions. A harmful revision changes a reserved-suite-passing program into a reserved-suite-failing program; a useful revision does the reverse. Unknown execution remains unknown. These are operational labels under a finite suite, not proofs of semantic correctness on every possible input.

The prepared corpus contains 123,981 distinct input fingerprints: 32,090 tool inputs and 91,891 reserved inputs. A fixed procedure separates supplier inputs W, independent verification inputs A, and reserved outcome inputs H. Their structural fingerprints are disjoint. Acquisition identities are committed before outcome lookup. H supplies evaluation labels and is withheld from actor interfaces. The selector receives source code and input features, but no expected outputs, pass/fail vectors, proposal intent, or H labels. The reviewer receives the task specification, both programs, a neutral recommendation, and displayed records. Its prompt warns that true observations may be selectively disclosed. Interface separation does not eliminate possible pretraining exposure to these public tasks. [E06]

### 3.3 Disclosure and independent verification

The supplier uniformly acquires up to 16 distinct observations from W. Both disclosure arms use the same acquisition. Uniform disclosure selects up to two acquired outcomes and can show failures. Selected disclosure filters to passing outcomes and selects a feature-similar pair when possible; otherwise it displays fewer records or none. Actual record count and outcome composition can therefore differ. This complete policy, rather than a count-matched passing-only selection heuristic, is H1's intervention.

Records include measured status and hashes binding the code, test, input, and expected-value identities. Input and expected-value previews have explicit truncation limits. Hashes bind the complete underlying payload. Independent-test arms share the selected W testimony and acquire up to eight additional inputs from A. They include uniform, edit-weighted, witness-complement-weighted, and hybrid acquisition; native reviews also include a no-witness arm. Fixed hash ordering is an offline control. [E03, E06]

The hybrid combines proximity to numeric/length boundaries implicated by edits, b(x), with structural distance from displayed witness inputs, d(x). Its weight is `1 + 2b(x) + d(x)`, with both features bounded in [0,1]. Missing boundary information or empty testimony gives the corresponding score zero. Sampling proceeds without replacement; each draw mixes 50% uniform sampling with 50% normalized feature weights. Edit-only and complement-only controls remove the other feature. No candidate execution or outcome lookup is permitted during input selection. The retained uniform component provides a standard finite-pool exploration guarantee, not a theorem that hybrid sampling outperforms uniform sampling. [E03]

### 3.4 Models and decision layers

Reviewers are `qwen.qwen3-coder-next` and `mistral.devstral-2-123b`, accessed through AWS Bedrock in `us-east-1`. Qwen also proposes one-shot repairs and instructed semantic corruptions without reserved-test feedback. Temperature is zero; review and proposal output caps are 1,024 and 2,048 tokens. Invalid reviews count as abstention. Recorded transport retries do not provide semantic retries selected for better outcomes. Programs execute through the frozen isolated worker and admission process, not directly in the analysis environment. [E03, E04]

Reviewer-only acceptance requires a valid accept response. Enforced acceptance additionally requires that no displayed authenticated test demonstrates a failure or error. This common veto is applied consistently; it must remain distinct from the acquisition-policy innovation. V1's gated observations remain nonexecutions rather than measured safe decisions.

### 3.5 Estimands and decision rules

H1 is selected-minus-uniform harmful reviewer acceptance. H2 is uniform-independent-minus-hybrid harmful enforced acceptance; positive values favor hybrid. Each source problem is an independent unit in the registered analysis. Multiple directions, acquisition replicates, and repeated reviews do not increase the independent task count. Primary model analyses use acquisition replicate zero. Offline analyses use budgets four and eight across 20 replicates, first averaging within source problem.

One-sided exact paired tests use discordant accept/keep outcomes. Holm adjustment covers all four primary tests, and 95% percentile intervals use 5,000 task-bootstrap draws. Invalid responses remain nonacceptances in assigned denominators; missing observations do not establish complete-data eligibility. The hybrid recommendation requires at least 40 harmful and 40 useful heldout tasks, harm reduction of at least five percentage points versus uniform A with an interval excluding zero, adjusted H2 p < .05, useful-retention lower bound above −5 points, favorable direction against edit-only selection, and complete required observations. A favorable secondary comparison cannot replace this rule. [E03, E07]

## 4. Results

### 4.1 Complete assignment accounting

V2 retains all 9,456 assigned review identities: 7,512 completed eligible reviews and 1,944 ineligible assignments. Of the completed reviews, 7,502 are valid. Its 328 generated-proposal assignments comprise 259 admitted, 58 ineligible, nine invalid, and two rejected proposals. Unchanged outputs are recorded separately; two admitted proposals are unchanged. Each version retains 131,200 offline assignment rows. These counts describe complete evidence accounting, not 9,456 independent experiments or a universally successful model interface. [E04, E07]

### 4.2 Four primary hypotheses

**Table 1. Native heldout harmful acceptance. Each arm has 101 source problems. Differences and confidence intervals are percentage points.**

| Contrast | Accepted, left/right | Difference | 95% interval | Holm-four p |
|---|---:|---:|---:|---:|
| Qwen H1: selected/uniform disclosure | 12/4 | +7.92 | [2.97, 13.86] | .015625 |
| Devstral H1: selected/uniform disclosure | 3/1 | +1.98 | [0.00, 4.95] | .750000 |
| Qwen H2: uniform A/hybrid, enforced | 3/4 | −0.99 | [−2.97, 0.00] | 1.000000 |
| Devstral H2: uniform A/hybrid, enforced | 0/0 | 0.00 | [0.00, 0.00] | 1.000000 |

Only Qwen H1 meets the primary statistical criterion. Four harmful revisions are accepted under both disclosure conditions, eight only under selected disclosure, none only under uniform disclosure, and 89 under neither. Both H1 arms have 101/101 valid responses. The raw exact p-value is .00390625; multiplying at its Holm step gives .015625. The supported effect is eight additional harmful acceptances among these 101 paired tasks. [E07–E08]

Devstral's H1 contrast is unsupported. Its observations are reused from V1: the adjusted p-value changes because other members of the four-test family change, not because Devstral supplied an independent replication. A confidence interval reaching zero and adjusted p = .75 do not establish equivalence or immunity.

H2 fails for both reviewers. Qwen numerically favors uniform testing, with three versus four enforced harmful acceptances; this is not a significant-worsening claim. Devstral has zero in both arms, leaving no observed benefit for hybrid. Its empirical zero-width interval does not guarantee population safety. Both full hybrid recommendation gates are false. [E07]

### 4.3 Useful repairs and the common veto

Useful enforced acceptance is 96/101 under both Qwen uniform A and hybrid, and 95/101 under both Devstral arms. Both paired useful differences are zero, with intervals [−2.97, 2.97] points and discordances in both directions. Useful retention satisfies its numerical component but cannot compensate for failed harm reduction and comparator requirements. The system is not merely preserving programs by rejecting every repair. [E07]

For Qwen harmful revisions, raw acceptance is 10/101 under uniform A and 11/101 under hybrid; enforcement reduces these to 3/101 and 4/101. Thus the authenticated-failure veto changes outcomes. That established veto is not evidence that the proposed sampling policy improves the harm/usefulness tradeoff. Qwen's harmful uniform-A arm also includes one invalid response, retained as nonacceptance. H1's clean validity does not imply every arm is entirely valid. [E08]

### 4.4 What changed in the eight selected-only acceptances

Only 60/101 harmful native proposals have two available passing supplier witnesses in acquisition replicate zero. The primary analysis retains all 101 tasks. Among the eight selected-only Qwen acceptances, seven omit a failed test visible under uniform disclosure. Six display two selected passing records, and two display no selected records against two failing uniform records. One of the six count-matched cases displays passing records in both arms, with different test identities. No discordance is an ordering-only change. [E08]

This is a post-result descriptive inspection, not a randomized mediation analysis. In particular, the two empty messages cannot support a claim that positive examples persuaded the reviewer. The single both-passing contrast cannot establish a geometric selection mechanism. The measured treatment combines filtering, withholding, changed record identities, and sometimes changed count. Separating those components requires a new prospective experiment.

### 4.5 Generated revisions and offline selection

The admitted heldout generated cohort contains 193 proposals across 100 source problems: 98 corruption proposals and 95 repair proposals. Reserved tests classify 34 as harmful, 90 as useful, and 69 as other transitions. Harmful and useful source sets overlap and must not be added as independent samples. [E09]

**Table 2. Secondary generated-heldout comparisons.**

| Outcome and contrast | Qwen | Devstral |
|---|---:|---:|
| Harmful reviewer acceptance, selected/uniform | 4/34 vs 4/34 | 1/34 vs 1/34 |
| Harmful enforced acceptance, uniform A/hybrid | 2/34 vs 1/34 | 1/34 vs 1/34 |
| Useful enforced acceptance, uniform A/hybrid | 87/90 vs 86/90 | 87/90 vs 88/90 |

Neither reviewer has an H1 discordance in this harmful generated cohort. The native disclosure contrast is not observed here. There are only 34 harmful tasks, below the 40-task recommendation requirement; this does not prove absence of an effect in a larger or different generated cohort. Qwen's one-pair hybrid improvement is secondary and cannot rescue the failed native H2. These are instructed corruptions, not a representative sample of naturally occurring model errors. [E08–E09]

Offline native acquisition at budget eight yields approximately 1.188 percentage points of uniform-minus-hybrid miss reduction, below the five-point practical criterion. A small edit-comparator gain does not replace the failed uniform comparison. The reused native vectors are not new observations. A disclosed secondary numerical erratum also corrects an exact-zero effect represented by floating-point arithmetic as approximately 4.08 × 10⁻¹⁹; it is interpreted as no directional benefit. Primary hypotheses and the overall recommendation are unchanged. [E10–E11]

## 5. Discussion and limitations

The result supports a practical distinction between evidence authenticity and evidence coverage. In one tested reviewer configuration, changing which genuine observations were visible increased harmful acceptance despite an explicit warning about selective disclosure. Preserving acquisition and disclosure records allows the omission pattern to be audited. The experiment does not validate a deployed reporting standard, establish general resistance to manipulation, or demonstrate a successful complex defense.

**Measurement limits.** Finite reserved tests can miss defects. A and H may disagree about a program's behavior, and qualification excludes tasks for compatibility or infrastructure reasons as well as substantive failures. The conclusion is conditional on the qualified cohort and its fixed execution/comparison contract. Native inserted bugs and instructed corruptions differ from real revision histories.

**Causal limits.** H1 changes a complete disclosure policy. Count, failure visibility, and selected identities are not separately randomized. The exploratory eight-case analysis supplies mechanism clues without identifying mediation. Managed services do not expose byte-pinned weights or sampling seeds; temperature zero does not remove all execution variability. V1's absent Qwen heldout calls prevent a causal comparison of schema enforcement.

**Statistical limits.** Source problems are reused across directions and policies. Task-based pairing and bootstrapping respect that structure, but sparse discordances and all-zero cells still limit precision. The four-test adjustment covers the stated family, not every secondary comparison or selection among earlier Praxis candidates. The generated null contrasts are descriptive, not equivalence results.

**Transfer and originality limits.** The positive finding is confined to schema-constrained Qwen on native function-level Python pairs. Devstral does not establish it; the smaller generated cohort does not exhibit it. Public-benchmark familiarity, narrow evidence previews, and fixed proposals constrain transfer to repository-scale agents. Closely related work already addresses selective evidence, executable criticism, and test-based patch checking. The candidate contribution is the explicit measurement and its boundaries. Its academic sufficiency remains an author/advisor decision.

The most informative follow-up would prospectively separate failure filtering, record count, and pairing, using a count-matched uniform-passing comparator and fresh source tasks. A policy-success study would also need stronger feasible differential/coverage comparators and enough qualified harmful generated revisions. Those are future studies, not unfinished conditions silently added to this completed experiment.

## 6. Reproducibility and verification

`EVIDENCE.json` maps the report's claim groups to repository-relative paths, SHA-256 hashes, and JSON pointers. It preserves original result bytes, version lineage, the failed initial numerical audit, and the correction. Archived full audits report 918,245 passing V1 checks and 1,099,300 passing amended V2 checks. Automated readiness passed 15/15 requirements; these are technical closure results, not human approval or novelty certification. [E11–E12]

On 17 September 2026, both public result packages were reprocessed with the existing archived `reproduce_statistics.py`, using Python 3.11.9 and NumPy 2.4.6. Every model and acquisition statistical field matched exactly, including the registered 5,000-draw bootstrap results. Only top-level provenance metadata is excluded from that comparison. The new receipts are in `verification/`. No model requests or candidate-program executions occurred. An additional direct recount independently checks the primary paired cells, exact p-values, and generated disclosure counts. [E13]

These checks reproduce analyses of retained observations; they do not recreate managed-service responses or rerun the entire private raw-request audit. A fresh provider experiment would be a replication attempt. The earlier data-cleaning audit remains a separate measurement-development record, and its completion is not represented as completion of the later model experiment.

## 7. Conclusion

Selective disclosure increases harmful native-code revision acceptance from 4/101 to 12/101 in the tested schema-constrained Qwen configuration. Eight acceptances are selected-only; most coincide with omission of a visible counterexample, including two cases with empty selected disclosure. The corresponding Devstral effect is unsupported, the proposed hybrid defense fails its primary criteria, and the disclosure contrast is not observed among 34 harmful generated revisions. The completed result supports a bounded empirical Praxis candidate with reproducible evidence. Author understanding, contribution sufficiency, and academic approval remain human decisions.

## References

1. Muennighoff, N., et al. *OctoPack: Instruction Tuning Code Large Language Models*. [arXiv:2308.07124](https://arxiv.org/abs/2308.07124).
2. Liu, J., Xia, C. S., Wang, Y., and Zhang, L. *Is Your Code Generated by ChatGPT Really Correct? Rigorous Evaluation of Large Language Models for Code Generation*. [arXiv:2305.01210](https://arxiv.org/abs/2305.01210).
3. Alqithami, S. *Preregistered Belief Revision Contracts*. [arXiv:2604.15558v1](https://arxiv.org/html/2604.15558v1).
4. Parmar, C., et al. *When Helping Hurts and How to Fix It: Multi-Agent Debate for Data Cleaning*. [arXiv:2606.02866v1](https://arxiv.org/html/2606.02866v1).
5. Greenblatt, R., et al. *AI Control: Improving Safety Despite Intentional Subversion*. [arXiv:2312.06942](https://arxiv.org/abs/2312.06942).
6. Xin, Q., and Reiss, S. P. *Identifying Test-Suite-Overfitted Patches through Test Case Generation*. ISSTA 2017. [Author manuscript](https://qixin5.github.io/files/pdf/research/issta17identify.pdf).
7. Ismayilzada, E., et al. *Poracle: Testing Patches under Preservation Conditions to Combat the Overfitting Problem of Program Repair*. [Author manuscript](https://www.jooyongyi.com/papers/TOSEM23.pdf).
8. Ehrlich, R., et al. *CodeMonkeys: Scaling Test-Time Compute for Software Engineering*. [arXiv:2501.14723](https://arxiv.org/abs/2501.14723).
9. Li, D., et al. S*: Test Time Scaling for Code Generation. [arXiv:2502.14382](https://arxiv.org/abs/2502.14382).
10. Alonso, P., Yovine, S., and Braberman, V. A. *TDAD: Test-Driven Agentic Development—Reducing Code Regressions in AI Coding Agents via Graph-Based Impact Analysis*. [arXiv:2603.17973](https://arxiv.org/abs/2603.17973).
