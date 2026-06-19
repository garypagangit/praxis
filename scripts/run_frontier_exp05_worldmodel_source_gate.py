from __future__ import annotations

import argparse
import json
import random
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "praxis-exp05-worldmodel-source-gate"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def check_github_repo(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}"
    row = {"repo": repo}
    try:
        payload = request_json(url, {"Accept": "application/vnd.github+json", "User-Agent": "praxis-exp05-worldmodel-source-gate"})
        row.update(
            {
                "status": "ACCESSIBLE",
                "full_name": payload.get("full_name"),
                "default_branch": payload.get("default_branch"),
                "pushed_at": payload.get("pushed_at"),
                "stars": payload.get("stargazers_count"),
            }
        )
    except Exception as exc:
        row.update({"status": "UNAVAILABLE", "error": str(exc)[:240]})
    return row


def check_pypi_package(package: str) -> dict[str, Any]:
    row = {"package": package}
    try:
        payload = request_json(f"https://pypi.org/pypi/{package}/json")
        releases = sorted(payload.get("releases", {}).keys())
        row.update(
            {
                "status": "ACCESSIBLE",
                "latest_version": payload.get("info", {}).get("version"),
                "release_count": len(releases),
            }
        )
    except urllib.error.HTTPError as exc:
        row.update({"status": "UNAVAILABLE", "http_status": exc.code, "error": str(exc)[:240]})
    except Exception as exc:
        row.update({"status": "UNAVAILABLE", "error": str(exc)[:240]})
    return row


