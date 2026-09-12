# Logic qualification: running

Updated12 September2026,20:11 UTC. The AWS detached job has started successfully and is preparing its GPU environment. No qualification result is available yet.

- Branch: `Final-Praxis-006-Cognitive-Expert-Containment`.
- Frozen experiment commit: `5075fe39d3f91ca378d052c4622c90171b20844d`.
- Run: `fp006-logic-5075fe39d3`; SSM deployment succeeded.
- Protocol SHA256: `1339e5e95de3dea8ceb14020ba0ff61b8cc744837da712ecde1656366d9ed94f`.
- Planned cohort:256 test questions x3 conditions, plus16 training questions x3 technical-pilot conditions;816 generations total.
- All17 local audit tests passed; pinned source/tokenizer and data checks passed. GPU numerical qualification remains pending.
- AWS supervisor/S3 synchronization is active. The host watchdog stops by13 September2026,04:09:58 UTC (12:09:58 a.m. Eastern), with earlier shutdown on completion or failure.
- Job cap:$75; eight-hour g5.xlarge compute bound approximately$8.05, excluding storage and other charges.

Private live artifacts: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp006-logic-5075fe39d3/`. `cloud_status.json` records lifecycle; `outputs/audit/RESULTS.md` will contain the automatic decision. Local connectivity is not required for the cloud supervisor, saved cells, audit or stop watchdog.

Use the read-only collector to wait for completion, download final evidence and independently recompute the audit:

```text
python collect.py --run-id fp006-logic-5075fe39d3 --out /private/path/collected --wait
```

The decision concerns only whether a useful logic capability is present. A novel containment method would require its own subsequent hypothesis and experiment. Existing failed option006 methods remain recorded.
