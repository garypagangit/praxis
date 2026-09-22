# Every frozen policy: raw flags, automatic labels and review costs

Mean of three fits on the identical test rows. All 13 arms and all nine policies are retained. Counts can be fractional because they average repeated fits; they are not additional independent events.

Each policy keeps the original current-flow model's movement flag and baseline attack queue, then adds the named arm's exfiltration flag. Both target flags mean unresolved review. An exfiltration flag in an insufficiently supported role group is also unresolved. Automatic exfiltration requires an exfiltration flag, no baseline movement flag and sufficient role support.

Review union = baseline any-attack OR candidate exfiltration. It includes already resolved baseline attack alerts and is therefore a workload queue, not just abstentions. Unsupported and both-flag counts can overlap and must not be added. The union retains baseline alerts by construction; this is not improved model recall.

The role-conditioned tail uses group-specific negative scores where at least 100 non-exfiltration calibration rows exist, otherwise the global threshold. Automatic exfiltration additionally requires at least 20 exfiltration and 100 non-exfiltration calibration rows. Neither support counts nor nominal tails certify safety; movement is absent from calibration.

## All test rows

### Calibration-F1 / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 88.52% | 67.40% | 0.7653 | 0.33 | 300.67 | 0.00 | 2320.00 |
| Prior flow + roles | 88.57% | 67.39% | 0.7654 | 0.33 | 299.33 | 0.00 | 2319.67 |
| Prior flow + flow history | 87.93% | 67.29% | 0.7623 | 4.33 | 314.00 | 0.00 | 2316.00 |
| Prior flow + roles + flow history | 88.21% | 67.26% | 0.7632 | 1.33 | 308.67 | 0.00 | 2315.00 |
| Prior flow + roles + wrong-host flow history | 88.51% | 67.42% | 0.7654 | 0.00 | 301.33 | 0.00 | 2320.67 |
| Prior roles only | 1.16% | 68.01% | 0.0228 | 186874.00 | 12424.00 | 0.00 | 2341.00 |
| Flow + log-volume/timing controls | 87.33% | 67.48% | 0.7613 | 2.33 | 334.67 | 0.00 | 2322.67 |
| Flow/role/history + log-volume/timing controls | 88.20% | 67.25% | 0.7631 | 1.00 | 308.67 | 0.00 | 2314.67 |
| Flow + controls + auth types/outcomes | 86.47% | 67.48% | 0.7580 | 1.67 | 362.00 | 0.00 | 2322.67 |
| Flow/role/history + controls + auth types/outcomes | 87.85% | 67.34% | 0.7624 | 0.67 | 320.00 | 0.00 | 2318.00 |
| Flow/role/history + controls + wrong-host auth | 87.95% | 67.28% | 0.7624 | 0.33 | 317.00 | 0.00 | 2315.67 |
| Log controls + auth only | 3.67% | 100.00% | 0.0708 | 89013.00 | 1299.00 | 1.00 | 3442.00 |
| Log-volume/timing controls only | 3.70% | 100.00% | 0.0713 | 88692.00 | 930.33 | 2.67 | 3442.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 88.52% | 67.40% | 0.7653 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Prior flow + roles | 88.57% | 67.39% | 0.7654 | 0.00 | 0.00 | 0.00 | 14884.33 / 157.33 | 2.00 |
| Prior flow + flow history | 87.93% | 67.29% | 0.7623 | 0.00 | 0.00 | 0.00 | 14889.00 / 157.67 | 6.67 |
| Prior flow + roles + flow history | 88.21% | 67.26% | 0.7632 | 0.00 | 0.00 | 0.00 | 14888.33 / 157.33 | 6.00 |
| Prior flow + roles + wrong-host flow history | 88.51% | 67.42% | 0.7654 | 0.00 | 0.00 | 0.00 | 14883.00 / 157.33 | 0.67 |
| Prior roles only | 1.16% | 68.01% | 0.0228 | 0.00 | 0.00 | 0.00 | 201773.67 / 186984.33 | 186891.33 |
| Flow + log-volume/timing controls | 87.33% | 67.48% | 0.7613 | 0.00 | 0.00 | 0.00 | 14884.33 / 157.33 | 2.00 |
| Flow/role/history + log-volume/timing controls | 88.20% | 67.25% | 0.7631 | 0.00 | 0.00 | 0.00 | 14887.33 / 157.33 | 5.00 |
| Flow + controls + auth types/outcomes | 86.47% | 67.48% | 0.7580 | 0.00 | 0.00 | 0.00 | 14884.33 / 157.33 | 2.00 |
| Flow/role/history + controls + auth types/outcomes | 87.85% | 67.34% | 0.7624 | 0.00 | 0.00 | 0.00 | 14894.00 / 157.33 | 11.67 |
| Flow/role/history + controls + wrong-host auth | 87.95% | 67.28% | 0.7624 | 0.00 | 0.00 | 0.00 | 14894.00 / 157.33 | 11.67 |
| Log controls + auth only | 2.63% | 68.01% | 0.0506 | 2.67 | 4638.00 | 4638.00 | 105049.67 / 89164.33 | 90167.33 |
| Log-volume/timing controls only | 2.65% | 68.01% | 0.0510 | 5.67 | 4641.00 | 4641.00 | 104727.67 / 88842.67 | 89845.33 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 0.10% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 84.61% | 67.53% | 0.7511 | 15.33 | 407.33 | 0.00 | 2324.33 |
| Prior flow + roles | 84.47% | 67.52% | 0.7505 | 13.67 | 414.00 | 0.00 | 2324.00 |
| Prior flow + flow history | 86.44% | 67.36% | 0.7571 | 11.33 | 353.00 | 0.00 | 2318.67 |
| Prior flow + roles + flow history | 86.58% | 67.41% | 0.7580 | 6.33 | 353.67 | 0.00 | 2320.33 |
| Prior flow + roles + wrong-host flow history | 82.62% | 67.54% | 0.7432 | 14.33 | 475.33 | 0.00 | 2324.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 82.65% | 67.55% | 0.7433 | 7.67 | 481.33 | 0.00 | 2325.00 |
| Flow/role/history + log-volume/timing controls | 87.60% | 67.36% | 0.7616 | 2.33 | 326.00 | 0.00 | 2318.67 |
| Flow + controls + auth types/outcomes | 80.80% | 67.54% | 0.7357 | 9.67 | 543.67 | 0.00 | 2324.67 |
| Flow/role/history + controls + auth types/outcomes | 86.59% | 67.48% | 0.7585 | 3.33 | 356.33 | 0.00 | 2322.67 |
| Flow/role/history + controls + wrong-host auth | 87.12% | 67.41% | 0.7601 | 0.33 | 342.67 | 0.00 | 2320.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 650.33 | 375.33 | 0.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 444.00 | 119.33 | 0.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 84.61% | 67.53% | 0.7511 | 0.00 | 0.00 | 0.00 | 14885.33 / 157.67 | 3.00 |
| Prior flow + roles | 84.47% | 67.52% | 0.7505 | 0.00 | 0.00 | 0.00 | 14895.00 / 157.67 | 12.67 |
| Prior flow + flow history | 86.45% | 67.36% | 0.7572 | 0.33 | 0.33 | 0.33 | 14892.33 / 159.00 | 10.00 |
| Prior flow + roles + flow history | 86.57% | 67.36% | 0.7577 | 0.00 | 1.67 | 1.67 | 14893.00 / 158.33 | 10.67 |
| Prior flow + roles + wrong-host flow history | 82.62% | 67.54% | 0.7432 | 0.00 | 0.00 | 0.00 | 14892.33 / 157.67 | 10.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 82.65% | 67.55% | 0.7433 | 0.00 | 0.00 | 0.00 | 14898.67 / 158.67 | 16.33 |
| Flow/role/history + log-volume/timing controls | 87.60% | 67.36% | 0.7616 | 0.00 | 0.00 | 0.00 | 14890.33 / 158.00 | 8.00 |
| Flow + controls + auth types/outcomes | 80.80% | 67.54% | 0.7357 | 0.00 | 0.00 | 0.00 | 14898.67 / 160.67 | 16.33 |
| Flow/role/history + controls + auth types/outcomes | 86.59% | 67.48% | 0.7585 | 0.00 | 0.00 | 0.00 | 14906.00 / 158.33 | 23.67 |
| Flow/role/history + controls + wrong-host auth | 87.12% | 67.41% | 0.7601 | 0.00 | 0.00 | 0.00 | 14902.00 / 157.33 | 19.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.00 | 13.33 | 13.33 | 15530.67 / 805.67 | 648.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 1.33 | 9.00 | 9.00 | 15325.67 / 600.67 | 443.33 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 1.67 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log controls + auth only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 23.67 | 0.67 | 24.33 | 0.00 |

