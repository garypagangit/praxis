# CTI Attribution Label Sufficiency Gate

Generated: 2026-05-10

## Decision

| Experiment | Gate result | Rationale |
|---|---|---|
| GNN Attribution - TTP Graph Embeddings | DATA READY | ATT&CK has enough intrusion-set to technique edges for a graph embedding pilot. |
| Few-Shot APT Group Attribution | PARTIAL DATA READY | ATT&CK supports held-out group few-shot simulation, but APTNotes lacks explicit group labels for document attribution. |
| LLM Threat Intelligence Fusion | BLOCKED | Local NVD/APTNotes/AnnoCTR sources support retrieval and extraction, but not early-warning success/failure outcomes. |

## MITRE ATT&CK Enterprise Graph

| Metric | Value |
|---|---:|
| Intrusion-set groups | 174 |
| Techniques / subtechniques | 697 |
| Group uses technique edges | 4546 |
| Groups with >= 1 technique | 170 |
| Groups with >= 3 techniques | 160 |
| Groups with >= 5 techniques | 151 |
| Groups with >= 10 techniques | 121 |
| Techniques used by >= 1 group | 492 |
| Techniques used by >= 3 groups | 302 |

Top groups by ATT&CK technique support:

| Group | ATT&CK ID | Technique count |
|---|---:|---:|
| Kimsuky | G0094 | 130 |
| APT28 | G0007 | 93 |
| Lazarus Group | G0032 | 93 |
| Mustang Panda | G0129 | 85 |
| APT41 | G0096 | 82 |
| Volt Typhoon | G1017 | 81 |
| Sandworm Team | G0034 | 79 |
| Magic Hound | G0059 | 78 |
| APT32 | G0050 | 78 |
| OilRig | G0049 | 76 |

## AnnoCTR MITRE Linking Labels

| Metric | Value |
|---|---:|
| Labeled mention rows | 6961 |
| Documents | 117 |
| Unique label titles | 389 |
| Unique label links | 395 |

| Split | Rows | Documents | Unique labels | Entity types |
|---|---:|---:|---:|---|
| train | 4153 | 67 | 306 | {'TECHNIQUE': 1947, 'MALWARE': 1034, 'TACTIC': 608, 'GROUP': 404, 'TOOL': 134, 'CON': 26} |
| dev | 890 | 16 | 120 | {'GROUP': 99, 'TECHNIQUE': 451, 'TACTIC': 95, 'MALWARE': 214, 'TOOL': 31} |
| test | 1918 | 34 | 187 | {'MALWARE': 421, 'TACTIC': 255, 'TECHNIQUE': 977, 'TOOL': 52, 'GROUP': 213} |

Top AnnoCTR MITRE labels:

| Label | Mentions |
|---|---:|
| Command and Control | 562 |
| Phishing | 455 |
| Command and Scripting Interpreter | 423 |
| Data Encrypted for Impact | 359 |
| Ingress Tool Transfer | 175 |
| Obfuscated Files or Information | 135 |
| Deobfuscate/Decode Files or Information | 121 |
| Cobalt Strike | 117 |
| TrickBot | 103 |
| Emotet | 102 |
| Application Layer Protocol | 92 |
| Credential Access | 80 |
| Ares | 79 |
| Bazar | 77 |
| Exfiltration | 66 |

## APTNotes Timeline

| Metric | Value |
|---|---:|
| Report rows | 317 |
| Year span | 2008 to 2016 |
| Has explicit actor/group column | False |

## Stop Conditions

- TTP graph embeddings can proceed because ATT&CK has enough group-technique supervision.
- Few-shot group attribution can proceed only as an ATT&CK TTP-set simulation until report-to-group labels are added or derived.
- LLM threat-intelligence fusion remains blocked for publishable early-warning claims because the local sources expose timelines and CTI labels, not success/failure outcome labels.
