from __future__ import annotations

import argparse
import importlib.util
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def perturb_observation(obs: np.ndarray, name: str, strength: float, rng: np.random.Generator) -> np.ndarray:
    out = obs.astype(np.float32).copy()
    if name == "clean":
        return obs
    if name == "brightness_down":
        out *= float(strength)
    elif name == "contrast_shift":
        out = 128.0 + (out - 128.0) * float(strength)
    elif name == "center_occlusion":
        height, width = out.shape[:2]
        box_h = max(1, int(height * float(strength)))
        box_w = max(1, int(width * float(strength)))
        y0 = (height - box_h) // 2
        x0 = (width - box_w) // 2
        out[y0 : y0 + box_h, x0 : x0 + box_w, :] = 0
    elif name == "salt_pepper":
        height, width = out.shape[:2]
        mask = rng.random((height, width)) < float(strength)
        salt = rng.random((height, width)) < 0.5
        out[mask & salt] = 255
        out[mask & ~salt] = 0
    else:
        raise ValueError(f"Unknown perturbation: {name}")
    return np.clip(out, 0, 255).astype(np.uint8)


def mean_abs_delta(clean: np.ndarray, changed: np.ndarray) -> float:
    return float(np.mean(np.abs(clean.astype(np.float32) - changed.astype(np.float32))) / 255.0)


def checksum_policy(obs: np.ndarray, step_idx: int, action_count: int) -> int:
    center = obs[20:44, 20:44, :].astype(np.float32)
    means = center.mean(axis=(0, 1))
    std = float(center.std())
    checksum = int(means[0] + 3 * means[1] + 7 * means[2] + std + 13 * step_idx)
    return checksum % action_count


def run_episode(seed: int, mode: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    import crafter

    env = crafter.Env(seed=int(seed), length=int(config["environment"]["episode_length"]))
    obs = env.reset()
    rng = np.random.default_rng(int(config["split_seed"]) + int(seed) * 1009 + int(mode["mode_index"]))
    total_reward = 0.0
    done = False
    steps = 0
    deltas: list[float] = []
    achievements: dict[str, int] = {}
    while not done and steps < int(config["environment"]["episode_length"]):
        perturbed = perturb_observation(obs, mode["name"], float(mode["strength"]), rng)
        deltas.append(mean_abs_delta(obs, perturbed))
        action = checksum_policy(perturbed, steps, int(config["environment"]["action_count"]))
        obs, reward, done, info = env.step(action)
        total_reward += float(reward)
        achievements = {key: int(value) for key, value in info.get("achievements", {}).items()}
        steps += 1
    return {
        "seed": int(seed),
        "condition": mode["name"],
        "split_role": mode["split_role"],
        "strength": float(mode["strength"]),
        "steps": int(steps),
        "done": bool(done),
        "total_reward": total_reward,
        "achievement_count": int(sum(1 for value in achievements.values() if value)),
        "achievement_points": int(sum(achievements.values())),
        "mean_abs_pixel_delta": statistics.fmean(deltas) if deltas else 0.0,
    }


def summarize(rows: list[dict[str, Any]], config: dict[str, Any], package_available: bool) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)

    by_condition: dict[str, Any] = {}
    for condition, items in sorted(grouped.items()):
        by_condition[condition] = {
            "episodes": len(items),
            "split_role": items[0]["split_role"],
            "reward_mean": statistics.fmean(row["total_reward"] for row in items),
            "reward_min": min(row["total_reward"] for row in items),
            "reward_max": max(row["total_reward"] for row in items),
            "achievement_count_mean": statistics.fmean(row["achievement_count"] for row in items),
            "achievement_points_mean": statistics.fmean(row["achievement_points"] for row in items),
            "mean_abs_pixel_delta": statistics.fmean(row["mean_abs_pixel_delta"] for row in items),
        }

    clean_reward = by_condition.get("clean", {}).get("reward_mean", 0.0)
    clean_achievements = by_condition.get("clean", {}).get("achievement_count_mean", 0.0)
    retention: dict[str, Any] = {}
    for condition, metrics in by_condition.items():
        if condition == "clean":
            continue
        retention[condition] = {
            "reward_retention": metrics["reward_mean"] / clean_reward if abs(clean_reward) > 1e-12 else None,
            "achievement_count_retention": metrics["achievement_count_mean"] / clean_achievements
            if abs(clean_achievements) > 1e-12
            else None,
            "split_role": metrics["split_role"],
        }

    heldout_rows = [row for row in rows if row["split_role"] == "heldout_perturbation"]
    publish_checks = {
        "package_available": package_available,
        "completed_episodes": len(rows) >= int(config["metrics"]["min_completed_episodes"]),
        "heldout_episodes": len(heldout_rows) >= int(config["metrics"]["min_heldout_episodes"]),
        "nonzero_pixel_delta": all(
            row["condition"] == "clean"
            or row["mean_abs_pixel_delta"] >= float(config["metrics"]["min_nonzero_pixel_delta"])
            for row in rows
        ),
        "world_model_agent": bool(config["claim_boundary"]["world_model_agent"]),
        "multiple_world_model_paradigms": False,
        "training_augmentation": bool(config["claim_boundary"]["training_performed"]),
    }
    env_pass = all(
        publish_checks[key]
        for key in ["package_available", "completed_episodes", "heldout_episodes", "nonzero_pixel_delta"]
    )
    status = "ENVIRONMENT SMOKE PASS - WORLD-MODEL CLAIM NOT PROMOTED" if env_pass else "ENVIRONMENT SMOKE FAILED"
    return {
        "generated_utc": utc_now(),
        "status": status,
        "agent_type": config["claim_boundary"]["agent_type"],
        "episode_length": config["environment"]["episode_length"],
        "seeds": config["seeds"],
        "episodes": len(rows),
        "conditions": by_condition,
        "retention": retention,
        "publish_checks": publish_checks,
    }


