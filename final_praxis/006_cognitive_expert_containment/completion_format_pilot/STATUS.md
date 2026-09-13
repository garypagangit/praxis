# Completion-format pilot: running

Run `fp006-format-811d7cc4a6` launched on AWS under preregistration commit `811d7cc4a60d610fd7e5c0a4b3a3f2fbf9a6b140`. Supervisor heartbeat verified at **13 September 2026, 00:46 UTC** (12 September, 8:46 p.m. Eastern), with zero initial synchronization errors. A later independent check at **00:52 UTC / 8:52 p.m. Eastern** validated **2/64 response cells**, with zero integrity errors, all **12 numerical probes passing**, and zero synchronization errors. The scientific result remains pending. [LIVE_CHECK.json](LIVE_CHECK.json) records that snapshot.

The fixed study has **32 unused GSM8K TRAIN questions, raw/chat paired intact generations, 64 cells total**. The source-backed chat wrapper is the only candidate; raw is diagnostic. Chat must have <=3 capped responses, >=29 numeric extractions and >=8 nontruncated flexible-correct responses, with all technical/integrity gates passing. The 1,024-token cap is unchanged. [PREREGISTRATION.md](PREREGISTRATION.md) freezes the literature, RQ, hypotheses, data, thresholds and stop rules.

All 28 offline checks passed. Public-data selection and all prompt/token identities reconstructed exactly. Both study arms use the intact model; numerical probes also test ablations. No held-out test inference or automatic subsequent study is part of this pilot.

The conservative incremental cap is **$15**, with a **two-hour external stop at 02:45:28 UTC / 10:45:28 p.m. Eastern**, supervised early shutdown, S3 synchronization and an active local result collector. [STARTUP.json](STARTUP.json) records launch identities and bounds. The collector will independently audit a stable terminal snapshot and publish its derived positive, negative or incomplete review to `completed/` when connectivity permits.

The predecessor [FP32 qualification](../logic_qualification_fp32/completed/RESULTS.md) remains a formal failure despite useful logic contribution. A passing pilot only permits a separately frozen fresh-test qualification. No containment efficacy, novelty or primary Praxis selection is claimed.
