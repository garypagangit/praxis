# Reproducing Final Praxis 002

Run commands from repository root with Python 3.11+, NumPy and the shared real-model HTTP adapter available. Fixture construction uses the standard library. Scientific execution requires the exact frozen Qwen revision, BF16, no quantization. All workloads are inert and write only experiment artifacts.

```powershell
python -m final_praxis.002_cascade_containment.harness.scenario_registry
python -m final_praxis.002_cascade_containment.harness.generate_fixtures
python -m final_praxis.002_cascade_containment.harness.validate_fixtures
```

The checked-in `FROZEN_PROTOCOL.json` binds code, config, scenarios and fixtures. Do not refreeze it after model results. The creation command is `python -m final_praxis.002_cascade_containment.harness.freeze_protocol`; it refuses an existing freeze. Before any live run the runner validates the existing frozen files.

With the shared model server listening on the chosen endpoint:

```powershell
python -m final_praxis.002_cascade_containment.harness.run_workflow --mode pilot --output final_praxis/002_cascade_containment/runs/pilot-v1 --base-url http://127.0.0.1:8765
python -m final_praxis.002_cascade_containment.harness.independent_verify final_praxis/002_cascade_containment/runs/pilot-v1
python -m final_praxis.002_cascade_containment.harness.run_workflow --mode discovery --output final_praxis/002_cascade_containment/runs/discovery-v1 --base-url http://127.0.0.1:8765 --pilot-dir final_praxis/002_cascade_containment/runs/pilot-v1
python -m final_praxis.002_cascade_containment.harness.independent_verify final_praxis/002_cascade_containment/runs/discovery-v1
python -m final_praxis.002_cascade_containment.harness.analyze_cascade final_praxis/002_cascade_containment/runs/discovery-v1
```

An interrupted run may use the identical command with `--resume`. Complete records are retained; incomplete raw attempts are preserved and the frozen infrastructure retry budget still applies. Never delete failed runs to make the denominator appear complete. No fixture model is available as a scientific runner fallback.

Raw stage records include prompts, unmodified model text, parsed and injected handoffs, model identities, token counts, lineage hashes, gate decisions and timing. `verification/audit.json` contains independent recomputation; `results.json` and `FINAL_DETERMINATION.md` contain the frozen decision. The scientific outcome is not inferred from fixture PASS.

After building the discovery report, run `python -m final_praxis.002_cascade_containment.paper.finalize_report` to restore the presentation refinements and explicitly labeled post hoc paired-attribution context. This changes no frozen source, raw result or decision threshold. It also creates a fully padded standalone GMR image while retaining its Mermaid source. The DOCX/PDF command is `python scripts/build_final_praxis_docx.py --experiment 002 --render`; final page images must be inspected after rendering.
