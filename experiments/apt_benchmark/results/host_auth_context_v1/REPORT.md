# Partial authentication test and movement-preserving review policies

**Scope gate: all Windows host events were excluded before fitting because clock alignment was unresolved.** This run uses Linux audit context. All 35 movement-stage test rows have the covered Linux source; all 3,442 exfiltration-stage test rows have the excluded Windows source. The full Windows-authentication/exfiltration hypothesis remains untested. See [host-event qualification](../../host_auth_context/HOST_EVENT_QUALIFICATION.md).

**Completed development comparison: 21 new fits plus 18 saved probability-arm replays. Independent calculation audit: PASS.** Three fitting seeds share the same later-period observations from one exposed UNRAVELED campaign and IT sensor.

Authentication histories, host roles, temporal context and fusion have direct prior art. This study tests incremental information and error costs; it does not establish a new algorithm. See the [novelty review](../../host_auth_context/NOVELTY_REVIEW.md) and [fixed design](../../host_auth_context/DESIGN.md).

## What was measured

All seven new arms use the same prior fixed LightGBM settings and fitting identities; six earlier network-only arms are evaluated from saved probabilities. No result chooses a new preferred model or threshold. The log controls include **observed-log volume/timing and availability**, so the matched authentication contrast measures additional event-type/outcome information beyond those controls, not merely access to event counts.

| Test author class | Rows |
|---|---:|
| Benign | 192,193 |
| OtherAttackStage | 12,424 |
| LateralMovement | 35 |
| DataExfiltration | 3,442 |

Movement labels in this sensor describe Remote System Discovery on one host pair; they are not independent verified successful logins. Exfiltration labels are author progress annotations, not content-confirmed theft. Earlier host events are source-side context, not proof of successful outgoing authentication to an unmonitored destination.

## Stage classification: every arm

Four-class argmax decisions; P = precision, R = recall, AP = average precision. Exact movement recall requires the movement label; any-attack recall also counts a different attack label. Normal false attacks and exfiltration false labels have different meanings. Values are arithmetic means of per-fit metrics, not metrics pooled across replicated events.

| Arm | Macro-F1 | Exfil AP | Exfil P | Exfil R | Exfil F1 | Movement exact R | Movement any-attack R | Benign false attacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.7552 | 0.6363 | 85.90% | 67.53% | 0.7561 | 69.52% | 69.52% | 157.33 |
| Prior flow + roles | 0.7537 | 0.6782 | 85.87% | 67.50% | 0.7558 | 70.48% | 70.48% | 149.00 |
| Prior flow + flow history | 0.7591 | 0.7300 | 88.52% | 67.19% | 0.7639 | 37.14% | 37.14% | 43.33 |
| Prior flow + roles + flow history | 0.7552 | 0.8823 | 88.61% | 67.17% | 0.7641 | 40.95% | 40.95% | 47.00 |
| Prior flow + roles + wrong-host flow history | 0.7533 | 0.6629 | 85.58% | 67.52% | 0.7548 | 69.52% | 69.52% | 142.67 |
| Prior roles only | 0.2401 | 0.0133 | 0.00% | 0.00% | 0.0000 | 0.00% | 0.00% | 0.00 |
| Flow + log-volume/timing controls | 0.7582 | 0.6455 | 84.89% | 67.55% | 0.7523 | 63.81% | 63.81% | 128.00 |
| Flow/role/history + log-volume/timing controls | 0.7543 | 0.8964 | 88.41% | 67.21% | 0.7637 | 40.00% | 40.00% | 46.00 |
| Flow + controls + auth types/outcomes | 0.7590 | 0.6546 | 81.69% | 67.53% | 0.7394 | 60.00% | 60.00% | 106.00 |
| Flow/role/history + controls + auth types/outcomes | 0.7752 | 0.8687 | 88.55% | 67.26% | 0.7645 | 58.10% | 58.10% | 60.00 |
| Flow/role/history + controls + wrong-host auth | 0.7633 | 0.8890 | 88.40% | 67.23% | 0.7637 | 45.71% | 45.71% | 45.33 |
| Log controls + auth only | 0.3500 | 0.0367 | 0.00% | 0.00% | 0.0000 | 0.00% | 0.95% | 15019.67 |
| Log-volume/timing controls only | 0.3387 | 0.0370 | 0.00% | 0.00% | 0.0000 | 0.00% | 9.52% | 14277.67 |

