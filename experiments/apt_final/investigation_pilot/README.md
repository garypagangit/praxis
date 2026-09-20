# APT investigation: is there room beyond ordinary identity lookup?

This bounded experiment executes the first gate in the [research shortlist](../docs/APT_PIVOT_SHORTLIST_20260920.md). It uses the already qualified public OTRF APT29 day-one recording. It does not train a detector or run an LLM.

## Frozen question and decision

Can ordinary identity-preserving retrieval answer factual process-relationship questions correctly with very little evidence? If it can, these questions do not justify a novel evidence selector.

The [machine-readable protocol](PROTOCOL.json) is committed before case preparation and outcome scoring. The recording and aggregate schema statistics were already inspected; this is a prospective method comparison on exposed development data, not a preregistered blind trial.

Select 60 source-grounded questions by a fixed hash: 20 random parent-creation lookups, 20 random network-owner creation lookups, and 20 distinct parent lookups enriched for repeated program names. All questions require a recorded creation event, image and UTC creation time. A parent GUID in another event does not supply a missing creation timestamp. Unavailable or contradictory source evidence must be reported explicitly.

Compare name/nearest-time lookup, name/time lookup with abstention, exact host/GUID lookup, and the same exact lookup with compact serialized identifiers. Exact methods retain all source identifiers and need return only the relevant record. Count index construction, lookup work and alias metadata; never force the strong comparator to return unrelated neighborhoods.

The primary stopping rule is **no room to improve** if a strong baseline recovers every available answer without an unsupported answer and correctly identifies unavailable evidence. Then close this dataset/task's novel-selector proposal before model work. A later, genuinely harder investigation task would require a new protocol. No percentage accuracy on this lookup exercise can be presented as APT detection or LLM performance.

## Reproduction

Source archive and generated source excerpts remain outside Git. Scripts will regenerate the selected question set from the archive with SHA-256 `98a073140860560d70080ace9142961be4f64b4862bae892d62d0f254d0fdbe5`. Committed receipts contain source-reference hashes, individual outcomes and aggregate metrics; the pinned public archive supplies the original evidence.

No cloud resources or external human review are required for this factual retrieval screen. Later claims about attack intent, explanation quality or analyst time would require an independently reviewed task and evaluation.
