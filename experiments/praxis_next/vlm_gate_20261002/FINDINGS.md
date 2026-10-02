# PX-098 — Visual Host Windows as an Additional Warning-Gate Member

**Latest update:** the local numeric follow-up below found useful warning recovery from five-minute host summaries, with more benign alerts than the frozen research limit allowed. The original VLM pilot remains negative.

## Input qualification completed

| Existing detector, clean replay | Exfiltration flows missed out of 3,442 |
|---|---:|
| Seed 8101 | 43 |
| Seed 8102 | 61 |
| Seed 8103 | 1,100 |
| Original three-member OR gate | 42 |
| Full five-member OR gate | 26 |

The previously quoted 1,081 is not the miss count for seed 8103 under this clean, budget-2 replay. More importantly, a single member's misses are not the gate's unrecoverable misses.

There are 19,469 eligible host-hours, including 136 with source-side exfiltration-labeled flows. The original gate leaves 12 of those host-hours unwarned; the full gate leaves two. These counts are lower than the individual flow counts because other flows can already produce a warning for the same host-hour. A window warning does not prove that every exfiltration flow was identified.

The pilot contains 16 windows selected without labels and eight diagnostic windows containing known full-gate flow misses. The first cohort contains zero exfiltration-positive windows and cannot estimate attack recall. Four diagnostic windows are unwarned by the original gate; one is unwarned by the full gate. Report these cohorts separately.

All 24 selected input matrices were independently reconstructed from completed flows. The audit passed 6,673 flow-boundary and feature checks. Images and numeric text use the same five features and bins. The source and ground-truth tables remain outside the model input bundle.

Here, a host means an observed endpoint address. This initial population includes traffic peers and is not a verified inventory of managed SOC assets. A deployment-oriented expansion must freeze the monitored-asset scope before sampling or estimating workload.

## Completed AWS pilot

Qwen2.5-VL-7B-Instruct ran on an NVIDIA A10G. All 48 window requests produced replies. The frozen bare-JSON parser rejected all 48 because they contained Markdown fences. A separately disclosed [syntax-only replay](PARSER_AMENDMENT.md) removed those fences and recovered 48 valid answers without changing their content.

| Measure after syntax-only replay | Images | Matched numeric text |
|---|---:|---:|
| Exfiltration-containing diagnostic windows flagged | 0 / 8 | 0 / 8 |
| Additional exfiltration windows beyond original gate | 0 | 0 |
| Additional exfiltration windows beyond full gate | 0 | 0 |
| Benign windows flagged in representative cohort | 1 / 14 | 0 / 14 |

The representative cohort has two additional other-attack windows, so its benign denominator is 14 rather than 16. The eight diagnostic windows were deliberately selected around known misses; this is not a population attack-recall estimate. Four of those windows were unwarned by the original gate and one by the full gate; none was recovered.

**Pilot finding: this model, prompt and rendering did not provide the intended repair.** Images showed no advantage over matched text on the diagnostic target and added one benign warning. This does not establish that all visual approaches fail, but it gives no reason to scale this unchanged configuration.

The successful combined PX-098/PX-099 model process took 312.55 seconds, including 132.90 seconds to download/load the model. Peak allocated GPU memory was about 17.05 GB. See [runtime](RUNTIME.JSON), [raw responses](RESPONSES.jsonl), [counts](RESULTS.json) and the compute receipt. Runtime is not the same as billable instance time.

The first cloud start was rejected for capacity. The next allocation failed during dependency setup. The corrected third allocation completed; all attempts are retained. No production gate was changed.

## Interpretation

This remains the simpler of the two candidates, but is not yet a positive Praxis result. Before more inference, examine whether hour aggregation hides the small exfiltration flows and whether the monitored-asset scope is appropriate. Freeze any new representation and parser version before rerunning. Do not tune prompts against these eight known answers and call the outcome independent validation.

A [posthoc aggregation check](AGGREGATION_DIAGNOSTIC.json) found that the missed exfiltration flows account for less than 0.5% of the displayed outgoing byte total in seven of the eight diagnostic windows. This suggests that coarse byte totals may hide the target signal. It does not prove why Qwen missed them; a controlled representation comparison would be needed.

Visual intrusion detection and visual time-series analysis already exist. The proposed contribution must be the controlled residual-warning and workload comparison; [literature review remains incomplete](LITERATURE_CHECK.md).

