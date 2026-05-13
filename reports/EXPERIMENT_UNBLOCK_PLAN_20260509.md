# Experiment Unblock Plan

Date: 2026-05-09

## Priority 1 - Keep TTA Moving

TTA is the current Praxis lead. The next work should lock the result:

1. leakage audit on the held-out source-file split,
2. frozen-vs-adapted ablation,
3. override-rate sensitivity,
4. AWS/local artifact comparison,
5. Praxis 06 candidate report.

## Priority 2 - Mirror One Real Provenance Subset

The biggest shared blocker is missing full DARPA TC / OpTC event data in S3. Current S3 has metadata repos only for DARPA TC and OpTC, while graph SSL, TGN, concept drift, stage routing on graphs, causal GNN, and SAE follow-up all need typed event/provenance data.

Recommended first pull:

| Target | Why first | Experiments unblocked |
|---|---|---|
| DARPA TC E5 `cadets` | Most directly aligned with MAGIC/Kairos-style provenance graph work and existing Praxis 05 notes. Smaller than broad E5 mirror. | SAE-for-APT, graph SSL, TGN, stage routing on provenance graphs, concept drift, causal GNN |
| OpTC `ecar` subset | Best cross-dataset enterprise telemetry candidate for drift and streaming validation. | TTA replication, concept drift, graph SSL/TGN if usable edges are available |

Do not mirror the full DARPA TC E5 or full OpTC release first. Start with a performer/partition, write a manifest, then expand only if the parser gate passes.

## Priority 3 - Build Missing Implementation Scaffolds

| Experiment | Current blocker | Practical unblock |
|---|---|---|
| SEC-LoRD / DS-LoRD | Data ready, no runnable extraction scaffold | Build small CTIBench/AnnoCTR adapter and vanilla-vs-domain-seeded query generator. |
| AI Supply Chain | PoisonBench ready, no training provenance | Run a small clean-vs-poisoned LoRA job and log per-step gradient/update diagnostics. |
| APT Detector Watermarking | Detector data ready, no watermark protocol | Generate trigger set, train watermarked detector, then query-extract surrogate. |
| MIA | Positive RF smoke, no shadow protocol | Add shadow models and distribution-matched nonmember controls. |
| Graph SSL / TGN / Causal GNN | Need typed provenance edges | Mirror DARPA E5 Cadets or OpTC ecar first. |

## Priority 4 - External Or Hard-to-Automate Blockers

| Item | Status | Action |
|---|---|---|
| NVD API key | Optional | Useful for larger historical syncs, not blocking current pilots. |
| SOC analyst collaboration | External | Needed only for XAI analyst-in-the-loop. |
| Honeypot simulator | Custom design | Needed only for Reverse TTP Extraction; keep shelved. |

## Recommended Execution Order

1. Run TTA robustness/leakage checks.
2. Start a cloud-side DARPA TC E5 Cadets targeted mirror/inventory.
3. Build SEC-LoRD minimal CTI adapter while the mirror runs.
4. If GPU quota becomes available, run AI Supply Chain LoRA provenance smoke.
5. Return to graph SSL/TGN once the Cadets parser gate passes.
