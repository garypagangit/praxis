# EXP03 VLA Source Gate Result

Generated: 2026-06-19T13:30:07.089222+00:00

Status: **SOURCE GATE PASS - SIMULATOR SMOKE PENDING**

## Primary Metrics

| Metric | Value |
|---|---:|
| Accessible GitHub repositories | `4` |
| Accessible HF models | `5` |
| Accessible HF datasets | `1` |
| Instruction manifest rows | `48` |
| Train-template rows | `32` |
| Heldout-template rows | `16` |
| Mean heldout/base token Jaccard | `0.6264` |

## Publish Checks

| Check | Pass |
|---|---:|
| `accessible_repositories` | `True` |
| `accessible_models` | `True` |
| `accessible_datasets` | `True` |
| `manifest_rows` | `True` |
| `heldout_template_rows` | `True` |

## Resource Notes

| Resource | Status | Detail |
|---|---:|---|
| GitHub `openvla/openvla` | `ACCESSIBLE` | branch `main` pushed `2025-03-23T23:41:01Z` |
| GitHub `moojink/openvla-oft` | `ACCESSIBLE` | branch `main` pushed `2025-09-09T06:25:07Z` |
| GitHub `Lifelong-Robot-Learning/LIBERO` | `ACCESSIBLE` | branch `master` pushed `2025-03-15T12:14:04Z` |
| GitHub `rail-berkeley/bridge_data_robot` | `ACCESSIBLE` | branch `main` pushed `2024-08-27T19:54:39Z` |
| HF model `openvla/openvla-7b` | `ACCESSIBLE` | downloads `1963865` modified `2026-02-17T03:43:23.000Z` |
| HF model `openvla/openvla-7b-finetuned-libero-spatial` | `ACCESSIBLE` | downloads `10343` modified `2024-10-09T04:41:18.000Z` |
| HF model `openvla/openvla-7b-finetuned-libero-10` | `ACCESSIBLE` | downloads `4903` modified `2024-10-09T04:42:43.000Z` |
| HF model `moojink/openvla-7b-oft-finetuned-libero-10` | `ACCESSIBLE` | downloads `3549` modified `2025-06-17T22:33:04.000Z` |
| HF model `moojink/openvla-7b-oft-finetuned-libero-spatial` | `ACCESSIBLE` | downloads `7839` modified `2025-06-17T22:28:54.000Z` |
| HF dataset `lerobot/libero_10` | `ACCESSIBLE` | viewer `True` error `` |
| HF dataset `lerobot/libero_spatial` | `UNAVAILABLE` | viewer `` error `401` |
| HF dataset `lerobot/libero_object` | `UNAVAILABLE` | viewer `` error `401` |
| HF dataset `lerobot/libero_goal` | `UNAVAILABLE` | viewer `` error `401` |
| HF dataset `lerobot/bridge_v2` | `UNAVAILABLE` | viewer `` error `401` |

## Claim Boundary

This is a source/readiness gate, not a VLA performance result. It proves that the core repositories, model checkpoints, and at least one public LIBERO data path are reachable and that held-out instruction templates are frozen before simulator work. The next gate must install LIBERO/OpenVLA-OFT and reproduce one official evaluation smoke.
