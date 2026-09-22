# Literature scope for a verified-action context experiment

**Reviewed:** September 22, 2026. **Decision:** proceed with a controlled development experiment; methodological novelty remains unestablished. This note supplies research context and claim boundaries, not completed experimental findings. It supplements the broader [role, authentication, and temporal-context novelty review](../host_auth_context/NOVELTY_REVIEW.md).

## 1. What this experiment can answer

**Research question:** When the current network transaction is ambiguous, does observable host role and strictly earlier activity improve recognition of verified remote actions versus verified file transfers, while avoiding false attack labels on ordinary administration and authorized uploads? How does that benefit change when relevant evidence arrives late or is missing?

This is worth testing because it separates three questions that coarse stage labels can collapse: what operation actually occurred, what evidence was available at decision time, and whether the operation was authorized in the scenario. The proposed contribution is a transparent measurement of those distinctions under controlled conditions. Generic context integration, real transaction generation, temporal reasoning, and abstention are not new methods.

The closest 2026 anchor explicitly recommends preceding-step context. A positive result would therefore test a published research direction under a more tightly observed, deliberately narrow task. It would not establish that a new APT detector, a novel fusion algorithm, or an operational security guarantee has been produced.

## 2. Closest primary sources

### CAM-LDS: the most direct motivation and overlap

**Status:** peer-reviewed journal article, published August 26, 2026. The final venue is *International Journal of Information Security*, not the venue string in an earlier preprint.

