"""Exact MiCRo Llama-1B checkpoint loader; no inference occurs on import.

Runtime entry point: load_model(source_dir, settings, device='cuda',
dtype='bfloat16') -> (model, tokenizer, receipt). source_dir is the bundled
``source`` directory; its sibling ``tokenizer`` directory contains official,
authorized, byte-verified tokenizer files. Calling load_model downloads the
four pinned checkpoint shards unless they are already cached.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import types

MODEL = 'bkhmsi/micro-llama-1b'
REVISION = 'b9ea46bbfb2836552e963ea3ad322d9fb3b07179'
SOURCE_REVISION = '275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7'
BASE = 'meta-llama/Llama-3.2-1B'
BASE_REVISION = '4e20de362430cd3b72f300e6b0f18e50e7166e08'
TOKENIZER = 'meta-llama/Llama-3.2-1B-Instruct'
TOKENIZER_REVISION = '9213176726f574b556790deb65791e0c5aa438b6'
SOURCE_HASHES = {
    'models/micro_llama.py': '2c6d4bda9994167bfd3f8d8a1b4d605f4559c2a9da8e780e9e6645835cd0eb41',
    'models/modules.py': '34696d4bfa9413c029a2cf0ac3b3541f527a08dff59c4622457fe6a3737f7dd1',
    'repo_config.yml': 'b467ac496716ed82c9bc0280a6900c79079b19311eb8e6e1064ef5402310dc4a',
    'checkpoint_config.json': 'f62145a71b6020f3051afbacd9242686c5a1c5be79ba565bef300e034b8877da',
    'model.safetensors.index.json': 'f40599424a522e1be80b42cdc678c356126a3c34605244eff2ad09422931d3c9',
    'generation_config.json': 'e41ed16c66408b8e6f5c06f189a5aabb39724ef2a0092da0aeb26b9bd1da324f',
}
TOKENIZER_HASHES = {
    'tokenizer.json': '79e3e522635f3171300913bb421464a87de6222182a0570b9b2ccba2a964b2b4',
    'tokenizer_config.json': '9823dcfdc1121869029da45192238e85cf44f0b232a6d9dc20e4fe6f4242a14e',
    'special_tokens_map.json': '6f38c73729248f6c127296386e3cdde96e254636cc58b4169d3fd32328d9a8ec',
    'LICENSE.txt': '0b4284c1f87029e67654c7953afa16279961632cf73dcfe33374c4c2f298fa35',
}
SHARDS = {
    'model-00001-of-00004.safetensors': ('bcd3f2811acea4b4363c24c553e6885db0a7703c84ef280ddd78d926fb6422df', 4943381688),
    'model-00002-of-00004.safetensors': ('9fc1b82242c728cb167ba3deec8963c8e266a3213964ad48b6676fc978129fcb', 4949792456),
    'model-00003-of-00004.safetensors': ('dc6eee178b3425cf08b6e539ba2bf43ce13ae9e5550b8a9d348c1e22795ab6ff', 4949792600),
    'model-00004-of-00004.safetensors': ('2a8e0a2040aa71ee86f063ef96ffa36a4ba7a7e20e257004e5e99fc1211f67f2', 3097724152),
}


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _verify_files(directory, expected):
    observed = {}
    for name, digest in expected.items():
        path = Path(directory) / name
        got = file_sha256(path)
        if got != digest:
            raise ValueError(f'Pinned file hash mismatch: {path}')
        observed[name] = {'sha256': got, 'size': path.stat().st_size}
    return observed


def expected_shapes():
    """All 611 checkpoint tensors, independently derived from architecture."""
    shapes = {'embed_tokens.weight': (128256, 2048),
              'lm_head.weight': (128256, 2048), 'final_norm.weight': (2048,)}
    block = {
        'input_layernorm.weight': (2048,), 'post_attention_layernorm.weight': (2048,),
        'self_attn.q_proj.weight': (2048, 2048), 'self_attn.o_proj.weight': (2048, 2048),
        'self_attn.k_proj.weight': (512, 2048), 'self_attn.v_proj.weight': (512, 2048),
        'mlp.gate_proj.weight': (8192, 2048), 'mlp.up_proj.weight': (8192, 2048),
        'mlp.down_proj.weight': (2048, 8192),
    }
    for layer in range(16):
        shapes[f'layers.{layer}.gate.0.weight'] = (2048, 2048)
        shapes[f'layers.{layer}.gate.1.weight'] = (4, 2048)
        for expert in range(4):
            for name, shape in block.items():
                shapes[f'layers.{layer}.experts.{expert}.{name}'] = shape
    return shapes


def verify_bundle(source_dir):
    """Offline verification of code/config/tokenizer files; no model imports."""
    source_dir = Path(source_dir).resolve()
    tokenizer_dir = source_dir.parent / 'tokenizer'
    sources = _verify_files(source_dir, SOURCE_HASHES)
    tokenizer = _verify_files(tokenizer_dir, TOKENIZER_HASHES)
    cfg = json.loads((source_dir / 'checkpoint_config.json').read_text())
    if (cfg['backbone_num_layers'], cfg['num_hidden_layers'], cfg['num_experts'],
        cfg['num_experts_per_tok']) != (16, 64, 4, 1):
        raise ValueError('Unexpected checkpoint architecture')
    index = json.loads((source_dir / 'model.safetensors.index.json').read_text())
    if set(index['weight_map']) != set(expected_shapes()):
        raise ValueError('Checkpoint index tensor names do not match exact architecture')
    if set(index['weight_map'].values()) != set(SHARDS):
        raise ValueError('Unexpected checkpoint shard set')
    if index['metadata']['total_size'] != 17940619264:
        raise ValueError('Unexpected tensor byte count')
    return {'sources': sources, 'tokenizer_files': tokenizer,
            'expected_tensor_count': 611, 'expected_parameters': 4485154816}


def _source_module(source_dir):
    original = (source_dir / 'models/micro_llama.py').read_text(encoding='utf-8')
    needle = 'self.config._attn_implementation = "flash_attention_2"'
    if original.count(needle) != 1:
        raise ValueError('SDPA portability patch must match exactly once')
    patched = original.replace(needle, 'self.config._attn_implementation = "sdpa"')
    # Import the pinned output dataclass through the author's original import.
    # Reject an unrelated already-imported package rather than silently using it.
    existing = sys.modules.get('models.modules')
    wanted = source_dir / 'models/modules.py'
    if existing is not None and Path(existing.__file__).resolve() != wanted.resolve():
        raise RuntimeError('Another models.modules is already imported; use a fresh process')
    source_text_path = str(source_dir)
    if source_text_path not in sys.path:
        sys.path.insert(0, source_text_path)
    name = '_praxis006_pinned_micro_llama'
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__file__ = str(source_dir / 'models/micro_llama.py')
        sys.modules[name] = module
        try:
            exec(compile(patched, module.__file__, 'exec'), module.__dict__)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    loaded = sys.modules['models.modules']
    if Path(loaded.__file__).resolve() != wanted.resolve():
        raise RuntimeError('Pinned output dataclass import resolved outside source bundle')
    patch_receipt = {
        'original_sha256': SOURCE_HASHES['models/micro_llama.py'],
        'compiled_sha256': hashlib.sha256(patched.encode()).hexdigest(),
        'change': 'Constructor flash_attention_2 default changed to sdpa; no other source edits',
    }
    return module, patch_receipt


def load_model(source_dir, settings, device='cuda', dtype='bfloat16'):
    """Load and validate exact weights. Caller owns inference and spending limits."""
    source_dir = Path(source_dir).resolve()
    receipt = verify_bundle(source_dir)
    pins = {'model': MODEL, 'model_revision': REVISION,
            'source_revision': SOURCE_REVISION, 'tokenizer': TOKENIZER,
            'tokenizer_revision': TOKENIZER_REVISION}
    for key, value in pins.items():
        if settings.get(key, value) != value:
            raise ValueError(f'Frozen {key} does not match loader contract')
    import torch
    from huggingface_hub import snapshot_download
    from safetensors import safe_open
    from transformers import AutoTokenizer
    if importlib.metadata.version('transformers') != '4.53.2':
        raise RuntimeError('Pinned author source requires qualified transformers==4.53.2')
    if dtype not in ('bfloat16', 'float32'):
        raise ValueError('Unsupported qualification dtype')
    torch_dtype = getattr(torch, dtype)
    if str(device).startswith('cuda'):
        if not torch.cuda.is_available():
            raise RuntimeError('Requested CUDA device is unavailable')
        if dtype == 'bfloat16' and not torch.cuda.is_bf16_supported():
            raise RuntimeError('Requested CUDA device does not support bfloat16')
    module, patch = _source_module(source_dir)
    tokenizer = AutoTokenizer.from_pretrained(str(source_dir.parent / 'tokenizer'),
                                             local_files_only=True, trust_remote_code=False)
    tokenizer.padding_side = 'left'
    tokenizer.pad_token_id = 128004  # Exact author inference override.
    special_ids = {'bos': tokenizer.bos_token_id, 'eos': tokenizer.eos_token_id,
                   'pad': tokenizer.pad_token_id}
    if special_ids != {'bos': 128000, 'eos': 128009, 'pad': 128004} or len(tokenizer) != 128256:
        raise ValueError('Unexpected pinned tokenizer special tokens or vocabulary')
    config_data = json.loads((source_dir / 'checkpoint_config.json').read_text())
    # The constructor expands this field. Restoring the saved backbone count
    # avoids constructing 64 groups (256 expert blocks) from the serialized 64.
    config_data['num_hidden_layers'] = config_data['backbone_num_layers']
    config_data['config_path'] = str(source_dir / 'repo_config.yml')
    config_data['ablate'] = []
    config_data['torch_dtype'] = torch_dtype
    config = module.MiCRoLlamaConfig(**config_data)
    checkpoint = Path(snapshot_download(
        MODEL, revision=REVISION,
        allow_patterns=list(SHARDS) + ['config.json', 'generation_config.json', 'model.safetensors.index.json'],
        cache_dir=settings.get('hf_cache_dir'), local_files_only=settings.get('local_files_only', False),
    ))
    artifact_receipts = _verify_files(checkpoint, {
        'config.json': SOURCE_HASHES['checkpoint_config.json'],
        'generation_config.json': SOURCE_HASHES['generation_config.json'],
        'model.safetensors.index.json': SOURCE_HASHES['model.safetensors.index.json'],
        **{key: value[0] for key, value in SHARDS.items()},
    })
    shapes = expected_shapes()
    observed_shapes = {}
    for shard, (_, size) in SHARDS.items():
        if (checkpoint / shard).stat().st_size != size:
            raise ValueError(f'Unexpected shard size: {shard}')
        with safe_open(str(checkpoint / shard), framework='pt', device='cpu') as tensors:
            for key in tensors.keys():
                if key in observed_shapes:
                    raise ValueError(f'Duplicate tensor in checkpoint shards: {key}')
                tensor = tensors.get_slice(key)
                shape = tuple(tensor.get_shape())
                if shape != shapes.get(key) or tensor.get_dtype() != 'F32':
                    raise ValueError(f'Unexpected checkpoint tensor shape or dtype: {key}')
                observed_shapes[key] = shape
    if observed_shapes != shapes:
        raise ValueError('Checkpoint shard tensor set is incomplete')
    model, loading = module.MiCRoLlama.from_pretrained(
        str(checkpoint), config=config, torch_dtype=torch_dtype,
        device_map={'': str(device)}, low_cpu_mem_usage=True, use_safetensors=True,
        output_loading_info=True, local_files_only=True,
    )
    if any(loading.get(key) for key in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')):
        raise RuntimeError(f'Checkpoint did not load exactly: {loading}')
    model.eval()
    actual_shapes = {name: tuple(tensor.shape) for name, tensor in model.state_dict().items()}
    if actual_shapes != shapes:
        raise ValueError('Loaded model tensor names/shapes differ from checkpoint contract')
    if len(model.layers) != 16 or model.config.num_hidden_layers != 64:
        raise ValueError('Incorrect backbone/expert layer expansion')
    if any(layer.num_experts != 4 or layer.top_k != 1 for layer in model.layers):
        raise ValueError('Incorrect expert count or top-k')
    if model.config._attn_implementation != 'sdpa':
        raise ValueError('SDPA portability setting was not retained')
    if any(p.dtype != torch_dtype or p.device.type != torch.device(device).type for p in model.parameters()):
        raise ValueError('Loaded parameters have incorrect precision/device')
    parameters = sum(p.numel() for p in model.parameters())
    if parameters != 4485154816:
        raise ValueError(f'Unexpected parameter count or weight tying: {parameters}')
    receipt.update(pins)
    receipt.update({
        'base_model_provenance': {'model': BASE, 'revision': BASE_REVISION,
                                 'downloaded': False, 'configuration_source': 'exact checkpoint config, layer count restored to 16'},
        'checkpoint_artifacts': artifact_receipts, 'loading': loading, 'source_patch': patch,
        'parameters': parameters, 'backbone_layers': 16, 'expert_blocks': 64,
        'dtype': dtype, 'device': str(device), 'torch': torch.__version__,
        'transformers': importlib.metadata.version('transformers'),
        'tokenizer_special_ids': special_ids, 'checkpoint_eos_token_id': 128001,
        'recommended_generation_eos_token_ids': [128001, 128009],
        'routing_output_semantics': 'routing_weights contains raw router logits, not normalized probabilities',
        'expert_order': ['logic', 'social', 'world', 'language'],
        'chat_template_sha256': hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
    })
    return model, tokenizer, receipt
