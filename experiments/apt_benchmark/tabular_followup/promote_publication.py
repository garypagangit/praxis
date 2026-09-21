"""Commit only a verified aggregate publication to the existing research branch."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from . import publish_followup as publisher


EXPECTED_REMOTE = "https://github.com/garypagangit/praxis.git"
EXPECTED_BRANCH = "apt-benchmark"
OUTPUT_RELATIVE = "experiments/apt_benchmark/results/tabular_followup_v1"
ALLOWED = {"REPORT.md", "E1_ANALYSIS.json", "COMPARISONS.json", "GATE_AGGREGATE.json", "GATE_AUDIT.json", "TRANSFER_SUMMARY.json", "PUBLICATION.json"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
    if done.returncode:
        raise RuntimeError(f"Git {args[0]} failed; no force, merge, or branch switch attempted")
    return done.stdout.strip()


def verify_publication(repo):
    folder = repo / OUTPUT_RELATIVE
    if not folder.resolve().is_relative_to(repo.resolve()) or folder.is_symlink():
        raise ValueError("Publication directory resolves outside the research repository")
    if any(path.name not in ALLOWED or not path.is_file() or path.is_symlink() for path in folder.iterdir()):
        raise ValueError("Unexpected file or link in aggregate publication")
    receipt = json.loads((folder / "PUBLICATION.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "COMPLETE_AUDITED" or receipt.get("no_raw_or_row_level_data_published") is not True:
        raise ValueError("Only a complete independently audited publication can be promoted")
    if receipt.get("publisher_sha256") != digest(Path(publisher.__file__)):
        raise ValueError("Publication was created by another publisher source")
    artifacts = receipt["artifact_sha256"]
    required = ALLOWED - {"TRANSFER_SUMMARY.json", "PUBLICATION.json"}
    if not required <= set(artifacts) or not set(artifacts) <= ALLOWED - {"PUBLICATION.json"}:
        raise ValueError("Unexpected publication file roster")
    for name, expected in artifacts.items():
        if digest(folder / name) != expected:
            raise ValueError("Publication bytes changed")
    if {path.name for path in folder.iterdir()} != set(artifacts) | {"PUBLICATION.json"}:
        raise ValueError("Publication contains stale or unbound files")
    json_names = ["E1_ANALYSIS.json", "COMPARISONS.json", "GATE_AGGREGATE.json", "GATE_AUDIT.json"]
    expected_sources = set(json_names) | ({"TRANSFER_SUMMARY.json"} if "TRANSFER_SUMMARY.json" in artifacts else set())
    if set(receipt.get("source_sha256", {})) != expected_sources:
        raise ValueError("Publication source receipt roster differs")
    values = {name: publisher.read(folder / name) for name in expected_sources}
    publisher.verify(*(values[name] for name in json_names))
    if receipt["source_sha256"]["GATE_AGGREGATE.json"] != values["GATE_AUDIT.json"]["artifact_hashes"]["AGGREGATE.json"]:
        raise ValueError("Published gate source is not the independently audited artifact")
    if "TRANSFER_SUMMARY.json" in values:
        publisher.verify_transfer(values["TRANSFER_SUMMARY.json"], values["E1_ANALYSIS.json"])
    for value in values.values():
        publisher.aggregate_only(value)
    return [f"{OUTPUT_RELATIVE}/{name}" for name in [*sorted(artifacts), "PUBLICATION.json"]]


def promote(repo):
    repo = repo.resolve()
    files = verify_publication(repo)
    if (git(repo, "branch", "--show-current") != EXPECTED_BRANCH
            or git(repo, "remote", "get-url", "--all", "origin") != EXPECTED_REMOTE
            or git(repo, "remote", "get-url", "--push", "--all", "origin") != EXPECTED_REMOTE):
        raise ValueError("Research branch or remote changed; preserve local results without Git mutation")
    staged = git(repo, "diff", "--cached", "--name-only").splitlines()
    if any(name not in files for name in staged):
        raise ValueError("Unrelated staged work exists; preserve it and leave results local")
    git(repo, "add", "-f", "--", *files)
    if git(repo, "diff", "--cached", "--name-only", "--", *files):
        git(repo, "commit", "--only", "-m", "Publish completed audited APT followup outcomes", "--", *files)
    git(repo, "push", "origin", "HEAD:refs/heads/apt-benchmark")
    head = git(repo, "rev-parse", "HEAD")
    remote = git(repo, "ls-remote", "origin", "refs/heads/apt-benchmark").split()
    if len(remote) != 2 or remote[1] != "refs/heads/apt-benchmark" or head != remote[0]:
        raise ValueError("Remote verification differs from local commit")
    return {"status": "PUSHED_AND_VERIFIED", "commit": head, "branch": EXPECTED_BRANCH,
            "report_url": "https://github.com/garypagangit/praxis/blob/apt-benchmark/" + OUTPUT_RELATIVE + "/REPORT.md"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(promote(args.repo)))
