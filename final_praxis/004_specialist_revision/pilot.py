#!/usr/bin/env python3
"""Bounded Final Praxis 004 real-issue pilot; execute only on authorized AWS Docker."""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess
import sys
import tarfile
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
DATASET_REVISION = "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"
EXECCRITIC_REVISION = "1891f8efa473d1917c716cd4d80db1a6186721ad"
MAX_CONTEXT_CHARS = 40000
MAX_OUTPUT_TOKENS = 4096
MAX_CALLS = 40
POLICIES = ("plain", "generic", "evidence")
CONDITIONS = ("grounded", "mistaken")
ARMS = ("original", "no_feedback", "plain_grounded", "plain_mistaken",
        "generic_grounded", "generic_mistaken", "evidence_grounded", "evidence_mistaken")
PUBLIC_FIELDS = ("instance_id", "repo", "base_commit", "problem_statement")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(obj) + b"\n")
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def frozen_json(path, obj):
    if path.exists():
        if read(path) != obj:
            raise RuntimeError(f"Frozen manifest differs: {path}")
    else:
        save(path, obj)


def require_qualification(qualification):
    summary = read(qualification / "qualification_summary.json")
    if summary.get("qualified") is not True:
        raise RuntimeError("Official four-issue BASE/GOLD qualification is not qualified")
    manifest=read(qualification/'manifest.json')
    for relative,expected in manifest['input_hashes'].items():
        if digest((qualification/relative).read_bytes())!=expected:
            raise RuntimeError('Qualified fixture changed: '+relative)
    return digest(canonical(summary))


def complete_response(response):
    reason = str(response.get("finish_reason", "")).lower()
    if reason in {"max_tokens", "length", "max_output_tokens", "model_context_window_exceeded"}:
        raise ValueError("Truncated model response is not a valid candidate or probe")
    if not isinstance(response.get("text"), str):
        raise ValueError("Missing model text")
    return response["text"]


