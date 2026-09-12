# Prospective float32 qualification review — 12 September 2026

**Recommendation:** a separately preregistered float32 qualification is technically reasonable and appears to fit the existing A10G at batch size one. Preserve the failed bfloat16 run. Keep all scientific gates, data, prompts, extraction, conditions and token limits unchanged. Commit the new precision/backend contract before any new inference. Passing the new technical checks remains a prerequisite, not an assumed outcome.

## What actually failed

Reviewed the S3 `outputs/technical.json`, `outputs/environment.json`, and `cloud_status.json` for `fp006-logic-5075fe39d3` under the campaign's `final-praxis/20260912/runs/` prefix. The supervisor recorded `FAILED` at 20:18:04 UTC, return code 1. A separate read-only listing found no objects under `outputs/cells/`; thus this run produced no pilot or test cells.

All artifact hashes, tensor shapes, exact loading, finite-logit checks, repeated evaluations, ablation reset, excluded-expert checks, and cached/full final-token checks passed. Cached/full routing selections also agreed on all six probes. Eager/SDPA final-token predictions differed on one of six probes: the short arithmetic prompt under social ablation. Its maximum absolute logit difference was 0.15625, within the old 0.25 bound; the independent top-token-equality rule correctly stopped the run. The other five eager/SDPA comparisons agreed. Minimum final-position router margins ranged from 0.009765625 to 0.033203125.

These observations identify backend-dependent behavior at bfloat16 precision. They do not isolate its cause: the receipt lacks eager/SDPA expert-route comparisons and vocabulary top-two margins. In particular, matching cached/full routes does not prove eager/SDPA routes matched. Do not call this a failed scientific hypothesis or infer that social ablation helps/hurts GSM8K.

## Memory calculation

The exact checkpoint contains 4,485,154,816 F32 parameters. The local, pinned tokenizer was used only to count tokens in the existing 16 pilot and 256 test prompts; no model inference was performed. Prompt lengths are 37–146 tokens, giving at most 1,170 context tokens with the unchanged 1,024-token generation cap.

| Allocation | Calculation | Size |
|---|---|---|
| Weights | 4,485,154,816 × 4 bytes | 17,940,619,264 bytes = **16.7085 GiB** |
| Persistent KV per token | 16 groups × 4 experts × 2 (K,V) × 8 KV heads × 64 head dimension × 4 bytes | 262,144 bytes |
| Maximum persistent KV | 262,144 × 1,170 | 306,708,480 bytes = **0.2856 GiB** |
| Weights plus maximum KV | Sum above | **16.9941 GiB** |
| One prefill attention score matrix | 32 heads × 146 × 146 × 4 bytes | 2.60 MiB |

The Transformers SDPA wrapper temporarily repeats 8 KV heads to 32 attention heads for the current expert call. At maximum context, those temporary key/value buffers total approximately 18.3 MiB; the stored cache remains at eight KV heads. Scratch activations, CUDA context, allocator reservations, model buffers and loading overhead are additional. The model executes expert blocks serially, so attention scratch is not multiplied by 64 as simultaneous retained activations in inference mode.

AWS documents 24 GB per A10G on G5. The calculated core footprint leaves plausible room for overhead, but marketed capacity is not a measurement of runtime free memory. Record `torch.cuda.mem_get_info()` after loading and peak allocated/reserved memory during qualification. Keep direct GPU shard loading, `torch.inference_mode()`, batch size one, fresh per-cell caches and `logits_to_keep=1`. Do not construct a second model or a full CPU F32 copy; some single-GPU G5 instances have only 16 GiB host RAM. [AWS G5 specifications](https://aws.amazon.com/ec2/instance-types/g5/)

## Precision and backend choice

Float32 uses the checkpoint's original stored precision rather than a bfloat16 cast. Keep both CUDA-matmul and cuDNN TF32 disabled, use no autocast, and verify every loaded parameter plus representative output/cache tensors is F32. The author's constructor writes a bfloat16 metadata flag; the explicit `from_pretrained(torch_dtype=torch.float32)` and actual tensor checks, rather than that descriptive flag, must govern the run.

PyTorch warns that floating-point operation order and batching can change results, and that TF32 reduces mantissa precision on Ampere. Consequently, `max_abs <= 1e-3` together with identical final top token is a prospective engineering gate, not a guaranteed theorem about float32. Preserve exact-repeat/reset checks and report routing agreement and margins. Do not widen the tolerance or remove the top-token rule after seeing new outputs. [PyTorch 2.6 numerical accuracy](https://docs.pytorch.org/docs/2.6/notes/numerical_accuracy.html)

Automatic FP32 SDPA is defensible if its permitted backends and software environment are recorded. A more explicit alternative is to restrict SDPA to `SDPBackend.MATH` using `torch.nn.attention.sdpa_kernel`, while retaining the independent Transformers eager comparison. PyTorch documents both automatic backend selection and numerical variation from fused operations. Explicit math selection removes that selection variable but may cost throughput. Choose and preregister one approach before running; do not cycle variants until the probes pass. BF16 math-SDPA is not clearly preferable here: it still retains BF16 weights/outputs and would need its own qualification. [PyTorch 2.6 SDPA reference](https://docs.pytorch.org/docs/2.6/generated/torch.nn.functional.scaled_dot_product_attention.html)

## Amendment record and stopping rule

Use a new sibling study and unique run ID, retaining the original v1 archive, failed receipt, costs and zero-cell outcome. State that the change follows a technical-only failure on fixed non-benchmark prompts. Freeze the same 256 test rows and 16 pilot rows, checkpoint/source/tokenizer hashes, raw prompt, three arms, 1,024-token budget, extraction, paired statistics and scientific investment gates. The changed items are numerical precision and the explicitly declared backend/tolerance contract.

Log predicted token IDs/top-two logit margins and eager/SDPA selected routes on the same six technical probes; these diagnostics must not modify acceptance afterward. Abort before pilot/test generation if any required technical gate fails or memory is insufficient. Retain the existing financial/runtime cap and independent shutdown mechanisms. FP32 can materially reduce throughput; incomplete output must remain incomplete and must not be promoted by changing the cohort or gate after observing it.

This review used public documentation, local tokenization and read-only S3 receipts. It did not perform model inference, download new model weights, or mutate AWS state.