## Paired component comparisons

Candidate minus reference. AP/F1 deltas use their original 0–1 scale; recall deltas are percentage points. All declared auth and log-control contrasts are shown, including wrong-host auth. No significance or independent-campaign confidence claim is made.

| Candidate − reference | Population | Δ exfil AP | Δ exfil F1 | Δ movement exact R (pp) | Δ movement any R (pp) | Δ benign false attacks |
|---|---|---:|---:|---:|---:|---:|
| Flow + controls + auth types/outcomes − Flow + log-volume/timing controls | all_test | +0.0091 | -0.0129 | -3.8095 | -3.8095 | -22.0000 |
| Flow + controls + auth types/outcomes − Flow + log-volume/timing controls | role_7 | +0.0291 | +0.0000 | -3.8095 | -3.8095 | -16.0000 |
| Flow/role/history + controls + auth types/outcomes − Flow/role/history + log-volume/timing controls | all_test | -0.0277 | +0.0008 | +18.0952 | +18.0952 | +14.0000 |
| Flow/role/history + controls + auth types/outcomes − Flow/role/history + log-volume/timing controls | role_7 | -0.0724 | +0.0000 | +18.0952 | +18.0952 | +14.0000 |
| Flow/role/history + controls + auth types/outcomes − Flow/role/history + controls + wrong-host auth | all_test | -0.0202 | +0.0008 | +12.3810 | +12.3810 | +14.6667 |
| Flow/role/history + controls + auth types/outcomes − Flow/role/history + controls + wrong-host auth | role_7 | -0.0339 | +0.0000 | +12.3810 | +12.3810 | +15.0000 |
| Flow + log-volume/timing controls − Prior current flow | all_test | +0.0092 | -0.0038 | -5.7143 | -5.7143 | -29.3333 |
| Flow + log-volume/timing controls − Prior current flow | role_7 | +0.1343 | +0.0000 | -5.7143 | -5.7143 | -20.0000 |
| Flow/role/history + log-volume/timing controls − Prior flow + roles + flow history | all_test | +0.0141 | -0.0005 | -0.9524 | -0.9524 | -1.0000 |
| Flow/role/history + log-volume/timing controls − Prior flow + roles + flow history | role_7 | +0.0379 | +0.0000 | -0.9524 | -0.9524 | -1.0000 |

## Destination-role shift: department → private services

Role code 7 has no fitting/calibration exfiltration examples. This is a later observed destination-role change, not a new independent campaign or a test of all unseen roles. All movement flows and the shifted exfiltration group still have different source-host associations. Reported macro-F1 includes all four classes even when a stratum has no support for one class.

| Arm | Macro-F1 | Exfil AP | Exfil P | Exfil R | Exfil F1 | Movement exact R | Movement any-attack R | Benign false attacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.2480 | 0.5786 | 0.00% | 0.00% | 0.0000 | 69.52% | 69.52% | 110.33 |
| Prior flow + roles | 0.2464 | 0.8695 | 0.00% | 0.00% | 0.0000 | 70.48% | 70.48% | 113.33 |
| Prior flow + flow history | 0.2539 | 0.4262 | 0.00% | 0.00% | 0.0000 | 37.14% | 37.14% | 42.33 |
| Prior flow + roles + flow history | 0.2502 | 0.7876 | 0.00% | 0.00% | 0.0000 | 40.95% | 40.95% | 46.33 |
| Prior flow + roles + wrong-host flow history | 0.2465 | 0.8132 | 0.00% | 0.00% | 0.0000 | 69.52% | 69.52% | 112.00 |
| Prior roles only | 0.1838 | 0.4060 | 0.00% | 0.00% | 0.0000 | 0.00% | 0.00% | 0.00 |
| Flow + log-volume/timing controls | 0.2537 | 0.7129 | 0.00% | 0.00% | 0.0000 | 63.81% | 63.81% | 90.33 |
| Flow/role/history + log-volume/timing controls | 0.2494 | 0.8255 | 0.00% | 0.00% | 0.0000 | 40.00% | 40.00% | 45.33 |
| Flow + controls + auth types/outcomes | 0.2600 | 0.7420 | 0.00% | 0.00% | 0.0000 | 60.00% | 60.00% | 74.33 |
| Flow/role/history + controls + auth types/outcomes | 0.2689 | 0.7531 | 0.00% | 0.00% | 0.0000 | 58.10% | 58.10% | 59.33 |
| Flow/role/history + controls + wrong-host auth | 0.2586 | 0.7871 | 0.00% | 0.00% | 0.0000 | 45.71% | 45.71% | 44.33 |
| Log controls + auth only | 0.1423 | 0.8851 | 0.00% | 0.00% | 0.0000 | 0.00% | 0.95% | 497.00 |
| Log-volume/timing controls only | 0.1640 | 0.8872 | 0.00% | 0.00% | 0.0000 | 0.00% | 9.52% | 253.67 |

