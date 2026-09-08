# Final Praxis 001 reproduction and execution

Run from repository root. The protocol and physical input hashes are validated on every launch. Preserve file bytes when transferring between Windows and Linux; do not silently normalize a frozen file's line endings. Real CUDA model inference is mandatory; tests and fixtures are separate infrastructure evidence.

The active protocol is version 2 (audit-binding amendment). Use distinct v2 run directories, such as `pilot_20260908_v2` and `discovery_20260908_v2`; the examples below are command shapes, with exact current run IDs controlled by the root orchestration. The first version and all frozen inputs are preserved under `history/protocol_v1_20260908/`. Earlier v1 pilot outputs are historical infrastructure evidence only.

```text
python -m unittest final_praxis.001_outcome_state_verification.harness.test_scientific -v
python -m final_praxis.001_outcome_state_verification.harness.run_scientific --dry-run --stage pilot
python -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage pilot --phase agent --run-dir final_praxis/001_outcome_state_verification/runs/pilot_20260908 --endpoint http://127.0.0.1:8765
python -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage pilot --phase judge --run-dir final_praxis/001_outcome_state_verification/runs/pilot_20260908 --endpoint http://127.0.0.1:8766
python -m final_praxis.001_outcome_state_verification.harness.verify_scientific final_praxis/001_outcome_state_verification/runs/pilot_20260908
python -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage discovery --phase agent --run-dir final_praxis/001_outcome_state_verification/runs/discovery_20260908 --endpoint http://127.0.0.1:8765
python -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage discovery --phase judge --run-dir final_praxis/001_outcome_state_verification/runs/discovery_20260908 --endpoint http://127.0.0.1:8766
python -m final_praxis.001_outcome_state_verification.harness.verify_scientific final_praxis/001_outcome_state_verification/runs/discovery_20260908
```

Endpoint 8765 must serve the frozen Qwen revision; endpoint 8766 must serve the frozen Mistral revision. Serial loading can use the same endpoint with the correct model loaded for each phase. `--endpoint` omitted loads the corresponding pinned model directly with the shared Transformers adapter. The root orchestration controls AWS resources and exact run IDs.

Records are written with exclusive-create mode. An interrupted unfinished phase can resume only missing records under the same manifest. A completed run rejects further execution. Independent verification on an already sealed run uses `--read-only` to avoid replacing evidence. The selected full-state judge diagnostic is part of the judge phase and is required before sealing.

Report sources are raw files under `runs/<id>/raw/{actions,agent,judge,full_state_judge}/`, the manifest, and independently generated `INDEPENDENT_VERIFICATION.json` / `FINAL_DETERMINATION.md`. `PILOT_PASS.json` certifies a verified infrastructure pilot only, not a hypothesis result.
