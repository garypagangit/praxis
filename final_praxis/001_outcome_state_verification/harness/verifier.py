from __future__ import annotations
from typing import Any
from .models import EvalResult, TaskSpec

def get_path(obj: Any, path: str):
    cur = obj
    for part in path.split('.'):
        cur = cur[part]
    return cur

def set_path(obj: Any, path: str, value):
    parts = path.split('.')
    cur = obj
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value

def verify(spec: TaskSpec, final_state: dict) -> EvalResult:
    gp = {c.path: get_path(final_state, c.path) == c.expected for c in spec.goal_conditions}
    inv = {c.path: get_path(final_state, c.path) == c.expected for c in spec.invariant_conditions}
    goal = all(gp.values())
    collateral = all(inv.values())
    reasons = []
    if not goal:
        reasons.append('GOAL_INCOMPLETE')
    if not collateral:
        reasons.append('COLLATERAL_VIOLATION')
    return EvalResult(gp, inv, goal, collateral, goal and collateral, reasons)
