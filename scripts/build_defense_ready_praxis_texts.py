from __future__ import annotations

from pathlib import Path
from textwrap import dedent


OUT_DIR = Path("reports/praxis_defense_ready_full_praxis_20260706")


COMMON_APA_NOTE = (
    "APA reference check status: External bibliographic entries were checked "
    "against primary publisher, arXiv, ACL Anthology, USENIX, OpenReview, "
    "MITRE, or project pages on 2026-07-06 where available. Local Praxis "
    "evidence artifacts are cited as repository reports because they are the "
    "primary experimental record for the defended claims."
)


COMMON_ACRONYMS = [
    ("APA", "American Psychological Association"),
    ("APT", "Advanced Persistent Threat"),
    ("ATT&CK", "Adversarial Tactics, Techniques, and Common Knowledge"),
    ("CI", "Confidence Interval"),
    ("CTI", "Cyber Threat Intelligence"),
    ("F1", "Harmonic mean of precision and recall"),
    ("GMR", "Graphical Methodology of Research"),
    ("LLM", "Large Language Model"),
    ("MCQ", "Multiple-Choice Question"),
    ("MoE", "Mixture of Experts"),
    ("MRR", "Mean Reciprocal Rank"),
    ("RAG", "Retrieval-Augmented Generation"),
    ("SVD", "Singular Value Decomposition"),
    ("TTA", "Test-Time Adaptation"),
    ("TTP", "Tactics, Techniques, and Procedures"),
]


REFERENCE_POOL = {
    "attack": (
        "Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., "
        "Pennington, A. G., & Thomas, C. B. (2020). MITRE ATT&CK: Design "
        "and philosophy. The MITRE Corporation. "
        "https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy"
    ),
    "tent": (
        "Wang, D., Shelhamer, E., Liu, S., Olshausen, B., & Darrell, T. "
        "(2021). Tent: Fully test-time adaptation by entropy minimization. "
        "International Conference on Learning Representations. "
        "https://openreview.net/forum?id=uXl3bZLkr3c"
    ),
    "graphsage": (
        "Hamilton, W. L., Ying, R., & Leskovec, J. (2017). Inductive "
        "representation learning on large graphs. Advances in Neural "
        "Information Processing Systems, 30. "
        "https://papers.nips.cc/paper/6703-inductive-representation-learning-on-large-graphs"
    ),
    "rag": (
        "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., "
        "Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., "
        "Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation "
        "for knowledge-intensive NLP tasks. Advances in Neural Information "
        "Processing Systems, 33. https://arxiv.org/abs/2005.11401"
    ),
    "ctibench": (
        "Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). "
        "CTIBench: A benchmark for evaluating LLMs in cyber threat "
        "intelligence. arXiv. https://arxiv.org/abs/2406.07599"
    ),
    "qwen": (
        "Qwen Team. (2025). Qwen2.5 technical report. arXiv. "
        "https://arxiv.org/abs/2412.15115"
    ),
    "qwen_coder": (
        "Hui, B., Yang, J., Cui, Z., Yang, J., Liu, D., Zhang, L., "
        "Liu, T., Zhang, J., Yu, B., Lu, K., Dang, K., Fan, Y., "
        "Zhang, Y., Yang, A., Men, R., Huang, F., Zheng, B., Miao, Y., "
        "Quan, S., Feng, Y., Ren, X., Ren, X., Zhou, J., & Lin, J. "
        "(2024). Qwen2.5-Coder technical report. arXiv. "
        "https://arxiv.org/abs/2409.12186"
    ),
    "falsecite": (
        "Mao, N., Kaushik, V., Shivkumar, S., Sharafoleslami, P., "
        "Zhu, K., & Dev, S. (2025). Visualizing and benchmarking LLM "
        "factual hallucination tendencies via internal state analysis and "
        "clustering. Proceedings of the 14th International Joint Conference "
        "on Natural Language Processing and the 4th Conference of the "
        "Asia-Pacific Chapter of the Association for Computational "
        "Linguistics: Student Research Workshop, 289-298. "
        "https://aclanthology.org/2025.ijcnlp-srw.24/"
    ),
    "halluhard": (
        "Fan, D., Delsad, S., Flammarion, N., & Andriushchenko, M. "
        "(2026). HalluHard: A hard multi-turn hallucination benchmark. "
        "arXiv. https://arxiv.org/abs/2602.01031"
    ),
    "package_hallucination": (
        "Spracklen, J., Wijewickrama, R., Sakib, A. H. M. N., Maiti, A., "
        "Viswanath, B., & Jadliwala, M. (2025). We have a package for you! "
        "A comprehensive analysis of package hallucinations by code "
        "generating LLMs. 34th USENIX Security Symposium, 3687-3706. "
        "https://www.usenix.org/conference/usenixsecurity25/presentation/spracklen"
    ),
    "standing_committee": (
        "Wang, Y., Xu, Y., Shen, N., Su, J., Huang, J., & Zhu, Z. "
        "(2026). The illusion of specialization: Unveiling the "
        "domain-invariant standing committee in mixture-of-experts models. "
        "Proceedings of the 64th Annual Meeting of the Association for "
        "Computational Linguistics. https://arxiv.org/abs/2601.03425"
    ),
    "olmoe": (
        "Muennighoff, N., Soldaini, L., Groeneveld, D., Lo, K., "
        "Morrison, J., Min, S., Shi, W., Walsh, P., Tafjord, O., "
        "Lambert, N., Gu, Y., Arora, S., Bhagia, A., Schwenk, D., "
        "Wadden, D., Wettig, A., Hui, B., Dettmers, T., Kiela, D., "
        "Farhadi, A., Smith, N. A., & Hajishirzi, H. (2024). OLMoE: "
        "Open mixture-of-experts language models. arXiv. "
        "https://arxiv.org/abs/2409.02060"
    ),
    "geiping": (
        "Geiping, J., McLeish, S., Jain, N., Kirchenbauer, J., "
        "Singh, S., Bartoldson, B. R., Kailkhura, B., Bhatele, A., "
        "& Goldstein, T. (2025). Scaling up test-time compute with "
        "latent reasoning: A recurrent depth approach. arXiv. "
        "https://arxiv.org/abs/2502.05171"
    ),
    "praxis_tracker": (
        "Praxis Research. (2026). Praxis research experiment tracker "
        "[Repository report]. reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html"
    ),
}