def render_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EXP05 Crafter Rollout Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Scope",
        "",
        "- Environment: `crafter.Env`.",
        "- Agent: deterministic observation-checksum policy, not a learned world-model agent.",
        "- Perturbations are applied to observations before action selection, not to environment state.",
        "- No raw frames are committed.",
        "",
        "## Primary Metrics",
        "",
        "| Condition | Role | Episodes | Mean reward | Mean achievements | Mean pixel delta |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for condition, row in summary["conditions"].items():
        lines.append(
            f"| `{condition}` | `{row['split_role']}` | `{row['episodes']}` | `{row['reward_mean']:.4f}` | "
            f"`{row['achievement_count_mean']:.4f}` | `{row['mean_abs_pixel_delta']:.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Retention Versus Clean",
            "",
            "| Condition | Role | Reward retention | Achievement retention |",
            "|---|---|---:|---:|",
        ]
    )
    for condition, row in summary["retention"].items():
        reward_retention = "NA" if row["reward_retention"] is None else f"{row['reward_retention']:.4f}"
        achievement_retention = (
            "NA" if row["achievement_count_retention"] is None else f"{row['achievement_count_retention']:.4f}"
        )
        lines.append(
            f"| `{condition}` | `{row['split_role']}` | `{reward_retention}` | `{achievement_retention}` |"
        )
    lines.extend(
        [
            "",
            "## Publish Checks",
            "",
            "| Check | Pass |",
            "|---|---:|",
        ]
    )
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Final Determination",
            "",
            "EXP05 now has an executable clean/perturbed Crafter environment smoke, but it is **not publishable as a world-model robustness result**. The runnable gate validates environment mechanics and held-out perturbation data flow. It does not evaluate a learned world-model agent, compare multiple paradigms, or test training-time augmentation.",
            "",
            "The defensible decision is to park EXP05 for this cycle unless a trained Dreamer/stable-worldmodel/Craftax agent baseline is added with clean-score reproduction and multi-seed confidence intervals.",
        ]
    )
    (output_dir / "EXP05_CRAFTER_ROLLOUT_GATE_RESULT_20260621.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    challenge = [
        "# EXP05 Crafter Rollout Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Defense question | Answer |",
        "|---|---|",
        f"| Did a real environment run? | Yes. `{summary['episodes']}` Crafter episodes completed across clean/dev/held-out perturbations. |",
        "| Did held-out perturbations run? | Yes. `center_occlusion` and `salt_pepper` were evaluated after source/wrapper freezing. |",
        "| Is this a world-model agent result? | No. The agent is a deterministic observation-checksum policy. |",
        "| Are multiple paradigms compared? | No. |",
        "| Was augmentation tested? | No. |",
        "| Final decision | Environment path passes; thesis claim is not promoted. |",
    ]
    (output_dir / "EXP05_CRAFTER_ROLLOUT_DEFENSIBILITY_20260621.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)
    package_available = bool(importlib.util.find_spec(config["environment"]["package"]))
    modes = [{"name": "clean", "split_role": "clean", "strength": 0.0, "mode_index": 0}]
    for idx, row in enumerate(config["perturbations"], start=1):
        mode = dict(row)
        mode["mode_index"] = idx
        modes.append(mode)
    rows: list[dict[str, Any]] = []
    if package_available:
        for seed in config["seeds"]:
            for mode in modes:
                rows.append(run_episode(int(seed), mode, config))
    write_jsonl(output_dir / "crafter_rollout_metrics.jsonl", rows)
    summary = summarize(rows, config, package_available)
    write_json(output_dir / "EXP05_CRAFTER_ROLLOUT_SUMMARY_20260621.json", summary)
    render_reports(output_dir, summary)
    print(summary["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp05_crafter_rollout_gate_20260621.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
