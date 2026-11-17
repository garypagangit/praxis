# Defender-visible telemetry experiment

## Question and scope

Can defender-side Windows Security, Sysmon and VPC flow metadata distinguish
human from AI operators in the existing exercise, without terminal commands?
This is an **exploratory follow-on**, not a preregistered or independent
replication. Existing study login start/end metadata defines the evaluation
periods; identifying an attack period from defender data is not tested.

For alignment, the script parses only the first `start` record of each included
login. It hashes each whole recorder file for integrity, but does not parse or
use terminal input/output records or reconstructed commands. The restricted
defender-side source records are read locally; their
free text, command lines, addresses, ports, host names and account names are
never added as features or written to the output.

## Fixed analysis

- All full, non-overlapping 30-second windows in the included logins are used,
  including windows dropped by the original terminal-activity filter. Partial
  final windows are excluded. The windows are not selected by terminal contents.
- Use Security and Sysmon from `dc01`, `dc03`, `srv02` and `srv03`, the common
  channels present in all nine sessions. `dc02` is excluded because some
  sessions lack the required channels.
- Windows Security and Sysmon features are counts of a fixed allowlist of event
  IDs plus an `other` count. Flow features count records, packets, bytes,
  protocols and accept/reject outcomes; IPs, ports and interface IDs are not
  features. A flow is assigned to the window containing its **end** time. Flow
  aggregation intervals can span multiple 30-second windows; this assignment
  does not establish when within the interval the traffic occurred, and
  delivery delay means this is not a real-time latency evaluation.
- Evaluate only windows inside the first-to-last observed timestamp extent of
  every required stream, and exclude windows overlapping any VPC `SKIPDATA`
  interval; zero-duration `SKIPDATA` marks the window containing its timestamp.
  First/last coverage is a coarse check: it does not prove complete collection
  inside the interval or on every interface, and a zero-duration gap does not
  reveal the extent of missing data. Missing channels and collection differences
  can still bias the result. The extraction manifest reports candidate and
  eligible windows by session so exclusions can be compared between classes.
- Compare four predetermined feature sets on the **same eligible windows**:
  Security only, Sysmon only, flows only and combined. Fixed logistic regression,
  `log1p` counts, training-fold standardization and equal class/session training
  weights are fitted within each leave-one-session-out fold. The threshold is
  fixed at 0.5. No terminal-derived features, labels, session IDs, timestamps,
  stage IDs or source host IDs enter the model.
- Report pooled window macro-F1, AI recall, human-window false-positive rate,
  session accuracy (mean window probability, threshold 0.5), and a 2,000-draw
  class-stratified session bootstrap interval. Results compare human and AI
  *attack* sessions; human false positives are not false alarms on benign data.
- For each feature set, refit every leave-one-session-out fold for all 126 ways
  of assigning four of nine sessions to AI. The p-value is the fraction whose
  macro-F1 is at least the true labeling's, including that labeling. Report
  Holm-adjusted p-values across the four feature sets. The permutation
  interpretation requires exchangeable session labels; lab-range, model,
  environment or collection differences can violate this assumption.

Every opened source is checked against Freeze 1 before use. Source records and
the original study folder are not modified. The new outputs are not part of the
original freeze. They include pseudonymous session keys, class labels and
features; treat them as restricted and keep them outside Git. The script hash
is fixed at extraction and checked again at evaluation; if code changes, start
a fresh output directory rather than mixing versions.

## Run

Use the Python 3.10.12 environment from `STUDY3_REPRODUCTION.md`. Extraction
reads and hashes substantial compressed logs and may take several minutes.
The evaluation uses CPUs, not GPUs; the exact permutation test fits 4,536
leave-one-session-out models.

```powershell
$python = 'C:\private\study3-venv\Scripts\python.exe'
$study = 'C:\Users\garyp\OneDrive\Desktop\study 3'
$output = 'C:\private\defender-telemetry-study'
& $python scripts\defender_telemetry_experiment.py extract --source $study --output $output
& $python scripts\defender_telemetry_experiment.py evaluate --output $output
```

The output directory must not already exist. `features.csv` and
`extraction.json` document the source hashes, coverage and common windows;
`RESULTS.md` summarizes the results, and `results.json` contains the detailed
results and predictions. `evaluate --smoke`
omits permutations and writes `smoke-results.json`; it is a plumbing check,
not evidence of significance. Existing outputs are not overwritten.

Do not interpret the results as detecting malicious activity among benign
traffic, as proof of autonomous operation, or as generalization beyond this
small lab dataset. Independent new operators, AI models, networks and lab ranges
are necessary for validation.
