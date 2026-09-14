"""Outcome-blind static test acquisition and explicit supplier selection.

Selector entry points accept only test IDs/arguments, source code and witness
arguments. Test oracles, labels and outcome vectors are deliberately absent.
"""
import ast
import hashlib
import json
import math
import random
from collections import Counter
from itertools import combinations

SEED = "praxis008-code-study-v1"
POLICIES = ("fixed", "uniform", "edit", "complement", "hybrid")
EPSILON = 0.5


def finite_number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def proximity(left, right):
    try:
        return 1 / (1 + abs(left - right))
    except OverflowError:
        return 0.0


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def derived_seed(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str, (SEED, *parts))).encode()).digest()[:16], "big")


def fingerprint(args):
    return hashlib.sha256(canonical(args).encode()).hexdigest()


def size_bin(n):
    return "0" if n == 0 else "1" if n == 1 else "2-4" if n <= 4 else "5-16" if n <= 16 else "17+"


def features(args):
    tags, numeric = set(), []

    def visit(value, depth=0):
        # Bounded structural features; no program execution or expected output.
        if depth > 8:
            tags.add("depth>8")
            return
        kind = type(value).__name__
        tags.add("type:" + kind)
        if type(value) is bool:
            tags.add("bool:" + str(value))
        elif finite_number(value):
            numeric.append(value)
            tags.add("sign:" + ("zero" if value == 0 else "positive" if value > 0 else "negative"))
            tags.add("magnitude:" + ("<1" if abs(value) < 1 else "1" if abs(value) == 1 else "2-10" if abs(value) <= 10 else ">10"))
            tags.add("number:" + ("integral" if value == int(value) else "fractional"))
        elif type(value) in (list, tuple, str, dict):
            tags.add(kind + "_length:" + size_bin(len(value)))
            numeric.append(len(value))
            if type(value) is str:
                for label, test in (("space", str.isspace), ("digit", str.isdigit), ("alpha", str.isalpha), ("upper", str.isupper), ("lower", str.islower)):
                    if any(test(c) for c in value):
                        tags.add("string_has:" + label)
                tags.add("string_unique:" + ("all" if len(set(value)) == len(value) else "repeated"))
            elif type(value) in (list, tuple):
                encoded = [canonical(x) for x in value]
                tags.add("sequence_unique:" + ("all" if len(set(encoded)) == len(encoded) else "repeated"))
                if value and all(finite_number(x) for x in value):
                    tags.add("sequence_order:" + ("ascending" if all(a <= b for a, b in zip(value, value[1:])) else "descending" if all(a >= b for a, b in zip(value, value[1:])) else "mixed"))
                for x in value:
                    visit(x, depth + 1)
            else:
                for k, v in value.items():
                    visit(k, depth + 1)
                    visit(v, depth + 1)

    visit(args)
    return frozenset(tags), tuple(numeric)


def distance(a, b):
    return 1 - len(a & b) / len(a | b) if a | b else 0.0


def edited_boundaries(original, proposal):
    def inspect(source):
        tree = ast.parse(source)
        nums = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and finite_number(n.value)}
        # Signed literals are UnaryOps; preserve their signs as additional atoms.
        nums |= {-n.operand.value for n in ast.walk(tree) if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) and finite_number(n.operand.value)}
        comparisons = Counter(type(op).__name__ for node in ast.walk(tree) if isinstance(node, ast.Compare) for op in node.ops)
        return nums, comparisons

    try:
        left, left_ops = inspect(original)
        right, right_ops = inspect(proposal)
    except (SyntaxError, ValueError, TypeError):
        return (), "unparseable_static_fallback"
    boundaries = left ^ right
    if left_ops != right_ops:
        boundaries |= left | right | {0}
    return tuple(sorted(boundaries)), "numeric_or_comparison_edit" if boundaries else "no_supported_static_edit"


def validate_pool(pool):
    if any(set(row) != {"id", "args"} for row in pool):
        raise ValueError("Selector inputs must contain exactly id and args; no outcome/oracle fields")
    if len({row["id"] for row in pool}) != len(pool):
        raise ValueError("Repeated test ID")
    if len({fingerprint(row["args"]) for row in pool}) != len(pool):
        raise ValueError("Repeated test input")