### 0.10% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 76.08% | 78.93% | 0.7699 | 404.00 | 407.33 | 33.00 | 2716.67 |
| Prior flow + roles | 79.62% | 99.38% | 0.8838 | 432.67 | 414.00 | 35.00 | 3420.67 |
| Prior flow + flow history | 82.78% | 71.40% | 0.7664 | 143.33 | 353.00 | 16.33 | 2457.67 |
| Prior flow + roles + flow history | 84.48% | 92.56% | 0.8820 | 207.67 | 353.67 | 21.67 | 3186.00 |
| Prior flow + roles + wrong-host flow history | 77.85% | 99.42% | 0.8728 | 473.00 | 475.33 | 34.33 | 3422.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 76.94% | 89.34% | 0.8226 | 394.67 | 481.33 | 32.00 | 3075.00 |
| Flow/role/history + log-volume/timing controls | 85.75% | 94.14% | 0.8969 | 196.33 | 326.00 | 16.33 | 3240.33 |
| Flow + controls + auth types/outcomes | 76.85% | 79.07% | 0.7759 | 234.67 | 543.67 | 21.33 | 2721.67 |
| Flow/role/history + controls + auth types/outcomes | 82.79% | 92.14% | 0.8710 | 283.67 | 356.33 | 16.33 | 3171.33 |
| Flow/role/history + controls + wrong-host auth | 81.65% | 92.39% | 0.8655 | 354.33 | 342.67 | 18.67 | 3180.00 |
| Log controls + auth only | 48.55% | 31.99% | 0.3855 | 793.33 | 375.33 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 60.54% | 31.99% | 0.4184 | 599.00 | 119.33 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 84.61% | 67.53% | 0.7511 | 133.67 | 814.00 | 814.00 | 15565.67 / 436.00 | 683.33 |
| Prior flow + roles | 84.47% | 67.52% | 0.7505 | 134.67 | 1550.67 | 1550.67 | 16311.00 / 466.33 | 1428.67 |
| Prior flow + flow history | 86.45% | 67.36% | 0.7572 | 93.67 | 287.67 | 287.67 | 15086.33 / 211.33 | 204.00 |
| Prior flow + roles + flow history | 86.57% | 67.36% | 0.7577 | 103.00 | 1090.33 | 1090.33 | 15878.67 / 272.67 | 996.33 |
| Prior flow + roles + wrong-host flow history | 82.62% | 67.54% | 0.7432 | 134.67 | 1590.33 | 1590.33 | 16348.00 / 506.00 | 1465.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 82.65% | 67.55% | 0.7433 | 127.33 | 1169.00 | 1169.00 | 15940.33 / 441.00 | 1058.00 |
| Flow/role/history + log-volume/timing controls | 87.60% | 67.36% | 0.7616 | 91.00 | 1132.00 | 1132.00 | 15931.33 / 273.00 | 1049.00 |
| Flow + controls + auth types/outcomes | 80.80% | 67.54% | 0.7357 | 112.33 | 643.33 | 643.33 | 15429.67 / 288.67 | 547.33 |
| Flow/role/history + controls + auth types/outcomes | 86.59% | 67.48% | 0.7585 | 96.33 | 1145.33 | 1145.33 | 15955.00 / 354.00 | 1072.67 |
| Flow/role/history + controls + wrong-host auth | 87.12% | 67.41% | 0.7601 | 98.33 | 1232.33 | 1232.33 | 16036.00 / 425.67 | 1153.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1258.33 | 1258.33 | 16774.33 / 947.33 | 1892.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1267.00 | 1267.00 | 16577.33 / 751.00 | 1695.00 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 139.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 867.33 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1097.33 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.67 | 32.00 | 33.67 | 750.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 12.33 | 16.33 | 28.67 | 921.67 |
| Flow + controls + auth types/outcomes | 24.33 | 9.00 | 21.33 | 30.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 12.67 | 16.33 | 29.00 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 11.67 | 18.67 | 30.33 | 859.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 0.50% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 74.40% | 67.55% | 0.7078 | 43.00 | 762.33 | 0.00 | 2325.00 |
| Prior flow + roles | 74.08% | 67.55% | 0.7064 | 27.00 | 791.67 | 0.00 | 2325.00 |
| Prior flow + flow history | 74.38% | 67.82% | 0.7094 | 281.67 | 520.00 | 3.33 | 2334.33 |
| Prior flow + roles + flow history | 75.57% | 74.48% | 0.7502 | 275.67 | 544.00 | 8.00 | 2563.67 |
| Prior flow + roles + wrong-host flow history | 73.75% | 67.55% | 0.7051 | 32.00 | 795.67 | 0.00 | 2325.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 71.66% | 67.58% | 0.6955 | 19.33 | 902.67 | 0.00 | 2326.00 |
| Flow/role/history + log-volume/timing controls | 73.88% | 87.45% | 0.7991 | 461.00 | 586.00 | 10.00 | 3010.00 |
| Flow + controls + auth types/outcomes | 69.02% | 67.58% | 0.6829 | 26.67 | 1017.67 | 0.00 | 2326.00 |
| Flow/role/history + controls + auth types/outcomes | 72.68% | 73.10% | 0.7286 | 390.00 | 554.67 | 5.00 | 2516.00 |
| Flow/role/history + controls + wrong-host auth | 74.20% | 85.28% | 0.7919 | 448.33 | 554.67 | 9.67 | 2935.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 1411.00 | 580.33 | 0.67 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 1308.67 | 365.67 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 74.40% | 67.55% | 0.7078 | 0.00 | 0.00 | 0.00 | 14904.33 / 167.00 | 22.00 |
| Prior flow + roles | 74.08% | 67.55% | 0.7064 | 0.00 | 0.00 | 0.00 | 14916.33 / 164.67 | 34.00 |
| Prior flow + flow history | 77.25% | 67.64% | 0.7212 | 44.00 | 125.67 | 125.67 | 15131.00 / 352.33 | 248.67 |
| Prior flow + roles + flow history | 76.39% | 67.74% | 0.7180 | 61.33 | 338.33 | 338.33 | 15340.67 / 333.00 | 458.33 |
| Prior flow + roles + wrong-host flow history | 73.75% | 67.55% | 0.7051 | 0.00 | 0.00 | 0.00 | 14918.00 / 165.33 | 35.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 71.66% | 67.58% | 0.6955 | 0.00 | 0.00 | 0.00 | 14917.33 / 162.00 | 35.00 |
| Flow/role/history + log-volume/timing controls | 73.29% | 67.80% | 0.7043 | 75.33 | 881.67 | 881.67 | 15960.67 / 504.00 | 1078.33 |
| Flow + controls + auth types/outcomes | 69.02% | 67.58% | 0.6829 | 0.00 | 0.00 | 0.00 | 14920.67 / 163.67 | 38.33 |
| Flow/role/history + controls + auth types/outcomes | 75.49% | 67.79% | 0.7143 | 57.33 | 373.67 | 373.67 | 15408.00 / 446.67 | 525.67 |
| Flow/role/history + controls + wrong-host auth | 74.27% | 67.78% | 0.7088 | 79.00 | 806.33 | 806.33 | 15870.33 / 488.00 | 988.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.00 | 20.00 | 20.00 | 16292.00 / 1566.33 | 1409.67 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 4.67 | 26.33 | 26.33 | 16190.00 / 1463.67 | 1307.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 21.00 | 3.33 | 24.33 | 6.33 |
| Prior flow + roles + flow history | 24.33 | 17.00 | 8.00 | 25.00 | 232.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 16.33 | 10.00 | 26.33 | 676.33 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 20.67 | 5.00 | 25.67 | 182.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 16.33 | 9.67 | 26.00 | 602.33 |
| Log controls + auth only | 24.33 | 24.33 | 0.67 | 25.00 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 0.50% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 68.11% | 78.95% | 0.7280 | 465.00 | 759.33 | 33.00 | 2717.33 |
| Prior flow + roles | 72.73% | 99.41% | 0.8396 | 476.00 | 782.67 | 35.00 | 3421.67 |
| Prior flow + flow history | 70.88% | 71.72% | 0.7128 | 440.33 | 559.00 | 16.33 | 2468.67 |
| Prior flow + roles + flow history | 75.47% | 92.95% | 0.8325 | 449.00 | 563.00 | 21.67 | 3199.33 |
| Prior flow + roles + wrong-host flow history | 72.16% | 99.43% | 0.8361 | 502.00 | 787.67 | 34.33 | 3422.33 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 69.44% | 89.37% | 0.7779 | 420.67 | 883.67 | 32.00 | 3076.00 |
| Flow/role/history + log-volume/timing controls | 71.82% | 94.59% | 0.8158 | 632.00 | 630.33 | 16.33 | 3255.67 |
| Flow + controls + auth types/outcomes | 67.98% | 79.11% | 0.7283 | 250.67 | 985.00 | 21.33 | 2723.00 |
| Flow/role/history + controls + auth types/outcomes | 71.07% | 92.47% | 0.8025 | 674.00 | 606.33 | 16.33 | 3182.67 |
| Flow/role/history + controls + wrong-host auth | 69.44% | 92.78% | 0.7930 | 798.67 | 596.00 | 18.67 | 3193.33 |
| Log controls + auth only | 34.30% | 31.99% | 0.3309 | 1538.67 | 573.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 38.33% | 31.99% | 0.3474 | 1447.67 | 365.67 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 74.48% | 67.55% | 0.7081 | 133.67 | 847.67 | 847.67 | 15618.33 / 479.00 | 736.00 |
| Prior flow + roles | 74.32% | 67.55% | 0.7074 | 134.67 | 1581.00 | 1581.00 | 16362.33 / 503.33 | 1480.00 |
| Prior flow + flow history | 74.85% | 67.68% | 0.7109 | 93.67 | 371.67 | 371.67 | 15387.67 / 471.33 | 505.33 |
| Prior flow + roles + flow history | 75.33% | 67.75% | 0.7133 | 103.00 | 1135.33 | 1135.33 | 16121.33 / 473.00 | 1239.00 |
| Prior flow + roles + wrong-host flow history | 73.95% | 67.55% | 0.7060 | 134.67 | 1602.00 | 1602.00 | 16385.00 / 525.33 | 1502.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 72.09% | 67.58% | 0.6975 | 127.33 | 1183.67 | 1183.67 | 15973.67 / 459.00 | 1091.33 |
| Flow/role/history + log-volume/timing controls | 71.11% | 67.81% | 0.6942 | 91.00 | 1251.33 | 1251.33 | 16369.00 / 663.33 | 1486.67 |
| Flow + controls + auth types/outcomes | 69.72% | 67.58% | 0.6863 | 112.33 | 643.67 | 643.67 | 15450.00 / 291.67 | 567.67 |
| Flow/role/history + controls + auth types/outcomes | 72.63% | 67.81% | 0.7013 | 96.33 | 1264.00 | 1264.00 | 16332.67 / 699.67 | 1450.33 |
| Flow/role/history + controls + wrong-host auth | 71.75% | 67.80% | 0.6971 | 98.33 | 1352.67 | 1352.67 | 16468.67 / 823.33 | 1586.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1258.33 | 1258.33 | 17519.67 / 1692.67 | 2637.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1267.00 | 1267.00 | 17427.00 / 1599.67 | 2544.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 139.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 867.33 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1097.33 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.67 | 32.00 | 33.67 | 750.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 12.33 | 16.33 | 28.67 | 921.67 |
| Flow + controls + auth types/outcomes | 24.33 | 9.00 | 21.33 | 30.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 12.67 | 16.33 | 29.00 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 11.67 | 18.67 | 30.33 | 859.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 1.00% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 67.11% | 67.56% | 0.6729 | 58.67 | 1089.67 | 0.00 | 2325.33 |
| Prior flow + roles | 67.80% | 67.55% | 0.6765 | 35.67 | 1072.67 | 0.00 | 2325.00 |
| Prior flow + flow history | 56.92% | 70.03% | 0.6270 | 877.33 | 949.67 | 13.33 | 2410.33 |
| Prior flow + roles + flow history | 63.63% | 90.46% | 0.7450 | 816.00 | 940.67 | 17.33 | 3113.67 |
| Prior flow + roles + wrong-host flow history | 67.97% | 67.56% | 0.6776 | 41.33 | 1054.67 | 0.00 | 2325.33 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 62.16% | 67.58% | 0.6475 | 27.67 | 1389.00 | 0.00 | 2326.00 |
| Flow/role/history + log-volume/timing controls | 61.66% | 91.58% | 0.7360 | 976.67 | 947.67 | 20.67 | 3152.33 |
| Flow + controls + auth types/outcomes | 60.83% | 67.58% | 0.6402 | 41.00 | 1457.00 | 0.00 | 2326.00 |
| Flow/role/history + controls + auth types/outcomes | 62.72% | 90.10% | 0.7371 | 929.00 | 899.00 | 13.00 | 3101.33 |
| Flow/role/history + controls + wrong-host auth | 60.31% | 91.11% | 0.7239 | 1081.00 | 951.00 | 20.33 | 3136.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2172.67 | 905.67 | 1.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 1909.67 | 570.00 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 67.11% | 67.56% | 0.6729 | 0.00 | 0.00 | 0.00 | 14918.00 / 169.67 | 35.67 |
| Prior flow + roles | 67.80% | 67.55% | 0.6765 | 0.00 | 0.00 | 0.00 | 14920.67 / 167.33 | 38.33 |
| Prior flow + flow history | 60.12% | 67.80% | 0.6367 | 84.67 | 355.33 | 355.33 | 15774.67 / 915.00 | 892.33 |
| Prior flow + roles + flow history | 61.23% | 67.80% | 0.6430 | 93.00 | 1064.00 | 1064.00 | 16411.33 / 848.00 | 1529.00 |
| Prior flow + roles + wrong-host flow history | 67.97% | 67.56% | 0.6776 | 0.00 | 0.00 | 0.00 | 14923.00 / 168.00 | 40.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 62.16% | 67.58% | 0.6475 | 0.00 | 0.00 | 0.00 | 14925.33 / 167.33 | 43.00 |
| Flow/role/history + log-volume/timing controls | 59.54% | 67.82% | 0.6341 | 97.67 | 1176.33 | 1176.33 | 16609.67 / 1004.67 | 1727.33 |
| Flow + controls + auth types/outcomes | 60.83% | 67.58% | 0.6402 | 0.00 | 0.00 | 0.00 | 14926.33 / 167.00 | 44.00 |
| Flow/role/history + controls + auth types/outcomes | 61.53% | 67.82% | 0.6449 | 90.67 | 1140.67 | 1140.67 | 16511.00 / 958.33 | 1628.67 |
| Flow/role/history + controls + wrong-host auth | 58.45% | 67.82% | 0.6277 | 103.00 | 1190.00 | 1190.00 | 16692.67 / 1103.00 | 1810.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.67 | 31.00 | 31.00 | 17054.00 / 2327.33 | 2171.67 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 5.67 | 34.67 | 34.67 | 16790.00 / 2063.67 | 1907.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 12.33 | 13.33 | 25.67 | 76.67 |
| Prior flow + roles + flow history | 24.33 | 10.00 | 17.33 | 27.33 | 780.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 9.00 | 20.67 | 29.67 | 818.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 14.67 | 13.00 | 27.67 | 767.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 9.67 | 20.33 | 30.00 | 801.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 1.00% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 62.78% | 78.96% | 0.6964 | 492.00 | 1072.67 | 33.00 | 2717.67 |
| Prior flow + roles | 67.07% | 99.41% | 0.8008 | 605.00 | 1044.67 | 35.00 | 3421.67 |
| Prior flow + flow history | 55.58% | 71.90% | 0.6262 | 972.33 | 1003.33 | 17.33 | 2474.67 |
| Prior flow + roles + flow history | 62.77% | 95.50% | 0.7569 | 937.67 | 998.67 | 21.67 | 3287.00 |
| Prior flow + roles + wrong-host flow history | 67.08% | 99.48% | 0.8013 | 602.33 | 1043.33 | 34.33 | 3424.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 63.42% | 99.51% | 0.7747 | 584.33 | 1358.33 | 33.33 | 3425.00 |
| Flow/role/history + log-volume/timing controls | 59.67% | 96.35% | 0.7369 | 1169.33 | 1049.33 | 22.00 | 3316.33 |
| Flow + controls + auth types/outcomes | 62.61% | 89.32% | 0.7335 | 350.33 | 1436.33 | 23.00 | 3074.33 |
| Flow/role/history + controls + auth types/outcomes | 60.00% | 95.55% | 0.7363 | 1203.00 | 978.00 | 23.67 | 3289.00 |
| Flow/role/history + controls + wrong-host auth | 57.57% | 96.74% | 0.7216 | 1413.67 | 1015.33 | 25.00 | 3329.67 |
| Log controls + auth only | 25.93% | 31.99% | 0.2864 | 2252.00 | 893.67 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 29.80% | 31.99% | 0.3081 | 2041.00 | 570.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 67.45% | 67.56% | 0.6746 | 133.67 | 859.00 | 859.00 | 15643.00 / 492.67 | 760.67 |
| Prior flow + roles | 68.36% | 67.55% | 0.6793 | 134.67 | 1701.00 | 1701.00 | 16487.00 / 626.33 | 1604.67 |
| Prior flow + flow history | 58.88% | 67.80% | 0.6296 | 95.67 | 487.67 | 487.67 | 15927.00 / 1001.00 | 1044.67 |
| Prior flow + roles + flow history | 59.87% | 67.81% | 0.6351 | 103.33 | 1326.33 | 1326.33 | 16700.67 / 961.00 | 1818.33 |
| Prior flow + roles + wrong-host flow history | 68.21% | 67.56% | 0.6788 | 134.67 | 1694.67 | 1694.67 | 16482.33 / 618.67 | 1600.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 62.68% | 67.58% | 0.6504 | 131.00 | 1689.67 | 1689.67 | 16483.33 / 616.67 | 1601.00 |
| Flow/role/history + log-volume/timing controls | 57.02% | 67.82% | 0.6195 | 103.33 | 1462.00 | 1462.00 | 16962.33 / 1192.00 | 2080.00 |
| Flow + controls + auth types/outcomes | 61.16% | 67.58% | 0.6421 | 115.67 | 1081.00 | 1081.00 | 15891.33 / 377.67 | 1009.00 |
| Flow/role/history + controls + auth types/outcomes | 59.36% | 67.83% | 0.6328 | 110.67 | 1552.33 | 1552.33 | 16963.33 / 1219.67 | 2081.00 |
| Flow/role/history + controls + wrong-host auth | 56.57% | 67.82% | 0.6167 | 112.67 | 1654.67 | 1654.67 | 17214.00 / 1428.67 | 2331.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1265.33 | 1265.33 | 18233.67 / 2406.00 | 3351.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1267.00 | 1267.00 | 18020.33 / 2193.00 | 3138.00 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.33 | 17.33 | 27.67 | 141.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 953.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1098.67 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.00 | 33.33 | 34.33 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 8.67 | 22.00 | 30.67 | 982.00 |
| Flow + controls + auth types/outcomes | 24.33 | 7.67 | 23.00 | 30.67 | 748.33 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 7.33 | 23.67 | 31.00 | 954.33 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 7.00 | 25.00 | 32.00 | 995.33 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 2.00% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 57.31% | 67.57% | 0.6200 | 59.67 | 1678.67 | 0.00 | 2325.67 |
| Prior flow + roles | 57.25% | 67.56% | 0.6196 | 58.67 | 1682.33 | 0.00 | 2325.33 |
| Prior flow + flow history | 41.51% | 71.89% | 0.5258 | 1663.33 | 1822.00 | 16.33 | 2474.33 |
| Prior flow + roles + flow history | 48.90% | 92.58% | 0.6389 | 1544.00 | 1760.00 | 24.67 | 3186.67 |
| Prior flow + roles + wrong-host flow history | 60.47% | 67.57% | 0.6382 | 46.00 | 1475.00 | 0.00 | 2325.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 52.36% | 67.58% | 0.5900 | 36.33 | 2080.67 | 0.00 | 2326.00 |
| Flow/role/history + log-volume/timing controls | 48.12% | 96.52% | 0.6423 | 1985.33 | 1572.33 | 24.33 | 3322.33 |
| Flow + controls + auth types/outcomes | 51.93% | 67.58% | 0.5873 | 47.33 | 2106.00 | 0.00 | 2326.00 |
| Flow/role/history + controls + auth types/outcomes | 48.59% | 92.11% | 0.6353 | 1816.33 | 1499.67 | 22.33 | 3170.33 |
| Flow/role/history + controls + wrong-host auth | 45.98% | 93.28% | 0.6154 | 2205.33 | 1532.33 | 25.33 | 3210.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2243.67 | 936.33 | 1.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 1909.67 | 570.00 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 57.31% | 67.57% | 0.6200 | 0.00 | 0.00 | 0.00 | 14926.33 / 170.00 | 44.00 |
| Prior flow + roles | 57.25% | 67.56% | 0.6196 | 0.00 | 0.00 | 0.00 | 14924.67 / 169.33 | 42.33 |
| Prior flow + flow history | 43.03% | 67.82% | 0.5261 | 96.67 | 534.67 | 534.67 | 16615.67 / 1690.67 | 1733.33 |
| Prior flow + roles + flow history | 45.08% | 67.81% | 0.5411 | 109.33 | 1318.00 | 1318.00 | 17204.00 / 1562.67 | 2321.67 |
| Prior flow + roles + wrong-host flow history | 60.47% | 67.57% | 0.6382 | 0.00 | 0.00 | 0.00 | 14926.00 / 169.33 | 43.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 52.37% | 67.58% | 0.5901 | 0.33 | 0.33 | 0.33 | 14931.67 / 171.00 | 49.33 |
| Flow/role/history + log-volume/timing controls | 45.31% | 67.83% | 0.5432 | 110.33 | 1749.00 | 1749.00 | 17780.33 / 2002.33 | 2898.00 |
| Flow + controls + auth types/outcomes | 51.94% | 67.58% | 0.5873 | 0.67 | 0.67 | 0.67 | 14930.67 / 169.00 | 48.33 |
| Flow/role/history + controls + auth types/outcomes | 47.36% | 67.83% | 0.5574 | 107.00 | 1568.00 | 1568.00 | 17460.67 / 1835.33 | 2578.33 |
| Flow/role/history + controls + wrong-host auth | 44.51% | 67.83% | 0.5373 | 112.33 | 1720.33 | 1720.33 | 17887.67 / 2220.67 | 3005.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.67 | 32.00 | 32.00 | 17125.00 / 2398.33 | 2242.67 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 5.67 | 34.67 | 34.67 | 16790.00 / 2063.67 | 1907.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 140.00 |
| Prior flow + roles + flow history | 24.33 | 6.67 | 24.67 | 31.33 | 852.67 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 7.33 | 24.33 | 31.67 | 987.67 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 8.67 | 22.33 | 31.00 | 835.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 7.00 | 25.33 | 32.33 | 876.00 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 2.00% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 54.47% | 79.19% | 0.6430 | 589.67 | 1634.00 | 34.67 | 2725.67 |
| Prior flow + roles | 59.40% | 99.46% | 0.7436 | 698.00 | 1614.00 | 35.00 | 3423.33 |
| Prior flow + flow history | 40.53% | 72.34% | 0.5190 | 1747.00 | 1903.67 | 20.00 | 2490.00 |
| Prior flow + roles + flow history | 47.96% | 95.90% | 0.6389 | 1710.00 | 1857.00 | 23.00 | 3301.00 |
| Prior flow + roles + wrong-host flow history | 61.09% | 99.53% | 0.7570 | 703.67 | 1446.67 | 35.00 | 3425.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 56.11% | 99.51% | 0.7175 | 632.00 | 2015.00 | 33.67 | 3425.00 |
| Flow/role/history + log-volume/timing controls | 46.36% | 96.78% | 0.6268 | 2082.67 | 1752.00 | 23.67 | 3331.33 |
| Flow + controls + auth types/outcomes | 54.95% | 89.33% | 0.6785 | 409.00 | 2052.67 | 24.67 | 3074.67 |
| Flow/role/history + controls + auth types/outcomes | 47.79% | 96.17% | 0.6383 | 1947.33 | 1640.33 | 26.00 | 3310.00 |
| Flow/role/history + controls + wrong-host auth | 45.61% | 98.50% | 0.6232 | 2329.33 | 1700.00 | 26.67 | 3390.33 |
| Log controls + auth only | 24.87% | 31.99% | 0.2797 | 2395.00 | 936.33 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 29.70% | 31.99% | 0.3076 | 2054.00 | 570.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 57.94% | 67.57% | 0.6236 | 134.67 | 964.67 | 964.67 | 15756.33 / 589.67 | 874.00 |
| Prior flow + roles | 58.29% | 67.56% | 0.6257 | 134.67 | 1777.67 | 1777.67 | 16567.33 / 703.67 | 1685.00 |
| Prior flow + flow history | 41.90% | 67.82% | 0.5175 | 102.00 | 568.33 | 568.33 | 16713.33 / 1771.67 | 1831.00 |
| Prior flow + roles + flow history | 43.50% | 67.81% | 0.5295 | 105.00 | 1503.00 | 1503.00 | 17487.33 / 1731.33 | 2605.00 |
| Prior flow + roles + wrong-host flow history | 60.92% | 67.57% | 0.6407 | 134.67 | 1792.67 | 1792.67 | 16584.00 / 716.67 | 1701.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 14882.33 / 157.33 | 0.00 |
| Flow + log-volume/timing controls | 53.16% | 67.58% | 0.5950 | 131.00 | 1729.33 | 1729.33 | 16529.00 / 659.33 | 1646.67 |
| Flow/role/history + log-volume/timing controls | 41.93% | 67.83% | 0.5182 | 106.67 | 1620.33 | 1620.33 | 17889.67 / 2103.00 | 3007.33 |
| Flow + controls + auth types/outcomes | 52.57% | 67.58% | 0.5914 | 118.33 | 1136.33 | 1136.33 | 15947.67 / 431.67 | 1065.33 |
| Flow/role/history + controls + auth types/outcomes | 44.43% | 67.83% | 0.5369 | 114.00 | 1667.00 | 1667.00 | 17728.00 / 1962.67 | 2845.67 |
| Flow/role/history + controls + wrong-host auth | 41.27% | 67.83% | 0.5129 | 116.67 | 1778.67 | 1778.67 | 18188.33 / 2341.67 | 3306.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.67 | 1284.33 | 1284.33 | 18376.33 / 2548.67 | 3494.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 10.67 | 1280.00 | 1280.00 | 18030.33 / 2203.00 | 3148.00 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 0.00 | 34.67 | 34.67 | 400.00 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1098.00 |
| Prior flow + flow history | 24.33 | 8.00 | 20.00 | 28.00 | 155.67 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 23.00 | 31.33 | 967.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 35.00 | 35.00 | 1100.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.00 | 33.67 | 34.67 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 7.67 | 23.67 | 31.33 | 996.67 |
| Flow + controls + auth types/outcomes | 24.33 | 6.00 | 24.67 | 30.67 | 748.67 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 5.33 | 26.00 | 31.33 | 975.33 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 5.67 | 26.67 | 32.33 | 1055.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

