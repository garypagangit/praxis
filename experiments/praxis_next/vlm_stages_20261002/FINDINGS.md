# PX-099 — Visual Reconstruction of APT Stages and Transitions

## Work completed

- Registered the separate experiment and its hypotheses.
- Built two label-free traffic timeline pages with matched numeric representations.
- Verified native source labels for all 208,094 existing test flows; see [label qualification](LABEL_QUALIFICATION.md).
- Established that reconnaissance has zero support in this test portion, and movement has only 35 flows.

## What the pilot can establish

The first AWS smoke run is complete:

| Input | Outcome |
|---|---|
| Timeline image 1 | Reply generated; wrong output schema; raw interval list covers only H0 of eight hosts. |
| Timeline image 2 | Reply generated; wrong output schema; raw interval list covers only H0 of eight hosts. |
| Matched text 1 | 29,758 input tokens; skipped under the frozen 8,192-token cap. |
| Matched text 2 | 30,365 input tokens; skipped under the same cap. |

No usable stage-accuracy or transition result was produced. The model's stage names and reasons are unverified assertions, not reconstructed ground truth. The image replies took 15.95 and 12.73 seconds; they used 1,104 input tokens each. This is an input-size observation, not an accuracy comparison.

The first pages cover eight hosts and twelve hours per capture. A successful response would show that the model can consume these inputs and produce valid host/time intervals. It would not establish correct stage reconstruction, whole-campaign coverage, transition accuracy or transfer.

The existing coarse labels merge foothold and cover-up. Source labels can recover those distinctions, but native host-time label sets and transition scoring must be frozen before a full-stage efficacy test.

## Interpretation

This is a higher-effort candidate than PX-098. Its main obstacle is evaluation: defining supported stage sets, handling simultaneous stages and source-label uncertainty, and scoring transitions without forcing a clean kill-chain story onto the data. Full timelines are retrospective; they cannot substantiate early detection.

Next: use smaller, fully covered pages and an explicit constrained output schema, then freeze host/time and native-stage scoring. Keep matched text within the same model's resource budget without discarding information. Do not scale up campaign inference until this feasibility gate passes.

[Smoke results](RESULTS.json) | [Raw replies](RESPONSES.jsonl)

[Protocol](PROTOCOL.md) | [Shared literature check](../vlm_gate_20261002/LITERATURE_CHECK.md)