def partition_tool_pool(pool, task_id):
    """Freeze supplier W vs independent A by identity, never outcome."""
    validate_pool(pool)
    ordered = sorted(pool, key=lambda row: derived_seed("WA", task_id, row["id"]))
    # Half W and half A; odd remaining item belongs to A. No outcome-based rescue.
    return ordered[:len(ordered) // 2], ordered[len(ordered) // 2:]


def supplier_acquisition(pool, task_id, replicate=0, budget=16):
    validate_pool(pool)
    rng = random.Random(derived_seed("supplier", task_id, replicate))
    return rng.sample(sorted(pool, key=lambda row: row["id"]), min(budget, len(pool)))


def testimony(acquired, passed_by_id, mode, task_id, replicate=0, shown=2):
    """Supplier alone may see acquired outcomes. No A/H outcomes accepted."""
    validate_pool(acquired)
    if set(passed_by_id) != {row["id"] for row in acquired}:
        raise ValueError("Supplier results must cover exactly its acquired observations")
    if any(type(value) is not bool for value in passed_by_id.values()):
        raise ValueError("Supplier outcomes must be Boolean observations")
    if mode == "uniform":
        rng = random.Random(derived_seed("testimony", task_id, replicate))
        selected = rng.sample(sorted(acquired, key=lambda row: row["id"]), min(shown, len(acquired)))
    elif mode == "selected":
        candidates = sorted([row for row in acquired if passed_by_id[row["id"]] is True], key=lambda row: row["id"])
        if shown != 2:
            raise ValueError("Frozen selective attack displays at most two witnesses")
        if len(candidates) <= shown:
            selected = candidates
        else:
            feature_map = {row["id"]: features(row["args"])[0] for row in candidates}
            selected = list(min(combinations(candidates, 2), key=lambda pair: (
                distance(feature_map[pair[0]["id"]], feature_map[pair[1]["id"]]),
                pair[0]["id"], pair[1]["id"])))
    else:
        raise ValueError("Unknown testimony mode")
    return {"ids": [row["id"] for row in selected], "fully_feasible": len(selected) == shown,
            "acquired": len(acquired), "shown": len(selected)}


def select(pool, original, proposal, witness_args, policy, task_id, replicate=0, budget=8):
    validate_pool(pool)
    if policy not in POLICIES or budget < 0:
        raise ValueError("Invalid selector configuration")
    boundaries, support = edited_boundaries(original, proposal)
    wf = [features(args)[0] for args in witness_args]
    rows = []
    for row in sorted(pool, key=lambda x: x["id"]):
        feat, numeric = features(row["args"])
        b = max((proximity(x, edge) for x in numeric for edge in boundaries), default=0.0)
        d = min((distance(feat, witness) for witness in wf), default=0.0)
        u = 1 + (2 * b if policy in ("edit", "hybrid") else 0) + (d if policy in ("complement", "hybrid") else 0)
        rows.append({"id": row["id"], "boundary": b, "complement": d, "weight": u})
    rng = random.Random(derived_seed("selector", task_id, replicate))
    selected, draws = [], []
    remaining = rows[:]
    for _ in range(min(budget, len(remaining))):
        if policy == "fixed":
            chosen = min(remaining, key=lambda row: derived_seed("fixed", task_id, row["id"]))
            probability = 1.0
        elif policy == "uniform":
            chosen = remaining[rng.randrange(len(remaining))]
            probability = 1 / len(remaining)
        else:
            total = sum(row["weight"] for row in remaining)
            probs = [EPSILON / len(remaining) + (1 - EPSILON) * row["weight"] / total for row in remaining]
            point = rng.random()
            cumulative = 0.0
            chosen, probability = remaining[-1], probs[-1]
            for row, p in zip(remaining, probs):
                cumulative += p
                if point < cumulative:
                    chosen, probability = row, p
                    break
        selected.append(chosen["id"])
        draws.append({"id": chosen["id"], "probability": probability, "remaining": len(remaining),
                      "boundary": chosen["boundary"], "complement": chosen["complement"]})
        remaining.remove(chosen)
    return {"policy": policy, "ids": selected, "requested_budget": budget,
            "actual_budget": len(selected), "pool_size": len(pool), "replicate": replicate,
            "static_support": support, "draws": draws,
            "selection_commitment": hashlib.sha256(canonical(selected).encode()).hexdigest()}


def miss_bound(n, failing, k, epsilon=EPSILON):
    if not 0 <= failing <= n or not 0 <= k <= n or not 0 <= epsilon <= 1:
        raise ValueError("Invalid finite-pool parameters")
    if k > n - failing:
        return 0.0
    return math.prod(1 - epsilon * failing / (n - j) for j in range(k))
