# Sandworm feature compatibility

All 73 frozen SCVIC predictor names occur exactly in the author Sandworm CSV. The adapter preserves their order and numeric values. This qualifies a descriptive transfer test; it does not establish identical extractor implementations.

Meanings below paraphrase [author README Table 3, pages 9–11](https://zenodo.org/records/16911636/files/APT_Dataset_Readme.pdf). Microseconds are explicit for Flow Duration. Other time units and bulk units follow CICFlowMeter conventions and are marked as inferred in the [machine-readable record](FEATURE_COMPATIBILITY.json). Counts, bytes and rates use the dimensions stated or implied by their feature definitions. Exact extractor revisions, timeout settings, sentinel handling, packet/header treatment and bulk grouping were not supplied sufficiently to prove equivalence. No target-fitted conversion is applied.

| Source and target column (same spelling/order) | Meaning | Unit convention |
|---|---|---|
| Protocol | Transport/network protocol identifier | integer protocol code |
| Flow Duration | Elapsed flow duration | microseconds |
| Total Fwd Packet | Total packets in forward direction | packets |
| Total Bwd packets | Total packets in backward direction | packets |
| Total Length of Fwd Packet | Sum of packet sizes in forward direction | bytes |
| Total Length of Bwd Packet | Sum of packet sizes in backward direction | bytes |
| Fwd Packet Length Max | Maximum forward packet/segment size | bytes |
| Fwd Packet Length Min | Minimum forward packet/segment size | bytes |
| Fwd Packet Length Mean | Mean forward packet/segment size | bytes |
| Fwd Packet Length Std | Standard deviation forward packet/segment size | bytes |
| Bwd Packet Length Max | Maximum backward packet/segment size | bytes |
| Bwd Packet Length Min | Minimum backward packet/segment size | bytes |
| Bwd Packet Length Mean | Mean backward packet/segment size | bytes |
| Bwd Packet Length Std | Standard deviation backward packet/segment size | bytes |
| Flow Bytes/s | Flow byte rate | bytes/second |
| Flow Packets/s | Flow packet rate | packets/second |
| Flow IAT Mean | Mean inter-arrival interval in bidirectional flow | microseconds |
| Flow IAT Std | Standard deviation inter-arrival interval in bidirectional flow | microseconds |
| Flow IAT Max | Maximum inter-arrival interval in bidirectional flow | microseconds |
| Flow IAT Min | Minimum inter-arrival interval in bidirectional flow | microseconds |
| Fwd IAT Total | Total inter-arrival interval in forward direction | microseconds |
| Fwd IAT Mean | Mean inter-arrival interval in forward direction | microseconds |
| Fwd IAT Std | Standard deviation inter-arrival interval in forward direction | microseconds |
| Fwd IAT Max | Maximum inter-arrival interval in forward direction | microseconds |
| Fwd IAT Min | Minimum inter-arrival interval in forward direction | microseconds |
| Bwd IAT Total | Total inter-arrival interval in backward direction | microseconds |
| Bwd IAT Mean | Mean inter-arrival interval in backward direction | microseconds |
| Bwd IAT Std | Standard deviation inter-arrival interval in backward direction | microseconds |
| Bwd IAT Max | Maximum inter-arrival interval in backward direction | microseconds |
| Bwd IAT Min | Minimum inter-arrival interval in backward direction | microseconds |
| Fwd PSH Flags | Packets with TCP PSH flag in forward direction | count |
| Bwd PSH Flags | Packets with TCP PSH flag in backward direction | count |
| Fwd URG Flags | Packets with TCP URG flag in forward direction | count |
| Bwd URG Flags | Packets with TCP URG flag in backward direction | count |
| Fwd Header Length | Summed forward header size | bytes |
| Bwd Header Length | Summed backward header size | bytes |
| Fwd Packets/s | Forward packet rate | packets/second |
| Bwd Packets/s | Backward packet rate | packets/second |
| Packet Length Min | Minimum packet/segment size | bytes |
| Packet Length Max | Maximum packet/segment size | bytes |
| Packet Length Mean | Mean packet/segment size | bytes |
| Packet Length Std | Standard deviation packet/segment size | bytes |
| Packet Length Variance | Variance packet/segment size | bytes squared |
| FIN Flag Count | Packets with TCP FIN flag | count |
| SYN Flag Count | Packets with TCP SYN flag | count |
| RST Flag Count | Packets with TCP RST flag | count |
| PSH Flag Count | Packets with TCP PSH flag | count |
| ACK Flag Count | Packets with TCP ACK flag | count |
| URG Flag Count | Packets with TCP URG flag | count |
| CWR Flag Count | Packets with TCP CWR flag | count |
| ECE Flag Count | Packets with TCP ECE flag | count |
| Down/Up Ratio | Download-to-upload traffic ratio | dimensionless |
| Average Packet Size | Mean packet/segment size | bytes |
| Fwd Segment Size Avg | Mean forward packet/segment size | bytes |
| Bwd Segment Size Avg | Mean backward packet/segment size | bytes |
| Fwd Bytes/Bulk Avg | Mean forward bulk byte size | bytes/bulk |
| Fwd Packet/Bulk Avg | Mean forward bulk packet count | packets/bulk |
| Fwd Bulk Rate Avg | Mean forward bulk throughput | bytes/second |
| Bwd Bytes/Bulk Avg | Mean backward bulk byte size | bytes/bulk |
| Bwd Packet/Bulk Avg | Mean backward bulk packet count | packets/bulk |
| Bwd Bulk Rate Avg | Mean backward bulk throughput | bytes/second |
| Subflow Fwd Packets | Mean forward packet amount per subflow | packets/subflow |
| Subflow Fwd Bytes | Mean forward byte amount per subflow | bytes/subflow |
| Subflow Bwd Packets | Mean backward packet amount per subflow | packets/subflow |
| Subflow Bwd Bytes | Mean backward byte amount per subflow | bytes/subflow |
| FWD Init Win Bytes | Initial forward TCP window measurement | bytes |
| Bwd Init Win Bytes | Initial backward TCP window measurement | bytes |
| Fwd Act Data Pkts | Forward packets with at least one TCP payload byte | packets |
| Fwd Seg Size Min | Minimum forward packet/segment size | bytes |
| Active Mean | Mean duration of an active interval before idleness | microseconds |
| Active Std | Standard deviation duration of an active interval before idleness | microseconds |
| Active Max | Maximum duration of an active interval before idleness | microseconds |
| Active Min | Minimum duration of an active interval before idleness | microseconds |

The source feature exclusion rule remains frozen: identifiers, IPs, ports, timestamps, labels and all Idle summaries are excluded. Target-only RST direction flags, backward payload/segment fields, ICMP metadata, retransmission counters and Total Connection Flow Time are also excluded. They are not padded into the source model.