PROJECTS = [
    {
        "id": "PX-001",
        "file": "PX001_SAFETY_GATED_TTA_FULL_PRAXIS_20260706.txt",
        "title": "Safety-Gated Test-Time Adaptation for Streaming APT Detection",
        "status": "Defense-ready positive",
        "thesis": (
            "A streaming intrusion detector can use tightly gated, unlabeled "
            "test-time adaptation to recover weak early-stage attack detection "
            "while preserving high-risk Data Exfiltration behavior under a "
            "locked source-file shift."
        ),
        "abstract": (
            "This praxis evaluates a safety-gated no-label test-time adaptation "
            "strategy for streaming APT stage detection. The defended result "
            "shows that a locked selective BatchNorm adaptation policy improved "
            "Macro-F1 from 0.7685 to 0.8658 and Reconnaissance F1 from 0.0250 "
            "to 0.5050 while preserving Data Exfiltration F1 and limiting "
            "overrides to 0.0470. A seven-seed defense extension preserved the "
            "conclusion, while DAPT2020 remains an external-validity boundary."
        ),
        "keywords": "test-time adaptation, APT detection, safety gate, source shift, intrusion detection",
        "motivation": (
            "Security operations need detectors that can adapt to stream shift "
            "without allowing adaptation to damage high-risk attack classes. "
            "PX-001 targets that practical tension by combining TTA with an "
            "explicit deployment safety gate."
        ),
        "problem": (
            "Unlabeled target streams can expose rare-stage failure modes, but "
            "naive online adaptation can introduce unsafe prediction changes. "
            "The problem is to recover rare Reconnaissance detection without "
            "sacrificing Data Exfiltration stability."
        ),
        "objectives": [
            "Measure the frozen support-floor detector under held-out source-file shift.",
            "Apply a validation-selected selective TTA policy without test-label tuning.",
            "Evaluate whether Reconnaissance and Macro-F1 improve under locked replay.",
            "Audit whether high-risk Data Exfiltration predictions remain protected.",
        ],
        "research_questions": [
            ("RQ1", "Can no-label TTA improve rare-stage detection under source-file shift?"),
            ("RQ2", "Can a selective safety gate preserve Data Exfiltration behavior?"),
            ("RQ3", "Is the gain distinct from simply rejecting uncertain predictions?"),
            ("RQ4", "Does the effect persist across a defense hardening replay?"),
        ],
        "hypotheses": [
            ("H1", "Locked selective TTA improves Macro-F1 by at least 0.05."),
            ("H2", "Locked selective TTA improves Reconnaissance F1 by at least 0.25."),
            ("H3", "Locked selective TTA does not reduce Data Exfiltration F1."),
            ("H4", "The override rate remains bounded at or below 0.05."),
        ],
        "scope": "Unraveled APT feature pipeline, held-out source-file split, frozen support-floor MLP, locked selective TTA replay.",
        "limitations": "Does not prove universal APT detection or DAPT2020 TTA transfer; DAPT2020 is a negative external-validity boundary.",
        "themes": [
            ("Streaming cyber detection under distribution shift", "APT stage classifiers face changing source files, attack-stage imbalance, and unstable rare-class support."),
            ("Fully test-time adaptation", "TTA literature motivates source-free adaptation, but deployment safety requires gates beyond aggregate accuracy."),
            ("Safety-gated model updates", "Selective overrides and protected high-risk classes convert an adaptation method into a defensible operational control."),
            ("Evaluation under locked replay", "Validation-selected thresholds and locked final replay separate experimental evidence from post-hoc tuning."),
        ],
        "gap": "Prior TTA work demonstrates adaptation under shift, but the Praxis gap is conservative class-protected adaptation for streaming APT stage detection.",
        "experiments": [
            ("Experiment 1", "Frozen source-shift baseline", "Evaluate the support-floor MLP on the held-out source-file stream.", "Frozen Macro-F1 0.7685; Reconnaissance F1 0.0250; Data Exfiltration F1 0.9157."),
            ("Experiment 2", "Selective TTA gate", "Apply locked BatchNorm adaptation with protected Data Exfiltration and Reconnaissance rescue rules.", "Locked TTA Macro-F1 0.8658; Reconnaissance F1 0.5050; Data Exfiltration F1 0.9202."),
            ("Experiment 3", "Matched confidence-reject control", "Compare against a frozen rejection/control policy to test whether uncertainty rejection explains the gain.", "Matched-rate frozen reject did not recover Reconnaissance, supporting the adaptation-specific claim."),
            ("Experiment 4", "Seven-seed and external boundary audit", "Repeat defense hardening and preserve DAPT2020 as external-validity boundary.", "Seven-seed Macro-F1 improved from 0.7165 to 0.8341 and Recon F1 from 0.0615 to 0.5219; changed-from-DE count 0."),
        ],
        "datasets": [
            "Unraveled APT feature pipeline and held-out source-file split.",
            "DAPT2020 external-validity boundary check.",
        ],
        "metrics": "Accuracy, Macro-F1, class F1, override rate, changed-from-DE count, seven-seed mean and variation.",
        "validation": "Locked replay, seven-seed hardening, matched confidence-reject comparison, and explicit DAPT2020 boundary.",
        "assumptions": "Source-file split approximates deployment stream shift; Data Exfiltration protection is a higher-priority safety constraint than unconstrained macro optimization.",
        "result_summary": [
            "Accuracy improved from 0.8984 to 0.9243.",
            "Macro-F1 improved from 0.7685 to 0.8658.",
            "Reconnaissance F1 improved from 0.0250 to 0.5050.",
            "Data Exfiltration F1 remained stable, 0.9157 to 0.9202.",
        ],
        "contributions": [
            "A class-protected TTA pattern for streaming cyber detection.",
            "A locked replay methodology for adaptation under source-file shift.",
            "Evidence that rare-stage recovery can coexist with bounded override rates.",
        ],
        "practitioner_recs": [
            "Use validation-selected gates before deployment, not post-hoc threshold tuning.",
            "Protect destructive/high-risk classes from adaptation overrides.",
            "Treat external datasets as boundary tests before claiming generality.",
        ],
        "future": [
            "Replicate on additional labeled APT/provenance streams.",
            "Study calibrated uncertainty gates and per-stage review routing.",
            "Test whether the same pattern holds for graph or temporal detectors.",
        ],
        "evidence": [
            "reports/tta_streaming_apt/TTA_FUNCTIONING_CAPABILITY_REPORT_20260513.md",
            "reports/tta_streaming_apt/LOCKED_FINAL_REPLAY_20260509.md",
            "runs/tta-defense-hardening-defense-audit-20260630/PRAXIS06_TTA_DEFENSE_HARDENING_REPORT_20260513.md",
            "scripts/run_tta_locked_final.py",
            "scripts/run_tta_defense_hardening.py",
        ],
        "code": [
            ("A.1", "scripts/run_tta_streaming_apt_pilot.py", "Builds the initial streaming APT pilot and baseline metrics."),
            ("A.2", "scripts/run_tta_locked_final.py", "Executes the locked selective TTA replay."),
            ("A.3", "scripts/run_tta_defense_hardening.py", "Runs the seven-seed defense hardening audit."),
            ("A.4", "reports/praxis_final_positive_reports_20260701/PX001_FINAL_REPORT_SAFETY_GATED_TTA.md", "Portable audit code appendix for claim checks."),
        ],
        "references": ["tent", "attack", "praxis_tracker"],
    },
    {
        "id": "PX-002",
        "file": "PX002_ATTACK_TTP_PROFILE_RETRIEVAL_FULL_PRAXIS_20260706.txt",
        "title": "Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets",
        "status": "Package-ready bounded lookup-style positive; supporting result only",
        "thesis": (
            "Small observed ATT&CK technique sets can retrieve likely group "
            "profiles under a known-profile lookup protocol, supporting analyst "
            "triage without claiming actor authorship or robust attribution."
        ),
        "abstract": (
            "This praxis evaluates whether partial observed ATT&CK TTP sets can "
            "retrieve likely group profiles. Under the standard five-shot lookup "
            "protocol, overlap cosine reached top-5 accuracy 0.960 and SVD "
            "reached 0.879, compared with random 0.028 and frequency prior 0.041. "
            "A defense audit demotes the result from defense-pillar status because "
            "leave-query-out overlap collapses to 0.000 and SVD weakens to 0.299."
        ),
        "keywords": "ATT&CK, TTP retrieval, analyst triage, GraphSAGE, profile lookup",
        "motivation": "Analysts often begin with partial TTP observations and need bounded candidate shortlists rather than premature actor attribution.",
        "problem": "Group profiles overlap and curated ATT&CK data can make lookup appear stronger than it would be under hidden-edge or report-level attribution conditions.",
        "objectives": [
            "Formalize few-shot ATT&CK group-profile retrieval.",
            "Benchmark overlap and SVD against random and frequency floors.",
            "Retain GraphSAGE as a negative learned-embedding boundary.",
            "Audit anti-tautology and noisy-query stress before promotion.",
        ],
        "research_questions": [
            ("RQ1", "Can five observed ATT&CK techniques retrieve the correct group profile?"),
            ("RQ2", "Do simple baselines exceed random and frequency floors?"),
            ("RQ3", "Does GraphSAGE improve the retrieval result?"),
            ("RQ4", "Does the result survive defense-style stress tests?"),
        ],
        "hypotheses": [
            ("H1", "Standard five-shot overlap and SVD top-5 accuracy exceed 0.80."),
            ("H2", "Random and frequency floors remain far below overlap/SVD."),
            ("H3", "GraphSAGE does not clear promotion unless it beats SVD."),
            ("H4", "Leave-query-out stress determines whether the result can be a defense pillar."),
        ],
        "scope": "MITRE ATT&CK group-technique profile matrix, 174 groups, 697 techniques, 4546 edges, 121 eligible groups.",
        "limitations": "Not CTI prose attribution, not actor authorship, not a robust defense mechanism, and not a GraphSAGE win.",
        "themes": [
            ("ATT&CK as a curated adversary behavior graph", "ATT&CK provides a practical group-technique structure for profile retrieval."),
            ("Few-shot retrieval and analyst triage", "Top-k retrieval can narrow attention without producing final attribution."),
            ("Graph embeddings versus simple baselines", "GraphSAGE must beat overlap/SVD before a graph-neural claim is credible."),
            ("Anti-tautology stress testing", "Leave-query-out stress separates lookup utility from stronger generalization claims."),
        ],
        "gap": "Prior profile or attribution work often risks overclaiming; the Praxis gap is a bounded retrieval protocol with explicit demotion boundaries.",
        "experiments": [
            ("Experiment 1", "Standard five-shot profile lookup", "Sample five techniques from each eligible group and rank candidates.", "Overlap top-5 0.960; SVD top-5 0.879; median rank 1.0."),
            ("Experiment 2", "Floor and degree-bucket checks", "Compare against random/frequency floors and degree buckets.", "Random top-5 0.028; frequency top-5 0.041; overlap/SVD remain above floors across buckets."),
            ("Experiment 3", "GraphSAGE negative gate", "Test whether learned graph embeddings beat simple baselines.", "GraphSAGE known-profile top-5 0.060 versus SVD 0.926 and overlap 0.985."),
            ("Experiment 4", "Defense audit stress", "Run noisy-query and leave-query-out tests.", "Noisy overlap 0.788; noisy SVD 0.577; leave-query-out overlap 0.000; leave-query-out SVD 0.299."),
        ],
        "datasets": ["MITRE ATT&CK Enterprise STIX group-technique relationships."],
        "metrics": "Top-1, Top-5, Top-10, MRR, median rank, degree-bucket top-5, noisy-query and leave-query-out stress metrics.",
        "validation": "Fresh rerun on 2026-07-06 reproduced closeout status and bounded lookup-only defense-audit status.",
        "assumptions": "Known-profile lookup is useful for triage, but not sufficient for attribution claims.",
        "result_summary": [
            "Standard five-shot lookup is strong.",
            "GraphSAGE is negative and must not be pitched as positive.",
            "Defense audit demotes the work to bounded lookup utility.",
        ],
        "contributions": [
            "A formal ATT&CK TTP-set lookup protocol.",
            "A clear boundary between profile retrieval and attribution.",
            "A model of honest demotion when stress tests fail.",
        ],
        "practitioner_recs": [
            "Use as a candidate shortlist, never as final attribution.",
            "Display overlap evidence and uncertainty to analysts.",
            "Require independent report, infrastructure, or malware evidence before attribution.",
        ],
        "future": [
            "Add temporal ATT&CK release drift splits.",
            "Test report-extracted TTP noise rather than sampled profile TTPs.",
            "Add metadata/text hybrid retrieval only with labeled report evidence.",
        ],
        "evidence": [
            "reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md",
            "reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md",
            "reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md",
            "scripts/run_attack_ttp_retrieval_closeout.py",
            "scripts/audit_px002_ttp_retrieval_defense.py",
        ],
        "code": [
            ("A.1", "scripts/run_attack_ttp_retrieval_closeout.py", "Standard retrieval and closeout analysis."),
            ("A.2", "scripts/run_attack_ttp_graph_embedding_baseline.py", "Shared ATT&CK matrix loader and rank metrics."),
            ("A.3", "scripts/run_attack_ttp_graphsage_pilot.py", "Failed GraphSAGE pilot retained as negative boundary evidence."),
            ("A.4", "scripts/audit_px002_ttp_retrieval_defense.py", "Noisy-query and leave-query-out defense audit."),
        ],
        "references": ["attack", "graphsage", "ctibench", "praxis_tracker"],
    },
    {
        "id": "PX-003/PX-034",
        "file": "PX003_PX034_CTI_EVIDENCE_ROUTING_FULL_PRAXIS_20260706.txt",
        "title": "Retrieval-Conditioned CTI Compliance with Source-Conflict Routing",
        "status": "Defense-ready positive",
        "thesis": (
            "Per-question ATT&CK evidence improves strict CTI answer compliance, "
            "and source-conflict routing can identify evidence strata for direct "
            "answering, abstention, or review."
        ),
        "abstract": (
            "This praxis evaluates retrieval-conditioned CTI multiple-choice "
            "answering using ATT&CK relationship evidence and a source-conflict "
            "router. On the locked decisive evidence-addressable slice, "
            "relationship evidence improves accuracy over vanilla prompting "
            "across Llama and Qwen families, including Qwen2.5-7B from 0.623 "
            "to 0.906. A full 500-row audit shows relationship evidence improves "
            "accuracy from 0.614 to 0.822 while narrowing the router claim to "
            "source-support risk stratification."
        ),
        "keywords": "CTI, retrieval-augmented generation, MITRE ATT&CK, source conflict, router",
        "motivation": "CTI assistants need answer discipline grounded in authoritative evidence rather than broad prompting or unsupported generation.",
        "problem": "Vanilla LLM answers can be invalid, unsupported, or brittle; broad domain seeding failed, requiring question-specific evidence and routing.",
        "objectives": [
            "Build a label-free ATT&CK evidence-addressable CTI-MCQ slice.",
            "Compare relationship evidence to vanilla, broad seed, technique-only, random, and empty controls.",
            "Replicate across model families.",
            "Classify source-support buckets for risk-aware routing.",
        ],
        "research_questions": [
            ("RQ1", "Does relationship evidence improve strict CTI-MCQ compliance?"),
            ("RQ2", "Does the effect replicate across Llama and Qwen models?"),
            ("RQ3", "Does relationship evidence outperform negative controls?"),
            ("RQ4", "Can a source-conflict router identify high-confidence evidence strata?"),
        ],
        "hypotheses": [
            ("H1", "Relationship evidence beats vanilla on the decisive slice."),
            ("H2", "Relationship evidence beats technique-only and negative controls in Qwen ablation."),
            ("H3", "A source-conflict router identifies a decisive direct-answer bucket."),
            ("H4", "Full-bucket forced answering remains useful but requires conservative router wording."),
        ],
        "scope": "CTIBench/CTI-MCQ style multiple-choice rows, MITRE ATT&CK relationship evidence, Llama and Qwen model-family evaluations.",
        "limitations": "Not a general deep research agent, not proof of pure causal relationship evidence, and not a hard answerability oracle.",
        "themes": [
            ("CTI evaluation benchmarks", "CTIBench motivates applied CTI evaluation beyond general language tasks."),
            ("Retrieval-conditioned answering", "RAG and evidence conditioning reduce reliance on parametric memory."),
            ("ATT&CK relationship evidence", "Question-specific relationships provide structured evidence for CTI-MCQ choices."),
            ("Source-support routing", "Evidence strength and conflict can guide direct answer versus review routing."),
        ],
        "gap": "Existing CTI benchmarks evaluate model answers, but the Praxis gap is deterministic evidence routing and source-support stratification for safer direct answering.",
        "experiments": [
            ("Experiment 1", "Llama 8B decisive-slice gate", "Evaluate vanilla versus relationship evidence.", "Accuracy improved from 0.642 to 0.915."),
            ("Experiment 2", "Llama 3B cross-model gate", "Repeat decisive-slice gate on smaller model family.", "Accuracy improved from 0.547 to 0.887."),
            ("Experiment 3", "Qwen ablation gate", "Compare relationship evidence against technique-only, broad seed, empty evidence, random facts, and vanilla.", "Relationship evidence 0.906; technique-only 0.726; vanilla 0.623; random facts 0.462."),
            ("Experiment 4", "Source-conflict and full-bucket audit", "Apply router buckets over 500 rows and evaluate forced-answer performance.", "Full table relationship evidence 0.822 vs vanilla 0.614; decisive bucket delta +0.2830."),
        ],
        "datasets": ["CTIBench/CTI-MCQ rows", "MITRE ATT&CK relationship evidence corpus"],
        "metrics": "Strict answer accuracy, bucket counts, per-condition delta, full-bucket downstream accuracy.",
        "validation": "Cross-model replication, negative controls, source-conflict bucket audit, full 500-row downstream audit.",
        "assumptions": "Multiple-choice CTI rows are a controlled proxy for compliance; evidence-addressable slices can be identified without leaking labels.",
        "result_summary": [
            "Relationship evidence consistently beats vanilla across evaluated models.",
            "Qwen ablation supports relationship evidence beyond broad seed and random facts.",
            "Router is a risk stratifier, not a perfect answerability oracle.",
        ],
        "contributions": [
            "A defensible retrieval-conditioned CTI compliance pattern.",
            "A source-conflict taxonomy for CTI answer routing.",
            "Cross-model evidence that structured ATT&CK support improves strict answers.",
        ],
        "practitioner_recs": [
            "Use question-specific ATT&CK evidence rather than broad CTI seed prompts.",
            "Route unsupported or conflicting rows to review instead of forcing all answers.",
            "Preserve evidence pointers for auditability.",
        ],
        "future": [
            "Extend beyond MCQ to evidence-cited prose with abstention.",
            "Add temporal ATT&CK release splits.",
            "Evaluate analyst-facing review workflows for conflicting evidence buckets.",
        ],
        "evidence": [
            "reports/relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md",
            "reports/relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md",
            "reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/PX003_PX034_FULL_BUCKET_DOWNSTREAM_ACCURACY_AUDIT.md",
            "cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py",
            "scripts/build_sec_lord_relationship_evidence_gate.py",
        ],
        "code": [
            ("A.1", "scripts/build_sec_lord_relationship_evidence_gate.py", "Builds relationship-evidence CTI prompts and slices."),
            ("A.2", "cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py", "Runs cloud model gate for relationship evidence."),
            ("A.3", "scripts/analyze_cti_source_conflict_gate.py", "Builds source-conflict routing buckets."),
            ("A.4", "scripts/analyze_cti_bucket_downstream_accuracy.py", "Audits full-bucket downstream accuracy."),
        ],
        "references": ["rag", "attack", "ctibench", "qwen", "praxis_tracker"],
    },
    {
        "id": "PX-004",
        "file": "PX004_FALSECITE_CODE_FULL_PRAXIS_20260706.txt",
        "title": "FalseCite-Code External Verification for Software-Artifact Citation Poisoning",
        "status": "Bounded defense-ready positive",
        "thesis": (
            "Code assistants can be induced to trust fabricated software-artifact "
            "citations, but external metadata verification can suppress this "
            "failure mode on a locked benchmark."
        ),
        "abstract": (
            "This praxis builds and evaluates a balanced software-artifact "
            "citation benchmark spanning PyPI versions, NPM versions, GitHub "
            "repositories, and GitHub tags. A strict external verifier reaches "
            "1.0000 accuracy and invalid recall on 80 locked claims. In audit "
            "and generation modes, model-only outputs trust fabricated citations "
            "at high rates, while metadata evidence and verifier guards reduce "
            "strict fabricated trust to 0.0000 under the tested conditions."
        ),
        "keywords": "citation hallucination, software artifacts, PyPI, NPM, GitHub, verifier",
        "motivation": "Software-artifact citations are operationally sensitive because trusting a fabricated version, repository, or tag can mislead code maintenance and dependency decisions.",
        "problem": "Language-model plausibility is not enough to determine whether a software artifact exists or whether a cited version/tag is real.",
        "objectives": [
            "Construct a balanced valid/fabricated artifact-citation benchmark.",
            "Measure model trust in fabricated citations.",
            "Evaluate deterministic external metadata verification.",
            "Audit freshness and strict-holdout behavior.",
        ],
        "research_questions": [
            ("RQ1", "Do code models accept fabricated software-artifact citations?"),
            ("RQ2", "Can metadata evidence suppress fabricated trust?"),
            ("RQ3", "Does a citation-aware verifier outperform trust-all and regex floors?"),
            ("RQ4", "Does the verifier remain stable under freshness audit?"),
        ],
        "hypotheses": [
            ("H1", "Base model trust in fabricated citations is non-zero and operationally meaningful."),
            ("H2", "External metadata verification reaches 1.0000 invalid recall on the locked benchmark."),
            ("H3", "Verifier-guarded answers reduce fabricated trust to zero in tested prompt settings."),
            ("H4", "API freshness audit does not introduce verifier errors."),
        ],
        "scope": "80 locked software-artifact claims across PyPI, NPM, GitHub repositories, and GitHub tags.",
        "limitations": "Not universal hallucination prevention, not general package-install safety, and not a claim across all code assistants.",
        "themes": [
            ("Citation hallucination", "False citations can induce downstream trust and unsupported claims."),
            ("Software supply-chain metadata", "Package/version/tag existence is externally checkable and should not be delegated to model plausibility."),
            ("Verifier-controller separation", "Deterministic checks separate factual validation from language generation."),
            ("Benchmark lock and freshness", "Artifact-ID keyed splits and API refreshes support defensible evaluation."),
        ],
        "gap": "Prior hallucination benchmarks focus on textual truthfulness; the Praxis gap is externally verifiable software-artifact citation trust.",
        "experiments": [
            ("Experiment 1", "Source/verifier gate", "Run strict verifier, trust-all, and regex baselines over locked claims.", "Strict verifier accuracy 1.0000 and invalid recall 1.0000; baselines invalid recall 0.0000."),
            ("Experiment 2", "Audit-mode model gate", "Measure base model, metadata prompt, and verifier on audit answers.", "Base strict fabricated accepted 0.8571; metadata/verifier strict fabricated accepted 0.0000."),
            ("Experiment 3", "Generation-mode model gate", "Measure suggested citation versus metadata answer and verifier guard.", "Suggested strict fabricated trusted 0.8333; verifier guard 0.0000."),
            ("Experiment 4", "Defense freshness refresh", "Recheck external metadata APIs and strict holdout.", "80 claims, 15 strict-holdout claims, API error rate 0.0000, verifier accuracy 1.0000."),
        ],
        "datasets": ["FalseCite-Code locked claims JSONL", "PyPI, NPM, and GitHub metadata APIs"],
        "metrics": "Accuracy, invalid recall, fabricated accepted/trusted rate, strict fabricated accepted/trusted rate, API error rate.",
        "validation": "Locked claims, artifact-keyed splits, strict holdout, metadata freshness refresh.",
        "assumptions": "Public metadata APIs are authoritative for the artifact-existence checks modeled here.",
        "result_summary": [
            "Base model accepted fabricated citations under tested prompts.",
            "Metadata evidence and verifier guards reduced fabricated trust to zero.",
            "The verifier passed the freshness audit with zero API errors.",
        ],
        "contributions": [
            "A locked software-artifact citation benchmark.",
            "A deterministic metadata verification pattern.",
            "Evidence that external verification can close a concrete hallucination risk.",
        ],
        "practitioner_recs": [
            "Never accept model-generated package/version/tag citations without metadata checks.",
            "Bind artifact claims to external registries before use in engineering workflows.",
            "Keep API error handling explicit; route unknown states to review.",
        ],
        "future": [
            "Expand to more ecosystems and package managers.",
            "Add cross-model family replication.",
            "Test integration into coding-agent pull request review workflows.",
        ],
        "evidence": [
            "reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md",
            "reports/falsecite_code/defense_refresh_20260630/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md",
            "reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_20260624.md",
            "reports/falsecite_code/FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md",
            "scripts/run_falsecite_code_gate.py",
        ],
        "code": [
            ("A.1", "scripts/run_falsecite_code_gate.py", "Builds and scores the source/verifier gate."),
            ("A.2", "scripts/run_falsecite_code_model_gate.py", "Runs audit-mode model trust evaluation."),
            ("A.3", "scripts/run_falsecite_code_generation_gate.py", "Runs generation-mode citation trust evaluation."),
            ("A.4", "reports/praxis_final_positive_reports_20260701/PX004_FINAL_REPORT_FALSECITE_CODE.md", "Portable verifier code appendix."),
        ],
        "references": ["falsecite", "rag", "qwen", "praxis_tracker"],
    },
    {
        "id": "PX-005",
        "file": "PX005_MOE_STANDING_COMMITTEE_FULL_PRAXIS_20260706.txt",
        "title": "Standing-Committee Routing in Sparse Mixture-of-Experts Models",
        "status": "Bounded publishable positive; confirmation/extension",
        "thesis": (
            "Sparse MoE routers can exhibit stable high-mass standing committees "
            "across prompt domains and style variants, challenging simple "
            "domain-specialization assumptions under a frozen audit."
        ),
        "abstract": (
            "This praxis evaluates standing-committee routing under a frozen "
            "480-prompt audit across OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. "
            "All models pass router capture, primary Jaccard, bootstrap CI, and "
            "committee-size sensitivity gates. The result is positioned as a "
            "bounded confirmation and extension because the 2026 Standing "
            "Committee literature already establishes the broader framing."
        ),
        "keywords": "mixture of experts, router audit, standing committee, OLMoE, Qwen MoE",
        "motivation": "MoE architectures are often described as domain-specialized, but router behavior may centralize computation through repeated expert committees.",
        "problem": "Claims about specialization need router-level evidence across prompt domains, architectures, and style perturbations.",
        "objectives": [
            "Capture routed expert committees under a frozen prompt-domain audit.",
            "Measure pairwise committee overlap using Jaccard metrics.",
            "Replicate across OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE.",
            "Position novelty relative to 2026 Standing Committee work.",
        ],
        "research_questions": [
            ("RQ1", "Do audited MoE models show stable high-overlap committees?"),
            ("RQ2", "Does the effect persist across base/instruct variants?"),
            ("RQ3", "Does the effect replicate in a Qwen MoE architecture?"),
            ("RQ4", "Is the result novel as first discovery or as local confirmation/extension?"),
        ],
        "hypotheses": [
            ("H1", "Router capture is at least 0.95 for each audited model."),
            ("H2", "Primary mean pairwise Jaccard is at least 0.25."),
            ("H3", "Bootstrap CI low is at least 0.20."),
            ("H4", "Committee-size sensitivity remains above 0.20."),
        ],
        "scope": "Frozen 480-prompt audit: five domains, twelve base prompts per domain, eight style variants per prompt, committee sizes 16/32/64.",
        "limitations": "Not first discovery, not causal expert specialization, not universal MoE behavior, and not behavior-level intervention evidence.",
        "themes": [
            ("Sparse MoE routing", "MoE models route tokens through selected expert subsets."),
            ("Standing Committee phenomenon", "Recent work identifies domain-invariant expert coalitions in MoE models."),
            ("Post-hoc router auditing", "Router trace analysis can reveal structure without claiming behavioral causality."),
            ("Novelty boundary", "PX-005 must be framed as a local confirmation/extension, not first discovery."),
        ],
        "gap": "The Praxis gap is a frozen reproducible prompt-domain audit that confirms committee structure across specific open models and adds a Qwen cross-architecture check.",
        "experiments": [
            ("Experiment 1", "OLMoE base audit", "Capture router traces and compute committee overlap.", "480/480 capture; primary Jaccard 0.4656; CI [0.4336, 0.4834]."),
            ("Experiment 2", "OLMoE-Instruct audit", "Repeat audit on instruction-tuned OLMoE.", "480/480 capture; primary Jaccard 0.4591; CI [0.4320, 0.4796]."),
            ("Experiment 3", "Qwen1.5-MoE audit", "Repeat audit on Qwen MoE architecture.", "480/480 capture; primary Jaccard 0.5826; CI [0.5552, 0.6281]."),
            ("Experiment 4", "Committee-size sensitivity and novelty check", "Evaluate committee sizes 16/32/64 and compare against 2026 literature.", "All size means remain above threshold; result retained as confirmation/extension."),
        ],
        "datasets": ["Frozen Praxis prompt-domain audit: cyber, code, math, policy, writing prompts with style variants."],
        "metrics": "Router capture rate, mean pairwise Jaccard, bootstrap confidence interval, committee-size sensitivity.",
        "validation": "Frozen prompts, deterministic style variants, cross-model replication, bootstrap CI, novelty-positioning audit.",
        "assumptions": "Captured router traces are sufficient to describe committee overlap but not to infer causal behavior.",
        "result_summary": [
            "All audited models passed router capture and Jaccard gates.",
            "Qwen1.5-MoE supplied cross-architecture confirmation.",
            "Claim is bounded to routed structure, not behavioral causality.",
        ],
        "contributions": [
            "A reproducible prompt-domain router audit.",
            "Cross-model confirmation of standing committees.",
            "A clear novelty boundary against current literature.",
        ],
        "practitioner_recs": [
            "Audit router traces before assuming domain specialization.",
            "Report committee overlap separately from behavioral performance.",
            "Avoid interpreting stable routing committees as causal explanations without intervention tests.",
        ],
        "future": [
            "Add causal interventions on committee experts.",
            "Test under fine-tuning and domain shift.",
            "Compare load-balancing losses against committee concentration.",
        ],
        "evidence": [
            "reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md",
            "reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md",
            "reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.md",
            "reports/moe_standing_committee/qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md",
        ],
        "code": [
            ("A.1", "cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py", "OLMoE base router audit runner."),
            ("A.2", "cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py", "OLMoE-Instruct router audit mode."),
            ("A.3", "cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py", "Qwen MoE router audit runner."),
            ("A.4", "reports/praxis_final_positive_reports_20260701/PX005_FINAL_REPORT_MOE_STANDING_COMMITTEE.md", "Portable Jaccard and gate-check code appendix."),
        ],
        "references": ["standing_committee", "olmoe", "qwen", "praxis_tracker"],
    },
    {
        "id": "PX-011",
        "file": "PX011_HALLUHARD_SOURCE_LOCKED_FULL_PRAXIS_20260706.txt",
        "title": "Source-Locked HalluHard Verifier Pipeline",
        "status": "Bounded source-locked positive",
        "thesis": (
            "A HalluHard-style hallucination guardrail can work when citation "
            "metadata are locked to retrieved evidence and the model is "
            "restricted to extractive claim generation."
        ),
        "abstract": (
            "This praxis evaluates a source-locked retrieval/controller pipeline "
            "on the HalluHard research_questions lane. The controller copies DOI, "
            "arXiv ID, title, year, and source identity from retrieved records, "
            "leaving Qwen2.5-7B to generate only a short extractive claim phrase. "
            "The final gate generated 250/250 extraction-valid rows, evaluated "
            "500 supported/shifted-source pairs, and achieved verifier accuracy "
            "0.9040 and macro F1 0.9031."
        ),
        "keywords": "HalluHard, hallucination verification, source locking, citation grounding, retrieval controller",
        "motivation": "Open-ended citation generation remains fragile; source locking converts a broad hallucination problem into a verifiable evidence-control problem.",
        "problem": "If the model invents citation metadata, a verifier must judge too much at once. PX-011 isolates the model to extractive content and keeps source identity deterministic.",
        "objectives": [
            "Lock citation metadata to retrieved source records.",
            "Generate only extractive claim content with Qwen2.5-7B.",
            "Evaluate supported pairs and shifted-source negatives.",
            "Compare against trivial baselines.",
        ],
        "research_questions": [
            ("RQ1", "Can a controller remove the freeform citation-metadata failure mode?"),
            ("RQ2", "Can extractive model content produce verifier-ready claims?"),
            ("RQ3", "Can the verifier detect shifted-source hallucinations?"),
            ("RQ4", "Does the verifier beat trivial support baselines?"),
        ],
        "hypotheses": [
            ("H1", "Extraction-valid rate reaches 1.0000 under the constrained lane."),
            ("H2", "Verifier macro F1 beats always-supported and field-presence baselines."),
            ("H3", "Shifted-source negatives are separable from supported pairs."),
            ("H4", "The result remains bounded to research_questions only."),
        ],
        "scope": "HalluHard research_questions lane only; Qwen2.5-7B extractive claim text; deterministic source metadata controller.",
        "limitations": "Not broad HalluHard coverage, not legal/medical/coding lane success, not freeform citation generation, and not open-ended source discovery.",
        "themes": [
            ("Hallucination benchmarks", "HalluHard motivates hard multi-turn citation-grounding tests."),
            ("Source-locked retrieval", "Deterministic source metadata reduces citation invention risk."),
            ("Verifier design", "Supported and shifted-source pairs test both content grounding and source identity."),
            ("Bounded claim discipline", "The result is constrained to one lane and one controller pattern."),
        ],
        "gap": "The Praxis gap is a constrained source-locking pattern that turns HalluHard citation checking into a repeatable verifier gate.",
        "experiments": [
            ("Experiment 1", "Source-lock controller", "Copy DOI, arXiv ID, title, year, and source identity from retrieved records.", "Freeform citation metadata generation removed from the model task."),
            ("Experiment 2", "Extractive Qwen generation", "Generate short claimed_content from abstracts.", "250/250 extraction-valid rows; extraction-valid rate 1.0000."),
            ("Experiment 3", "Supported and shifted-source verification", "Evaluate paired supported and shifted-source rows.", "500 evaluation pairs; verifier accuracy 0.9040; macro F1 0.9031."),
            ("Experiment 4", "Baseline and boundary audit", "Compare against always-supported and field-presence baselines.", "Both trivial baselines macro F1 0.3333; claim limited to research_questions lane."),
        ],
        "datasets": ["HalluHard research_questions lane", "retrieved source records and shifted-source negative pairs"],
        "metrics": "Extraction-valid rate, supported rate, verifier accuracy, macro F1, baseline macro F1, wall time.",
        "validation": "Supported/shifted-source paired evaluation and trivial-baseline comparison.",
        "assumptions": "Source records are trusted inputs; extractive claim phrases can be evaluated against retrieved abstracts.",
        "result_summary": [
            "250/250 extraction-valid rows.",
            "202/250 supported claims passed verifier.",
            "Verifier accuracy 0.9040 and macro F1 0.9031.",
        ],
        "contributions": [
            "A source-locking control pattern for citation verification.",
            "A shifted-source negative test for hallucination detection.",
            "A bounded positive HalluHard lane result.",
        ],
        "practitioner_recs": [
            "Copy citation metadata from retrieval, never from model generation.",
            "Require shifted-source negative tests for citation verifiers.",
            "Treat unsupported or non-extractive claims as review cases.",
        ],
        "future": [
            "Extend to legal, medical, and coding lanes only after separate gates.",
            "Add stronger semantic entailment checks for paraphrased claims.",
            "Evaluate multi-turn persistence of source-locking controls.",
        ],
        "evidence": [
            "reports/halluhard_source_verifier/PX011_SOURCE_LOCKED_CONSTRAINED_GATE_20260701.md",
            "reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json",
            "cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py",
        ],
        "code": [
            ("A.1", "cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py", "Cloud gate for source-locked generation and verification."),
            ("A.2", "reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.csv", "Row-level generated and verifier-scored records."),
            ("A.3", "reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json", "Machine-readable metrics summary."),
            ("A.4", "reports/praxis_final_positive_reports_20260701/PX011_FINAL_REPORT_HALLUHARD_SOURCE_LOCKED.md", "Portable verifier code appendix."),
        ],
        "references": ["halluhard", "rag", "qwen", "falsecite", "praxis_tracker"],
    },
    {
        "id": "PX-050",
        "file": "PX050_AGENTIC_PACKAGE_GATE_FULL_PRAXIS_20260706.txt",
        "title": "Deterministic Tool-Boundary Gates for Agentic Package-Install Hallucination",
        "status": "Lead defense-ready positive",
        "thesis": (
            "Deterministic validation at the package-install tool boundary can "
            "block invalid or policy-unsafe model-generated install actions "
            "before execution while preserving useful valid installs under an "
            "observable, no-execution boundary."
        ),
        "abstract": (
            "This praxis evaluates deterministic package-install gates for "
            "model-generated PyPI/NPM install strings and dry-run live-agent "
            "tool-call arguments. Across fixed, live-model, parser-stress, "
            "controller/extractor, crafted stress, and two-model dry-run "
            "live-agent gates, the hardened path produced zero observed invalid "
            "package escapes under the defended corpora. The final 288-row "
            "Qwen/DeepSeek live-agent corpus had raw unsafe rate 0.9453, "
            "controller recovery 0.9757, registry-only invalid allows 20, "
            "hardened invalid allows 0, and valid allow 1.0000."
        ),
        "keywords": "agentic deployment, package hallucination, slopsquatting, tool boundary, deterministic verifier",
        "motivation": "Agentic coding systems can turn model hallucinations into executable tool calls. Package-install boundaries are a narrow but high-value deployment control point.",
        "problem": "Registry checks alone can miss policy-unsafe or malformed install actions, while overblocking valid installs would destroy utility.",
        "objectives": [
            "Evaluate hardened deterministic package-install verification.",
            "Compare against registry-only validation.",
            "Repair noisy model output with controller/extractor routing.",
            "Validate on dry-run live-agent tool-call corpora without package-manager execution.",
        ],
        "research_questions": [
            ("RQ1", "Can a deterministic verifier block invalid install strings?"),
            ("RQ2", "Does hardened validation outperform registry-only checking on adversarial/mixed corpora?"),
            ("RQ3", "Can controller/extractor repair preserve valid utility under noisy model output?"),
            ("RQ4", "Does the boundary hold under dry-run live-agent tool calls?"),
        ],
        "hypotheses": [
            ("H1", "Hardened invalid escape is 0.0000 on defended corpora."),
            ("H2", "Valid allow remains high, with final live-agent valid allow 1.0000."),
            ("H3", "Controller/extractor target recovery exceeds 0.95 in deployment-shaped tests."),
            ("H4", "Policy/provenance refreshes preserve utility and traceability."),
        ],
        "scope": "Observable PyPI/NPM install command strings and dry-run tool-call arguments; no package managers executed.",
        "limitations": "Not broad coding-agent safety, not malicious existing-package detection, not arbitrary shell-command safety, and not chain-of-thought monitoring.",
        "themes": [
            ("Package hallucination and slopsquatting", "Prior work establishes package hallucinations as a software supply-chain risk."),
            ("Tool-boundary enforcement", "Agentic systems need deterministic controls at executable boundaries."),
            ("Controller/extractor repair", "Noisy raw model output requires target selection and review fallback."),
            ("Security-utility-provenance deployment layers", "Policy operating points and provenance traces make the verifier deployable and auditable."),
        ],
        "gap": "The Praxis gap is a measured no-execution tool-boundary defense that blocks invalid installs while preserving valid tool-call utility.",
        "experiments": [
            ("Experiment 1", "Fixed and live adaptive gates", "Score fixed, Qwen live, and DeepSeek live command corpora.", "Fixed 138 rows escape 0.0000; Qwen hardened escape 0.0000; DeepSeek hardened escape 0.0000."),
            ("Experiment 2", "Parser stress", "Generate inert parser mutations from command corpora.", "984 mutations; hardened escape 0.0000; valid clean allow 1.0000; registry-only invalid escape 0.3483."),
            ("Experiment 3", "Controller/extractor repair and crafted stress", "Repair StarCoder boundary and stress crafted raw-output attacks.", "PX-050S 440 rows invalid allows 0; PX-050T 1,440 crafted strings invalid allows 0 and valid allow 1.0000."),
            ("Experiment 4", "Dry-run live-agent, policy, and provenance refresh", "Evaluate Qwen/DeepSeek tool-call rows plus policy/provenance layers.", "288 rows; raw unsafe 0.9453; hardened invalid allows 0; valid allow 1.0000; policy review 0.0243; provenance recall 1.0000."),
        ],
        "datasets": ["PyPI/NPM package-install command corpora", "Qwen2.5-Coder and DeepSeek dry-run live-agent tool-call corpora", "crafted raw-output stress strings"],
        "metrics": "Invalid escape, invalid allow count, valid allow, controller recovery, registry-only invalid allows, review rate, provenance recall, trace completeness.",
        "validation": "Fixed fixtures, two live models, parser stress, held-out StarCoder boundary, controller repair, crafted adaptive stress, two-model dry-run live-agent gate, policy/provenance refresh.",
        "assumptions": "Dry-run tool-call arguments approximate the observable package-install boundary; no execution safety claims are made.",
        "result_summary": [
            "Final live-agent corpus: 288 rows.",
            "Raw unsafe rate 0.9453 and controller recovery 0.9757.",
            "Registry-only invalid allows 20; hardened invalid allows 0.",
            "Valid allow 1.0000; provenance trace completeness 1.0000.",
        ],
        "contributions": [
            "A lead Praxis agent-defense result for deterministic tool-boundary control.",
            "A controller/extractor repair pattern for noisy coding-agent outputs.",
            "Security-utility and provenance layers for deployment judgment.",
        ],
        "practitioner_recs": [
            "Enforce package-install validation before execution.",
            "Use review fallback when controller target recovery fails.",
            "Separate registry existence from policy-safe install validation.",
            "Preserve provenance metadata for every tool-call argument.",
        ],
        "future": [
            "Extend to executed sandbox package-manager tests.",
            "Detect malicious packages that exist in registries.",
            "Generalize the boundary pattern to broader shell commands and build tools.",
        ],
        "evidence": [
            "reports/agentic_deployment_defense/px050_final_defense_package_export_20260705/PX050_FINAL_DEFENSE_PACKAGE_EXPORT_20260705.md",
            "reports/agentic_deployment_defense/px050_live_agent_two_model_determination_20260705/PX050_LIVE_AGENT_TWO_MODEL_FINAL_DETERMINATION_20260705.md",
            "reports/agentic_deployment_defense/px051v_live_agent_policy_refresh_20260705/PX051V_LIVE_AGENT_POLICY_REFRESH_20260705.md",
            "reports/agentic_deployment_defense/px052v_live_agent_provenance_refresh_20260705/PX052V_LIVE_AGENT_PROVENANCE_REFRESH_20260705.md",
        ],
        "code": [
            ("A.1", "cloud_jobs/px050u_live_agent_tool_boundary_20260705/run_px050u_live_agent_tool_boundary.py", "Qwen dry-run live-agent tool-boundary runner."),
            ("A.2", "cloud_jobs/px050v_second_model_live_agent_tool_boundary_20260705/run_px050v_second_model_live_agent_tool_boundary.py", "DeepSeek dry-run live-agent replication runner."),
            ("A.3", "scripts/run_px050s_controller_adaptive_stress.py", "Controller/extractor crafted stress runner."),
            ("A.4", "scripts/run_d1_live_agent_corpus_refresh.py", "Policy and provenance refresh over combined live-agent corpus."),
        ],
        "references": ["package_hallucination", "qwen_coder", "rag", "praxis_tracker"],
    },
    {
        "id": "PX-054",
        "file": "PX054_REFUSAL_GEOMETRY_FULL_PRAXIS_20260706.txt",
        "title": "Depth-Indexed Refusal-Style Geometry in a Recurrent Language Model",
        "status": "Defense-ready bounded characterization",
        "thesis": (
            "Huginn-0125 exposes depth-indexed latent states whose refusal-style "
            "direction is measurable and stable across recurrent depth on a safe "
            "paraphrase-family prompt suite."
        ),
        "abstract": (
            "This praxis characterizes refusal-style geometry in Huginn-0125, a "
            "recurrent-depth language model. A source gate confirmed public, "
            "ungated, Apache-2.0, Transformers-compatible recurrent-depth access. "
            "An activation smoke gate captured 60/60 latent rows across depths "
            "4, 8, 16, and 32. The scale gate captured 600/600 rows across 120 "
            "safe prompts and depths 4, 8, 16, 32, and 64, with cross-depth "
            "stability 0.9257, CI [0.9067, 0.9273], benign-control FPR 0.0000, "
            "and worst refusal TPR 0.9750."
        ),
        "keywords": "mechanistic interpretability, recurrent depth, refusal geometry, Huginn, latent states",
        "motivation": "Recurrent-depth models expose repeated latent computation steps that may make safety-relevant representation dynamics measurable.",
        "problem": "Refusal behavior is often studied behaviorally; PX-054 asks whether refusal-style directions can be measured across recurrent depth without harmful prompting or intervention.",
        "objectives": [
            "Verify source/model readiness for recurrent-depth activation capture.",
            "Run a safe activation smoke gate.",
            "Scale to a larger safe prompt-family corpus.",
            "Define an observational claim boundary.",
        ],
        "research_questions": [
            ("RQ1", "Does Huginn-0125 expose usable latent states across recurrent depth?"),
            ("RQ2", "Is a refusal-style direction measurable on safe prompts?"),
            ("RQ3", "Is that direction stable across recurrent depths up to 64?"),
            ("RQ4", "Can the result be defended without causal or jailbreak claims?"),
        ],
        "hypotheses": [
            ("H1", "Source gate passes model availability and recurrent-depth metadata checks."),
            ("H2", "Activation smoke gate captures all planned depth rows."),
            ("H3", "Scale gate cross-depth stability exceeds the registered threshold."),
            ("H4", "Benign-control and helpful false-positive rates remain 0.0000 in the scale corpus."),
        ],
        "scope": "Safe paraphrase-family prompts, Huginn-0125, observational latent-state capture, no intervention or harmful-request evaluation.",
        "limitations": "Not causal refusal mechanism, not deployed safety defense, not jailbreak detection, not refusal removal, and not transfer to other models.",
        "themes": [
            ("Recurrent-depth language models", "Huginn reuses model computation across depth steps, enabling depth-indexed activation analysis."),
            ("Mechanistic characterization", "Latent directions can be studied observationally before causal intervention claims."),
            ("Safety-preserving prompt design", "Safe paraphrase families avoid harmful request generation while still characterizing refusal-style geometry."),
            ("Claim boundary discipline", "Representation stability is not the same as deployed safety or behavior control."),
        ],
        "gap": "The Praxis gap is a safe, reproducible recurrent-depth representation characterization with explicit no-intervention boundaries.",
        "experiments": [
            ("Experiment 1", "Source gate", "Check model availability, license, configuration, and recurrent-depth metadata.", "SOURCE_GATE_PASS; Huginn-0125 is public, ungated, Apache-2.0, Transformers-compatible, and documents num_steps."),
            ("Experiment 2", "Activation smoke gate", "Capture safe prompt activations across depths 4, 8, 16, and 32.", "60/60 latent rows captured; cross-depth stability 0.8321; benign-control FPR 0.0000."),
            ("Experiment 3", "Scale gate", "Capture 120 safe prompts across depths 4, 8, 16, 32, and 64.", "600/600 rows; cross-depth stability 0.9257; CI [0.9067, 0.9273]; worst refusal TPR 0.9750."),
            ("Experiment 4", "Claim-boundary synthesis", "Evaluate false-positive controls and no-intervention defense boundary.", "Benign-control FPR 0.0000; helpful FPR 0.0000; bounded positive characterization."),
        ],
        "datasets": ["Safe paraphrase-family prompt suite", "Huginn-0125 activation rows and reduced latent vectors"],
        "metrics": "Activation capture rate, cross-depth stability, bootstrap CI, benign-control FPR, helpful FPR, worst refusal TPR.",
        "validation": "Source gate, activation smoke gate, scale gate, family-level bootstrap intervals, explicit no-intervention boundary.",
        "assumptions": "Safe paraphrase prompts are sufficient for representation characterization but not for harmful-request safety evaluation.",
        "result_summary": [
            "Source, activation, and scale gates passed.",
            "Scale gate captured 600/600 latent rows.",
            "Cross-depth stability reached 0.9257 with CI [0.9067, 0.9273].",
            "Benign-control and helpful false-positive rates were 0.0000.",
        ],
        "contributions": [
            "A safe recurrent-depth activation-capture protocol.",
            "Evidence of stable refusal-style latent direction across depth.",
            "A bounded mechanistic characterization suitable for defense without harmful prompting.",
        ],
        "practitioner_recs": [
            "Use PX-054 as a mechanistic characterization result, not a deployed safety defense.",
            "Keep safe prompt-family boundaries explicit.",
            "Require causal interventions and cross-model replication before operational claims.",
        ],
        "future": [
            "Replicate on held-out safe prompts and another recurrent-depth checkpoint.",
            "Test causal patching only under safe and approved protocols.",
            "Compare depth-stability metrics across model families.",
        ],
        "evidence": [
            "reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md",
            "reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md",
            "reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_RESULT_SYNTHESIS_20260705.md",
        ],
        "code": [
            ("A.1", "scripts/run_px054_refusal_geometry_source_gate.py", "Source gate runner for model metadata and readiness."),
            ("A.2", "cloud_jobs/px054_refusal_geometry_20260705/run_px054_refusal_geometry_activation_gate.py", "Activation smoke gate runner."),
            ("A.3", "cloud_jobs/px054_refusal_geometry_scale_20260705/run_px054_refusal_geometry_scale_gate.py", "Scale gate runner and metrics writer."),
            ("A.4", "cloud_jobs/px054_refusal_geometry_scale_20260705/run_on_instance.sh", "AWS wrapper for scale execution and sync."),
        ],
        "references": ["geiping", "qwen", "praxis_tracker"],
    },
]


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str]) -> str:
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(items, start=1))


