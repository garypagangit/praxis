from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable


SHELL_META = ("&&", ";", "|", "`", "$(", ">", "<", "\n", "\r")
REMOTE_SPECS = ("http://", "https://", "git+", "file:", "ftp://")
FAMILIES = ("direct", "version_pin", "manager_variant", "two_package_mixed", "flagged_install", "shell_chain")
SAFE_FAMILIES = set(FAMILIES) - {"shell_chain"}
PIP_VALUELESS_FLAGS = {"--no-cache-dir"}
NPM_VALUELESS_FLAGS = {"--exact"}


def normalize_pypi(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().lower())


def normalize_npm(value: str) -> str:
    return value.strip().lower()


def read_lines(path: Path) -> Iterable[str]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            value = line.strip().strip('"')
            if value:
                yield value


def load_registries(data_root: Path) -> tuple[list[str], set[str], list[str], set[str]]:
    pypi_path = data_root / "Python" / "pypi_package_names.csv"
    npm_zip = data_root / "Javascript" / "npm_package_names.zip"
    pypi_set = {normalize_pypi(x) for x in read_lines(pypi_path)}
    with zipfile.ZipFile(npm_zip) as archive:
        with archive.open("npm_package_names.csv") as raw:
            npm_set = {
                normalize_npm(line.decode("utf-8", errors="replace").strip().strip('"'))
                for line in raw
                if line.strip()
            }
    return sorted(pypi_set), pypi_set, sorted(npm_set), npm_set


def strip_pypi_spec(token: str) -> str:
    token = token.strip().strip("'\"")
    token = token.split("[", 1)[0]
    token = re.split(r"(?:===|==|~=|!=|<=|>=|<|>)", token, maxsplit=1)[0]
    return normalize_pypi(token)


def strip_npm_spec(token: str) -> str:
    token = token.strip().strip("'\"")
    if token.startswith("@") and "/" in token:
        scope, rest = token.split("/", 1)
        return f"{scope}/{rest.split('@', 1)[0]}".lower()
    return token.split("@", 1)[0].lower()


def parse_install(command: str) -> tuple[str, list[str], str]:
    lowered = command.lower()
    if any(x in command for x in SHELL_META) or any(x in lowered for x in REMOTE_SPECS):
        return "unknown", [], "unsafe"
    pip_match = re.fullmatch(r"\s*(?:python\s+-m\s+)?pip3?\s+install\s+(.+?)\s*", command, re.I)
    if pip_match:
        tokens = [x for x in pip_match.group(1).split() if x.lower() not in PIP_VALUELESS_FLAGS]
        return "pypi", [strip_pypi_spec(x) for x in tokens], "parsed"
    npm_match = re.fullmatch(r"\s*(?:npm\s+(?:install|i)|pnpm\s+add|yarn\s+add)\s+(.+?)\s*", command, re.I)
    if npm_match:
        tokens = [x for x in npm_match.group(1).split() if x.lower() not in NPM_VALUELESS_FLAGS]
        return "npm", [strip_npm_spec(x) for x in tokens], "parsed"
    return "unknown", [], "unparsed"


def gate(command: str, pypi: set[str], npm: set[str]) -> str:
    ecosystem, packages, status = parse_install(command)
    if status == "unsafe":
        return "block"
    if status != "parsed" or not packages:
        return "review"
    registry = pypi if ecosystem == "pypi" else npm
    return "allow" if all(package in registry for package in packages) else "block"


def invalid_name(seed: int, ecosystem: str, row: int, anchor: str, registry: set[str]) -> str:
    attempt = 0
    while True:
        digest = hashlib.sha256(f"{seed}|{ecosystem}|{row}|{anchor}|{attempt}".encode()).hexdigest()[:12]
        candidate = f"{anchor}-px050w-{digest}"
        normalized = normalize_pypi(candidate) if ecosystem == "pypi" else normalize_npm(candidate)
        if normalized not in registry:
            return candidate
        attempt += 1


def render_command(ecosystem: str, family: str, package: str, anchor2: str) -> str:
    if ecosystem == "pypi":
        return {
            "direct": f"pip install {package}",
            "version_pin": f"pip install {package}==1.0.0",
            "manager_variant": f"python -m pip install {package}",
            "two_package_mixed": f"pip install {anchor2} {package}",
            "flagged_install": f"pip install --no-cache-dir {package}",
            "shell_chain": f"pip install {package} && echo done",
        }[family]
    return {
        "direct": f"npm install {package}",
        "version_pin": f"npm install {package}@1.0.0",
        "manager_variant": f"pnpm add {package}",
        "two_package_mixed": f"npm i {anchor2} {package}",
        "flagged_install": f"yarn add --exact {package}",
        "shell_chain": f"npm install {package} && echo done",
    }[family]


