"""Source binding and honest numerical comparison for 009 qualification."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import sys

PIN = 'b0a6338232f47d7ffabac90deb810728c2e179b4'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind_source(source):
    root = Path(source).resolve()
    manifest = json.loads(Path(__file__).with_name('SOURCE_MANIFEST.json').read_text())
    bad = [name for name, digest in manifest['files'].items()
           if not (root / name).is_file() or sha(root / name) != digest]
    if bad:
        raise RuntimeError('Pinned source mismatch: ' + ', '.join(bad))
    sys.path.insert(0, str(root / 'src'))
    import soup_cli.utils.layer_stream_runtime as runtime
    if not Path(runtime.__file__).resolve().is_relative_to(root):
        raise RuntimeError('Imported a different Soup installation')
    return runtime


def provenance():
    here = Path(__file__).parent
    versions = {}
    for package in ['torch', 'transformers', 'peft', 'safetensors', 'bitsandbytes', 'numpy']:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {'source_pin': PIN, 'python': sys.version, 'platform': platform.platform(),
            'dependencies': versions, 'protocol_sha256': sha(here / 'QUALIFICATION_PROTOCOL.md'),
            'source_manifest_sha256': sha(here / 'SOURCE_MANIFEST.json'),
            'harness_files': {p.name: sha(p) for p in sorted(here.glob('*.py'))}}


def exact_tensor_report(left, right):
    import torch
    if set(left) != set(right) or not left:
        return {'passed': False, 'reason': 'missing_or_different_tensor_keys'}
    differences = []
    for key in sorted(left):
        a, b = left[key], right[key]
        finite = bool(torch.isfinite(a).all() and torch.isfinite(b).all())
        same = a.shape == b.shape and a.dtype == b.dtype
        equal = same and finite and torch.equal(a, b)
        if not equal:
            differences.append({'key': key, 'same_shape_dtype': same, 'finite': finite,
                                'max_abs': float((a.float()-b.float()).abs().max()) if same and finite else None})
    return {'passed': not differences, 'tensors': len(left), 'differences': differences}


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
