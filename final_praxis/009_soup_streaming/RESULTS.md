# Soup qualification results

**Disposition: GO for a separately specified bounded pilot only.** The streaming and staging paths passed the tested numerical controls. The added prefetch did not improve the measured warm-cache workload. This is a correctness and feasibility result, with no pretrained quality reproduction, laptop benchmark, established novelty or paper-ready efficacy claim.

## What actually ran

The frozen protocol and Soup commit `b0a6338232f47d7ffabac90deb810728c2e179b4` ran on one NVIDIA A10G. The generated random Llama has 152,128 parameters and four layers. Its 16 LoRA adapter tensors start nonzero. BF16 and NF4 at sequence lengths 12 and 64 were each evaluated through RAM, stock disk, synchronous owned staging and owned prefetch, against a matched resident reference.

All **16/16** positive trajectories match exactly across 52 saved tensors per trajectory: both steps' logits, loss and 16 gradients, plus the final 16 adapter states. All gradients are finite and nonzero. All **4/4** deliberate modifications to recorded gradients are rejected. These negative controls test comparator sensitivity; they are not four independently generated model defects. Both local and cloud CPU controls also passed **10/10**.

The separate artifact checker recomputed equality from all 20 saved safetensor files and reconciled assignments, counters, provenance, staging bounds and timing completeness: **107/107 checks passed**. It does not import the worker's comparator. The checker and worker share an author; the coordinator's source review is a separate review, not an independent laboratory replication.

Owned staging used at most two slots, reaching its declared bound of 147,968 bytes for BF16 and 38,640 bytes for NF4. These are staging allocations, not total process or model memory. Large embedding/head streaming remains outside this qualification. NF4 uses the matched dequantization reference; equivalence with a distinct native fused-kernel path is not established.

## Warm-cache timing

Three rotated blocks per arm each contain two warmup and three measured optimizer steps. The table reports each block's median step time and their mean. These are descriptive development measurements on the same tiny model, not independent scientific replicates.

| Arm | Block 0 median (ms) | Block 1 median (ms) | Block 2 median (ms) | Mean of block medians (ms) |
|---|---:|---:|---:|---:|
| Stock disk | 63.55 | 64.69 | 65.21 | 64.49 |
| Synchronous owned staging | 64.86 | 64.95 | 66.13 | 65.31 |
| Owned prefetch | 67.26 | 70.00 | 68.42 | 68.56 |

Prefetch took **6.32% more time than stock disk** and **4.97% more than synchronous staging**, using ratios of the unrounded mean block medians. All 27 measured steps recorded zero process `read_bytes` increase. Logical staging reads are not physical disk traffic; this test supplies no cold-disk or memory-pressure benefit estimate. No confidence interval, significance or general performance claim is inferred from these three development blocks.

## Investment boundary and next gate

The implementation is suitable for a narrow systems pilot if a credible I/O-bound use case can be specified. The next protocol should freeze actual memory pressure, source/storage placement, cold and warm conditions, full-step wall time, physical I/O, CPU/host/GPU memory accounting and matched stock-disk plus synchronous-staging baselines before outcomes. Establish that the target workload is actually limited by reads before spending on a larger quality study. A background reader alone is established engineering and does not satisfy a novelty claim.

The public Emotion split files are available for educational/research use and have been checked, but exact original paper sample preparation was not recovered. The full supplied splits also contain exact-text overlap, which requires a prospective deduplication/split policy for a new adapted study. A fresh model or new sample split must be described as an adapted reproduction. None of these quality experiments ran here.

The [failed-attempt history](EXECUTION_ATTEMPTS.md) is preserved. [Summary JSON](results/GPU_SUMMARY.json), [raw GPU receipt](results/gpu/GPU_QUALIFICATION.json), [artifact review](results/gpu/ARTIFACT_REVIEW.json), [environment](results/gpu/PIP_FREEZE.txt), and [lineage](results/EXECUTION_LINEAGE.json) provide the evidence. The original [protocol](QUALIFICATION_PROTOCOL.md) and [bundle manifest](BUNDLE_MANIFEST.json) are unchanged.

## Recheck without running a model

From this directory, with Python, CPU PyTorch and safetensors:

```text
python review/audit_gpu_results.py --results results/gpu --manifest BUNDLE_MANIFEST.json --output artifact_review_recheck.json
python review/summarize_gpu_results.py --input results/gpu/GPU_QUALIFICATION.json --output summary_recheck.json
python review/verify_release.py --root . --manifest RELEASE_MANIFEST.json --output release_recheck.json
```

The seal verifies listed file bytes. It does not turn qualified instrumentation into a scientific efficacy result.