## Department → private services (role 7)

### Calibration-F1 / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Log controls + auth only | 88.51% | 100.00% | 0.9390 | 142.00 | 0.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 88.70% | 100.00% | 0.9401 | 137.67 | 0.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.67 | 1244.00 | 1244.00 | 1376.00 / 249.67 | 1241.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 5.67 | 1241.33 | 1241.33 | 1370.33 / 244.67 | 1235.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 0.10% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 0.33 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles + flow history | 33.33% | 0.15% | 0.0030 | 0.00 | 0.00 | 0.00 | 1.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 11.00 | 0.00 | 0.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 3.67 | 0.00 | 0.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 0.33 | 0.33 | 0.33 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 1.67 | 1.67 | 136.33 / 110.33 | 1.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.00 | 11.00 | 11.00 | 143.67 / 119.33 | 9.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 1.33 | 4.33 | 4.33 | 137.67 / 113.33 | 3.00 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles + flow history | 24.33 | 24.33 | 0.00 | 24.33 | 1.67 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log controls + auth only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 23.67 | 0.67 | 24.33 | 0.00 |

### 0.10% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 29.41% | 35.63% | 0.3040 | 379.00 | 0.00 | 33.00 | 392.33 |
| Prior flow + roles | 71.80% | 99.61% | 0.8327 | 408.67 | 0.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 47.47% | 12.62% | 0.1977 | 119.00 | 0.00 | 16.33 | 139.00 |
| Prior flow + roles + flow history | 78.56% | 78.78% | 0.7750 | 190.67 | 0.00 | 21.67 | 867.33 |
| Prior flow + roles + wrong-host flow history | 70.70% | 99.67% | 0.8251 | 436.00 | 0.00 | 34.33 | 1097.33 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 51.73% | 68.12% | 0.5734 | 377.00 | 0.00 | 32.00 | 750.00 |
| Flow/role/history + log-volume/timing controls | 81.77% | 83.71% | 0.8223 | 185.67 | 0.00 | 16.33 | 921.67 |
| Flow + controls + auth types/outcomes | 39.68% | 36.06% | 0.3484 | 192.00 | 0.00 | 21.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 73.05% | 77.08% | 0.7412 | 270.00 | 0.00 | 16.33 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 69.69% | 78.08% | 0.7265 | 340.33 | 0.00 | 18.67 | 859.67 |
| Log controls + auth only | 87.78% | 100.00% | 0.9349 | 152.33 | 0.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 87.57% | 100.00% | 0.9337 | 153.67 | 0.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 133.67 | 804.33 | 804.33 | 805.33 / 379.00 | 670.67 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 134.67 | 1540.33 | 1540.33 | 1540.33 / 408.67 | 1405.67 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 93.67 | 274.33 | 274.33 | 315.33 / 149.33 | 180.67 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 103.00 | 1079.67 | 1079.67 | 1111.33 / 214.00 | 976.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 134.67 | 1567.67 | 1567.67 | 1567.67 / 436.00 | 1433.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 127.33 | 1159.00 | 1159.00 | 1166.33 / 382.67 | 1031.67 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 91.00 | 1123.67 | 1123.67 | 1167.33 / 217.00 | 1032.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 112.33 | 610.33 | 610.33 | 632.67 / 205.33 | 498.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 96.33 | 1135.00 | 1135.00 | 1173.33 / 295.67 | 1038.67 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 98.33 | 1218.67 | 1218.67 | 1255.00 / 365.00 | 1120.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1254.33 | 1254.33 | 1385.67 / 259.33 | 1251.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1257.33 | 1257.33 | 1384.33 / 258.67 | 1249.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 139.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 867.33 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1097.33 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.67 | 32.00 | 33.67 | 750.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 12.33 | 16.33 | 28.67 | 921.67 |
| Flow + controls + auth types/outcomes | 24.33 | 9.00 | 21.33 | 30.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 12.67 | 16.33 | 29.00 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 11.67 | 18.67 | 30.33 | 859.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 0.50% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + flow history | 10.05% | 0.58% | 0.0109 | 43.33 | 0.00 | 3.33 | 6.33 |
| Prior flow + roles + flow history | 73.11% | 21.07% | 0.3223 | 63.33 | 0.00 | 8.00 | 232.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + log-volume/timing controls | 82.83% | 61.43% | 0.6716 | 84.67 | 0.00 | 10.00 | 676.33 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 71.03% | 16.59% | 0.2673 | 70.67 | 0.00 | 5.00 | 182.67 |
| Flow/role/history + controls + wrong-host auth | 81.21% | 54.71% | 0.6179 | 89.33 | 0.00 | 9.67 | 602.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 16.33 | 0.00 | 0.67 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 14.67 | 0.00 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 44.00 | 53.00 | 53.00 | 143.67 / 113.00 | 9.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 61.33 | 303.33 | 303.33 | 376.67 / 119.67 | 242.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 75.33 | 771.00 | 771.00 | 830.33 / 127.67 | 695.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 57.33 | 258.33 | 258.33 | 335.67 / 127.33 | 201.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 79.00 | 701.33 | 701.33 | 757.00 / 128.67 | 622.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.00 | 17.00 | 17.00 | 149.67 / 124.67 | 15.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 4.67 | 17.33 | 17.33 | 147.33 / 122.67 | 12.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 21.00 | 3.33 | 24.33 | 6.33 |
| Prior flow + roles + flow history | 24.33 | 17.00 | 8.00 | 25.00 | 232.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 16.33 | 10.00 | 26.33 | 676.33 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 20.67 | 5.00 | 25.67 | 182.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 16.33 | 9.67 | 26.00 | 602.33 |
| Log controls + auth only | 24.33 | 24.33 | 0.67 | 25.00 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 0.50% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 29.41% | 35.63% | 0.3040 | 379.00 | 0.00 | 33.00 | 392.33 |
| Prior flow + roles | 71.80% | 99.61% | 0.8327 | 408.67 | 0.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 47.47% | 12.62% | 0.1977 | 119.00 | 0.00 | 16.33 | 139.00 |
| Prior flow + roles + flow history | 78.56% | 78.78% | 0.7750 | 190.67 | 0.00 | 21.67 | 867.33 |
| Prior flow + roles + wrong-host flow history | 70.70% | 99.67% | 0.8251 | 436.00 | 0.00 | 34.33 | 1097.33 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 51.73% | 68.12% | 0.5734 | 377.00 | 0.00 | 32.00 | 750.00 |
| Flow/role/history + log-volume/timing controls | 81.77% | 83.71% | 0.8223 | 185.67 | 0.00 | 16.33 | 921.67 |
| Flow + controls + auth types/outcomes | 39.68% | 36.06% | 0.3484 | 192.00 | 0.00 | 21.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 73.05% | 77.08% | 0.7412 | 270.00 | 0.00 | 16.33 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 69.69% | 78.08% | 0.7265 | 340.33 | 0.00 | 18.67 | 859.67 |
| Log controls + auth only | 87.78% | 100.00% | 0.9349 | 152.33 | 0.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 87.57% | 100.00% | 0.9337 | 153.67 | 0.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 133.67 | 804.33 | 804.33 | 805.33 / 379.00 | 670.67 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 134.67 | 1540.33 | 1540.33 | 1540.33 / 408.67 | 1405.67 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 93.67 | 274.33 | 274.33 | 315.33 / 149.33 | 180.67 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 103.00 | 1079.67 | 1079.67 | 1111.33 / 214.00 | 976.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 134.67 | 1567.67 | 1567.67 | 1567.67 / 436.00 | 1433.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 127.33 | 1159.00 | 1159.00 | 1166.33 / 382.67 | 1031.67 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 91.00 | 1123.67 | 1123.67 | 1167.33 / 217.00 | 1032.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 112.33 | 610.33 | 610.33 | 632.67 / 205.33 | 498.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 96.33 | 1135.00 | 1135.00 | 1173.33 / 295.67 | 1038.67 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 98.33 | 1218.67 | 1218.67 | 1255.00 / 365.00 | 1120.33 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1254.33 | 1254.33 | 1385.67 / 259.33 | 1251.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1257.33 | 1257.33 | 1384.33 / 258.67 | 1249.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 139.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 867.33 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1097.33 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.67 | 32.00 | 33.67 | 750.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 12.33 | 16.33 | 28.67 | 921.67 |
| Flow + controls + auth types/outcomes | 24.33 | 9.00 | 21.33 | 30.33 | 397.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 12.67 | 16.33 | 29.00 | 848.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 11.67 | 18.67 | 30.33 | 859.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 1.00% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + flow history | 34.13% | 6.96% | 0.1128 | 91.00 | 0.00 | 13.33 | 76.67 |
| Prior flow + roles + flow history | 78.86% | 70.84% | 0.7089 | 133.33 | 0.00 | 17.33 | 780.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + log-volume/timing controls | 80.09% | 74.30% | 0.7416 | 146.67 | 0.00 | 20.67 | 818.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 79.93% | 69.66% | 0.6969 | 155.00 | 0.00 | 13.00 | 767.00 |
| Flow/role/history + controls + wrong-host auth | 76.95% | 72.81% | 0.7145 | 171.00 | 0.00 | 20.33 | 801.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 26.00 | 0.00 | 1.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 22.33 | 0.00 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 84.67 | 181.00 | 181.00 | 231.00 / 128.67 | 96.33 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 93.00 | 930.67 | 930.67 | 972.33 / 165.00 | 837.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 97.67 | 985.33 | 985.33 | 1022.33 / 174.67 | 887.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 90.67 | 935.00 | 935.00 | 979.00 / 184.33 | 844.33 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 103.00 | 993.00 | 993.00 | 1024.67 / 193.00 | 890.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.67 | 27.00 | 27.00 | 159.00 / 133.67 | 24.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 5.67 | 25.00 | 25.00 | 154.00 / 129.33 | 19.33 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 12.33 | 13.33 | 25.67 | 76.67 |
| Prior flow + roles + flow history | 24.33 | 10.00 | 17.33 | 27.33 | 780.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 9.00 | 20.67 | 29.67 | 818.00 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 14.67 | 13.00 | 27.67 | 767.00 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 9.67 | 20.33 | 30.00 | 801.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 1.00% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 29.36% | 35.63% | 0.3039 | 382.33 | 0.00 | 33.00 | 392.33 |
| Prior flow + roles | 67.70% | 99.61% | 0.8060 | 489.00 | 0.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 46.50% | 12.81% | 0.1990 | 126.33 | 0.00 | 17.33 | 141.00 |
| Prior flow + roles + flow history | 80.60% | 86.56% | 0.8317 | 202.67 | 0.00 | 21.67 | 953.00 |
| Prior flow + roles + wrong-host flow history | 66.43% | 99.79% | 0.7975 | 522.33 | 0.00 | 34.33 | 1098.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 67.48% | 99.82% | 0.8050 | 498.00 | 0.00 | 33.33 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 76.78% | 89.19% | 0.8247 | 272.00 | 0.00 | 22.00 | 982.00 |
| Flow + controls + auth types/outcomes | 57.24% | 67.97% | 0.5981 | 276.33 | 0.00 | 23.00 | 748.33 |
| Flow/role/history + controls + auth types/outcomes | 70.17% | 86.68% | 0.7716 | 382.67 | 0.00 | 23.67 | 954.33 |
| Flow/role/history + controls + wrong-host auth | 68.51% | 90.40% | 0.7778 | 432.33 | 0.00 | 25.00 | 995.33 |
| Log controls + auth only | 87.29% | 100.00% | 0.9321 | 159.33 | 0.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 87.57% | 100.00% | 0.9337 | 153.67 | 0.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 133.67 | 807.67 | 807.67 | 808.67 / 382.33 | 674.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 134.67 | 1620.67 | 1620.67 | 1620.67 / 489.00 | 1486.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 95.67 | 284.67 | 284.67 | 323.67 / 155.00 | 189.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 103.33 | 1177.33 | 1177.33 | 1208.67 / 225.67 | 1074.00 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 134.67 | 1655.33 | 1655.33 | 1655.33 / 522.33 | 1520.67 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 131.00 | 1630.33 | 1630.33 | 1634.00 / 500.67 | 1499.33 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 103.33 | 1276.00 | 1276.00 | 1307.33 / 294.67 | 1172.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 115.67 | 1047.67 | 1047.67 | 1066.67 / 287.67 | 932.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 110.67 | 1360.67 | 1360.67 | 1384.67 / 399.33 | 1250.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 112.67 | 1452.67 | 1452.67 | 1474.67 / 447.33 | 1340.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.33 | 1261.33 | 1261.33 | 1392.67 / 266.33 | 1258.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 7.67 | 1257.33 | 1257.33 | 1384.33 / 258.67 | 1249.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 1.00 | 33.00 | 34.00 | 392.33 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1096.67 |
| Prior flow + flow history | 24.33 | 10.33 | 17.33 | 27.67 | 141.00 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 21.67 | 30.00 | 953.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 34.33 | 34.33 | 1098.67 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.00 | 33.33 | 34.33 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 8.67 | 22.00 | 30.67 | 982.00 |
| Flow + controls + auth types/outcomes | 24.33 | 7.67 | 23.00 | 30.67 | 748.33 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 7.33 | 23.67 | 31.00 | 954.33 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 7.00 | 25.00 | 32.00 | 995.33 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |

