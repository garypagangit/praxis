# Literature check — 2026-10-02

This is an initial overlap check, not a claim of exhaustive novelty clearance.

| Primary source | What overlaps | What remains to test here |
|---|---|---|
| [Visual Semantics of NetFlow: Zero-Shot DoS Attack Detection with Vision–Language Models](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7315138), Luay, Layeghy and Portmann | The search-indexed author abstract explicitly describes NetFlow visualizations, matched structured text and transfer tests. Direct full-text access returned 403. | Residual exfiltration-warning recovery beyond frozen existing experts, with added case workload. Full-paper comparison remains required. |
| [Harnessing Vision-Language Models for Time Series Anomaly Detection](https://ojs.aaai.org/index.php/AAAI/article/view/39319), He, Alnegheimish and Reimherr, AAAI 2026 | Visual time-series anomaly detection and comparison with language approaches. | Whether this specific residual-warning target is recoverable and useful. |
| [MM-AttacKG](https://arxiv.org/html/2506.16968v1), Zhang et al. | Uses images and text in CTI reports to construct attack graphs. | Our traffic-only time-bin stage reconstruction is a different task; this paper does not automatically validate it. |
| [Qwen2.5-VL technical report](https://arxiv.org/abs/2502.13923) and [model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | Reproducible model foundation and chart interpretation capability. | Security outcomes require our own evaluation. |
| [On Combining Classifiers](https://doi.org/10.1109/34.667881), Kittler et al., 1998 | Classifier combination is established. | OR monotonicity is a verification property, not the novelty claim. |

Decision: run a bounded feasibility pilot. Do not call either idea novel or committee-ready yet. PX-098 has the clearer outcome and cheaper evaluation. PX-099 requires substantially more label and temporal evaluation work.
