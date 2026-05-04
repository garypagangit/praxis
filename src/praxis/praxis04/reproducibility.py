from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SeedState:
    seed: int
    torch_available: bool
    deterministic_torch: bool


def seed_everything(seed: int, deterministic_torch: bool = True) -> SeedState:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    torch_available = False
    if deterministic_torch:
        try:
            import torch

            torch_available = True
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            torch.use_deterministic_algorithms(True, warn_only=True)
            torch.backends.cudnn.benchmark = False
        except Exception:
            torch_available = False

    return SeedState(
        seed=int(seed),
        torch_available=torch_available,
        deterministic_torch=bool(deterministic_torch),
    )


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

