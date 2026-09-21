# Execution notes

The first launch stopped while creating its pre-fit receipt because a relative protocol path was compared to an absolute repository path. No model was fitted, no prediction was generated, and the first output directory remained empty. The runner now resolves the path for receipt bookkeeping. The protocol, features, labels, settings and decision gates were unchanged. The completed run uses a fresh immutable directory, `window_diagnostic_v1/run2`.

This is a software launch correction before fitting, not a scientific amendment based on model results.