[Protocol](PROTOCOL.md) | [Input audit](INPUT_AUDIT.json) | [Frozen inputs](FREEZE.json)

## Local follow-up: four numeric fits

Completed locally with four fixed LightGBM fits and no new AWS or VLM calls. All models use outgoing bytes, incoming bytes, flow count, DNS-associated flow count and distinct peers. Original train, calibration and test captures remain separate. Training uses exfiltration-positive groups and wholly benign groups; other-attack groups remain in evaluation. Thresholds were selected on calibration data to allow at most 14 alerts among its 1,450 benign host-hours.

The hour views contain twelve five-minute bins. The five-minute views contain one five-minute summary each; they use shorter decision windows, not finer within-bin timestamps. Destination/service views partition the same observed traffic. Partitioning and shorter windows also change the number of training examples, so this is not a causal test of rendering alone.

### Same-unit comparison against the original gate

Test support: 19,469 endpoint-hours, including 136 exfiltration-positive hours and 19,023 wholly benign hours. The original gate warns on 124 exfiltration-positive hours and 48 benign hours. Count each added endpoint-hour once even when several subgroups fire.

| View | Additional exfil-positive hours warned | Additional benign alerts | Increase in benign FPR | Frozen screen |
|---|---:|---:|---:|---|
| Hour, all host traffic | 7 | 385 | 2.02 percentage points | Fail |
| Five minutes, all host traffic | **11** | **360** | **1.89 percentage points** | Fail |
| Hour, destination/service groups | 7 | 492 | 2.59 percentage points | Fail |
| Five minutes, destination/service groups | 7 | 624 | 3.28 percentage points | Fail |

All four met the calibration budget, but test alert rates rose. None met the predeclared test screen of at least one additional exfil-positive hour with no more than a one-percentage-point increase in benign alerts. That screen is a research choice, not a measured analyst capacity or a universal definition of acceptable cost.

### Best observed tradeoff: five-minute host summaries

- Added to the original gate: exfil-positive hour coverage rises from **124/136 to 135/136**, with **360 additional benign alerts** and **375 additional cases of all labels**.
- Added to the full five-member gate: coverage rises from **134/136 to 136/136**, with **247 additional benign alerts** and **253 additional cases of all labels**. Its added benign FPR is 1.30 percentage points, also above the screen.
- Among the full gate's 26 missed exfiltration flows, **23 occur in a five-minute group that the numeric model warns on**. Median group-close delay for those 23 is **77.24 seconds after flow completion**, excluding inference time. This does not prove the model identified each individual flow or warned before data transfer.
- Twenty-three covered flows are not 23 newly recovered incidents. Only two previously unwarned exfil-positive host-hours are added beyond the full gate.

### What the representation check established

Across the 26 missed flows, the median share of outgoing bytes attributable to missed exfiltration flows in the assigned group rises from **0.16%** in hour views to **1.14%** in five-minute host summaries, **92.31%** in destination/service hour groups, and **100%** in destination/service five-minute groups. The corresponding counts of missed flows covered by their own scored group are **21, 23, 2 and 1**.

Making the target flow more prominent did not make it easier for these models to classify. Removing surrounding traffic can also remove useful context. No exact exfil-versus-benign feature duplicates were found in the evaluated groups, but that does not establish generalizable separation.

The trained numeric model can recover warnings using the original hour representation. Therefore, the VLM pilot's failures do not establish that the input lacked all useful information. This is not a matched training comparison: the numeric models received supervised training and Qwen did not.

### Decision and limits

**Do not scale up the unchanged VLM pilot.** The five-minute numeric member is the best lead from this comparison. Its next test should address calibration-to-test alert growth and transfer to a separately qualified execution under a new freeze. Do not adjust the threshold against these test outcomes and call it independent confirmation.

The result is from one previously exposed campaign, one fixed seed per representation, and observed endpoint addresses rather than a verified managed-asset inventory. The hour fits contain only 31 positive training groups; the five-minute fits contain 349. There is no new novelty or production-readiness claim. The separate audit passed 154,440 checks, including source reconstruction for all 26 missed flows and 12 wholly benign controls per view.

[Frozen local protocol](local_followup/PROTOCOL.json) | [Results](local_followup/RESULTS.json) | [Audit](local_followup/AUDIT.json) | [Tradeoff chart](local_followup/tradeoff.png) | [Diagnostic byte views](local_followup/diagnostic_views.png) | [Benign byte views](local_followup/benign_views.png)
