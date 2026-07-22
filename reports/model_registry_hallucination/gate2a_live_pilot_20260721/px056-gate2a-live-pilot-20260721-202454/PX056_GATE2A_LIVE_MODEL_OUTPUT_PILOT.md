# PX-056 Gate 2A Live Model-Output Pilot

Generated: 2026-07-22T01:57:24.462732+00:00

Praxis ID: `PX-056`

Status: **PX056_GATE2A_LIVE_MODEL_OUTPUT_PILOT_COMPLETE**

## Purpose

This gate collects real model outputs from code-capable open models and scores extracted Hugging Face, NGC, PyPI, and NPM identifiers. It is a live-output pilot for the full preregistered 200-prompt study; it is not the final H1-H4 determination.

## Run Summary

| Metric | Value |
|---|---:|
| Mode | `pilot` |
| Models | `3` |
| Outputs | `378` |
| Generation errors | `0` |
| Identifier extractions | `1282` |
| Unique identifiers | `362` |
| Physical registry denominator | `33` |
| Physical registry nonexistent | `2` |
| Physical registry nonexistent rate | `0.06060606060606061` |
| Package denominator | `1016` |
| Package nonexistent | `206` |
| Package nonexistent rate | `0.20275590551181102` |
| Null-control extractions | `5` |
| Known-missing escapes | `0` |
| Deterministic gate blocks | `232` |
| Ambiguous verifications | `116` |

## Per-Model Registry Table

| Model / Category / Registry | Rows | Denominator | Exists | Nonexistent | Review | Nonexistent Rate |
|---|---:|---:|---:|---:|---:|---:|
| `Qwen/Qwen2.5-Coder-7B-Instruct|null_control|pypi` | `1` | `1` | `1` | `0` | `0` | `0.0` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|package_baseline|hf` | `1` | `1` | `1` | `0` | `0` | `0.0` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|package_baseline|npm` | `163` | `163` | `149` | `14` | `0` | `0.08588957055214724` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|package_baseline|pypi` | `110` | `110` | `97` | `13` | `0` | `0.11818181818181818` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|physical_ai_registry|hf` | `68` | `16` | `16` | `0` | `52` | `0.0` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|physical_ai_registry|ngc` | `1` | `1` | `0` | `1` | `0` | `1.0` |
| `Qwen/Qwen2.5-Coder-7B-Instruct|physical_ai_registry|pypi` | `89` | `89` | `67` | `22` | `0` | `0.24719101123595505` |
| `bigcode/starcoder2-7b|package_baseline|hf` | `4` | `1` | `1` | `0` | `3` | `0.0` |
| `bigcode/starcoder2-7b|package_baseline|npm` | `469` | `469` | `327` | `142` | `0` | `0.302771855010661` |
| `bigcode/starcoder2-7b|package_baseline|pypi` | `57` | `57` | `47` | `10` | `0` | `0.17543859649122806` |
| `bigcode/starcoder2-7b|physical_ai_registry|hf` | `31` | `9` | `9` | `0` | `22` | `0.0` |
| `bigcode/starcoder2-7b|physical_ai_registry|ngc` | `1` | `1` | `0` | `1` | `0` | `1.0` |
| `bigcode/starcoder2-7b|physical_ai_registry|pypi` | `11` | `11` | `10` | `1` | `0` | `0.09090909090909091` |
| `deepseek-ai/deepseek-coder-6.7b-instruct|null_control|pypi` | `4` | `4` | `3` | `1` | `0` | `0.25` |
| `deepseek-ai/deepseek-coder-6.7b-instruct|package_baseline|npm` | `94` | `94` | `90` | `4` | `0` | `0.0425531914893617` |
| `deepseek-ai/deepseek-coder-6.7b-instruct|package_baseline|pypi` | `123` | `123` | `100` | `23` | `0` | `0.18699186991869918` |
| `deepseek-ai/deepseek-coder-6.7b-instruct|physical_ai_registry|hf` | `45` | `6` | `6` | `0` | `39` | `0.0` |
| `deepseek-ai/deepseek-coder-6.7b-instruct|physical_ai_registry|pypi` | `10` | `10` | `10` | `0` | `0` | `0.0` |

## Sanitized Repeat Nonexistent Identifiers

Repeat nonexistent identifiers are redacted by hash to avoid publishing slopsquatting targets.

| Registry | Kind | Redacted ID | Count |
|---|---|---|---:|
| `npm` | `package` | `redacted-30094e0bec00` | `23` |
| `npm` | `package` | `redacted-bdf51a6ee6e5` | `23` |
| `npm` | `package` | `redacted-304afc32b7ff` | `23` |
| `npm` | `package` | `redacted-63035fde32ef` | `23` |
| `npm` | `package` | `redacted-16ec2a275b93` | `23` |
| `npm` | `package` | `redacted-b2439bcb8dee` | `23` |
| `pypi` | `package` | `redacted-0ec458a135e6` | `11` |
| `pypi` | `package` | `redacted-46d9dded7c9d` | `7` |
| `pypi` | `package` | `redacted-4d7c51b1efe9` | `3` |
| `pypi` | `package` | `redacted-6201111b83a0` | `3` |
| `pypi` | `package` | `redacted-2b4229e125bf` | `3` |
| `pypi` | `package` | `redacted-fa51fd49abf6` | `2` |
| `pypi` | `package` | `redacted-f83916135509` | `2` |
| `pypi` | `package` | `redacted-10c22bcf4c76` | `2` |
| `npm` | `package` | `redacted-a35ea9e5404e` | `2` |
| `npm` | `package` | `redacted-19ff8761fa64` | `2` |

## Interpretation

A useful PX-056 signal requires two separate facts: the models must emit registry identifiers in realistic physical-AI code, and the verifier must prevent nonexistent identifiers from being treated as install/load-safe. This pilot reports whether that measurement path works with live model outputs. The full preregistered study must still run the complete prompt set and hypothesis tests before PX-056 can be promoted as a positive hallucination-rate result.

## Claim Boundary

Gate 2A is a live-output pilot. It may support feasibility, extractor coverage, and preliminary directional evidence, but it must not be described as the final PX-056 H1-H4 result.

## Private Raw Evidence

Raw generations and unsanitized verification caches were written to `s3://praxis-garypagan-272615233626-us-east-1/experiments/model-registry-hallucination/gate2a-live-pilot-20260721/results/px056-gate2a-live-pilot-20260721-202454/`.