Role-7 denominators: 1,576 Benign, 0 OtherAttackStage, 35 LateralMovement, 1,101 DataExfiltration.
Its target-pair exfiltration prevalence is 96.92%; a high pairwise AP can therefore be weak evidence. All pairwise APs, full confusions, captures and other role groups remain in EVIDENCE.json.

## Source-host diagnostics

These are published laboratory source addresses, used only to report strata. Literal source identities are excluded from model inputs. Within-host reporting cannot remove all time, operating-system or collection confounding. The sole movement source prevents an independent unseen-source movement evaluation.

### Source 10.1.3.17

32,312 Benign, 358 OtherAttackStage, 0 LateralMovement, 3,442 DataExfiltration.

| Arm | Macro-F1 | Exfil AP | Exfil P | Exfil R | Exfil F1 | Movement exact R | Movement any-attack R | Benign false attacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.4371 | 0.6800 | 87.99% | 67.53% | 0.7641 | 0.00% | N/A | 3.00 |
| Prior flow + roles | 0.4375 | 0.8475 | 87.94% | 67.50% | 0.7638 | 0.00% | N/A | 2.67 |
| Prior flow + flow history | 0.4394 | 0.8011 | 88.69% | 67.19% | 0.7646 | 0.00% | N/A | 0.33 |
| Prior flow + roles + flow history | 0.4399 | 0.9446 | 88.80% | 67.17% | 0.7649 | 0.00% | N/A | 0.00 |
| Prior flow + roles + wrong-host flow history | 0.4365 | 0.7917 | 87.86% | 67.52% | 0.7636 | 0.00% | N/A | 2.33 |
| Prior roles only | 0.2361 | 0.0794 | 0.00% | 0.00% | 0.0000 | 0.00% | N/A | 0.00 |
| Flow + log-volume/timing controls | 0.4363 | 0.6956 | 87.58% | 67.55% | 0.7627 | 0.00% | N/A | 3.00 |
| Flow/role/history + log-volume/timing controls | 0.4366 | 0.9449 | 88.60% | 67.21% | 0.7644 | 0.00% | N/A | 0.00 |
| Flow + controls + auth types/outcomes | 0.4361 | 0.7032 | 87.46% | 67.53% | 0.7621 | 0.00% | N/A | 5.33 |
| Flow/role/history + controls + auth types/outcomes | 0.4367 | 0.9375 | 88.65% | 67.26% | 0.7648 | 0.00% | N/A | 0.00 |
| Flow/role/history + controls + wrong-host auth | 0.4366 | 0.9417 | 88.56% | 67.23% | 0.7643 | 0.00% | N/A | 0.33 |
| Log controls + auth only | 0.2361 | 0.0953 | 0.00% | 0.00% | 0.0000 | 0.00% | N/A | 0.00 |
| Log-volume/timing controls only | 0.2361 | 0.0953 | 0.00% | 0.00% | 0.0000 | 0.00% | N/A | 0.00 |

### Source 10.1.3.8

39,845 Benign, 12,066 OtherAttackStage, 35 LateralMovement, 0 DataExfiltration.