### 2.00% calibration tail / global

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior flow + flow history | 44.79% | 12.72% | 0.1953 | 141.00 | 0.00 | 16.33 | 140.00 |
| Prior flow + roles + flow history | 75.27% | 77.44% | 0.7426 | 226.33 | 0.00 | 24.67 | 852.67 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.33 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + log-volume/timing controls | 71.59% | 89.71% | 0.7950 | 361.33 | 0.00 | 24.33 | 987.67 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.67 | 0.00 | 0.00 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 66.21% | 75.90% | 0.6893 | 352.00 | 0.00 | 22.33 | 835.67 |
| Flow/role/history + controls + wrong-host auth | 64.01% | 79.56% | 0.7008 | 427.00 | 0.00 | 25.33 | 876.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 27.00 | 0.00 | 1.00 | 0.00 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 22.33 | 0.00 | 2.67 | 0.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 96.67 | 297.33 | 297.33 | 335.33 / 168.33 | 200.67 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 109.33 | 1103.67 | 1103.67 | 1129.00 / 245.00 | 994.33 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 0.33 | 0.33 | 0.33 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 110.33 | 1373.33 | 1373.33 | 1397.67 / 378.33 | 1263.00 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 0.67 | 0.67 | 0.67 | 134.67 / 110.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 107.00 | 1210.00 | 1210.00 | 1237.67 / 371.00 | 1103.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 112.33 | 1328.33 | 1328.33 | 1350.67 / 442.33 | 1216.00 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 2.67 | 28.00 | 28.00 | 160.00 / 134.67 | 25.33 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 5.67 | 25.00 | 25.00 | 154.00 / 129.33 | 19.33 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + roles | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior flow + flow history | 24.33 | 10.67 | 16.33 | 27.00 | 140.00 |
| Prior flow + roles + flow history | 24.33 | 6.67 | 24.67 | 31.33 | 852.67 |
| Prior flow + roles + wrong-host flow history | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 7.33 | 24.33 | 31.67 | 987.67 |
| Flow + controls + auth types/outcomes | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 8.67 | 22.33 | 31.00 | 835.67 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 7.00 | 25.33 | 32.33 | 876.00 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 0.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 0.00 |