def table(rows: list[tuple[str, str]], headers: tuple[str, str] = ("Item", "Description")) -> str:
    widths = [max(len(headers[0]), *(len(str(r[0])) for r in rows)), max(len(headers[1]), *(len(str(r[1])) for r in rows))]
    out = [
        f"{headers[0]} | {headers[1]}",
        f"{'-' * widths[0]}-+-{'-' * widths[1]}",
    ]
    out.extend(f"{str(a)} | {str(b)}" for a, b in rows)
    return "\n".join(out)


def figure_list() -> str:
    return "\n".join(
        [
            "Figure 1. Praxis research framework and evidence flow.",
            "Figure 2. Graphical Methodology of Research (GMR) for the experiment suite.",
            "Figure 3. Claim-boundary decision flow.",
        ]
    )


def table_list(project: dict) -> str:
    return "\n".join(
        [
            "Table 1. Acronyms and abbreviations.",
            "Table 2. Research questions and hypotheses.",
            "Table 3. Experiment design matrix.",
            "Table 4. Dataset and evidence artifacts.",
            "Table 5. Results summary and hypothesis outcomes.",
        ]
    )


def acronyms() -> str:
    return table(COMMON_ACRONYMS, ("Acronym", "Meaning"))


def references(keys: list[str]) -> str:
    selected = [REFERENCE_POOL[k] for k in keys]
    return "\n\n".join(selected)


