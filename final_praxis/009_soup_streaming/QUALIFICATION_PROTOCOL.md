# 009: Soup streaming qualification

Status: prospective qualification, September 14, 2026. No GPU outcome was inspected when this protocol was written. Source inspection and local instrumentation controls are distinct from a scientific efficacy experiment. Vendor code and weights stay outside Git. AWS launch and spending are controlled by the parent coordinator.

## Literature and scope

Base: Alpamys Makazhan, *Exact Layer Streaming: LoRA Fine-Tuning of an 8B Model on a 4 GB Laptop GPU*, Zenodo preprint, August 2026. [Current paper record](https://doi.org/10.5281/zenodo.21918325), [v2 inspected in the literature review](https://doi.org/10.5281/zenodo.21877316), [Soup](https://github.com/MakazhanAlpamys/Soup).

Source pin: `b0a6338232f47d7ffabac90deb810728c2e179b4`; downloaded archive SHA256 `789c69de0ae95410f0847a29b8671513b16225fd60866b9acb5da0715108cf6f`. The earlier literature pin `e2c13ffc866c3c5f91f5b0d7fba2b35a27dcbe32` is 19 commits behind. The selected pin includes the NF4 reference-path correction and sharder mapping fix; this choice precedes execution. Code is Apache-2.0. Version 0.75.0 is not a sufficient immutable pin.

The September 12 upstream probe identifies synchronous disk reads as a bottleneck on its Windows laptop. Its cold large-model result uses synthetic weights, and its old RTX 3050 training throughput cannot be relabeled as current inference performance. Background prefetch, offloading, bounded buffers and layer-major scheduling are established ideas. [MegaTrain](https://arxiv.org/abs/2604.05091), ZeRO-Offload and LoHan require explicit comparison before a novel algorithm claim. Implementing an obvious background reader is an engineering qualification; it is not itself a defensible new mathematical contribution.

## Questions and hypotheses fixed before compute

**RQ-Q1 (correctness):** Does the pinned implementation preserve forward values, all trainable adapter gradients and a short update trajectory across resident, RAM and disk execution when weight bytes, inputs, adapter initialization and computation paths match?

**H-Q1:** All assigned positive controls are exactly equal and finite in the same execution environment; every intentionally corrupted control is rejected. Missing CUDA/dependencies, skipped tests and exceptions are incomplete qualification, never evidence of equality. Near-equality is reported descriptively and does not silently replace this gate.

**RQ-Q2 (process feasibility):** Can a bounded source that reads upcoming layers into owned staging tensors overlap CPU file reads with computation without reusing a tensor while its GPU copy is in flight?

**H-Q2:** The source respects its explicit staging-slot/byte bounds, preserves the Q1 outcomes, closes resources and surfaces read errors. A synchronous owned-staging arm separates asynchronous scheduling from pinning/copy effects. A CPU synthetic delay is only an instrumentation control, not disk-speed evidence.

**Candidate scientific RQ-S1:** On a declared resource-constrained machine and pretrained model, does a bounded read-ahead schedule reduce end-to-end LoRA step time under fixed host/device memory caps while preserving gradients and held-out task quality?

**Candidate H-S1 (not yet a registered efficacy experiment):** At least a 10% paired median step-time reduction against the strongest matched synchronous/fixed-prefetch baseline, with a block-level 95% interval excluding zero and a prospectively specified quality noninferiority margin. Thresholds and the final baseline pool must be frozen before a fresh efficacy test. This qualification does not validate H-S1.

## Qualification phases and assigned controls

1. Source/data gate: inspect runtime, benchmark harnesses, changed reference path, data terms, exact public artifact availability and minimal dependency metadata. Parse and hash source; execute no unreviewed setup scripts.
2. Local CPU controls: use installed PyTorch/safetensors only. Exercise the actual shipped `DiskSource`, `LayerBufferPool`, `StreamPrefetcher` and checkpointed layer wrapper on generated toy linear/LoRA blocks. Compare float32 forward/gradients/update trajectories against a resident reference. Check nonzero adapter contributions, deliberate wrong weights, recycled ownership, forward/backward direction changes, staging bounds, a missing source file, and close behavior. These are not pretrained model/data results.
3. Bounded GPU gate: generated tiny Llama checkpoint, four decoder layers, hidden size 64, vocabulary 64, two buffer slots, LoRA rank 4 on q/v. Match resident BF16 and resident NF4-dequant paths to the corresponding streamed arms. Use sequence lengths 12 and 64, no dropout, fixed seeds, nonzero LoRA-B, and two optimizer steps. Compare resident/RAM/shipped disk/synchronous owned staging/asynchronous owned staging. Run negative-gradient/weight checks separately. No network or model-token credentials are required for these generated inputs.
4. Development timing only after correctness: interleave the three disk arms in counterbalanced order, record startup and wall time after synchronization, allocated/reserved GPU memory, process RSS, staging bytes, source read bytes and Linux physical `read_bytes` when available. Small warm-cache timings can establish only software overhead, not a laptop cold-disk improvement. Do not infer a useful effect from artificial delay, stale-value ablations, or a tiny-model speed ratio.

Every invocation writes a receipt containing arguments, exact source/harness hashes, dependency versions, hardware, assigned/completed/failed counts, and an explicit scope. Vendor test exit code zero is insufficient because the old `bitexact.py` exits zero on no-CUDA skip. The pinned standalone `bitexact.py` also leaves the NF4 resident kernel unpatched; a dedicated harness must match `install_dequant_forward` on the resident NF4 arm. Native fused-kernel disagreement is a separate descriptive check, not a streaming defect by definition.

## Base-paper data and reproducibility gate

The paper's quality task is `dair-ai/emotion`, with five disjoint 3,000-item training subsets and a fixed 300-item test panel described in v2. Its dataset card declares `license: other`; public download is not unrestricted redistribution permission. The original Llama-3.1 checkpoint is gated and uses its own license. Historical scratch harnesses and exact sample/seed provenance are not all archived. This is a material barrier to claiming complete independent reproduction of the paper's downstream result.

Qualification will verify accessible paper/code/data metadata and record whether exact IDs, prompts, adapter initialization, score rules and split seeds can be reconstructed. If they cannot, label any later task run an adapted reproduction, use licensed alternative data for transfer, and do not report the original quality finding as independently reproduced. No dataset terms are bypassed; generated instrumentation proceeds without this dataset.

## Decision, spending and stopping rules

No paid job before source/control review. Proposed shared AWS host: one A10G on `g5.xlarge`, Linux, with an isolated environment. Parent owns the launch, enforced timeout and shutdown. Ceiling: two hours combined qualification occupancy and $25 reserved per route, with the parent enforcing the combined campaign limit. Requested first GPU gate is expected to take minutes after environment setup and needs no pretrained weights; dependency installation can dominate. No autonomous size escalation.

Advance only if all correctness/resource controls complete, base artifacts are adequate for the intended claim, and an explicit closest-prior gap survives review. A tiny-model pass permits a larger development feasibility check; it is neither a successful primary Praxis nor a novel speedup. Any mismatch, source drift, silent skip, budget overrun, unbounded staging or unhandled file error stops advancement. Preserve failures and amend the protocol openly before rerunning.
