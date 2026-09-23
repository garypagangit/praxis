# Bounded AWS acquisition and qualification of the small ProvICS subset

September 23, 2026. This operation acquires and qualifies source files; it performs **zero model fits** and does not convert incomplete acquisition into experimental success.

## Payload

Run the committed `data_qualification/acquire_provics.py` on the public README, two physical-state CSVs, and four annotation CSVs. Resolve the author's Hugging Face metadata once to a 40-hex commit, record it, and request all seven files at that immutable revision. Never mix floating `main` downloads in the cloud bundle. Three connections maximum; each file is capped at 100 MB. No PCAP, massive provenance graph, credentials, HF token, or source execution artifact is needed. Keep source bytes and event linkage in the existing private AWS bucket and private local data directory. Public Git contains only code, aggregate qualification reports, and sanitized receipts.

The existing local attempts failed before obtaining bytes. AWS uses an independent ordinary network path; no authentication challenge is solved or bypassed. The gate remains closed unless signal bytes are actually downloaded, hash-bound, parsed, and subsequently qualified. The code intentionally does not automatically certify successful attack outcomes.

## Compute plan

Reuse the existing designated `g5.xlarge` only after authenticated inventory verifies its identity, stopped state, expected account, and stop-on-guest-shutdown behavior. The acquisition itself runs on CPU. GPU hardware is not used merely because it is present, and no GPU speedup claim is made. A later TabM fit requires its own frozen payload and scientific comparison.

The existing `experiments/apt_final/native_graph/cloud_control.py` provides a pre-start EventBridge stop watchdog and one-shot execution control. The scoped `provics_cloud_control.py` wrapper preserves those checks with an explicitly tighter 45-minute outer ceiling, a stop request scheduled at 40 minutes, and a 30-minute worker/publication deadline. Use a new private attempt directory and unique S3 prefix. The acquisition command targets at most 900 seconds after submission, with publication reserved and root-controlled immediate stop afterward. The fallback watchdog is an outer bound, not intended runtime. The reserve is $2 including a $0.75 incidental allowance; it is an estimate rather than a billing receipt.

## Execution and collection

1. Bind the protocol, downloader, worker shell, and bundle builder hashes before launch. Root commits/reviews the executable payload and generated freeze.
2. Upload the checked bundle to the unique private prefix. The existing controller verifies the account, stopped instance and scheduled stop before starting.
3. Wait for SSM Online within the existing bounded readiness window. Send the worker through `AWS-RunShellScript` with an explicit timeout and absolute publication deadline.
4. Worker checks the archive and each file hash, uses an existing Python with pandas/requests if available, and records package/runtime versions. No package installation is required by this worker; unavailable prerequisites produce a published failure receipt.
5. Download public files normally, qualify actual bytes, and publish the source subset plus reports as a checksummed private result archive. A complete worker run can still report `acquisition_incomplete`.
6. Root requests stop in its unconditional cleanup path and verifies stopped state before deleting only this attempt's watchdog. Collect and verify the result archive; do not extract links, traversal paths, or oversized content.

## Decisions after collection

- No signals: retain acquisition failure, do not fit substitutes labeled as new data.
- Signals acquired: inspect clocks, dimensions, missingness, explicit skipped/failed annotations and event coverage before defining a new study. A physical-only subset is an ICS signal development resource, not validated movement/exfiltration telemetry.
- All identity, shutdown and result checks are factual receipts. Do not claim AWS ran, the host stopped, or data were obtained before those actions are observed.