def render_project(project: dict) -> str:
    rq_rows = [(f"{rq} / {hyp[0]}", f"{question} Hypothesis: {hyp[1]}") for (rq, question), hyp in zip(project["research_questions"], project["hypotheses"], strict=True)]
    exp_rows = [(name, f"{purpose} Result: {result}") for name, _title, purpose, result in project["experiments"]]
    code_rows = [(section, f"{path} - {desc}") for section, path, desc in project["code"]]
    evidence_rows = [(f"Artifact {idx}", item) for idx, item in enumerate(project["evidence"], start=1)]
    result_rows = [(name, result) for name, _title, _purpose, result in project["experiments"]]

    experiment_method_sections = []
    experiment_result_sections = []
    for idx, (name, title, purpose, result) in enumerate(project["experiments"], start=1):
        experiment_method_sections.append(
            f"3.{3 + idx} {name}: {title}\n"
            f"Purpose: {purpose}\n"
            f"Design: The experiment is executed as a gated artifact in the Praxis repository, with fixed inputs, locked metrics, and a claim boundary recorded before promotion.\n"
            f"Expected defense role: {result}\n"
        )
        experiment_result_sections.append(
            f"4.{idx} Results: {name} - {title}\n"
            f"{result}\n"
        )

    code_sections = []
    for section, path, desc in project["code"]:
        code_sections.append(
            f"{section} {path}\n"
            f"Description: {desc}\n"
            "Defense use: This artifact is the cited implementation or portable audit reference for the corresponding experiment. Reviewers should inspect the repository path, rerun where dependencies are available, and compare outputs to the reported result tables.\n"
        )

    doc = f"""
{project['title'].upper()}
Doctor of Engineering Praxis Draft
Praxis ID: {project['id']}
Generated: 2026-07-06
Status: {project['status']}

FRONT MATTER

Certification Page
This praxis draft is prepared as a defense-ready technical document for review by an engineering praxis committee. The candidate certifies that the research claim is bounded to the evidence artifacts listed in Appendix B and Appendix C, that negative and boundary results are preserved, and that no unsupported generalization is intentionally asserted.

Candidate: [Candidate Name]
Program: Doctor of Engineering in AI/ML
Institution: [Institution Name]
Committee Chair: [Committee Chair]
Committee Members: [Committee Members]
Date: 2026-07-06

Copyright Page
Copyright (c) 2026 [Candidate Name]. All rights reserved. Repository artifacts may be reviewed under the repository license and access controls. Third-party datasets, papers, and model artifacts remain governed by their respective licenses and terms.

Dedication / Acknowledgments
This praxis is dedicated to the practical engineering discipline of building AI/ML systems that can be tested, bounded, audited, and improved without overclaiming. Acknowledgment is given to the open-source research community, dataset maintainers, model publishers, and the Praxis Research repository artifacts that make this work reviewable.

Abstract of Praxis
{project['abstract']}

Keywords: {project['keywords']}

Table of Contents
Front Matter
Chapter 1: Introduction
  1.1 Background
  1.2 Research Motivation
  1.3 Problem Statement
  1.4 Thesis Statement
  1.5 Research Objectives
  1.6 Research Questions and Hypotheses
  1.7 Scope of Research
  1.8 Research Limitations
  1.9 Organization of the Praxis
Chapter 2: Literature Review
  2.1 Overview and Review Strategy
  2.2 Thematic Review Area 1
  2.3 Thematic Review Area 2
  2.4 Thematic Review Area 3
  2.5 Thematic Review Area 4
  2.6 Critical Analysis and Gap Synthesis
Chapter 3: Methodology
  3.1 Research Approach and Design
  3.2 Graphical Methodology of Research (GMR)
  3.3 Research Framework
  3.4 Experiment 1
  3.5 Experiment 2
  3.6 Experiment 3
  3.7 Experiment 4
  3.8 Data Sources and Datasets
  3.9 Evaluation Metrics and Statistical Methods
  3.10 Validation Approach
  3.11 Assumptions
Chapter 4: Results and Discussion
  4.1 Results: Experiment 1
  4.2 Results: Experiment 2
  4.3 Results: Experiment 3
  4.4 Results: Experiment 4
  4.5 Cross-Experiment Analysis
  4.6 Hypothesis Test Outcomes
  4.7 Discussion: Relation to Research Questions and Prior Literature
Chapter 5: Conclusions and Future Work
References
Appendices

List of Figures
{figure_list()}

List of Tables
{table_list(project)}

List of Acronyms
{acronyms()}

CHAPTER 1: INTRODUCTION

1.1 Background
{project['title']} is part of the Praxis Research portfolio, a future-work-to-experiment program for AI/ML and cybersecurity engineering. The portfolio standard is evidence-first: a result is promoted only when it has a defined objective, a reproducible artifact trail, a measured gate, and a written claim boundary.

1.2 Research Motivation
{project['motivation']}

1.3 Problem Statement
{project['problem']}

1.4 Thesis Statement
{project['thesis']}

1.5 Research Objectives
{numbered(project['objectives'])}

1.6 Research Questions and Hypotheses
{table(rq_rows, ('RQ / Hypothesis', 'Statement'))}

1.7 Scope of Research
{project['scope']}

1.8 Research Limitations
{project['limitations']}

1.9 Organization of the Praxis
Chapter 1 introduces the problem, thesis, scope, and limitations. Chapter 2 reviews the relevant literature and identifies the gap. Chapter 3 describes the research design, GMR, framework, four experiments, data, metrics, validation, and assumptions. Chapter 4 reports results, cross-experiment analysis, and hypothesis outcomes. Chapter 5 concludes with contributions, recommendations, and future work. Appendices provide experiment code references, supplementary tables, and dataset documentation.

CHAPTER 2: LITERATURE REVIEW

2.1 Overview and Review Strategy
The review strategy prioritizes peer-reviewed venues, arXiv technical reports when they are primary model or benchmark releases, official project pages, and the local Praxis evidence record. References were checked for APA-style author, year, title, venue/source, and URL completeness. {COMMON_APA_NOTE}

2.2 Thematic Review Area 1
{project['themes'][0][0]}: {project['themes'][0][1]}

2.3 Thematic Review Area 2
{project['themes'][1][0]}: {project['themes'][1][1]}

2.4 Thematic Review Area 3
{project['themes'][2][0]}: {project['themes'][2][1]}

2.5 Thematic Review Area 4
{project['themes'][3][0]}: {project['themes'][3][1]}

2.6 Critical Analysis and Gap Synthesis
{project['gap']} This praxis addresses that gap by using fixed evaluation gates, explicit boundary language, negative-result preservation, and artifact links that allow an examiner or peer reviewer to trace claims back to the underlying evidence.

CHAPTER 3: METHODOLOGY

3.1 Research Approach and Design
This is an applied engineering praxis using empirical AI/ML evaluation. The design is bounded, artifact-backed, and falsifiable. Each experiment is treated as a gate: it has a defined input, method, metric, pass/fail interpretation, and claim impact. The research design favors conservative claim promotion over broad narrative claims.

3.2 Graphical Methodology of Research (GMR)
Problem identification -> literature and future-work gap -> artifact/data readiness gate -> experiment design -> execution -> metric audit -> boundary audit -> defense-ready package.

ASCII GMR:
[Problem] -> [Research Gap] -> [Data/Source Gate] -> [Experiment 1]
                                             -> [Experiment 2]
                                             -> [Experiment 3]
                                             -> [Experiment 4]
        -> [Cross-Experiment Synthesis] -> [Claim Boundary] -> [Praxis Defense Package]

3.3 Research Framework
{table(exp_rows, ('Experiment', 'Purpose and defended result'))}

{''.join(experiment_method_sections)}
3.8 Data Sources and Datasets
{bullets(project['datasets'])}

3.9 Evaluation Metrics and Statistical Methods
{project['metrics']}

3.10 Validation Approach
{project['validation']}

3.11 Assumptions
{project['assumptions']}

CHAPTER 4: RESULTS AND DISCUSSION

{''.join(experiment_result_sections)}
4.5 Cross-Experiment Analysis
{bullets(project['result_summary'])}

4.6 Hypothesis Test Outcomes
{table([(h, statement) for h, statement in project['hypotheses']], ('Hypothesis', 'Outcome framing'))}
Overall determination: {project['status']}. Hypotheses are accepted only within the stated scope and limitations.

4.7 Discussion: Relation to Research Questions and Prior Literature
The results answer the research questions within a bounded engineering frame. The work contributes by converting a literature-motivated opportunity into a measurable artifact, while preserving negative findings and boundary cases. The relation to prior literature is complementary: the praxis does not replace foundational benchmarks, model reports, or prior methods; it defines an applied gate and produces a defensible claim with reviewable evidence.

CHAPTER 5: CONCLUSIONS AND FUTURE WORK

5.1 Conclusions
{project['title']} is defensible in the following bounded form: {project['thesis']}

5.2 Contributions to the Body of Knowledge and Practice
{numbered(project['contributions'])}

5.3 Recommendations for Practitioners
{numbered(project['practitioner_recs'])}

5.4 Future Research
{numbered(project['future'])}

REFERENCES

{references(project['references'])}

APPENDICES

Appendix A: Experiment Code
{''.join(code_sections)}
Appendix B: Full Results Tables and Supplementary Figures
Primary result summary:
{table(result_rows, ('Experiment', 'Result'))}

Evidence artifacts:
{table(evidence_rows, ('Artifact', 'Repository path'))}

Supplementary figures to produce for final submission:
- Figure B1. End-to-end evidence flow for {project['id']}.
- Figure B2. Per-experiment metric comparison.
- Figure B3. Claim-boundary and failure-mode diagram.

Appendix C: Dataset Documentation
Dataset and artifact scope:
{bullets(project['datasets'])}

Data governance and reproducibility notes:
- Use the repository paths listed in Appendix B as the primary experimental record.
- Preserve raw outputs, summaries, and claim-boundary reports together.
- Do not expand claims beyond the dataset and boundary stated in Sections 1.7 and 1.8.
- For peer review, provide the exact commit SHA and environment notes used for reruns.
"""
    return dedent(doc).strip() + "\n"


