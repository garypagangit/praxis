# PX-049 Agentic Slopsquatting Live Gate

Purpose: run a live open-weight code/tool agent gate for PX-049.

The job prompts a code-capable model to produce one package-install tool action for 100 package-selection tasks. Half of the task suggestions name real PyPI/NPM packages; half name intentionally nonexistent, date-suffixed package names. The job does not execute installs. It extracts the proposed tool action and applies official registry metadata verification.

Default model:

```text
Qwen/Qwen2.5-Coder-7B-Instruct
```

Outputs include `summary.json`, `predictions.jsonl`, `row_outcomes.csv`, and `PX049_AGENTIC_SLOPSQUATTING_LIVE_GATE_20260705.md`.