CAM-LDS executes Linux attack scenarios and associates host/network manifestations with attack steps. Section 6.3 explicitly proposes preceding-step context for actions resembling legitimate administration. Section 6.2 reports no concurrent benign user activity, possible delayed-event labeling errors, artificial spacing between steps, and uncertainty about whether every step completed. Consequently, a comparison with executed administrative/upload lookalikes and separately verified outcomes is a reasonable empirical extension. It is not the first proposal to interpret activity through surrounding context. [Final article, §§6.2–6.3](https://link.springer.com/article/10.1007/s10207-026-01318-x).

Our existing [CAM-LDS qualification](../camlds/QUALIFICATION.md) also limits local results to membership in author-designated manifestation windows; it does not certify maliciousness of each event.

### DEDALE and RESCOUSSE: benign background and attack generation already exist

**Status:** peer-reviewed ESORICS 2025 workshop chapter, first published online in 2026.

DEDALE combines a four-week environment, generated benign activity, and a multi-stage attack using the RESCOUSSE testbed. Its author documentation distinguishes benign, malicious, and attack-related traffic; some attack-related activity is not inherently malicious. Network annotation uses execution information with time, host, and sometimes port matching. This is direct prior art for combining ordinary activity with attack scenarios. Our narrower receipt-based operation verification cannot be presented as the invention of mixed benign/attack testbeds. [Publisher chapter](https://link.springer.com/chapter/10.1007/978-3-032-16092-8_1); [author project and labeling documentation](https://dedale.inria.fr/).

### Dataset-quality analysis: why plausible-looking lab scores can mislead

**Status:** peer-reviewed IEEE Symposium on Security and Privacy, 2025.

Liu and colleagues analyze endpoint benchmarks using background repetition and the distinctiveness of attack activity. Their experiments show that synthetic background can inflate true-negative performance and unusually conspicuous attacks can inflate true-positive performance. This directly motivates challenging legitimate lookalikes, crossed scenario schedules, and reporting behavior families separately. A high score on newly generated transactions alone does not establish generalization to enterprise activity. [Author paper](https://www.jdliu2.web.illinois.edu/papers/sp25-wwtawwtal.pdf); [author publication record](https://sts.cs.illinois.edu/papers/paper/WhatWeTalkAboutWhenW20250512.html).

### IMPROV: missing or disordered provenance is already a research problem

**Status:** peer-reviewed PRISM workshop paper, 2026; narrower evidence than a large operational evaluation.

Kimm and colleagues document missing edges, spurious paths, and out-of-order audit events. IMPROV obtains additional context from the operating system while processing audit data. It is a concrete provenance-repair mechanism, not a general guarantee that arbitrary missing historical evidence can be recovered. Our injected clock, delay, and log-removal conditions should therefore measure sensitivity to specified observations; they should not be called reconstruction of real lost enterprise evidence. [Official workshop paper](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf).

### SOCBED: reproducible execution and logging ablations are established

**Status:** peer-reviewed ACSAC conference paper, 2021; retained because it directly limits the generation-method novelty claim.

SOCBED provides reproducible, adaptable log generation. Its published evaluation artifacts include repeated executions across two physical host machines and two logging configurations. Thus a reproducible custom environment or a comparison of logging configurations is not, by itself, new research. The proposed lab must earn its value through a sharply defined question and auditable measurements. [Author evaluation repository](https://github.com/fkie-cad/socbed-eval-acsac-2021); [paper DOI](https://doi.org/10.1145/3485832.3488020).

### LMDG: additional direct overlap in fine-grained action labeling

**Status:** the reviewed author source is a 2025 arXiv preprint. A final peer-reviewed venue was not verified in this bounded review, so it is not counted as such here.

LMDG combines benign activity, multi-stage lateral-movement execution, system/network collection, and process-tree-based attack-step labeling. Its reported environment comprises 25 virtual machines and 35 movement attacks over 25 days. It is direct prior art against claiming that execution-linked, fine-grained movement labeling is new. The reviewed source does not establish our particular movement-versus-file-transfer comparison; that is a limitation of this review's evidence, not a claim that the paper omits every related experiment. [Author preprint](https://arxiv.org/abs/2508.02942).

## 3. The narrow contribution worth testing

**Proposed applied contribution:** a controlled, reproducible assessment of the incremental value of earlier observable activity and host roles for distinguishing transaction outcomes and scenario-defined misuse from legitimate lookalikes, with independent outcome receipts, matched information controls, and explicit evidence-availability stress tests.

This wording deliberately describes a measurement contribution. It does not assert that this exact combination has never been studied. The bounded review establishes direct overlap and useful motivation; it does not establish priority over all published work.

There are two possible useful findings. Context may improve a difficult distinction at a measurable false-alert cost. Alternatively, the experiment may identify conditions under which the available observations cannot support the distinction. Either can guide a better evaluation or collection design. Neither is automatically a completed, novel praxis contribution without stronger independent validation.

## 4. Keep operation, authorization, and observation separate

| Item | What can be verified | What must not be inferred automatically |
|---|---|---|
| Remote action | A receiving service executed a permitted operation and returned an outcome receipt | That a machine was compromised or malicious lateral movement occurred |
| File transfer | The receiver obtained the expected bytes and verified their content hash | That the bytes were stolen, sensitive, or sent without authorization |
| Failed attempt | A request was attempted and failed according to an explicit outcome record | Successful movement or completed transfer |
| Authorization | A frozen scenario policy identifies an approved or unapproved action | That ordinary transaction telemetry reveals the hidden policy |
| Missing evidence | A declared observation source was withheld or unavailable at the decision deadline | That the underlying operation never occurred |

The controller's intent and outcome ledger must remain separate from model features. A transaction identifier may join receipts during auditing, but must not encode the class, split, role, or scenario. Receipt verification performed after the event is valid for labels; it cannot silently become a feature for an earlier prediction.

**Identifiability limitation:** if an authorized and unauthorized action have exactly the same observable history and the relevant authorization policy is unavailable, the classifier has no evidence from which to recover the distinction. Preserve such cases as matched ambiguity tests. Do not make them separable by inserting scenario names, maliciousness flags, special payload text, fixed IDs, or artificial timing shortcuts into the input.

## 5. Minimum design requirements for an interpretable result

These are methodological recommendations for the new lab, not a claim that each has already been implemented.

1. **Use executed hard negatives.** Normal administration must perform real remote actions, and authorized uploads must transfer real bytes. Idle background is insufficient. Cross approved/unapproved intent with operation type, outcome, host role, payload size, and order where the scenario permits.
2. **Specify the decision deadline.** An after-completion interpretation may use completion evidence available by its deadline. A before-completion prediction may not. Report these as different tasks, not a single early-detection score.
3. **Verify outcomes independently of features.** Retain request/response agreement, remote-operation receipts, and sender/receiver byte hashes in a blinded label ledger. Include unsuccessful operations rather than equating attempted steps with successful ones.
4. **Separate independent executions.** Split whole freshly generated runs or scenario instances. The clean, delayed, and masked versions of a transaction remain paired observations of that same transaction. They are not additional independent attack executions.
5. **Control added information.** Compare current evidence, current plus roles, current plus earlier activity, and their combination. Add wrong-host or wrong-time history and matched observed-log volume/timing controls. These distinguish useful event meaning from an increase in evidence count.
6. **Prevent identity and schedule shortcuts.** Rotate or withhold host identities, cross roles with outcomes, randomize task order, and overlap benign/attack transaction sizes and timing. A deterministic role-to-label scenario tests memorization of its generator.
7. **Represent time explicitly.** Keep event time, observer time, and availability time. At a deadline, use only data actually available by then. Apply declared clock error, transport delay, and source removal to observations without changing the frozen outcome labels or query roster.
8. **Report the full cost.** Give confusion counts by actual operation and authorization, false accusations on admin/upload cases, missed harmful scenarios, ambiguous cases, and review workload. Report movement-to-transfer and transfer-to-movement mistakes separately from any-attack detection.
9. **Keep a future confirmation boundary.** Freeze the first complete analysis before inspecting its holdout. Any adaptation after its results needs a new independently generated confirmation set and a disclosed new protocol.

## 6. Realism and domain claims

| Execution environment | Defensible description | Additional evidence needed for a stronger claim |
|---|---|---|
| Separate local processes exchanging actual requests | Executed application transactions in a controlled local lab | Distinct host/OS effects, independent sensors, realistic authentication |
| Isolated services on AWS hosts | Executed transactions on the stated cloud topology | Enterprise deployment behavior; AWS itself adds no detection validity |
| Custom remote-action/file-transfer service | Service-level operation recognition with verified outcomes | Instrumented SSH/RDP/SMB/AD or other actual mechanisms before claiming coverage of those techniques |
| Injected loss, delay, or clock offsets | Sensitivity to the stated artificial observation failures | Measurements of real collection failures before calling the stress distribution representative |
| Repeated scripted scenarios | Generalization across the specified generated executions | Distinct campaigns, users, environments, and unseen implementation families |

A controlled lab can repair the immediate uncertainty about whether a transaction completed and whether its evidence was available. It cannot reproduce an entire adversary merely by assigning stage labels. Do not call a custom-service task operational APT detection, verified malicious lateral movement, prevented exfiltration, or reconstruction of an attack campaign. Those claims require evidence beyond this experiment.

## 7. References

Kimm, H., Mishra, S., & Sekar, R. (2026). Minding the gap: Bridging causal disconnects in system provenance. In *Workshop on Attack Provenance, Reasoning, and Investigation for Security in the Monitored Environment (PRISM 2026)*. Internet Society. https://doi.org/10.14722/prism.2026.23023

Landauer, M., Hotwagner, W., Boenke, T., Skopik, F., & Wurzenberger, M. (2026). CAM-LDS: Cyber attack manifestations for automatic interpretation of system logs and security alerts. *International Journal of Information Security, 25*, Article 148. https://doi.org/10.1007/s10207-026-01318-x

Lanvin, M., & Majorczyk, F. (2026). Get out of DEDALE with RESCOUSSE: A new dataset and testbed for evaluating the detection of APT attacks among network and system logs. In R. Laborde, J. Garcia-Alfaro, G. Blanc, P.-F. Gimenez, H. Kalutarage, N. Yanai, A. Shukla, S. Pirbhulal, J. Posegga, & K.-Y. Lam (Eds.), *Computer security. ESORICS 2025 international workshops* (Lecture Notes in Computer Science, Vol. 16232, pp. 3–23). Springer. https://doi.org/10.1007/978-3-032-16092-8_1

Liu, J., Inam, M. A., Goyal, A., Riddle, A., Westfall, K., & Bates, A. (2025). What we talk about when we talk about logs: Understanding the effects of dataset quality on endpoint threat detection research. In *2025 IEEE Symposium on Security and Privacy (SP)* (pp. 112–129). IEEE. [Author paper](https://www.jdliu2.web.illinois.edu/papers/sp25-wwtawwtal.pdf).

Mabrouk, A., Hatem, M., Mamun, M., & Saad, S. (2025). *LMDG: Advancing lateral movement detection through high-fidelity dataset generation* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2508.02942

Uetz, R., Hemminghaus, C., Hackländer, L., Schlipper, P., & Henze, M. (2021). Reproducible and adaptable log data generation for sound cybersecurity experiments. In *Proceedings of the 37th Annual Computer Security Applications Conference* (pp. 690–705). Association for Computing Machinery. https://doi.org/10.1145/3485832.3488020
