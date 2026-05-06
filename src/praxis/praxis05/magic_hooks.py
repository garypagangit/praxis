from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import torch


def resolve_module(model: torch.nn.Module, module_path: str) -> torch.nn.Module:
    current: Any = model
    for part in module_path.split("."):
        if part.isdigit() and hasattr(current, "__getitem__"):
            current = current[int(part)]
        else:
            current = getattr(current, part)
    if not isinstance(current, torch.nn.Module):
        raise TypeError(f"Resolved path is not a torch module: {module_path}")
    return current


@dataclass
class ActivationCaptureHook:
    model: torch.nn.Module
    module_path: str
    flatten_leading_dims: bool = True
    captured: list[torch.Tensor] = field(default_factory=list)
    handle: Any = None

    def __enter__(self) -> "ActivationCaptureHook":
        module = resolve_module(self.model, self.module_path)
        self.handle = module.register_forward_hook(self._hook)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is not None:
            self.handle.remove()
            self.handle = None

    def _hook(self, _module, _inputs, output) -> None:
        tensor = output[0] if isinstance(output, (tuple, list)) else output
        if not isinstance(tensor, torch.Tensor):
            raise TypeError("Hooked MAGIC layer did not return a tensor.")
        tensor = tensor.detach().cpu().float()
        if self.flatten_leading_dims and tensor.ndim > 2:
            tensor = tensor.reshape(-1, tensor.shape[-1])
        self.captured.append(tensor)

    def tensor(self) -> torch.Tensor:
        if not self.captured:
            raise ValueError("No activations captured.")
        return torch.cat(self.captured, dim=0)

