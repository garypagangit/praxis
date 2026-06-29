from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "praxis-swe-evo-true-eval-sweep-20260629"
SWE_DATASET = "Fsoft-AIC/SWE-EVO"
SWE_ROWS_URL = "https://datasets-server.huggingface.co/rows?dataset=Fsoft-AIC%2FSWE-EVO&config=default&split=test&offset=0&length=48"
SWE_MODEL = os.environ.get("SWE_MODEL", "glm-4p5")
DEFAULT_INSTANCE_IDS = [
    "psf__requests_v2.9.0_v2.9.1",
    "psf__requests_v2.12.2_v2.12.3",
    "psf__requests_v2.27.0_v2.27.1",
    "iterative__dvc_0.30.0_0.30.1",
    "iterative__dvc_2.21.1_2.21.2",
    "scikit-learn__scikit-learn_0.21.1_0.21.2",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_json(url: str, timeout: int = 120) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def hf_resolve(path: str) -> str:
    quoted = urllib.parse.quote(path, safe="/")
    return f"https://huggingface.co/datasets/{SWE_DATASET}/resolve/main/{quoted}"


def patch_files(patch_text: str) -> list[str]:
    return sorted(
        {
            match.group(2)
            for match in re.finditer(r"^diff --git a/(.+?) b/(.+)$", patch_text or "", flags=re.MULTILINE)
        }
    )


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def run_cmd(command: list[str], cwd: Path | None = None, timeout: int = 1800) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "timeout": False,
            "wall_seconds": time.time() - started,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "cmd": command,
            "returncode": 124,
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
            "timeout": True,
            "wall_seconds": time.time() - started,
        }


def apply_patch(repo_path: Path, patch_text: str, patch_path: Path) -> dict[str, Any]:
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(patch_text or "", encoding="utf-8")
    if not (patch_text or "").strip():
        return {
            "applied": True,
            "check": {"returncode": 0, "stdout": "", "stderr": "", "timeout": False, "wall_seconds": 0},
            "apply": {"returncode": 0, "stdout": "", "stderr": "", "timeout": False, "wall_seconds": 0},
        }
    check = run_cmd(["git", "apply", "--check", str(patch_path)], cwd=repo_path, timeout=180)
    if check["returncode"] != 0:
        return {"applied": False, "check": check, "apply": None}
    applied = run_cmd(["git", "apply", str(patch_path)], cwd=repo_path, timeout=180)
    return {"applied": applied["returncode"] == 0, "check": check, "apply": applied}


def docker_eval(image: str, repo_path: Path, tests: list[str], out_path: Path, timeout: int) -> dict[str, Any]:
    test_args = " ".join(shlex.quote(test) for test in tests)
    command = [
        "sudo",
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo_path}:/testbed",
        "-w",
        "/testbed",
        image,
        "bash",
        "-lc",
        f"python -m pytest -q {test_args}",
    ]
    result = run_cmd(command, timeout=timeout)
    write_json(out_path, result)
    return result


