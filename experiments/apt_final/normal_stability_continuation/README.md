# Finish the same experiment after a worker time limit

This is a runtime continuation for [normal stability](../normal_stability/README.md). It preserves every scientific setting and candidate. It saves work by reusing only completed encoder training and normal graph representations from that same registered experiment.

Every reference bank, calibration score, normal-validation result, and attack result is recomputed by the unchanged original runner. Cases lacking a completion manifest train normally. A present but invalid completion manifest aborts preparation; corrupt completed evidence is never silently replaced. Earlier scores do not choose what is reused.

## Required preparation

1. Collect and verify the interrupted attempt; retain its original archive, receipts, and output directory. Confirm the host stopped. An interruption is incomplete evidence, not a scientific failure.
2. Use `checkpoints.prepare_reuse` to create a new private staging directory from the collected outputs, with the original config, data, registration, original result archive, and its verified transport checksum. Each selected file and source receipt must match its archive member. `REUSE_MANIFEST.json` identifies eligible checkpoint sets and records incomplete cases. It must not contain old bank or attack files.
3. Commit the continuation modules, [config.json](config.json), and [PROTOCOL.md](PROTOCOL.md). The original normal-stability files and registration remain unchanged.
4. Register the exact reuse tree, then commit that continuation registration before launch. The controller requires committed protocol and registration bytes.

Example preparation from the repository root, using the collected original attempt:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m experiments.apt_final.normal_stability_continuation.checkpoints --prior-output C:/w/apt_stability_20260920/cloud_attempt1/collected/outputs --staging-dir C:/w/apt_stability_20260920/reuse_attempt1 --config experiments/apt_final/normal_stability/config.json --data-dir C:/w/apt_native_graph_20260920/data --original-registration experiments/apt_final/normal_stability/REGISTRATION.json --transport-archive C:/w/apt_stability_20260920/cloud_attempt1/result.tar.gz --transport-receipt C:/w/apt_stability_20260920/cloud_attempt1/result.sha256
```

Then register after committing the source:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m experiments.apt_final.normal_stability_continuation.provenance register --data-dir C:/w/apt_native_graph_20260920/data --original-registration experiments/apt_final/normal_stability/REGISTRATION.json --reuse-dir C:/w/apt_stability_20260920/reuse_attempt1 --registration experiments/apt_final/normal_stability_continuation/REGISTRATION.json
```

Create a new private cloud attempt directory and settings file. Preserve the approved host, account, bucket, profile, stop role, and price fields; use a distinct S3 prefix such as `apt-normal-stability-continuation-20260920/<unique-attempt>/`. Do not copy old execution receipts into that directory.

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m experiments.apt_final.normal_stability_continuation.launch --settings C:/w/apt_stability_20260920/cloud_attempt2/settings.json --data-dir C:/w/apt_native_graph_20260920/data --original-registration experiments/apt_final/normal_stability/REGISTRATION.json --reuse-dir C:/w/apt_stability_20260920/reuse_attempt1 --registration experiments/apt_final/normal_stability_continuation/REGISTRATION.json
```

The launcher verifies and bundles both source chains, original data, and staged checkpoint files. The worker calls the wrapper once. Input and output archives are limited to 2,000 members and 4 GB. The existing one-hour/$10 controller and independent shutdown protection remain active.

## Evidence and closure

The continuation's registration and runtime receipt explain the added mechanism; original science artifacts retain their original source identity. Keep both chains. Confirm the full case inventory, independent audit, and verified shutdown before declaring completion. Report total costs and work across attempts.

The original decision rules still decide detector readiness and repair impact. No new checker, threshold, seed, or architecture is introduced. This continuation does not add independent campaigns or establish novelty.

Run synthetic checks before freezing:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m unittest discover -s tests -p 'test_apt_stability_continuation*.py' -v
```
