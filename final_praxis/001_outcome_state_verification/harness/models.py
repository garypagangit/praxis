from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass(frozen=True)
class Condition:
    path: str
    expected: Any

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    family: str
    title: str
    initial_state: Dict[str, Any]
    goal_conditions: List[Condition]
    invariant_conditions: List[Condition]

@dataclass
class EvalResult:
    goal_predicates: Dict[str, bool]
    protected_invariants: Dict[str, bool]
    goal_complete: bool
    collateral_valid: bool
    success: bool
    reason_codes: List[str]