### 2.00% calibration tail / role-conditioned

| Arm | Raw exfil P | Raw exfil R | Raw exfil F1 | False benign→exfil | False other→exfil | False movement→exfil | Raw true exfil |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 28.89% | 36.33% | 0.3031 | 459.33 | 0.00 | 34.67 | 400.00 |
| Prior flow + roles | 65.72% | 99.73% | 0.7921 | 539.33 | 0.00 | 35.00 | 1098.00 |
| Prior flow + flow history | 45.22% | 14.14% | 0.2127 | 154.33 | 0.00 | 20.00 | 155.67 |
| Prior flow + roles + flow history | 74.97% | 87.83% | 0.8036 | 305.33 | 0.00 | 23.00 | 967.00 |
| Prior flow + roles + wrong-host flow history | 64.44% | 99.91% | 0.7835 | 572.00 | 0.00 | 35.00 | 1100.00 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 0.00 |
| Flow + log-volume/timing controls | 66.60% | 99.82% | 0.7986 | 520.33 | 0.00 | 33.67 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 72.00% | 90.52% | 0.7980 | 379.67 | 0.00 | 23.67 | 996.67 |
| Flow + controls + auth types/outcomes | 56.22% | 68.00% | 0.5917 | 294.67 | 0.00 | 24.67 | 748.67 |
| Flow/role/history + controls + auth types/outcomes | 67.51% | 88.59% | 0.7629 | 442.67 | 0.00 | 26.00 | 975.33 |
| Flow/role/history + controls + wrong-host auth | 68.59% | 95.88% | 0.7984 | 466.00 | 0.00 | 26.67 | 1055.67 |
| Log controls + auth only | 85.99% | 100.00% | 0.9247 | 178.33 | 0.00 | 1.00 | 1101.00 |
| Log-volume/timing controls only | 86.68% | 100.00% | 0.9286 | 166.67 | 0.00 | 2.67 | 1101.00 |

