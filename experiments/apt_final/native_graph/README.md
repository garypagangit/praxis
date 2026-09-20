# Native graph APT development pilot

This alternative starts from locally available DARPA TC E3 CADETS and THEIA graphs distributed by the MAGIC authors. No Unraveled author reply or manual network-to-host joining is needed for this scope.

## Completed data audit

- 10 graphs, **3,251,001 nodes** and **6,178,085 retained relationships**.
- CADETS evaluation graph: 357,173 nodes, including 12,846 annotated malicious nodes.
- THEIA evaluation graph: 344,767 nodes, including 25,319 annotated malicious nodes.
- Both source archives match their upstream Git blobs.
- The decoder inspects graph serialization without executing pickle constructors; normalized NPZ files preserve original row indices.

The audit permits **static development experiments only**. Training benign status follows the author's filtering assumptions. Unannotated nodes are benchmark negatives, not exhaustively verified benign entities. These prepared graphs lack timestamps and original UUID mappings. The frozen Unraveled E0 HOLD is unchanged.

## Experiment

See the [protocol](PROTOCOL.md) and [configuration](config.json). Fit a small graph autoencoder, a non-message-passing autoencoder, and Isolation Forest on three author training graphs. Set alert thresholds on a fourth benign graph. Compare these and a node-type rarity baseline with fixed quality and confidence selectors on the attack-bearing graph, including controlled missing-relationship conditions.

Local relationship counts are recomputed after removal for every arm. Fit and calibrate separately on CADETS and THEIA because their integer type IDs have no verified shared semantics. This is a repeated development procedure, not frozen-model transfer or a new MAGIC reproduction.

## Reproduction

The original archives remain outside Git. Use Python with NumPy for the data adapter; the model also requires PyTorch and scikit-learn. The output captures actual versions. Cloud execution uses the existing CUDA environment without changing its packages.

```powershell
python -m experiments.apt_final.native_graph.data --help
python -m unittest discover -s tests -p "test_apt_native_*.py" -v
python -m experiments.apt_final.native_graph.provenance register --data-dir C:/w/apt_native_graph_20260920/data --registration NEW_REGISTRATION.json
python -m experiments.apt_final.native_graph.pilot --config experiments/apt_final/native_graph/config.json --data-dir C:/w/apt_native_graph_20260920/data --dataset cadets --output NEW_OUTPUT --device cpu --registration NEW_REGISTRATION.json
```

Commit exact code/config/protocol bytes before registration. Any operative change requires a fresh registration and a new run directory. Dataset arrays, per-node outputs, and model weights remain private; Git holds code, aggregate findings, audit receipts and hashes.

## AWS

`launch.py` prepares a hash-bound bundle and uses `cloud_control.py`, a label-only adaptation of the already reviewed CTI controller. Its original operational limits remain: one existing g5.xlarge, one-hour cap, independent automatic stop, $10 reserve, and verified shutdown. A separate private settings directory and S3 prefix keep this attempt separate from earlier jobs. No CTI workload or secret is used.

`run_cloud.sh` verifies the archive hash, validates archive paths, selects an existing CUDA environment, records versions, and executes the bounded worker. The actual models must pass a small CPU/GPU numerical and deterministic repeat check before fitting. Runtime predictions and timings do not by themselves establish production efficiency or generalization.
