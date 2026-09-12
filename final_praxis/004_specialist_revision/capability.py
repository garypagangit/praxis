#!/usr/bin/env python3
"""Exploratory stage-2 capability baseline: six public-source turns, no feedback."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAX_TURNS = 6
MAX_RESPONSE_CHARS = 40000
MAX_CONTEXT_CHARS = 160000
MAX_OUTPUT_TOKENS = 4096
MODEL_ID = "qwen.qwen3-coder-next"


def load_pilot():
    path = HERE / "pilot.py"
    if not path.exists():
        path = HERE / "pilot004.py"
    spec = importlib.util.spec_from_file_location("fp004_stage1_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = load_pilot()


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def context_size(messages):
    return sum(len(item["content"]) for item in messages)


class SourceAccess:
    """All access is to whitelisted in-memory Base source, never a filesystem path."""
    def __init__(self, sources):
        if any(not pilot.allowed_source(path) for path in sources):
            raise ValueError("Source snapshot contains a forbidden path")
        self.sources = sources
        self.paths = sorted(sources)

    def _finish(self, result, cap):
        if len(encode(result)) > cap:
            raise ValueError("Response exceeds available context budget; request a smaller window")
        return result

    def dispatch(self, action, cap=MAX_RESPONSE_CHARS):
        cap = min(cap, MAX_RESPONSE_CHARS)
        if cap < 512:
            raise ValueError("Insufficient remaining context budget")
        name = action.get("action")
        if name == "read":
            path = action.get("path")
            if path not in self.sources:
                raise ValueError("Unknown public Base source path")
            lines = self.sources[path].splitlines(keepends=True)
            start, end = action.get("start_line", 1), action.get("end_line", 200)
            if (type(start) is not int or type(end) is not int or
                    start < 1 or end < start or end-start+1 > 200 or start > len(lines)):
                raise ValueError("Read requires valid 1-based bounds covering at most 200 lines")
            requested_end, end = end, min(end, len(lines))
            while end >= start:
                result = {"status": "ok", "action": "read", "path": path,
                          "start_line": start, "end_line": end, "total_lines": len(lines),
                          "source": "".join(lines[start-1:end]),
                          "truncated": end < min(requested_end, len(lines)),
                          "next_start_line": end+1 if end < len(lines) else None}
                if len(encode(result)) <= cap:
                    return result
                end -= 1
            raise ValueError("One source line exceeds response budget")
        if name == "list":
            prefix = action.get("prefix", "sympy/")
            offset, limit = action.get("offset", 0), action.get("limit", 200)
            if not isinstance(prefix, str) or ".." in prefix or "\\" in prefix:
                raise ValueError("Invalid literal path prefix")
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
                raise ValueError("List limit must be 1..200 and offset nonnegative")
            paths = [p for p in self.paths if p.startswith(prefix)]
            selected = paths[offset:offset+limit]
            while selected:
                result = {"status": "ok", "action": "list", "paths": selected,
                          "matched_paths": len(paths), "offset": offset,
                          "next_offset": offset+len(selected) if offset+len(selected)<len(paths) else None}
                if len(encode(result)) <= cap:
                    return result
                selected.pop()
            return self._finish({"status": "ok", "action": "list", "paths": [],
                                 "matched_paths": len(paths), "offset": offset,
                                 "next_offset": None}, cap)
        if name == "search":
            query = action.get("query")
            prefix = action.get("prefix", "sympy/")
            limit, offset = action.get("limit", 20), action.get("offset", 0)
            sensitive = action.get("case_sensitive", False)
            if not isinstance(query, str) or not 1 <= len(query) <= 160 or "\n" in query:
                raise ValueError("Search query must be a literal string of 1..160 characters")
            if not isinstance(prefix, str) or ".." in prefix or "\\" in prefix:
                raise ValueError("Invalid path prefix")
            if type(limit) is not int or not 1 <= limit <= 30 or type(offset) is not int or offset < 0:
                raise ValueError("Search limit must be 1..30 and offset nonnegative")
            if type(sensitive) is not bool:
                raise ValueError("case_sensitive must be boolean")
            matches, seen, truncated = [], 0, False
            needle = query if sensitive else query.lower()
            for path in self.paths:
                if not path.startswith(prefix):
                    continue
                lines = self.sources[path].splitlines(keepends=True)
                for index, line in enumerate(lines):
                    if needle not in (line if sensitive else line.lower()):
                        continue
                    seen += 1
                    if seen <= offset:
                        continue
                    start, end = max(0,index-2), min(len(lines),index+3)
                    match = {"path": path, "match_line": index+1,
                             "start_line": start+1, "end_line": end,
                             "source": "".join(lines[start:end])}
                    candidate = {"status": "ok", "action": "search", "query": query,
                                 "matches": matches+[match], "truncated": True,
                                 "next_offset": offset+len(matches)+1}
                    if len(matches) >= limit or len(encode(candidate)) > cap:
                        truncated = True
                        break
                    matches.append(match)
                if truncated:
                    break
            return self._finish({"status": "ok", "action": "search", "query": query,
                                 "matches": matches, "truncated": truncated,
                                 "next_offset": offset+len(matches) if truncated else None}, cap)
        raise ValueError("Action must be list, search, read, or submit")


SYSTEM = """You are fixing a real SymPy repository issue in a bounded source-access study.
You have SIX total model responses, including your final submission. Use controlled
public Base source access to inspect exact text before editing. There is no shell,
test execution, internet, hidden reference patch or external tool beyond these actions.
Return exactly one JSON object per response, with one of these actions:
{"action":"list","prefix":"sympy/","offset":0,"limit":200}
{"action":"search","query":"literal substring","prefix":"sympy/","limit":20,"offset":0}
{"action":"read","path":"sympy/path.py","start_line":1,"end_line":150}
{"action":"submit","decision":"REVISE","reason":"brief explanation",
 "edits":[{"path":"sympy/path.py","old":"exact existing text","new":"replacement"}]}
