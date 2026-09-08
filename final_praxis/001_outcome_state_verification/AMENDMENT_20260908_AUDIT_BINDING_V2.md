# Final Praxis 001: audit binding correction, protocol version 2

Date: 2026-09-08. Timing: the first version's infrastructure pilot had begun, but no discovery run had started. This correction followed a read-only cross-agent code audit. It does not depend on observed model behavior or change any scientific threshold, task, condition allocation, model revision, prompt, token budget, or precision setting.

## Finding and impact

The first independent verifier checked frozen input hashes but read numerical thresholds and model identities from the run manifest without additionally requiring that the manifest's embedded configuration exactly equal the frozen configuration file. A tampered manifest could therefore carry changed decision rules while retaining the original protocol-hash pointer. Its embedded frozen-artifact ledger also lacked an equality check. Normal generation used the frozen configuration, but the independent audit was not sufficiently strict to defend against this artifact alteration.

Version 2 adds exact equality checks for the manifest's full configuration and input-hash ledger, experiment identity and permitted stage. It also independently reconstructs the controlled projection, public receipts, and natural action state; binds archived system/user prompts to the frozen prompt constructors; binds each task response to the matching raw inference request/response lineage; checks attempt limits, actual model/runtime settings and token/provenance metadata; and verifies the full-state diagnostic prompts and complete inference-response denominator. A discovery run additionally requires a pilot marker belonging to the current protocol hash.

## Preservation and new evidence

The original version 1 frozen protocol and every input it named were copied byte-for-byte into `history/protocol_v1_20260908/` before changes. `ARCHIVE_MANIFEST.json` maps each original relative path to its archived copy and SHA-256. The v1 protocol hash was `e6383f87199c0e26862b71fc1cbac2ebf4d0cf07d56d8fcef5c5d816effc8b62`.

Any v1 pilot outputs are retained as historical infrastructure evidence and are not eligible for the v2 discovery denominator or v2 pilot gate. A new 16-case v2 pilot must pass before any 400-case discovery launch. Pilot outputs are never combined across versions.

Four additional focused tests reject changed manifest thresholds/models/stages, altered frozen-input ledgers, inference runtime/prompt tampering, and confirm independent intervention/receipt reconstruction. Eighteen tests now pass, alongside unchanged replay of all 140 legacy fixtures and checks of all 400 controlled-state constructions. The new exact test output is preserved separately from v1 test output.

The original preregistration and first amendment remain unchanged; this file documents a narrower implementation/audit correction. The active `FROZEN_PROTOCOL.json` names version 2 and the superseded v1 hash. It is a pointer to preserved versioned evidence, not a retroactive rewrite of the preregistration.
