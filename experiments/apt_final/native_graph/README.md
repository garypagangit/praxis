# Native graph APT development pilot

This alternative starts from locally available DARPA TC E3 CADETS and THEIA graphs distributed by the MAGIC authors. No Unraveled author reply or manual network-to-host joining is needed for this scope.

## Current status: completed and stopped

**Follow-up now available:** [Changing the anomaly score while preserving these trained models](../embedding_baseline/results/gpu_scoring_20260920/REPORT.md) recovered useful THEIA detections, while revealing reference/calibration instability and a failed degree checker. The original results below remain unchanged.

The first real GPU pilot completed **both datasets with three seeds**, passed independent saved-evidence verification, and finished with the AWS host stopped. Latest software verification: **50 tests passed**. Read the [full results and decision](results/gpu_pilot_20260920/REPORT.md), [independent audit](results/gpu_pilot_20260920/INDEPENDENT_RESULT_AUDIT.json), and [AWS closeout](results/gpu_pilot_20260920/AWS_CLOSEOUT.json).

**The first detector/checker combination was not useful.** At thresholds fixed using benign calibration, clean-graph GIN recall averaged approximately **0.10% on CADETS** and **0.043% on THEIA**. The fixed quality checker made essentially the same alert decisions. These results concern the tested representation, anomaly score and routing rule; they do not establish that the datasets or all routing approaches fail.

The [completed scoring follow-up](../embedding_baseline/README.md) isolated the effect of benign embedding anomaly scoring while preserving these encoders. A stronger encoder remains a later comparison. The initial [post-hoc diagnostic](results/gpu_pilot_20260920/POSTHOC_DIAGNOSTIC.json) documents extensive reconstruction-score ties and little complementary detection between these original neural decisions. It changes no thresholds or original results.

## Completed data audit

- 10 graphs, **3,251,001 nodes** and **6,178,085 retained relationships**.
- CADETS evaluation graph: 357,173 nodes, including 12,846 annotated malicious nodes.
- THEIA evaluation graph: 344,767 nodes, including 25,319 annotated malicious nodes.
- Both source archives match their upstream Git blobs.
- The decoder inspects graph serialization without executing pickle constructors; normalized NPZ files preserve original row indices.

The audit permits **static development experiments only**. Training benign status follows the author's filtering assumptions. Unannotated nodes are benchmark negatives, not exhaustively verified benign entities. These prepared graphs lack timestamps and original UUID mappings. The frozen Unraveled E0 HOLD is unchanged.

## Experiment

The completed pilot followed the [protocol](PROTOCOL.md) and [configuration](config.json): fit a small graph autoencoder, a non-message-passing autoencoder, and Isolation Forest on three author training graphs; set alert thresholds on a fourth benign graph; then compare these and a node-type rarity baseline with fixed quality and confidence selectors on the attack-bearing graph, including controlled missing-relationship conditions.

Local relationship counts are recomputed after removal for every arm. Fit and calibrate separately on CADETS and THEIA because their integer type IDs have no verified shared semantics. This is a repeated development procedure, not frozen-model transfer or a new MAGIC reproduction.

## Reproduction

The original archives remain outside Git. Use Python with NumPy for the data adapter; the model also requires PyTorch and scikit-learn. The output captures actual versions. Cloud execution inherits existing CUDA PyTorch into an isolated per-run environment and installs the pinned numerical packages there, preserving existing host environments.

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

The completed run passed those live device checks, including deterministic backward qualification. The initial software/data qualification receipt predates GPU execution; current run evidence is under [gpu_pilot_20260920](results/gpu_pilot_20260920/REPORT.md).