def clean_frame(width: int = 64, height: int = 64, channels: int = 3) -> list[list[list[int]]]:
    frame: list[list[list[int]]] = []
    for y in range(height):
        row: list[list[int]] = []
        for x in range(width):
            row.append([(x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256][:channels])
        frame.append(row)
    return frame


def perturb(frame: list[list[list[int]]], name: str, strength: float, seed: int) -> list[list[list[int]]]:
    rng = random.Random(seed)
    height = len(frame)
    width = len(frame[0])
    out = [[pixel[:] for pixel in row] for row in frame]
    if name == "brightness_down":
        for y in range(height):
            for x in range(width):
                out[y][x] = [max(0, min(255, int(value * strength))) for value in out[y][x]]
    elif name == "contrast_shift":
        for y in range(height):
            for x in range(width):
                out[y][x] = [max(0, min(255, int(128 + (value - 128) * strength))) for value in out[y][x]]
    elif name == "center_occlusion":
        box_h = max(1, int(height * strength))
        box_w = max(1, int(width * strength))
        y0 = (height - box_h) // 2
        x0 = (width - box_w) // 2
        for y in range(y0, y0 + box_h):
            for x in range(x0, x0 + box_w):
                out[y][x] = [0, 0, 0]
    elif name == "salt_pepper":
        total = height * width
        flips = int(total * strength)
        for _ in range(flips):
            y = rng.randrange(height)
            x = rng.randrange(width)
            value = 0 if rng.random() < 0.5 else 255
            out[y][x] = [value, value, value]
    else:
        raise ValueError(f"unknown perturbation: {name}")
    return out


def frame_shape(frame: list[list[list[int]]]) -> tuple[int, int, int]:
    return len(frame), len(frame[0]), len(frame[0][0])


def mean_abs_delta(a: list[list[list[int]]], b: list[list[list[int]]]) -> float:
    total = 0
    count = 0
    for row_a, row_b in zip(a, b):
        for pix_a, pix_b in zip(row_a, row_b):
            for value_a, value_b in zip(pix_a, pix_b):
                total += abs(value_a - value_b)
                count += 1
    return total / max(count * 255, 1)


def run_perturbation_smoke(config: dict[str, Any]) -> list[dict[str, Any]]:
    frame = clean_frame()
    rows: list[dict[str, Any]] = []
    for idx, perturbation in enumerate(config["perturbations"]):
        changed = perturb(frame, perturbation["name"], float(perturbation["strength"]), int(config["split_seed"]) + idx)
        rows.append(
            {
                "perturbation": perturbation["name"],
                "split_role": perturbation["split_role"],
                "strength": perturbation["strength"],
                "input_shape": list(frame_shape(frame)),
                "output_shape": list(frame_shape(changed)),
                "shape_preserved": frame_shape(frame) == frame_shape(changed),
                "mean_abs_pixel_delta": mean_abs_delta(frame, changed),
            }
        )
    return rows


def summarize(config: dict[str, Any], repos: list[dict[str, Any]], packages: list[dict[str, Any]], perturbations: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = config["metrics"]
    accessible_repos = sum(1 for row in repos if row["status"] == "ACCESSIBLE")
    accessible_packages = sum(1 for row in packages if row["status"] == "ACCESSIBLE")
    heldout = [row for row in perturbations if row["split_role"] == "heldout_perturbation"]
    nonzero_deltas = [row["mean_abs_pixel_delta"] for row in perturbations if row["mean_abs_pixel_delta"] >= float(metrics["min_nonzero_pixel_delta"])]
    shape_failures = sum(1 for row in perturbations if not row["shape_preserved"])
    publish_checks = {
        "accessible_repositories": accessible_repos >= int(metrics["min_accessible_repositories"]),
        "accessible_packages": accessible_packages >= int(metrics["min_accessible_packages"]),
        "perturbation_rows": len(perturbations) >= int(metrics["min_perturbation_rows"]),
        "heldout_perturbations": len(heldout) >= int(metrics["min_heldout_perturbations"]),
        "nonzero_pixel_delta": len(nonzero_deltas) == len(perturbations),
        "shape_preserved": shape_failures <= int(metrics["max_shape_failures"]),
    }
    status = "SOURCE GATE PASS - AGENT EVAL PENDING" if all(publish_checks.values()) else "SOURCE GATE MIXED"
    return {
        "generated_utc": utc_now(),
        "status": status,
        "accessible_repositories": accessible_repos,
        "accessible_packages": accessible_packages,
        "perturbation_rows": len(perturbations),
        "heldout_perturbations": len(heldout),
        "shape_failures": shape_failures,
        "min_mean_abs_pixel_delta": min((row["mean_abs_pixel_delta"] for row in perturbations), default=0.0),
        "github_repositories": repos,
        "pypi_packages": packages,
        "perturbation_smoke": perturbations,
        "publish_checks": publish_checks,
    }


def render_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EXP05 World-Model Source Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Accessible repositories | `{summary['accessible_repositories']}` |",
        f"| Accessible PyPI packages | `{summary['accessible_packages']}` |",
        f"| Perturbation rows | `{summary['perturbation_rows']}` |",
        f"| Held-out perturbations | `{summary['heldout_perturbations']}` |",
        f"| Shape failures | `{summary['shape_failures']}` |",
        f"| Minimum mean absolute pixel delta | `{summary['min_mean_abs_pixel_delta']:.4f}` |",
        "",
        "## Publish Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Perturbation Smoke",
            "",
            "| Perturbation | Role | Shape preserved | Mean abs pixel delta |",
            "|---|---|---:|---:|",
        ]
    )
    for row in summary["perturbation_smoke"]:
        lines.append(
            f"| `{row['perturbation']}` | `{row['split_role']}` | `{row['shape_preserved']}` | `{row['mean_abs_pixel_delta']:.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a source and wrapper smoke gate, not a world-model robustness result. It proves that source paths are reachable and that visual perturbation wrappers preserve observation shape while creating nonzero visual shift. The next gate must install the environment and run clean plus perturbed agent evaluation.",
        ]
    )
    (output_dir / "EXP05_WORLDMODEL_SOURCE_GATE_RESULT_20260619.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    challenge = [
        "# EXP05 Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Challenge | Answer |",
        "|---|---|",
        f"| Are source repos reachable? | Accessible repos: `{summary['accessible_repositories']}`. |",
        f"| Are environment packages discoverable? | Accessible PyPI packages: `{summary['accessible_packages']}`. |",
        f"| Are held-out perturbations frozen? | Held-out perturbations: `{summary['heldout_perturbations']}`. |",
        f"| Do wrappers preserve observation shape? | Shape failures: `{summary['shape_failures']}`. |",
        "| Does this prove robustness? | No. No agent score or world-model rollout was run. |",
        "| Main weakness | Agent/environment install and clean baseline reproduction remain pending. |",
        "| Main strength | Dev and held-out perturbations are explicit and auditable before score runs. |",
    ]
    (output_dir / "EXP05_INTERNAL_DEFENSIBILITY_CHALLENGE_20260619.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)
    repos = [check_github_repo(repo) for repo in config["github_repositories"]]
    packages = [check_pypi_package(package) for package in config["pypi_packages"]]
    perturbations = run_perturbation_smoke(config)
    write_json(output_dir / "source_checks.json", {"github_repositories": repos, "pypi_packages": packages})
    write_jsonl(output_dir / "visual_perturbation_manifest.jsonl", perturbations)
    summary = summarize(config, repos, packages, perturbations)
    write_json(output_dir / "EXP05_WORLDMODEL_SOURCE_GATE_SUMMARY_20260619.json", summary)
    render_reports(output_dir, summary)
    print(summary["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp05_worldmodel_source_gate_20260619.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
