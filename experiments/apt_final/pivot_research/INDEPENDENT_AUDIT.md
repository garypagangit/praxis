# Independent review of the public APT29 artifact qualification

Reviewed September 20, 2026. **Outcome: the corrected qualification counts agree with an independent archive recount. This establishes data feasibility, not model effectiveness.**

## Evidence and scope

The reviewer read [qualify_otrf.py](qualify_otrf.py), inspected the [final qualification receipt](OTRF_APT29_DAY1_QUALIFICATION.json), and independently streamed the pinned ZIP's JSON records without invoking the qualifier. The checks covered the archive SHA-256, member count and size, process identities, Windows basenames, full paths, minute groups, and recorded parent joins. The independent implementation parsed GUIDs with `uuid.UUID` and formed minute groups from parsed timestamps rather than the qualifier's string slicing.

The archive contains one JSON member, 385,334,029 expanded bytes and **196,081 records**. Its SHA-256 agrees with the qualification receipt. No archive extraction, payload execution, model training, inference or cloud work occurred during this review.

## Schema issue surfaced and resolved

The initial flattened-field recount confirmed **446 process identities, 327 parent joins and 119 unmatched parent creations**. However, one additional valid Sysmon process-create event retained its process fields inside `Message`, rather than top-level JSON fields. Ignoring that record understated recoverable identity coverage.

A separate strict parser recovered seven uniquely named fields from that record. The corrected qualifier now checks the Sysmon source and `Process Create:` header, rejects duplicate or missing required fields, validates GUIDs and time, and reconciles overlapping identity fields. It handles event-header `ProcessId` separately because that value is not the created process's identifier. The receipt retains flattened-field presence counts and explicitly records the single fallback.

| Final quantity | Independently confirmed |
|---|---:|
| Sysmon process-create records / unique host-plus-process-GUID identities | 447 / 447 |
| GUIDs present as flattened fields / recovered from Message | 446 / 1 |
| Same-host basename groups | 141 |
| Same-host basename groups containing multiple process GUIDs | 61 |
| Those groups containing multiple full paths | 1 |
| Same-host basename-and-minute groups containing multiple GUIDs | 55 |
| Creation records with a recorded parent creation / without one | 329 / 118 |
| Duplicate creation identities | 0 |

The fallback resolves both its own parent and one previously unmatched child's parent, explaining the increase from 327 to 329 joins. Collision-group counts remain unchanged. No remaining discrepancy was identified in these bounded checks.

## Scientific interpretation

These are **structural properties of one exposed APT29 emulation recording across four hosts**. They are not counts of independent campaigns, measured LLM mistakes, or evidence that a proposed checker improves investigation. A same-name or same-minute group need not be ambiguous once a real question includes exact timestamps, UUIDs or other context. The single multiple-path group gives limited support for a path-confusion-specific study.

Exact host/GUID joins already recover 329 recorded parent relations and are a mandatory baseline. The 118 unmatched parent creations do not establish corrupted logs or malicious behavior; the relevant creation may lie outside this capture. Attack-event labels, complete attack-story answers and causal ground truth were not qualified. A later effectiveness study requires a separately frozen task, scoring endpoint and fair controls.

## Reviewed byte identities

- Archive SHA-256: `98a073140860560d70080ace9142961be4f64b4862bae892d62d0f254d0fdbe5`.
- Qualifier SHA-256: `cc3703b8109a5ad932c1cddf3359b06d6743c1efc32383f22fdf9b66a2186110`.
- Final qualification receipt SHA-256: `1b30e1b66a6ea3a0ca57a7f80b208b7ec33f3215b22c8f2bd8ad8b2271f597cf`.

This review is independent of the qualifier's counting implementation, but uses the same public source recording. It is not an independent-dataset replication or a general security audit of the parser.
