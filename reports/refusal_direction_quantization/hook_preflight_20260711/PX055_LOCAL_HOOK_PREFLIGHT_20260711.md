# PX-055 Local Hook-Gate Preflight

Generated: 2026-07-12T03:23:22.473055+00:00

## Status

**LOCAL_PREFLIGHT_BLOCKED**

This local Windows session is not suitable for the quantized activation hook gate. The result is an environment check only, not a PX-055 model result.

## Environment

| Item | Value |
|---|---|
| Python | `3.11.9` |
| Platform | `Windows-10-10.0.26200-SP0` |
| Torch present | `False` |
| Transformers present | `False` |
| bitsandbytes present | `False` |
| nvidia-smi return code | `missing` |

## Decision

Run the hook-feasibility gate on a CUDA GPU environment. The next executable step is the cloud job under `cloud_jobs/px055_quantization_hook_gate_20260711/`.