def upper_zero_event(n: int, alpha: float = 0.05) -> float:
    return 1.0 - alpha ** (1.0 / n) if n else 1.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: argparse.Namespace) -> dict:
    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    pypi_names, pypi_set, npm_names, npm_set = load_registries(args.data_root)
    registries = {"pypi": (pypi_names, pypi_set), "npm": (npm_names, npm_set)}
    counts: Counter = Counter()
    failures: list[dict] = []
    rows_per_cell = args.rows // 4

    for ecosystem in ("pypi", "npm"):
        names, registry = registries[ecosystem]
        for label in ("valid", "invalid"):
            for row in range(rows_per_cell):
                family = FAMILIES[row % len(FAMILIES)]
                anchor = names[(row * 104729 + args.seed) % len(names)]
                anchor2 = names[(row * 130363 + args.seed + 1) % len(names)]
                package = anchor if label == "valid" else invalid_name(args.seed, ecosystem, row, anchor, registry)
                command = render_command(ecosystem, family, package, anchor2)
                decision = gate(command, pypi_set, npm_set)
                expected = "block" if family == "shell_chain" or label == "invalid" else "allow"
                key = (ecosystem, label, family, decision)
                counts[key] += 1
                if decision != expected and len(failures) < 10000:
                    failures.append({
                        "ecosystem": ecosystem,
                        "label": label,
                        "family": family,
                        "decision": decision,
                        "expected": expected,
                        "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                    })

    invalid_n = sum(v for (e, label, f, d), v in counts.items() if label == "invalid")
    invalid_allow = sum(v for (e, label, f, d), v in counts.items() if label == "invalid" and d == "allow")
    safe_valid_n = sum(v for (e, label, f, d), v in counts.items() if label == "valid" and f in SAFE_FAMILIES)
    safe_valid_allow = sum(v for (e, label, f, d), v in counts.items() if label == "valid" and f in SAFE_FAMILIES and d == "allow")
    shell_n = sum(v for (e, label, f, d), v in counts.items() if f == "shell_chain")
    shell_block = sum(v for (e, label, f, d), v in counts.items() if f == "shell_chain" and d == "block")
    invalid_upper = upper_zero_event(invalid_n) if invalid_allow == 0 else 1.0

    strata = [
        {"ecosystem": e, "label": label, "family": f, "decision": d, "rows": n}
        for (e, label, f, d), n in sorted(counts.items())
    ]
    checks = {
        "rows_exactly_registered": args.rows == prereg["corpus"]["total_rows"],
        "invalid_allow_count_zero": invalid_allow == 0,
        "invalid_95pct_upper_below_1e_5": invalid_upper < 0.00001,
        "safe_valid_allow_rate_at_least_0_99": safe_valid_allow / safe_valid_n >= 0.99,
        "shell_chain_block_rate_one": shell_block / shell_n == 1.0,
        "no_recorded_failures": not failures,
    }
    result = {
        "experiment_id": prereg["experiment_id"],
        "status": "PASS" if all(checks.values()) else "FAIL",
        "preregistration_sha256": sha256(args.prereg),
        "runner_sha256": sha256(Path(__file__)),
        "registry_sha256": {
            "pypi_csv": sha256(args.data_root / "Python" / "pypi_package_names.csv"),
            "npm_zip": sha256(args.data_root / "Javascript" / "npm_package_names.zip"),
        },
        "source_commit": prereg["source_artifact"]["repository_commit"],
        "rows": args.rows,
        "seed": args.seed,
        "registry_counts": {"pypi": len(pypi_set), "npm": len(npm_set)},
        "invalid_rows": invalid_n,
        "invalid_allow_count": invalid_allow,
        "invalid_allow_rate": invalid_allow / invalid_n,
        "invalid_allow_rate_one_sided_95pct_upper": invalid_upper,
        "safe_valid_rows": safe_valid_n,
        "safe_valid_allow_rate": safe_valid_allow / safe_valid_n,
        "shell_chain_rows": shell_n,
        "shell_chain_block_rate": shell_block / shell_n,
        "checks": checks,
        "strata": strata,
        "failure_rows": failures,
        "claim_boundary": prereg["claim_if_passed"],
        "forbidden_claims": prereg["forbidden_claims"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "strata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ecosystem", "label", "family", "decision", "rows"])
        writer.writeheader()
        writer.writerows(strata)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=50050)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({k: v for k, v in result.items() if k not in {"strata", "failure_rows"}}, indent=2))


if __name__ == "__main__":
    main()
