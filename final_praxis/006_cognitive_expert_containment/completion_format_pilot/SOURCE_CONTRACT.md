FP32 follow-up note: this runner explicitly passes dtype=float32; the historical loader below also supports BF16. Expected FP32 weights occupy16.71GiB before runtime overhead. See RUNTIME_FP32_REVIEW.md.

# MiCRo Llama-1B loader contract — 12 September 2026

The staged loader preserves the author's full-block expert architecture and routing mathematics. Its only source-code change replaces the constructor's hard-coded `flash_attention_2` with `sdpa`. Numerical equivalence, cache equivalence, ablation reset, and routing observations must still pass the separate GPU qualification; these checks have not run here.

## Frozen artifacts and provenance

| Artifact | Exact revision / location |
|---|---|
| Checkpoint | [`bkhmsi/micro-llama-1b`](https://huggingface.co/bkhmsi/micro-llama-1b/tree/b9ea46bbfb2836552e963ea3ad322d9fb3b07179), revision `b9ea46bbfb2836552e963ea3ad322d9fb3b07179` |
| Author source | [`BKHMSI/mixture-of-cognitive-reasoners`](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/tree/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7), revision `275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7` |
| Original backbone | [`meta-llama/Llama-3.2-1B`](https://huggingface.co/meta-llama/Llama-3.2-1B/tree/4e20de362430cd3b72f300e6b0f18e50e7166e08), revision `4e20de362430cd3b72f300e6b0f18e50e7166e08` |
| Official tokenizer | [`meta-llama/Llama-3.2-1B-Instruct`](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct/tree/9213176726f574b556790deb65791e0c5aa438b6), revision `9213176726f574b556790deb65791e0c5aa438b6` |

The [official YAML](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/configs/config_micro_llama.yml) names the base backbone and instruct tokenizer separately. Both official repositories are gated. The four bundled tokenizer files were obtained with existing authorized access and independently matched to public Git-blob fingerprints from the pinned official tree. `tokenizer_receipts.json` records SHA-256 and Git-blob SHA-1. No credentials are part of the bundle. Public Unsloth/ONNX tokenizer versions checked during preparation differed byte-for-byte and were not used.

The checkpoint has no tokenizer files and no declared model-license metadata; its model card is a generic placeholder. Base and tokenizer cards declare `llama3.2`, and the exact official `LICENSE.txt` is bundled. The source repository's metadata has no declared license. This memo records artifact provenance; it does not resolve the checkpoint author's missing license declaration.

## Architecture and loading

The checkpoint contains **4,485,154,816 parameters stored as F32**, with 17,940,619,264 tensor bytes across four safetensors shards. “1B” denotes the original backbone scale, not the total checkpoint size. On GPU, bfloat16 parameters alone require approximately 8.97 GB decimal (8.35 GiB), before activations, caches and runtime overhead. Source hashes and shard SHA-256/byte sizes are hard-coded in `model_loader.py` and readable in its returned receipt. No weights were downloaded during this preparation.

The checkpoint configuration serializes `num_hidden_layers=64` and `backbone_num_layers=16`. The [custom constructor](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/models/micro_llama.py) multiplies its input layer count by four. Passing the checkpoint config unchanged would therefore incorrectly construct 64 backbone groups / 256 expert blocks. The loader restores `num_hidden_layers` to the checkpoint's recorded 16 before invoking the constructor, resulting in exactly 16 groups, 64 expert blocks, four experts and top-1 selection.

All other architectural values come directly from the pinned checkpoint config, avoiding a second base-config download. The loader independently derives and checks all 611 tensor names and shapes: 64 full Llama blocks, 16 two-linear-layer routers, separate embedding and output tensors, and final normalization. It verifies F32 tensor storage, strict checkpoint loading with no missing/unexpected/mismatched keys, total parameter count, and final dtype/device. It requests direct bfloat16 GPU loading through `device_map` and requires the qualified author's `transformers==4.53.2` interface. Runtime also needs PyTorch, Accelerate, PyYAML, safetensors and huggingface_hub as supplied by the campaign environment.

The YAML's model key is `micro-llama`; `generate.py` maps the published checkpoint under `micro-llama-1b`. The loader uses the explicit pinned model ID rather than invoking that inconsistent demo mapping. The saved architecture name is `MiCRoLlama`, but `model_type` is `llama` and no remote auto-map is supplied. Stock `AutoModelForCausalLM` is not the qualified loader.

## Runtime interface and interpretation

```python
settings = json.loads((bundle / "loader_settings.json").read_text())
model, tokenizer, receipt = load_model(bundle / "source", settings,
                                       device="cuda", dtype="bfloat16")
```

`verify_bundle(bundle / "source")` performs only offline hash/config/index checks and can run without Torch or Transformers. Calling `load_model` downloads the pinned model shards if absent and then validates them. `local_files_only=true` prohibits those downloads; `hf_cache_dir` may select a campaign cache. The official tokenizer loads entirely from the bundled sibling `tokenizer` directory and needs no AWS credential.

Author expert order is **logic=0, social=1, world=2, language=3**. Despite its name, the returned `routing_weights` field contains **raw router logits**. Reproduce the author's selection for exact route counts: `torch.topk(torch.softmax(r, dim=-1, dtype=torch.float32), 1, dim=-1).indices.squeeze(-1)`. Plain argmax can choose a different expert when BF16 logits tie. Do not count these values as already normalized weights. Ablation sets specified logits to negative infinity before the author's softmax/top-k operation. Layer ablation state persists, so pass `experts_ablate=[]` explicitly for each intact condition and start independent generations with fresh KV caches.

Checkpoint BOS/EOS IDs are 128000/128001; the official instruct tokenizer's EOS is 128009 (`<|eot_id|>`). It has no native padding token. The author overrides padding to 128004; the loader applies that exact override and left padding. The caller must explicitly freeze generation stopping, recommended IDs `[128001, 128009]`, and its benchmark stop strings and output-token budget. These IDs do not establish the paper's unstated benchmark generation details.

The official instruct chat template embeds a date by default. For any preregistered chat-template arm, pass an explicit `date_string` such as the frozen `12 Sep 2026` setting and record rendered token IDs. A raw-task arm must explicitly decide BOS insertion and must not accidentally wrap its prompt through this template. This loader does not select or alter the benchmark prompt.

The metadata/code/tokenizer preparation and offline verification used no model inference, paid calls or GPU starts. GPU numerical qualification and any GSM8K outcomes remain outstanding.