def copy_repo(base_repo: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(base_repo, destination, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return destination


def load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows_payload = fetch_json(SWE_ROWS_URL)
    rows = {item["row"]["instance_id"]: item["row"] for item in rows_payload["rows"]}
    predictions = fetch_json(hf_resolve(f"SWE-agent/{SWE_MODEL}/preds.json"))
    return rows, predictions


def selected_instance_ids(rows: dict[str, dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> list[str]:
    if os.environ.get("INSTANCE_IDS"):
        return [item.strip() for item in os.environ["INSTANCE_IDS"].split(",") if item.strip()]
    selected = [instance_id for instance_id in DEFAULT_INSTANCE_IDS if instance_id in rows and instance_id in predictions]
    limit = int(os.environ.get("SWEEP_LIMIT", str(len(selected))))
    return selected[:limit]


def classify_result(
    base_eval: dict[str, Any],
    model_eval: dict[str, Any],
    gold_eval: dict[str, Any],
    test_patch_applied: bool,
    model_patch_applied: bool,
    gold_patch_applied: bool,
) -> str:
    if not test_patch_applied or not model_patch_applied or not gold_patch_applied:
        return "INFRA_OR_APPLY_FAIL"
    if gold_eval["returncode"] != 0:
        return "GOLD_FAIL"
    if base_eval["returncode"] == 0:
        return "BASE_UNEXPECTED_PASS"
    if model_eval["returncode"] == 0:
        return "PASS"
    return "MODEL_FAIL"


def eval_instance(
    outdir: Path,
    row: dict[str, Any],
    pred: dict[str, Any],
    p2p_limit: int,
    eval_timeout: int,
) -> dict[str, Any]:
    started = time.time()
    instance_id = row["instance_id"]
    slug = safe_name(instance_id)
    work = outdir / "work" / slug
    eval_dir = outdir / "evals" / slug
    patch_dir = outdir / "patches" / slug
    if work.exists():
        shutil.rmtree(work)
    eval_dir.mkdir(parents=True, exist_ok=True)
    patch_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    tests = list(dict.fromkeys((row.get("FAIL_TO_PASS") or []) + (row.get("PASS_TO_PASS") or [])[:p2p_limit]))
    model_patch = pred.get("model_patch", "") or ""
    gold_patch = row.get("patch", "") or ""
    test_patch = row.get("test_patch", "") or ""
    model_files = patch_files(model_patch)
    gold_files = patch_files(gold_patch)
    test_files = patch_files(test_patch)

    result: dict[str, Any] = {
        "instance_id": instance_id,
        "repo": row.get("repo"),
        "image": row.get("image"),
        "model": SWE_MODEL,
        "fail_to_pass_count": len(row.get("FAIL_TO_PASS") or []),
        "pass_to_pass_count": len(row.get("PASS_TO_PASS") or []),
        "selected_test_count": len(tests),
        "model_patch_files": model_files,
        "gold_patch_files": gold_files,
        "test_patch_files": test_files,
        "file_overlap_count": len(set(model_files) & set(gold_files)),
        "tests": tests,
    }
    try:
        result["docker_pull"] = run_cmd(["sudo", "docker", "pull", row["image"]], timeout=2400)
        result["clone"] = run_cmd(["git", "clone", f"https://github.com/{row['repo']}.git", "base"], cwd=work, timeout=1200)
        base_repo = work / "base"
        result["checkout"] = run_cmd(["git", "checkout", row["base_commit"]], cwd=base_repo, timeout=300) if base_repo.exists() else {"returncode": 1, "stdout": "", "stderr": "base clone missing", "timeout": False, "wall_seconds": 0}
        if result["docker_pull"]["returncode"] != 0 or result["clone"]["returncode"] != 0 or result["checkout"]["returncode"] != 0:
            result.update(
                {
                    "status": "INFRA_OR_APPLY_FAIL",
                    "base_returncode": None,
                    "model_returncode": None,
                    "gold_returncode": None,
                    "wall_seconds": time.time() - started,
                }
            )
            return result

        base_eval_repo = copy_repo(base_repo, work / "eval_base")
        model_eval_repo = copy_repo(base_repo, work / "eval_model")
        gold_eval_repo = copy_repo(base_repo, work / "eval_gold")

        base_test_apply = apply_patch(base_eval_repo, test_patch, patch_dir / "test_base.patch")
        model_test_apply = apply_patch(model_eval_repo, test_patch, patch_dir / "test_model.patch")
        gold_test_apply = apply_patch(gold_eval_repo, test_patch, patch_dir / "test_gold.patch")
        model_apply = apply_patch(model_eval_repo, model_patch, patch_dir / "model.patch")
        gold_apply = apply_patch(gold_eval_repo, gold_patch, patch_dir / "gold.patch")

        test_patch_applied = base_test_apply["applied"] and model_test_apply["applied"] and gold_test_apply["applied"]
        if base_test_apply["applied"]:
            base_eval = docker_eval(row["image"], base_eval_repo, tests, eval_dir / "base_eval.json", timeout=eval_timeout)
        else:
            base_eval = {"returncode": 997, "stdout": "", "stderr": "test patch did not apply to base", "timeout": False, "wall_seconds": 0}
            write_json(eval_dir / "base_eval.json", base_eval)
        if model_test_apply["applied"] and model_apply["applied"]:
            model_eval = docker_eval(row["image"], model_eval_repo, tests, eval_dir / "model_eval.json", timeout=eval_timeout)
        else:
            model_eval = {"returncode": 998, "stdout": "", "stderr": "test or model patch did not apply", "timeout": False, "wall_seconds": 0}
            write_json(eval_dir / "model_eval.json", model_eval)
        if gold_test_apply["applied"] and gold_apply["applied"]:
            gold_eval = docker_eval(row["image"], gold_eval_repo, tests, eval_dir / "gold_eval.json", timeout=eval_timeout)
        else:
            gold_eval = {"returncode": 999, "stdout": "", "stderr": "test or gold patch did not apply", "timeout": False, "wall_seconds": 0}
            write_json(eval_dir / "gold_eval.json", gold_eval)

        result.update(
            {
                "base_test_apply": base_test_apply,
                "model_test_apply": model_test_apply,
                "gold_test_apply": gold_test_apply,
                "model_apply": model_apply,
                "gold_apply": gold_apply,
                "test_patch_applied": test_patch_applied,
                "model_patch_applied": model_apply["applied"],
                "gold_patch_applied": gold_apply["applied"],
                "base_returncode": base_eval["returncode"],
                "model_returncode": model_eval["returncode"],
                "gold_returncode": gold_eval["returncode"],
                "base_timeout": base_eval.get("timeout", False),
                "model_timeout": model_eval.get("timeout", False),
                "gold_timeout": gold_eval.get("timeout", False),
                "base_wall_seconds": base_eval.get("wall_seconds", 0),
                "model_wall_seconds": model_eval.get("wall_seconds", 0),
                "gold_wall_seconds": gold_eval.get("wall_seconds", 0),
            }
        )
        result["status"] = classify_result(
            base_eval,
            model_eval,
            gold_eval,
            test_patch_applied,
            model_apply["applied"],
            gold_apply["applied"],
        )
        result["wall_seconds"] = time.time() - started
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


def write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = [
        "instance_id",
        "repo",
        "status",
        "base_returncode",
        "model_returncode",
        "gold_returncode",
        "selected_test_count",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "file_overlap_count",
        "model_patch_file_count",
        "gold_patch_file_count",
        "test_patch_file_count",
        "wall_seconds",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    **{field: row.get(field) for field in fields},
                    "model_patch_file_count": len(row.get("model_patch_files") or []),
                    "gold_patch_file_count": len(row.get("gold_patch_files") or []),
                    "test_patch_file_count": len(row.get("test_patch_files") or []),
                }
            )


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PX-033 SWE-EVO Multi-Task True-Eval Sweep",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Model patch source | `{summary['model']}` |",
        f"| Requested tasks | `{summary['requested_tasks']}` |",
        f"| Evaluated tasks | `{summary['evaluated_tasks']}` |",
        f"| PASS_TO_PASS tests per task | `{summary['p2p_limit']}` |",
        f"| PASS | `{summary['status_counts'].get('PASS', 0)}` |",
        f"| MODEL_FAIL | `{summary['status_counts'].get('MODEL_FAIL', 0)}` |",
        f"| GOLD_FAIL | `{summary['status_counts'].get('GOLD_FAIL', 0)}` |",
        f"| INFRA_OR_APPLY_FAIL | `{summary['status_counts'].get('INFRA_OR_APPLY_FAIL', 0)}` |",
        f"| Pass rate | `{summary['pass_rate']:.4f}` |",
        f"| Wall seconds | `{summary['wall_seconds']:.1f}` |",
        "",
        "## Task Results",
        "",
        "| Instance | Repo | Status | Base | Model | Gold | Tests | Overlap |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["results"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['instance_id']}`",
                    f"`{row.get('repo')}`",
                    f"`{row.get('status')}`",
                    f"`{row.get('base_returncode')}`",
                    f"`{row.get('model_returncode')}`",
                    f"`{row.get('gold_returncode')}`",
                    f"`{row.get('selected_test_count')}`",
                    f"`{row.get('file_overlap_count')}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a released-prediction execution sweep. A PASS means the selected base task fails after applying the SWE test patch, while both the released model patch and the gold patch pass in the benchmark image. This does not yet prove a trained repo-state world model; it tests whether the SWE-EVO lane has enough executable signal to justify predictor and world-model experiments.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--p2p-limit", type=int, default=int(os.environ.get("P2P_LIMIT", "10")))
    parser.add_argument("--eval-timeout", type=int, default=int(os.environ.get("EVAL_TIMEOUT", "1800")))
    args = parser.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    rows, predictions = load_inputs()
    instance_ids = selected_instance_ids(rows, predictions)
    results: list[dict[str, Any]] = []
    for instance_id in instance_ids:
        row = rows.get(instance_id)
        pred = predictions.get(instance_id)
        if row is None or pred is None or not (pred.get("model_patch") or "").strip():
            results.append(
                {
                    "instance_id": instance_id,
                    "status": "INFRA_OR_APPLY_FAIL",
                    "repo": row.get("repo") if row else None,
                    "reason": "missing row, prediction, or model patch",
                    "wall_seconds": 0,
                }
            )
            continue
        result = eval_instance(outdir, row, pred, args.p2p_limit, args.eval_timeout)
        write_json(outdir / "per_instance" / f"{safe_name(instance_id)}.json", result)
        results.append(result)

    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    evaluated = len(results)
    pass_count = counts.get("PASS", 0)
    pass_rate = pass_count / evaluated if evaluated else 0.0
    status = "MULTI-TASK SWEEP PASS" if evaluated >= 4 and pass_rate >= 0.5 and counts.get("GOLD_FAIL", 0) == 0 else "MULTI-TASK SWEEP MIXED"
    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "model": SWE_MODEL,
        "p2p_limit": args.p2p_limit,
        "eval_timeout": args.eval_timeout,
        "requested_tasks": len(instance_ids),
        "evaluated_tasks": evaluated,
        "status_counts": counts,
        "pass_rate": pass_rate,
        "instance_ids": instance_ids,
        "results": results,
        "wall_seconds": time.time() - started,
        "claim_boundary": "Small SWE-EVO released-prediction true-eval sweep over selected executable tasks. When p2p_limit is 0, this is a fail-to-pass viability sweep only, not a regression-preservation benchmark. This is not a full benchmark sweep and not a trained repo-state world model.",
    }
    write_json(outdir / "swe_evo_true_eval_sweep_summary.json", summary)
    write_csv(outdir / "swe_evo_true_eval_sweep_results.csv", results)
    render_report(outdir / "SWE_EVO_TRUE_EVAL_SWEEP_20260629.md", summary)
    print(json.dumps({k: summary[k] for k in ("status", "model", "requested_tasks", "evaluated_tasks", "status_counts", "pass_rate", "wall_seconds")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
