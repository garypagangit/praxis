# A Stronger Graph Model for Detecting Stealthy Cyberattacks

**Status: both registered 50-epoch evaluations completed and independently audited; AWS is stopped.**

## Plain-language finding

We replaced the earlier lightweight experimental models with the published MAGIC graph model. The model learns patterns in normal computer activity and assigns higher scores to activity that looks different. This test establishes what that stronger published model can do on the available prepared data. It does not establish a new praxis method or an independently calibrated operational detector.

## Measured results

**The alert thresholds in this table were chosen using the attack labels, following the author's evaluation rule. These are descriptive oracle results.** They must not be presented as alert performance at a threshold chosen before seeing attacks.

| Dataset | Completed training | Attack recall | False-positive rate | Precision | F1 | AUROC |
|---|---:|---:|---:|---:|---:|---:|
| THEIA | 50 epochs | 99.996% | 0.144% | 98.216% | 0.9910 | 0.9987 |
| CADETS | 50 epochs | 99.774% | 0.236% | 94.049% | 0.9683 | 0.9976 |

Supplemental maximum-F1 thresholds also use test labels and are reported in [SUMMARY.json](SUMMARY.json), along with average precision and all confusion counts. They are not an additional unbiased validation.

## What was actually run

- Original MAGIC source at commit `aa0b647eea74b6faa0e52eb444370c4411a32cbe`: three edge-aware attention layers, 64-dimensional embeddings, feature/structure reconstruction, 50% masking and original seed zero.
- Four prepared normal training graphs and one previously exposed labeled test graph per dataset. THEIA: 1,279,199 training rows and 344,767 test rows. CADETS: 1,269,862 training rows and 357,173 test rows.
- Every training row contributes to standardization and the reference distribution; k=10 THEIA and k=200 CADETS. No reference sampling, approximate nearest-neighbor search, changed training objective, or checkpoint reuse.
- Author masking-target mutation and absent normalization behavior were preserved and measured. Python/Torch/DGL are a qualified newer runtime, not the paper's historical environment. Full original-source and runtime-amendment registrations remain available.

## How the runtime barrier was resolved

The two original training-only qualifications projected approximately 103 and 107 minutes of remaining work, including safety, for our direct-float64 uncompressed GPU scoring adapter. These were estimates, not completed full-scoring timings or evidence that the author's original CPU implementation is inherently slow. Neither qualification loaded its attack test graph.

Exact duplicate compression stores identical standardized vectors once and retains their integer counts. It reduces repeated distance calculations while preserving the mathematical k-neighbor score. Small floating-point summation differences are audited. The THEIA first-epoch probe reduced 1,279,199 rows to 26,087 distinct vectors. The table below reports the actual final banks:

| Dataset | Original reference rows | Distinct final vectors | Duplicate rows represented by counts |
|---|---:|---:|---:|
| THEIA | 1,279,199 | 25,934 | 97.97% |
| CADETS | 1,269,862 | 8,058 | 99.37% |

This is an engineering adaptation. Duplicate-aware search already exists in [Faiss](https://github.com/facebookresearch/faiss/blob/v1.7.4/faiss/IndexIVFFlat.cpp#L336). Counts and full-bank sample scores were independently checked; no speedup or retraining-stability novelty is claimed.

## What the evidence supports

This completed reproduction supplies a substantially stronger published baseline for future APT detector or checker work. A favorable oracle score shows that the model can separate annotated activity at a label-selected threshold; it does not prove that a deployable checker knows where to set that threshold. The next scientific question is whether normal-only calibration can retain useful recall and a low false-alert rate without consulting attack labels. That separate comparison was not run here.

The previous normal-reference stability family remains closed with its negative result. This new result does not retroactively change its gates or validate a new stopping/checking policy.

## Limits and checks

- One seed and one test graph per dataset; prepared rows are not independent campaigns or verified unique entities. Test-negative rows mean absent from supplied malicious annotations, not independently verified innocence.
- The graphs have no usable UUID/time mapping for independent campaign, delay, real outage, actor-attribution or attack-stage claims. Type vocabulary dimensions were determined using training and test data upstream.
- Independent audits recomputed metrics, thresholds, scaler values, normalizer selections, full-bank sampled distances, exact duplicate counts, checkpoint inventories and hashes. Neural training and embedding inference were not rerun by the auditor.
- Seventy distinct software tests passed across source fidelity, scoring, transport, runtime substitution and independent evidence validation. A preserved qualification addendum records the final added auditor test.
- All 3 AWS attempts are verified stopped. Estimated compute: **$0.411**, excluding storage, transfer and other charges; not an invoice. See [AWS_CLOSEOUT.json](AWS_CLOSEOUT.json).

## Literature and next decision

Jia, Z., Xiong, Y., Nan, Y., Zhang, Y., Zhao, J., & Wen, M. (2024). MAGIC: Detecting advanced persistent threats via masked graph representation learning. In *33rd USENIX Security Symposium* (pp. 5197–5214). [Primary paper](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian).

The broader literature/data gates remain explicit: [S-DAPT withdrawal and SCVIC correction](../../../docs/LITERATURE_CORRECTION_20260920.md); [local-LLM artifact and novelty boundaries](../../../docs/LOCAL_LLM_ARTIFACT_GATE_20260920.md). A defended praxis claim still needs a specific contribution and independent evidence beyond this baseline reproduction.
