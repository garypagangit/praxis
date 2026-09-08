"""Pinned real-model inference. No fixture or synthetic fallback is supported."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone


class HTTPAdapter:
    def __init__(self, base_url, model_id, revision, seed=20260908, timeout=900):
        self.base_url = base_url.rstrip("/")
        self.model_id, self.revision, self.seed = model_id, revision, seed
        self.timeout = timeout

    def generate(self, messages, max_new_tokens=256, temperature=0):
        payload = {"messages": messages, "max_new_tokens": max_new_tokens, "temperature": temperature,
                   "model_id": self.model_id, "revision": self.revision, "request_id": str(uuid.uuid4())}
        req = urllib.request.Request(self.base_url + "/generate", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        # Bypass inherited proxy variables only for this explicitly local inference service.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=self.timeout) as response:
            result = json.load(response)
        if result.get("model_id") != self.model_id or result.get("revision") != self.revision:
            raise RuntimeError("Inference model identity differs from frozen protocol")
        if "text" not in result:
            raise RuntimeError("Inference response has no generated text")
        return result

    def generate_batch(self, list_messages, max_new_tokens=256, temperature=0):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(lambda messages: self.generate(messages, max_new_tokens, temperature), list_messages))


class TransformersAdapter:
    def __init__(self, model_id, revision, seed=20260908, max_input_tokens=6144):
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
            raise ValueError("A full immutable model revision is required")
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not torch.cuda.is_available():
            raise RuntimeError("Scientific inference requires the declared CUDA hardware")
        self.model_id, self.revision, self.seed = model_id, revision, seed
        self.max_input_tokens = max_input_tokens
        self.torch = torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, revision=revision, torch_dtype=torch.bfloat16, device_map="cuda:0",
            attn_implementation="sdpa", trust_remote_code=False,
        ).eval()
        observed_revision = getattr(self.model.config, "_commit_hash", None)
        if observed_revision != revision:
            raise RuntimeError(f"Loaded model revision mismatch: {observed_revision}")
        self.runtime = {"torch": torch.__version__, "transformers": transformers.__version__,
                        "python": platform.python_version(), "cuda": torch.version.cuda,
                        "gpu": torch.cuda.get_device_name(0), "dtype": "bfloat16", "attention": "sdpa",
                        "quantization": None, "seed": seed, "model_id": model_id, "revision": revision,
                        "max_input_tokens": max_input_tokens}

    def _template_messages(self, messages):
        if self.model_id.startswith("mistralai/"):
            # The pinned Mistral template does not support a system role.
            # Preserve those exact instructions by prepending them to its first user turn.
            system = "\n\n".join(x["content"] for x in messages if x["role"] == "system")
            adjusted = [dict(x) for x in messages if x["role"] != "system"]
            if system:
                if not adjusted or adjusted[0]["role"] != "user":
                    raise ValueError("Mistral requires a user turn after system instructions")
                adjusted[0]["content"] = system + "\n\n" + adjusted[0]["content"]
            return adjusted
        return messages

    def generate(self, messages, max_new_tokens=256, temperature=0):
        return self.generate_batch([messages], max_new_tokens, temperature)[0]

    def generate_batch(self, list_messages, max_new_tokens=256, temperature=0):
        if temperature != 0:
            raise ValueError("Frozen discovery generation is greedy (temperature=0)")
        if not 1 <= max_new_tokens <= 1024:
            raise ValueError("Generation token budget outside supported bound")
        if not list_messages:
            return []
        prompts = [self.tokenizer.apply_chat_template(self._template_messages(messages), tokenize=False,
                                                     add_generation_prompt=True) for messages in list_messages]
        inputs = self.tokenizer(prompts, return_tensors="pt", padding=True, add_special_tokens=False)
        counts = inputs["attention_mask"].sum(dim=1).tolist()
        if max(counts) > self.max_input_tokens:
            raise ValueError("Frozen input token limit exceeded; silent truncation is forbidden")
        inputs = {key: value.to("cuda:0") for key, value in inputs.items()}
        started = time.monotonic()
        with self.torch.inference_mode():
            outputs = self.model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens,
                                          pad_token_id=self.tokenizer.pad_token_id,
                                          use_cache=True)
        duration = time.monotonic() - started
        generated = outputs[:, inputs["input_ids"].shape[1]:].cpu().tolist()
        eos = self.model.generation_config.eos_token_id
        eos_ids = set(eos if isinstance(eos, list) else [eos])
        results = []
        for i, tokens in enumerate(generated):
            stop = next((j + 1 for j, token in enumerate(tokens) if token in eos_ids), len(tokens))
            tokens = tokens[:stop]
            results.append({"text": self.tokenizer.decode(tokens, skip_special_tokens=True),
                            "model_id": self.model_id, "revision": self.revision,
                            "prompt_tokens": int(counts[i]), "completion_tokens": len(tokens),
                            "finish_reason": "stop" if tokens and tokens[-1] in eos_ids else "length",
                            "request_id": str(uuid.uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "prompt_sha256": hashlib.sha256(prompts[i].encode("utf-8")).hexdigest(),
                            "batch_size": len(prompts), "batch_seconds": duration, "runtime": self.runtime})
        return results