| Arm | Auto exfil P | Auto exfil R | Auto exfil F1 | Both flags | Unsupported exfil | Unresolved union | Review queue / benign | Added reviews |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.00% | 0.00% | 0.0000 | 134.67 | 894.00 | 894.00 | 894.00 / 459.33 | 759.33 |
| Prior flow + roles | 0.00% | 0.00% | 0.0000 | 134.67 | 1672.33 | 1672.33 | 1672.33 / 539.33 | 1537.67 |
| Prior flow + flow history | 0.00% | 0.00% | 0.0000 | 102.00 | 330.00 | 330.00 | 362.67 / 179.00 | 228.00 |
| Prior flow + roles + flow history | 0.00% | 0.00% | 0.0000 | 105.00 | 1295.33 | 1295.33 | 1325.00 / 326.67 | 1190.33 |
| Prior flow + roles + wrong-host flow history | 0.00% | 0.00% | 0.0000 | 134.67 | 1707.00 | 1707.00 | 1707.00 / 572.00 | 1572.33 |
| Prior roles only | 0.00% | 0.00% | 0.0000 | 0.00 | 0.00 | 0.00 | 134.67 / 110.33 | 0.00 |
| Flow + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 131.00 | 1653.00 | 1653.00 | 1656.67 / 523.00 | 1522.00 |
| Flow/role/history + log-volume/timing controls | 0.00% | 0.00% | 0.0000 | 106.67 | 1400.00 | 1400.00 | 1428.00 / 400.00 | 1293.33 |
| Flow + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 118.33 | 1068.00 | 1068.00 | 1084.33 / 305.00 | 949.67 |
| Flow/role/history + controls + auth types/outcomes | 0.00% | 0.00% | 0.0000 | 114.00 | 1444.00 | 1444.00 | 1464.67 / 458.00 | 1330.00 |
| Flow/role/history + controls + wrong-host auth | 0.00% | 0.00% | 0.0000 | 116.67 | 1548.33 | 1548.33 | 1566.33 / 478.33 | 1431.67 |
| Log controls + auth only | 0.00% | 0.00% | 0.0000 | 3.67 | 1280.33 | 1280.33 | 1411.33 / 285.00 | 1276.67 |
| Log-volume/timing controls only | 0.00% | 0.00% | 0.0000 | 10.67 | 1270.33 | 1270.33 | 1394.33 / 268.67 | 1259.67 |

