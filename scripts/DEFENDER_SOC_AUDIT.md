# Reproducing the SOC telemetry audit

This follow-on reads the frozen Study 3 logs and completed private defender
experiments; it does not change them. Use the existing Python environment and
reproduction prerequisites from
[DEFENDER_EXPANDED_EXPERIMENT.md](DEFENDER_EXPANDED_EXPERIMENT.md). The
following variables must be absolute local paths:

```powershell
$python = 'C:\path\to\python.exe'
$study = 'C:\path\to\study 3'
$prior = 'C:\path\to\defender-telemetry-30s-final'
$expanded = 'C:\path\to\defender-expanded-study'
$out = 'C:\path\to\private-audit-outputs'
```

`$prior` is the completed 30-second extraction; `$expanded` is the completed
expanded extraction and behavior evaluation. `$out` must be outside the
repository and inputs, and each named output directory below must not exist.
Detailed outputs contain pseudonymous session data, predictions or feature
tables and must remain private. Do not commit raw logs, addresses, identifiers
or private outputs.

```powershell
& $python scripts\defender_flow_investigation.py --source $study --prior $prior --output "$out\flow-investigation"
& $python scripts\defender_flow_attribution.py --source $study --prior $prior --output "$out\flow-attribution"
& $python scripts\defender_flow_ablation.py --experiment $expanded --output "$out\flow-ablation"
& $python scripts\defender_host_only.py extract --source $study --experiment $expanded --output "$out\host-only"
& $python scripts\defender_host_only.py evaluate --experiment $expanded --output "$out\host-only"
& $python scripts\defender_flow_filter.py extract --source $study --experiment $expanded --output "$out\flow-filter"
& $python scripts\defender_flow_filter.py evaluate --experiment $expanded --output "$out\flow-filter"
```

Each command must succeed before proceeding. Extractions verify frozen input
hashes; evaluation checks input and code hashes. If code changes after an
extraction or a run is interrupted, use a fresh output directory and repeat
the extraction. Evaluation refits all 126 session-label assignments and can be
CPU-intensive. The port filter is a post hoc sensitivity analysis, not a
reliable process identifier. See the [results and limitations](../reports/soc_operations_identification/SOC_TELEMETRY_AUDIT.md).

## Visibility and outside-login controls

After completing the flow investigation above, use a fresh output directory:

```powershell
& $python scripts\defender_visibility_audit.py extract --source $study --experiment $expanded --prior-investigation "$out\flow-investigation" --output "$out\visibility-audit"
& $python scripts\defender_visibility_audit.py evaluate --experiment $expanded --output "$out\visibility-audit"
& $python scripts\defender_visibility_transfer.py --experiment $expanded --audit-output "$out\visibility-audit" --output "$out\visibility-transfer"
& $python scripts\defender_flow_only_filter.py --experiment $expanded --filtered-output "$out\flow-filter" --visibility-output "$out\visibility-audit" --output "$out\flow-only-filter"
```

The matched process-free model removes Security 4688 and Sysmon 1 records,
checks their per-window counts against the prior extraction, and removes them
from five-second bins before recomputing timing and co-activity. Other
process-related and correlated records remain. The matched flow-only model
uses only VPC flow features and flow timing. Both use the previous
common-coverage 30-second attack windows.

The separate flow-only controls use covered windows up to five minutes before
the first and after the last included login. These windows are assigned the
session's label; the active operator is unknown and they are not established
as benign. After-login windows may contain continuing activity or effects.
Flow coverage is required but host coverage is not. The before-only analysis
may include fewer sessions than the matched attack analysis. Interpret these
as shortcut checks, not causal tests or evidence of deployability.
The transfer check also applies each flow-only model trained on other
sessions' attack windows to the held-out session's outside-login windows. It
verifies that held-out attack predictions match the prior flow-only result;
outside-login transfer metrics are descriptive and have no permutation test.

Evaluation holds out sessions and repeats fitting over all class-preserving
session-label assignments: 126 for nine sessions, or 70 for eight sessions
with four labels of each class. Holm correction covers only the five new
exploratory analyses, not earlier exploration. Paired intervals use fixed
predictions and do not account for refitting or model selection. Outputs are
restricted and should not be committed.

The flow-only port sensitivity comparison reuses the completed port-filter
extraction above, verifies matching windows and unchanged non-flow fields, and
reproduces the previous flow-only predictions. It retrains on the filtered
flow features and repeats all 126 session-label assignments. Its raw
permutation p-value is post hoc and tests label association, not the change
from the unfiltered model. The fixed-prediction paired interval does not
include refitting or selection uncertainty.
