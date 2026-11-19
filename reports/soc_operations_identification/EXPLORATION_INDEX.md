# SOC non-command detection: exploratory follow-on

This is a retrospective exploration of whether defender-visible host and
network telemetry can distinguish AI-labeled from human-labeled attack
sessions without terminal-command content. It is **not part of the current
Praxis paper**, does not test its H1-H3, and is not evidence of a deployable
SOC detector.

The analysis reuses nine existing sessions and evaluates 30-second windows
with whole-session holdouts. Network-flow-only telemetry scored macro-F1
0.691; excluding two process-creation event types from combined telemetry
scored 0.672. Filtering selected UDP traffic lowered flow-only macro-F1 to
0.568. These results are exploratory and do not establish that the measured
signal reflects operator behavior rather than the lab environment.

## Reports and reproduction

- [Visibility and environment results](SOC_VISIBILITY_ENVIRONMENT_RESULTS.md):
  matched comparisons, outside-login checks, uncertainty and limitations.
- [SOC telemetry audit](SOC_TELEMETRY_AUDIT.md): flow features, traffic
  filtering, coverage and host-only results.
- [SOC operations identification](SOC_OPERATIONS_IDENTIFICATION.md): broader
  command-free SOC analysis and its interpretation.
- [Audit reproduction runbook](../../scripts/DEFENDER_SOC_AUDIT.md): commands,
  prerequisites and data-handling constraints.

The reports use aggregate results only. Raw logs, pseudonymous session data,
predictions and private extraction outputs are not included.