| Arm | Movement exact baseline flags | Movement resolved alone | Movement in unresolved review | Movement in any review | Exfil in unresolved review |
|---|---:|---:|---:|---:|---:|
| Prior current flow | 24.33 | 0.00 | 34.67 | 34.67 | 400.00 |
| Prior flow + roles | 24.33 | 0.00 | 35.00 | 35.00 | 1098.00 |
| Prior flow + flow history | 24.33 | 8.00 | 20.00 | 28.00 | 155.67 |
| Prior flow + roles + flow history | 24.33 | 8.33 | 23.00 | 31.33 | 967.00 |
| Prior flow + roles + wrong-host flow history | 24.33 | 0.00 | 35.00 | 35.00 | 1100.00 |
| Prior roles only | 24.33 | 24.33 | 0.00 | 24.33 | 0.00 |
| Flow + log-volume/timing controls | 24.33 | 1.00 | 33.67 | 34.67 | 1099.00 |
| Flow/role/history + log-volume/timing controls | 24.33 | 7.67 | 23.67 | 31.33 | 996.67 |
| Flow + controls + auth types/outcomes | 24.33 | 6.00 | 24.67 | 30.67 | 748.67 |
| Flow/role/history + controls + auth types/outcomes | 24.33 | 5.33 | 26.00 | 31.33 | 975.33 |
| Flow/role/history + controls + wrong-host auth | 24.33 | 5.67 | 26.67 | 32.33 | 1055.67 |
| Log controls + auth only | 24.33 | 24.33 | 1.00 | 25.33 | 1101.00 |
| Log-volume/timing controls only | 24.33 | 22.00 | 2.67 | 24.67 | 1101.00 |