| Arm | Macro-F1 | Exfil AP | Exfil P | Exfil R | Exfil F1 | Movement exact R | Movement any-attack R | Benign false attacks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior current flow | 0.5976 | N/A | 0.00% | 0.00% | 0.0000 | 69.52% | 69.52% | 65.67 |
| Prior flow + roles | 0.5971 | N/A | 0.00% | 0.00% | 0.0000 | 70.48% | 70.48% | 67.67 |
| Prior flow + flow history | 0.5814 | N/A | 0.00% | 0.00% | 0.0000 | 37.14% | 37.14% | 32.00 |
| Prior flow + roles + flow history | 0.5841 | N/A | 0.00% | 0.00% | 0.0000 | 40.95% | 40.95% | 36.33 |
| Prior flow + roles + wrong-host flow history | 0.5964 | N/A | 0.00% | 0.00% | 0.0000 | 69.52% | 69.52% | 66.33 |
| Prior roles only | 0.2170 | N/A | 0.00% | 0.00% | 0.0000 | 0.00% | 0.00% | 0.00 |
| Flow + log-volume/timing controls | 0.5989 | N/A | 0.00% | 0.00% | 0.0000 | 63.81% | 63.81% | 56.33 |
| Flow/role/history + log-volume/timing controls | 0.5836 | N/A | 0.00% | 0.00% | 0.0000 | 40.00% | 40.00% | 34.67 |
| Flow + controls + auth types/outcomes | 0.5990 | N/A | 0.00% | 0.00% | 0.0000 | 60.00% | 60.00% | 48.67 |
| Flow/role/history + controls + auth types/outcomes | 0.6068 | N/A | 0.00% | 0.00% | 0.0000 | 58.10% | 58.10% | 39.00 |
| Flow/role/history + controls + wrong-host auth | 0.5893 | N/A | 0.00% | 0.00% | 0.0000 | 45.71% | 45.71% | 38.33 |
| Log controls + auth only | 0.2977 | N/A | 0.00% | 0.00% | 0.0000 | 0.00% | 0.95% | 15005.00 |
| Log-volume/timing controls only | 0.2865 | N/A | 0.00% | 0.00% | 0.0000 | 0.00% | 9.52% | 14265.33 |

## Exfiltration policies and review workload

The complete [policy tables](POLICIES.md) include every arm, calibration-F1 global cutoff and all four nominal tails (0.1%, 0.5%, 1%, 2%) under global and role-conditioned decisions. They separate raw flags, false labels by true class, automatic exfiltration, both flags, insufficient-support reviews, total review queue and added benign work. EVIDENCE.json retains every seed, threshold and class-specific routing count.

All policies retain the prior current-flow model's attack alerts mechanically. Their movement flag is also copied from that baseline. Retaining an alert in a union queue does not repair stage classification or guarantee movement detection. Role 7 lacks calibration exfiltration support: flagged cases are marked for review, and an unsupported review is not a correct automatic label. Movement is absent from calibration globally, so no threshold has a calibrated movement-error guarantee.

## Interpretation boundaries

- This is already exposed development data from one campaign; fitting seeds do not create independent attacks.
- All fitted arms must be read with the volume/timing, availability-only and wrong-host controls. More information can identify a host or time regime instead of distinguishing attack semantics.
- Histories are strictly earlier by the qualified event clock. Unmeasured collection latency remains unresolved, and completed-flow statistics prevent a live early-warning claim.
- Exfiltration AP improvement alone is insufficient if exact stage precision/recall or movement recognition deteriorates. Binary any-attack detection is a separate endpoint.
- Abstention moves work to review. Precision among automatic outputs must be read alongside coverage, unresolved attacks and benign reviews; a smaller queue of decided cases can conceal difficult cases.
- A PASS calculation audit checks source/output binding and arithmetic, not human adjudication, attack truth, peer review or external deployment validity.

## Bound artifacts

[EVIDENCE.json](EVIDENCE.json) includes all mean and per-seed aggregate outcomes and paired contrasts. [PUBLICATION.json](PUBLICATION.json) binds the public files and source-summary hash. Private arrays and model files are retained in the experiment workspace and are not copied here.

[AUDIT.json](AUDIT.json) contains the bound independent calculation audit.