def combined_export(projects: list[dict]) -> str:
    parts = [
        "DEFENSE-READY PRAXIS TEXT EXPORT",
        "Generated: 2026-07-06",
        "",
        "This combined export contains one full Doctor of Engineering praxis draft per defense-ready or bounded-support Praxis result.",
        "PX-002 is included as a bounded lookup-style supporting result and is explicitly not a defense pillar.",
        "",
        "Included documents:",
    ]
    parts.extend(f"- {p['id']}: {p['title']} ({p['file']})" for p in projects)
    parts.append("\n" + ("=" * 96) + "\n")
    for project in projects:
        parts.append(render_project(project))
        parts.append("\n" + ("=" * 96) + "\n")
    return "\n".join(parts)


def index(projects: list[dict]) -> str:
    rows = [
        (p["id"], f"{p['title']} - {p['status']} - {p['file']}")
        for p in projects
    ]
    return (
        "Praxis Defense-Ready Full Text Drafts\n"
        "Generated: 2026-07-06\n\n"
        "Purpose\n"
        "This folder contains one defense-format Doctor of Engineering praxis "
        "text document for each currently defensible Praxis result.\n\n"
        "Important boundary\n"
        "PX-002 is included because it is packaged and useful as a bounded CTI "
        "lookup result. It is not labeled as a lead defense pillar.\n\n"
        "Files\n"
        f"{table(rows, ('ID', 'Document'))}\n\n"
        "Combined export\n"
        "PRAXIS_DEFENSE_READY_FULL_TEXT_EXPORT_20260706.txt\n\n"
        "Reference check\n"
        f"{COMMON_APA_NOTE}\n"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for project in PROJECTS:
        (OUT_DIR / project["file"]).write_text(render_project(project), encoding="utf-8")
    (OUT_DIR / "PRAXIS_DEFENSE_READY_FULL_TEXT_EXPORT_20260706.txt").write_text(
        combined_export(PROJECTS), encoding="utf-8"
    )
    (OUT_DIR / "README.txt").write_text(index(PROJECTS), encoding="utf-8")
    print(f"Wrote {len(PROJECTS)} praxis files plus index/export to {OUT_DIR}")


if __name__ == "__main__":
    main()
