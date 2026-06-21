# EXP03 LIBERO Data and Simulator Gate Result

Generated: 2026-06-21T11:07:20.529300+00:00

Status: **FINAL STOP/REFRAME - PUBLIC DATA LACKS LANGUAGE AND SIMULATOR SUPPORT**

## Scope

- Public dataset: `lerobot/libero_10`.
- Gate purpose: determine whether EXP03 can fairly advance from source readiness to official VLA instruction-diversity evaluation.
- No robot policy inference, model training, or raw video export was performed.

## Primary Metrics

| Metric | Value |
|---|---:|
| Public frames | `101469` |
| Public episodes | `379` |
| Public task indices | `10` |
| Sample parquet rows inspected | `843` |
| Data columns | `observation.state, action, timestamp, frame_index, episode_index, index, task_index` |
| Task metadata columns | `task_index` |
| Language columns in data | `NONE` |
| Task text columns in metadata | `NONE` |

## Import Checks

| Package | Available |
|---|---:|
| `libero` | `False` |
| `robosuite` | `False` |
| `torch` | `False` |
| `transformers` | `False` |
| `gymnasium` | `False` |

## Publish Checks

| Check | Pass |
|---|---:|
| `public_libero_data_accessible` | `True` |
| `task_text_metadata_present` | `False` |
| `language_columns_present` | `False` |
| `simulator_imports_available` | `False` |
| `official_eval_ready` | `False` |

## Final Determination

EXP03 is **not publishable as an instruction-diversity VLA result in the current cycle**. The public LIBERO data path is real and large enough for data-loader work, but the available `lerobot/libero_10` schema exposes only numeric `task_index` values and state/action/video references. It does not expose natural-language task instructions or trajectory-level language annotations, and the local official simulator/model stack imports are absent.

The defensible decision is to stop or reframe EXP03 as a data-readiness artifact unless a complete LIBERO/OpenVLA-OFT evaluation environment and instruction metadata are added later.
