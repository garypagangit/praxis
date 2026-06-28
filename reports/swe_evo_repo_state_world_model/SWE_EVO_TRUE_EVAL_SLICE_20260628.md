# PX-033 SWE-EVO True Evaluation Slice

Generated: 2026-06-28T21:58:49.797916+00:00

Status: **TRUE EVAL PASS**

## Claim Boundary

One released-prediction SWE-EVO execution slice. This is not a full benchmark sweep or a trained repo-state world model.

## Metrics

| Metric | Value |
|---|---:|
| Instance | `psf__requests_v2.9.0_v2.9.1` |
| Model patch source | `glm-4p5` |
| Test patch applied | `True` |
| Model patch applied | `True` |
| Gold patch applied | `True` |
| Base return code | `1` |
| Model return code | `0` |
| Gold return code | `0` |
| File overlap | `3` |
| Wall seconds | `5.8` |

## Interpretation

A PASS means the released model patch turns a failing targeted test slice into a passing slice while the gold patch also passes. A FAIL means the next PX-033 step should inspect the patch/test logs before spending on agent generation.