For a deliberate unchanged submission use decision KEEP and edits=[].
Read windows contain at most 200 raw source lines; bounds are outside the source text.
Search is literal, not a regex or shell command. All edits must match Base text exactly
once. No whitespace fuzzing. At most eight edits, existing non-test SymPy Python source
only. Preserve final newlines. Each old/new edit is at most 16000 characters.
You may correct an invalid submission if turns remain. Invalid edits are never applied.
Do not claim execution results. You must explicitly submit before your six responses end.
"""


def initial_messages(issue, access):
    if set(issue) != set(pilot.PUBLIC_FIELDS):
        raise ValueError("Unexpected model-visible issue field")
    paths = []
    for path in access.paths:
        trial = {"issue": issue, "source_paths": paths+[path],
                 "path_count": len(access.paths), "paths_truncated": True,
                 "responses_remaining": MAX_TURNS}
        if len(encode(trial)) > MAX_RESPONSE_CHARS:
            break
        paths.append(path)
    content = encode({"issue": issue, "source_paths": paths,
                      "path_count": len(access.paths),
                      "paths_truncated": len(paths)<len(access.paths),
                      "responses_remaining": MAX_TURNS})
    if len(content) > MAX_RESPONSE_CHARS:
        raise ValueError("Public issue alone exceeds initial context limit")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


class Calls:
    def __init__(self, output, qualification):
        from final_praxis.shared_20260912.bedrock_adapter import BedrockAdapter, BudgetLedger
        pilot.require_qualification(qualification)
        self.output, self.qualification = output, qualification
        self.adapter = BedrockAdapter(model_id=MODEL_ID, profile=None,
            receipt_dir=output/"bedrock_receipts",
            ledger=BudgetLedger(output/"budget.json", limit_usd=15), max_attempts=2)

    def call(self, key, messages):
        pilot.require_qualification(self.qualification)
        if context_size(messages) > MAX_CONTEXT_CHARS:
            raise RuntimeError("Context exceeds frozen character budget")
        request_hash = pilot.digest(pilot.canonical(
            {"messages": messages, "model": MODEL_ID, "max_new_tokens": MAX_OUTPUT_TOKENS}))
        path = self.output/"responses"/f"{key}.json"
        if path.exists():
            cached = pilot.read(path)
            if cached["request_sha256"] != request_hash:
                raise RuntimeError("Cached request mismatch")
            return cached["result"]
        request_path = self.output/"requests"/f"{key}.json"
        if not request_path.exists() and len(list((self.output/"requests").glob("*.json"))) >= 24:
            raise RuntimeError("Maximum 24 issue-turn requests reached")
        pilot.frozen_json(request_path, {"request_sha256": request_hash, "messages": messages})
        result = self.adapter.generate(messages, max_new_tokens=MAX_OUTPUT_TOKENS,
            temperature=0, request_id=f"fp004cap-{key}-{request_hash[:16]}")
        pilot.save(path, {"request_sha256": request_hash, "result": result})
        return result


def solve_issue(issue, base, calls, output):
    access = SourceAccess(base)
    messages = initial_messages(issue, access)
    events, candidate = [], None
    terminal = "no_final_submission"
    for turn in range(1, MAX_TURNS+1):
        if context_size(messages) > MAX_CONTEXT_CHARS:
            terminal = "context_budget_exhausted"
            break
        key = f"{issue['instance_id']}-turn{turn:02d}"
        try:
            response = calls.call(key, messages)
        except Exception as exc:
            terminal = "model_request_error"
            events.append({"turn": turn, "status": terminal,
                           "error": f"{type(exc).__name__}: {exc}"})
            break
        # Retain the FULL prior model response, including malformed/truncated output.
        text = response.get("text", "")
        messages.append({"role": "assistant", "content": text if isinstance(text,str) else str(text)})
        event = {"turn": turn, "finish_reason": response.get("finish_reason")}
        try:
            action = pilot.parse_object(pilot.complete_response(response))
            name = action.get("action")
            event["action"] = action
            if name == "submit":
                submission = {k: v for k,v in action.items() if k != "action"}
                _, trial = pilot.candidate_from_response(base, base,
                    {"text": json.dumps(submission), "finish_reason": "end_turn"})
                if not trial["protocol_valid"]:
                    raise ValueError(trial["error"])
                candidate, terminal = trial, "submitted"
                event["status"] = terminal
                events.append(event)
                break
            remaining = MAX_CONTEXT_CHARS-context_size(messages)-512
            result = access.dispatch(action, cap=min(MAX_RESPONSE_CHARS-128,remaining))
            result["responses_remaining"] = MAX_TURNS-turn
            event["status"], event["operation_result"] = "source_access", result
        except Exception as exc:
            result = {"status": "operational_error",
                      "error": f"{type(exc).__name__}: {exc}",
                      "responses_remaining": MAX_TURNS-turn,
                      "instruction": "Inspect exact Base source or correct your JSON/edit, then submit."}
            event["status"], event["operation_result"] = "invalid_action_or_edit", result
        events.append(event)
        messages.append({"role": "user", "content": encode(result)})
        pilot.save(output/"trajectories"/f"{issue['instance_id']}.checkpoint.json",
                   {"events": events, "messages": messages})
    record = {"instance_id": issue["instance_id"], "terminal_status": terminal,
              "submitted": candidate is not None, "candidate": candidate,
              "model_responses": sum("finish_reason" in e for e in events),
              "events": events, "messages": messages,
              "context_characters": context_size(messages),
              "verification": None, "scientific_resolution": None}
    pilot.save(output/"trajectories"/f"{issue['instance_id']}.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-cache")
    args = parser.parse_args()
    qualification, output = Path(args.qualification).resolve(), Path(args.output).resolve()
    if not os.environ.get("DOCKER_HOST"):
        raise RuntimeError("Explicit campaign Docker daemon required")
    prereg = Path(os.environ["PRAXIS_PREREG_PATH"])
    prereg_hash = pilot.digest(prereg.read_bytes())
    if prereg_hash != os.environ["PRAXIS_PREREG_SHA256"]:
        raise RuntimeError("Stage-2 preregistration hash mismatch")
    qualified_hash = pilot.require_qualification(qualification)
    issues = pilot.read(qualification/"public_instances.json")
    ids = [x["instance_id"] for x in issues]
    if len(ids)!=4 or len(set(ids))!=4 or ids!=sorted(ids):
        raise RuntimeError("Expected same four frozen sorted SymPy issues")
    if any(set(x)!=set(pilot.PUBLIC_FIELDS) or x["repo"]!="sympy/sympy" for x in issues):
        raise RuntimeError("Unexpected model-visible public fields or repository")
    output.mkdir(parents=True,exist_ok=True)
    source_cache = Path(args.source_cache).resolve() if args.source_cache else output
    snapshots = {x["instance_id"]: pilot.source_snapshot(x,source_cache) for x in issues}
    config = {"stage": "exploratory_source_access_baseline_only", "model": MODEL_ID,
              "max_turns":MAX_TURNS, "max_response_chars":MAX_RESPONSE_CHARS,
              "max_context_chars":MAX_CONTEXT_CHARS, "max_output_tokens":MAX_OUTPUT_TOKENS,
              "budget_usd":15, "preregistration_sha256":prereg_hash,
              "driver_sha256":pilot.digest(Path(__file__).read_bytes()),
              "helper_sha256":pilot.digest(Path(pilot.__file__).read_bytes()),
              "qualified_summary_sha256":qualified_hash,
              "public_issues_sha256":pilot.digest(pilot.canonical(issues)),
              "source_hashes":{iid:pilot.digest(pilot.canonical(snapshots[iid])) for iid in ids}}
    pilot.frozen_json(output/"run_manifest.json",config)
    calls = Calls(output,qualification)
    # Absolutely no official evaluation/Gold inspection until ALL FOUR trajectories finish.
    records = []
    for issue in issues:
        records.append(solve_issue(issue,snapshots[issue["instance_id"]],calls,output))
    pilot.save(output/"model_trajectories_complete.json",
               {"complete":True,"instance_ids":ids,"records":len(records)})
    evaluator_path = qualification/"evaluator_only"/"instances.json"
    for issue,record in zip(issues,records):
        if record["submitted"]:
            verification = pilot.official_verify(output,evaluator_path,issue,
                            record["candidate"],snapshots[issue["instance_id"]])
            record["verification"]=verification
            record["scientific_resolution"]=verification.get("resolved")
        # No submission is explicitly NO CANDIDATE, not a scientific wrong answer.
        pilot.save(output/"trajectories"/f"{issue['instance_id']}.json",record)
    submitted=sum(x["submitted"] for x in records)
    scored=[x for x in records if x["scientific_resolution"] is not None]
    resolved=sum(x["scientific_resolution"] is True for x in scored)
    pilot.save(output/"capability_summary.json",{
        "exploratory":True,"stage":"source_access_baseline_only","instance_ids":ids,
        "expected_issues":4,"completed_trajectories":len(records),
        "submitted_candidates":submitted,"no_candidate":4-submitted,
        "officially_scored_candidates":len(scored),"resolved_candidates":resolved,
        "candidate_resolution_rate":None if not scored else resolved/len(scored),
        "all_issue_completion_rate":resolved/4,
        "all_issue_completion_note":"Counts missing candidates as uncompleted, not verified-wrong.",
        "invalid_action_or_edit_count":sum(e["status"]=="invalid_action_or_edit"
                    for r in records for e in r["events"]),
        "records":records,
        "interpretation":"Exploratory same-cohort capability check; no feedback/defense efficacy claim."})


if __name__=="__main__":
    main()