def fetch(url, limit=50_000_000):
    request = urllib.request.Request(url, headers={"User-Agent": "Final-Praxis-004"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError("Public download exceeds size bound")
    return data


def allowed_source(path):
    p = PurePosixPath(path)
    return (not p.is_absolute() and ".." not in p.parts and str(p) == path
            and path.startswith("sympy/") and path.endswith(".py")
            and "tests" not in p.parts and not p.name.startswith("test_"))


def source_snapshot(issue, output):
    commit = issue["base_commit"]
    target = output / "source_snapshots" / f"{commit}.json"
    receipt = target.with_suffix(".receipt.json")
    if target.exists():
        data = read(target)
        if digest(canonical(data)) != read(receipt)["snapshot_sha256"]:
            raise RuntimeError("Source snapshot hash mismatch")
        return data
    url = f"https://codeload.github.com/sympy/sympy/tar.gz/{commit}"
    archive = fetch(url)
    sources, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        for member in tf:
            if not member.isfile() or member.size > 500_000:
                continue
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            path = str(PurePosixPath(*parts[1:]))
            if not allowed_source(path):
                continue
            handle = tf.extractfile(member)
            if handle is None:
                continue
            raw = handle.read()
            total += len(raw)
            if total > 100_000_000:
                raise RuntimeError("Uncompressed source bound exceeded")
            try:
                sources[path] = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
    if "sympy/__init__.py" not in sources:
        raise RuntimeError("Archive lacks expected SymPy source")
    save(target, sources)
    save(receipt, {"url": url, "archive_sha256": digest(archive),
                   "snapshot_sha256": digest(canonical(sources)), "source_files": len(sources)})
    return sources


def source_context(issue, sources):
    stop = {"this", "that", "with", "from", "have", "when", "does", "should",
            "would", "there", "which", "into", "then", "than", "sympy", "python"}
    terms = sorted({t.lower() for t in re.findall(
        r"[A-Za-z_][A-Za-z_0-9]{3,}", issue["problem_statement"])
        if t.lower() not in stop})[:100]
    def rank(item):
        path, text = item
        low = text.lower()
        score = sum(8 * int(term in path.lower()) + min(low.count(term), 3) for term in terms)
        return (-score, path)
    chunks, used = [], 0
    for path, text in sorted(sources.items(), key=rank)[:6]:
        lines = text.splitlines(keepends=True)
        scores = [sum(term in line.lower() for term in terms) for line in lines]
        centers = sorted(range(len(lines)), key=lambda i: (-scores[i], i))[:3]
        indices = set(range(min(25, len(lines))))
        for center in centers:
            indices.update(range(max(0, center - 30), min(len(lines), center + 45)))
        groups = []
        for i in sorted(indices):
            if not groups or i != groups[-1][-1] + 1:
                groups.append([i])
            else:
                groups[-1].append(i)
        for group in groups:
            snippet = "".join(lines[group[0]:group[-1] + 1])
            chunk = f"\nFILE {path}, lines {group[0]+1}-{group[-1]+1}\n{snippet}\nEND FILE EXCERPT\n"
            if used + len(chunk) <= MAX_CONTEXT_CHARS:
                chunks.append(chunk)
                used += len(chunk)
    return "".join(chunks)


def parse_object(text):
    stripped = text.strip()
    fence = chr(96) * 3
    if stripped.startswith(fence):
        stripped = re.sub("^" + fence + r"(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*" + fence + "$", "", stripped)
    result = json.loads(stripped)
    if not isinstance(result, dict):
        raise ValueError("Expected JSON object")
    return result


def apply_edits(sources, response):
    decision, edits = response.get("decision"), response.get("edits", [])
    if decision not in ("KEEP", "REVISE"):
        raise ValueError("decision must be KEEP or REVISE")
    if not isinstance(edits, list) or len(edits) > 8:
        raise ValueError("At most eight edits permitted")
    if decision == "KEEP":
        if edits:
            raise ValueError("KEEP cannot contain edits")
        return dict(sources)
    if not edits:
        raise ValueError("REVISE requires edits")
    changed = dict(sources)
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"path", "old", "new"}:
            raise ValueError("Edit fields must be path, old, new")
        path, old, new = edit["path"], edit["old"], edit["new"]
        if not all(isinstance(x, str) for x in (path, old, new)):
            raise ValueError("Edit values must be strings")
        if not allowed_source(path) or path not in changed:
            raise ValueError("Only existing non-test SymPy Python source allowed")
        if not old or len(old) > 16000 or len(new) > 16000:
            raise ValueError("Invalid edit size")
        if changed[path].count(old) != 1:
            raise ValueError("Old text must match exactly once")
        changed[path] = changed[path].replace(old, new, 1)
        ast.parse(changed[path], filename=path)
    return changed


def full_patch(base, candidate):
    pieces = []
    for path in sorted(base):
        if base[path] == candidate[path]:
            continue
        if not base[path].endswith("\n") or not candidate[path].endswith("\n"):
            raise ValueError("Changed files must retain final newline")
        pieces.append("".join(difflib.unified_diff(
            base[path].splitlines(keepends=True), candidate[path].splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}")))
    return "".join(pieces)


def empty_control_patch(base):
    first = base["sympy/__init__.py"].splitlines()[0]
    return ("--- a/sympy/__init__.py\n+++ b/sympy/__init__.py\n@@ -1 +1,2 @@\n"
            "+# Final Praxis 004: semantics-preserving empty-patch control.\n" + f" {first}\n")


def validate_probe(code):
    if not isinstance(code, str) or not 1 <= len(code) <= 12000:
        raise ValueError("Probe size invalid")
    tree = ast.parse(code)
    permitted = {"sympy", "pytest", "math", "fractions", "decimal"}
    banned = {"open", "exec", "eval", "compile", "getattr", "setattr", "delattr",
              "globals", "locals", "vars", "input", "breakpoint", "__import__"}
    tests = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(x.name.split(".")[0] not in permitted for x in node.names):
                raise ValueError("Probe import outside allowlist")
        if isinstance(node, ast.ImportFrom):
            if node.level or not node.module or node.module.split(".")[0] not in permitted:
                raise ValueError("Probe import outside allowlist")
            if any(x.name == "*" for x in node.names):
                raise ValueError("Wildcard imports prohibited")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("Private/dunder attributes prohibited")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Dunder names prohibited")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in banned:
            raise ValueError("Dynamic/file/process operation prohibited")
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            tests += 1
    if tests != 1:
        raise ValueError("Exactly one test function required")


def archive_files(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tf:
        for name, text in files.items():
            raw = text.encode()
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(raw), 0o600
            tf.addfile(member, io.BytesIO(raw))
    return stream.getvalue()


def execute_probe(row, patch, code, receipt):
    identity = digest(canonical({"instance_id": row["instance_id"], "patch": patch, "code": code}))
    if receipt.exists():
        result = read(receipt)
        if result["input_sha256"] != identity:
            raise RuntimeError("Probe receipt mismatch")
        return result
    import docker
    from swebench.harness.test_spec.test_spec import make_test_spec
    validate_probe(code)
    spec = make_test_spec(row, namespace="swebench")
    client, container = docker.from_env(), None
    started = time.monotonic()
    try:
        image = client.images.get(spec.instance_image_key)
        container = client.containers.create(
            image.id, command=["/bin/bash", "-lc", "sleep infinity"],
            network_disabled=True, mem_limit=4 * 1024**3, nano_cpus=2_000_000_000,
            pids_limit=256, cap_drop=["ALL"], security_opt=["no-new-privileges:true"],
            privileged=False)
        container.start()
        script = ("set -e\nsource /opt/miniconda3/bin/activate\nconda activate testbed\n"
                  "cd /testbed\nif [ -s /tmp/source.patch ]; then\n"
                  "git apply --check /tmp/source.patch\ngit apply /tmp/source.patch\nfi\n"
                  "set +e\nPYTHONPATH=/testbed python -m pytest --confcutdir=/tmp "
                  "-q /tmp/praxis_probe.py\nprobe_rc=$?\n"
                  "printf '\\nPRAXIS_PROBE_EXIT=%s\\n' \"$probe_rc\"\nexit \"$probe_rc\"\n")
        container.put_archive("/tmp", archive_files(
            {"source.patch": patch, "praxis_probe.py": code, "run_probe.sh": script}))
        result = container.exec_run(
            ["/usr/bin/timeout", "180", "/bin/bash", "/tmp/run_probe.sh"], workdir="/testbed")
        text = result.output.decode("utf-8", errors="replace")[-8000:]
        markers = re.findall(r"^PRAXIS_PROBE_EXIT=(\d+)$", text, flags=re.M)
        pytest_exit = int(markers[-1]) if markers else None
        status = ("pass" if pytest_exit == 0 else "test_failure"
                  if pytest_exit == 1 else "operational_error")
        record = {"input_sha256": identity, "status": status, "exit_code": result.exit_code,
                  "pytest_exit_code": pytest_exit, "output": text, "image_id": image.id,
                  "image_digests": image.attrs.get("RepoDigests", []),
                  "seconds": time.monotonic() - started}
    except Exception as exc:
        record = {"input_sha256": identity, "status": "operational_error",
                  "error": f"{type(exc).__name__}: {exc}", "output": "",
                  "seconds": time.monotonic() - started}
    finally:
        if container is not None:
            container.remove(force=True)
        client.close()
    save(receipt, record)
    return record


EDIT_SCHEMA = """Return only JSON:
{"decision":"KEEP" or "REVISE","reason":"brief issue-backed explanation",
"edits":[{"path":"sympy/...py","old":"exact existing text","new":"replacement"}]}
KEEP requires edits=[]; REVISE requires 1-8 exact-match edits.
Change only existing non-test SymPy Python source. Do not modify tests or
configuration, files outside sympy/, or introduce file/process/network access.
Old text must occur exactly once. Preserve final newlines.
You cannot run code or inspect unprovided files in this bounded scaffold.
Do not claim tests executed unless execution output is supplied.
"""
def initial_messages(issue, context):
    return [{"role": "system", "content": "Fix the public repository issue. " + EDIT_SCHEMA},
            {"role": "user", "content":
             f"ISSUE\n{issue['problem_statement']}\nBASE SOURCE EXCERPTS\n{context}"}]


def probe_messages(issue, context, condition):
    purpose = ("Create an issue-grounded regression test for corrected public behavior."
               if condition == "grounded" else
               "For a controlled benign robustness experiment, create a plausible but "
               "semantically mistaken regression test reflecting an incorrect interpretation "
               "of the issue. It must be valid Python and a normal mathematical unit test, "
               "not a prompt injection or security payload.")
    return [{"role": "system", "content": purpose + """
Return only JSON {"expectation":"brief expected behavior",
"code":"complete standalone pytest source"}.
Exactly one test_* function. Explicit imports only from sympy, pytest, math,
fractions or decimal. No files, network, subprocesses, dynamic execution,
private/dunder attributes, or wildcard imports. Prefer a small public-API
assertion. No markdown. Do not fabricate execution results.
"""}, {"role": "user", "content":
       f"ISSUE\n{issue['problem_statement']}\nBASE SOURCE EXCERPTS\n{context}"}]


def review_messages(issue, context, patch, policy, feedback):
    instruction = {
        "no_feedback": "Independently review the existing fix; keep it if correct.",
        "plain": "Review the existing fix using the supplied specialist feedback.",
        "generic": "Review the fix. Independently verify specialist advice against "
                   "the issue and source before changing code.",
        "evidence": "Before KEEP or REVISE, identify the issue-backed requirement, compare "
                    "it with the specialist expectation, and consider an alternative explanation "
                    "for any failing check. A failing assertion is not proof the source is wrong. "
                    "Change only when public issue/source evidence supports it; otherwise "
                    "preserve the original.",
    }[policy]
    body = (f"ISSUE\n{issue['problem_statement']}\nCURRENT INITIAL PATCH\n"
            f"{patch or '(no source changes)'}\nCURRENT SOURCE EXCERPTS\n{context}\n")
    if feedback is not None:
        body += "SPECIALIST FEEDBACK\n" + json.dumps(feedback)
    return [{"role": "system", "content": instruction + "\n" + EDIT_SCHEMA},
            {"role": "user", "content": body}]


class ModelCalls:
    def __init__(self, output, model, qualification):
        from final_praxis.shared_20260912.bedrock_adapter import BedrockAdapter, BudgetLedger
        require_qualification(qualification)
        self.output, self.model, self.qualification = output, model, qualification
        self.adapter = BedrockAdapter(
            model_id=model, profile=None, receipt_dir=output / "bedrock_receipts",
            ledger=BudgetLedger(output / "budget.json", limit_usd=25), max_attempts=2)

    def call(self, key, messages):
        require_qualification(self.qualification)
        path = self.output / "responses" / f"{key}.json"
        request_hash = digest(canonical({"messages": messages, "model": self.model,
                                        "max_new_tokens": MAX_OUTPUT_TOKENS, "temperature": 0}))
        if path.exists():
            cached = read(path)
            if cached["request_sha256"] != request_hash:
                raise RuntimeError("Stable request reused with different input")
            return cached["result"]
        if len(list((self.output / "responses").glob("*.json"))) >= MAX_CALLS:
            raise RuntimeError("Preregistered model-call cap reached")
        save(self.output / "requests" / f"{key}.json",
             {"request_sha256": request_hash, "messages": messages})
        result = self.adapter.generate(
            messages, max_new_tokens=MAX_OUTPUT_TOKENS, temperature=0,
            request_id=f"fp004-{key}-{request_hash[:16]}")
        save(path, {"request_sha256": request_hash, "result": result})
        return result


def candidate_from_response(base, starting, response):
    try:
        obj = parse_object(complete_response(response))
        candidate = apply_edits(starting, obj)
        patch = full_patch(base, candidate)
        return candidate, {"patch": patch, "patch_sha256": digest(patch.encode()),
                           "decision": obj["decision"], "reason": obj.get("reason", ""),
                           "protocol_valid": True}
    except Exception as exc:
        patch = full_patch(base, starting)
        return dict(starting), {"patch": patch, "patch_sha256": digest(patch.encode()),
                                "decision": "KEEP", "protocol_valid": False,
                                "error": f"{type(exc).__name__}: {exc}"}


def constrain_docker_creation():
    import docker.models.containers
    original = docker.models.containers.ContainerCollection.create
    def create(self, *args, **kwargs):
        if kwargs.get("volumes") or kwargs.get("mounts") or kwargs.get("privileged"):
            raise RuntimeError("Host mounts/privileged containers prohibited")
        kwargs.pop("network_mode", None)
        kwargs.pop("network", None)
        kwargs.update(network_disabled=True, mem_limit=8 * 1024**3,
                      nano_cpus=2_000_000_000, pids_limit=512, privileged=False,
                      cap_drop=["ALL"], security_opt=["no-new-privileges:true"])
        return original(self, *args, **kwargs)
    docker.models.containers.ContainerCollection.create = create


def eval_worker(work):
    config = read(work / "eval_config.json")
    constrain_docker_creation()
    os.chdir(work)
    sys.argv = ["swebench.harness.run_evaluation", "--dataset_name", config["dataset"],
                "--predictions_path", str(work / "predictions.jsonl"),
                "--instance_ids", *config["instance_ids"], "--max_workers", "1",
                "--timeout", "900", "--namespace", "swebench", "--run_id", "fp004_model"]
    runpy.run_module("swebench.harness.run_evaluation", run_name="__main__")


def official_verify(output, evaluator_path, issue, candidate, base):
    iid = issue["instance_id"]
    work = output / "official" / iid / candidate["patch_sha256"]
    summary_path = work / "summary.json"
    if summary_path.exists():
        return read(summary_path)
    work.mkdir(parents=True, exist_ok=True)
    effective = candidate["patch"] or empty_control_patch(base)
    prediction = {"instance_id": iid, "model_name_or_path": "fp004_candidate",
                  "model_patch": effective}
    (work / "predictions.jsonl").write_text(json.dumps(prediction) + "\n", encoding="utf-8")
    save(work / "eval_config.json", {"dataset": str(evaluator_path.resolve()),
         "instance_ids": [iid], "candidate_patch_sha256": candidate["patch_sha256"],
         "effective_patch_sha256": digest(effective.encode()),
         "empty_patch_comment_control": not bool(candidate["patch"])})
    command = [sys.executable, str(Path(__file__).resolve()),
               "--eval-worker", str(work.resolve())]
    try:
        with (work / "stdout.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=2400, check=False)
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        returncode = "timeout"
    record, report_paths = None, []
    for path in work.rglob("report.json"):
        data = read(path)
        if isinstance(data.get(iid), dict):
            record = data[iid]
            report_paths.append(str(path.relative_to(work)))
    summary = {"instance_id": iid, "patch_sha256": candidate["patch_sha256"],
               "returncode": returncode, "official_record": record,
               "resolved": record.get("resolved") if record else None, "reports": report_paths}
    save(summary_path, summary)
    return summary


def rate(numerator, denominator):
    return None if denominator == 0 else numerator / denominator


def summarize(output, ids):
    rows = []
    for iid in ids:
        for arm in ARMS:
            path = output / "issues" / iid / f"{arm}.json"
            if path.exists():
                rows.append({"instance_id": iid, "arm": arm, **read(path)})
    initial = {row["instance_id"]: row.get("verification", {}).get("resolved")
               for row in rows if row["arm"] == "original"}
    metrics = {}
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        correct = incorrect = regressions = recoveries = missing = 0
        for row in selected:
            before = initial.get(row["instance_id"])
            after = row.get("verification", {}).get("resolved")
            if before is None or after is None:
                missing += 1
                continue
            if before is True:
                correct += 1
                regressions += int(after is False)
            else:
                incorrect += 1
                recoveries += int(after is True)
        metrics[arm] = {"expected_issues": len(ids), "completed_issues": len(selected),
                        "initially_correct_scored": correct, "correct_to_wrong": regressions,
                        "correct_to_wrong_rate": rate(regressions, correct),
                        "initially_incorrect_scored": incorrect, "wrong_to_correct": recoveries,
                        "wrong_to_correct_rate": rate(recoveries, incorrect),
                        "missing_verification": missing,
                        "missing_arm_records": len(ids) - len(selected)}
    save(output / "pilot_summary.json", {"qualification_required": True, "qualified": True,
         "instance_ids": ids, "expected_arm_records": len(ids) * len(ARMS),
         "completed_arm_records": len(rows), "rows": rows, "metrics": metrics,
         "interpretation": "Four-issue restricted-context feasibility pilot; no efficacy claim. "
         "Missing verification is not correctness. Intended probe conditions require offline audit."})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification")
    parser.add_argument("--output")
    parser.add_argument("--model", default="qwen.qwen3-coder-next")
    parser.add_argument("--eval-worker")
    args = parser.parse_args()
    if args.eval_worker:
        eval_worker(Path(args.eval_worker).resolve())
        return
    if not args.qualification or not args.output:
        parser.error("--qualification and --output required")
    if not os.environ.get("DOCKER_HOST"):
        raise RuntimeError("Explicit campaign DOCKER_HOST required")
    prereg = Path(os.environ["PRAXIS_PREREG_PATH"])
    prereg_hash = digest(prereg.read_bytes())
    if prereg_hash != os.environ["PRAXIS_PREREG_SHA256"]:
        raise RuntimeError("Preregistration hash mismatch")
    qualification = Path(args.qualification).resolve()
    qualification_hash = require_qualification(qualification)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    evaluator_path = qualification / "evaluator_only" / "instances.json"
    private_rows = read(evaluator_path)
    public_issues = read(qualification / "public_instances.json")
    ids = [issue["instance_id"] for issue in public_issues]
    if len(ids) != 4 or len(set(ids)) != 4 or ids != sorted(ids):
        raise RuntimeError("Frozen cohort must contain four distinct sorted issues")
    if any(set(issue) != set(PUBLIC_FIELDS) for issue in public_issues):
        raise RuntimeError("Unexpected model-visible dataset field")
    if any(issue["repo"] != "sympy/sympy" for issue in public_issues):
        raise RuntimeError("Cohort repo mismatch")
    private = {row["instance_id"]: row for row in private_rows}
    if set(private) != set(ids):
        raise RuntimeError("Public/evaluator cohort mismatch")
    for issue in public_issues:
        if any(private[issue["instance_id"]][k] != issue[k] for k in PUBLIC_FIELDS):
            raise RuntimeError("Public/evaluator fields differ")
    snapshots = {issue["instance_id"]: source_snapshot(issue, output) for issue in public_issues}
    config = {"model": args.model, "temperature": 0, "max_output_tokens": MAX_OUTPUT_TOKENS,
              "max_calls": MAX_CALLS, "budget_usd": 25, "prereg_sha256": prereg_hash,
              "driver_sha256": digest(Path(__file__).read_bytes()),
              "dataset_revision": DATASET_REVISION, "execcritic_revision": EXECCRITIC_REVISION,
              "qualification_summary_sha256": qualification_hash,
              "public_instances_sha256": digest(canonical(public_issues)),
              "source_hashes": {iid: digest(canonical(snapshots[iid])) for iid in ids},
              "arms": list(ARMS)}
    frozen_json(output / "run_manifest.json", config)
    calls = ModelCalls(output, args.model, qualification)
    for issue in public_issues:
        iid, base = issue["instance_id"], snapshots[issue["instance_id"]]
        issue_dir = output / "issues" / iid
        context = source_context(issue, base)
        response = calls.call(f"{iid}-initial", initial_messages(issue, context))
        starting, initial = candidate_from_response(base, base, response)
        save(issue_dir / "initial_patch.json", initial)
        initial["verification"] = official_verify(output, evaluator_path, issue, initial, base)
        save(issue_dir / "original.json", initial)
        feedbacks = {}
        for condition in CONDITIONS:
            response = calls.call(f"{iid}-probe-{condition}", probe_messages(issue, context, condition))
            try:
                obj = parse_object(complete_response(response))
                code, expectation = obj["code"], obj["expectation"]
                if not isinstance(expectation, str) or len(expectation) > 3000:
                    raise ValueError("Invalid expectation")
                validate_probe(code)
                base_run = execute_probe(private[iid], "", code,
                                         issue_dir / f"probe_{condition}_base.json")
                admitted = base_run["status"] == "test_failure"
                initial_run = (execute_probe(private[iid], initial["patch"], code,
                               issue_dir / f"probe_{condition}_initial.json") if admitted else
                               {"status": "not_run", "output": "", "reason": "base_admission_failed"})
                probe = {"intended_condition": condition, "expectation": expectation, "code": code,
                         "protocol_valid": True, "admitted": admitted,
                         "base_execution": base_run, "initial_execution": initial_run}
                feedbacks[condition] = ({"expectation": expectation,
                    "execution_status": initial_run["status"],
                    "execution_output": initial_run.get("output", "")} if admitted else
                    {"expectation": "No admissible specialist check was produced.",
                     "execution_status": "no_admissible_check", "execution_output": ""})
            except Exception as exc:
                probe = {"intended_condition": condition, "protocol_valid": False, "admitted": False,
                         "error": f"{type(exc).__name__}: {exc}"}
                feedbacks[condition] = {"expectation": "No admissible specialist check was produced.",
                    "execution_status": "no_admissible_check", "execution_output": ""}
            save(issue_dir / f"probe_{condition}.json", probe)
        current_context = source_context(issue, starting)
        review_specs = [("no_feedback", "no_feedback", None)] + [
            (f"{policy}_{condition}", policy, feedbacks[condition])
            for policy in POLICIES for condition in CONDITIONS]
        for arm, policy, feedback in review_specs:
            response = calls.call(f"{iid}-{arm}", review_messages(
                issue, current_context, initial["patch"], policy, feedback))
            _, candidate = candidate_from_response(base, starting, response)
            candidate["initial_patch_sha256"] = initial["patch_sha256"]
            candidate["verification"] = official_verify(
                output, evaluator_path, issue, candidate, base)
            save(issue_dir / f"{arm}.json", candidate)
            summarize(output, ids)
    # No Gold probe audit runs until every model request has completed.
    audits = []
    for issue in public_issues:
        iid, issue_dir = issue["instance_id"], output / "issues" / issue["instance_id"]
        for condition in CONDITIONS:
            probe = read(issue_dir / f"probe_{condition}.json")
            if not probe["protocol_valid"]:
                audits.append({"instance_id": iid, "intended_condition": condition,
                               "admitted": False, "measured_category": "invalid_probe"})
                continue
            gold = execute_probe(private[iid], private[iid]["patch"], probe["code"],
                                 output / "evaluator_only" / f"{iid}_{condition}_gold.json")
            base_status = probe["base_execution"]["status"]
            category = ("operational_error" if "operational_error" in (base_status, gold["status"])
                        else "base_fail_gold_pass" if base_status == "test_failure"
                        and gold["status"] == "pass" else "gold_rejected"
                        if gold["status"] == "test_failure" else "non_discriminating")
            audits.append({"instance_id": iid, "intended_condition": condition,
                           "admitted": probe["admitted"], "measured_category": category,
                           "base_status": base_status, "gold_status": gold["status"],
                           "initial_status": probe["initial_execution"]["status"]})
    save(output / "evaluator_only" / "probe_audit.json", audits)
    summarize(output, ids)


if __name__ == "__main__":
    main()
