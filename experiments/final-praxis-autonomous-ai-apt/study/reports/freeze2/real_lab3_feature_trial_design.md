# Real lab logs, study 3: feature and trial design

Drafted 2026-11-12 02:50 EST from the pipeline review in `real_lab3_pipeline_register.md`. For study 3 it replaces the feature and model parts of `real_lab2_preprocessing_design.md` (§8, §11, §15) and `STUDY2B_PROTOCOL.md`; those stay as the record of studies 2 and 2b. It follows `real_lab3_preprocessing_design.md` (the rules that produce the windows) and sits beside `real_lab3_eda_handoff.md`.

**Status: approved by the user on 2026-11-12. F1 to F9 and F11 at 22:05 EST, F10 at 22:18 EST; F12 on 2026-11-13 at 03:05 EST; F13 to F15 on 2026-11-13 between 05:51 and 05:57 EST; F16 on 2026-11-13 at 06:11 EST (§12). F17, the readings of the trial code (§6a), was applied on the user's instruction of 06:11 EST to go on to Freeze 2 and the trials; the user has not gone through it item by item.** The decisions in §1 are the user's; the rest was proposed by Claude and approved. EDA Pass 1 was run and the feature table was built on Nov 13, and the table was rebuilt at 05:57 EST with F13 and F14 (`real_lab3_eda_pass1_feature_run.md`). The trial code was written and the plumbing run made on Nov 13 (`real_lab3_trial_run.md`). **This is the document as it stood when Freeze 2 was written: every trial had been fitted in the plumbing run and none had been scored.** All nine sessions are in hand as of Nov 13 (preprocessing design §0, §2).

## 0. Plan
1. Preprocessing on all sessions, then Freeze 1 (preprocessing design).
2. EDA Pass 1 (counts only).
3. Feature table and per-command table (§3, §4).
4. Review of the feature table (§10; closed by the user on Nov 13). EDA Pass 2 on training rows was moved after the trials, as a report only (F16).
5. Plumbing run: every trial fitted, nothing scored (§10).
6. **Freeze 2:** this document, the feature and trial code, the feature table, the EDA Pass 1 outputs, the plumbing log.
7. Trials, each scored once (§7 to §9).
8. EDA Pass 2 as a report (F16), and EDA Pass 3.

The design is written for 5 human and 4 AI sessions, which are in hand as of Nov 13. It cannot run on fewer than 3 AI sessions (§7.1).

## 1. Decisions this design rests on (user, Nov 12)

| # | Decision |
|---|---|
| P1 | Whole sessions are held out. Every window is scored once, by models that never saw its session. Target: 5 human, 4 AI |
| P2 | Held-out-session macro-F1 is the main result. All five models are reported. There is no five-model mean |
| P3 | Command diversity and transition entropy are computed for the window and over the look-back; the H1 ablation runs on both forms |
| P4 | The look-back is 2 minutes in the main configuration. No longer look-back for now |
| P5 | Model settings are the library defaults |
| P6 | The honeypot word-list columns are retired |
| P7 | One column for each quantity. No repeated or engineered extra columns; the log is applied inside logistic regression's own pipeline |
| P8 | The chance baseline relabels whole sessions and runs every relabeling |
| P9 | The command reconstruction is part of the preprocessing and of Freeze 1 (preprocessing design A7) |
| P10 | The 2b model is not run on the new sessions. A follow-up (3b) is built only if study 3 turns out to be missing something |
| — | Every session's score is reported; no session cut-off is fitted |
| — | One window threshold, set for macro-F1. No threshold set for AI precision; precision is reported at the main threshold |
| — | No SMOTE and no SMOTE side comparison |
| — | The no-context row and the input-bearing-windows row are kept |
| — | H1 is the claim that the two features improve classification, and the ablation decides it. Clearing the macro-F1 of Alt (2026) is a goal for the classifier, reported beside the main result |

## 2. Terms
Session, login, window and classifier data are as in the preprocessing design §1. Added here:

| Term | Meaning |
|---|---|
| **Look-back** | The 2 minutes of the same login before a window: its previous 4 windows at 30 s, 2 at 60 s |
| **Tier** | A group of features by what they read: behavior, command content, context, input channel |
| **Configuration** | A set of tiers given to the models |
| **Fold** | One held-out session and the models trained on the other sessions |
| **Calibration fold** | Inside a fold, one training session left out in turn to get predictions for calibration and the threshold |
| **Session score** | The mean calibrated P(AI) over a held-out session's windows |

## 3. Feature step
- **Reads** only `data/`: the cleaned recorder and audit records of each kept window, the window table, and the command list written by the preprocessing (§6.7 there). It never reads a label, the split file or a stage.
- **Writes** `data/features/w30/` and `w60/`: the feature table (one row for each kept window), a column file (tier, kind and definition of every column, with input and output hashes), and the per-command table the EDA asked for (command text, entry style, programs started).
- **Row by row.** Every feature is a fixed rule applied to one window and, for the context tier, to earlier windows of the same login. Nothing is fitted across windows.
- **Rules carried from studies 2 and 2b:**
  - A command belongs to the window that holds its Enter. `exit` and `logout` are not commands. Validator commands are already gone. A line typed into a program that is waiting for input is a command that starts no program, in both classes (preprocessing design A14, A15).
  - A command's gap is the time since the previous kept command in the same login.
  - Only successful program starts are counted; the login shell's own start is not. Programs that ran before the login's first submitted line (message of the day, profile scripts) are not counted either (F13).
  - Program output is what is printed after a command's Enter until the shell prompt comes back or the operator starts the next line, whichever comes first (preprocessing design A15). Validator output is not counted.
  - Process depth uses the rule of D29a.
- **Undefined is not zero.** A column with nothing to compute on is stored as empty.
- **Counts, not rates.** Study 2 kept both a count and the same count divided by the window length. Study 3 keeps the count. A login's last window can be 15 to 30 s long and is used as it is.

## 4. Features
60 columns in four tiers. Study 2b had 115.

### 4.1 Behavior (18): what the operator's commands did, without reading the command text
| Column | Definition | Undefined when |
|---|---|---|
| `cmd_count` | Commands submitted in the window | never |
| `gap_mean`, `gap_median`, `gap_min`, `gap_max`, `gap_std` | Over the gaps of the window's commands | no gap in the window |
| `gap_cv` | `gap_std` ÷ `gap_mean` | no gap, or mean 0 |
| `gap_autocorr` | Correlation between each gap and the next, within the window | fewer than 4 gaps (F14) |
| `exec_count` | Programs started by the login in the window, from the login's first submitted line onward (F13) | never |
| `exec_distinct` | Distinct programs among them | never |
| `exec_per_cmd` | `exec_count` ÷ `cmd_count` | no command |
| `proc_depth_max` | Longest parent-to-child chain of program starts; the login shell is 0 | never |
| `output_bytes` | Program output bytes that appear in the window | never |
| `output_per_cmd_mean`, `output_per_cmd_cv` | Mean, and standard deviation ÷ mean, of the total output of each command submitted in the window | no command; for the second, also mean 0 |
| `fail_ratio` | Share of the window's commands whose output holds an error line (§4.5) | no command |
| `shell_error_count` | Shell error lines in the output of the window's commands (§4.5) | never |
| `retry_count` | Failed commands in the window that are followed by a similar command (§4.5) | never |

`retry_count` compares command text but stores only a count, so it stays in this tier as it did in 2b.

### 4.2 Command content (14): the shape of the submitted text
| Column | Definition | Undefined when |
|---|---|---|
| `chars_submitted` | Characters of command text submitted | never |
| `cmd_len_mean`, `cmd_len_max` | Length of each command's first line | no command |
| `cmd_unique` | Distinct command texts | never |
| `cmd_diversity` (H1) | `cmd_unique` ÷ `cmd_count` | no command |
| `transition_entropy` (H1) | Entropy of the program-to-program transitions in the window (§4.5) | fewer than 2 commands |
| `prog_distinct` | Distinct program names (the first word of each command) | never |
| `prog_entropy` | Entropy of the program-name counts | no command |
| `flags_per_cmd` | Mean number of flags in a command, capped at 12 a command | no command |
| `pipes_per_cmd` | Mean number of pipes in a command | no command |
| `chain_ratio` | Share of commands that chain with `&&`, `\|\|` or `;` | no command |
| `redirect_ratio` | Share of commands with `<` or `>` | no command |
| `help_count` | Commands that ask for help | never |
| `io_ratio` | `output_bytes` ÷ `chars_submitted` | no characters |

Here-document bodies are set aside before flags, pipes, chaining and redirects are counted (§4.5, F12).

### 4.3 Context (12): the same login over the look-back
Past windows only. A window in the look-back that was not kept counts as empty. Near a login's start the look-back holds fewer windows.

| Column | Definition | Goes with |
|---|---|---|
| `ctx_cmd_count`, `ctx_exec_count`, `ctx_output_bytes` | Sums of the window columns over the look-back | behavior |
| `ctx_active_windows` | Look-back windows with at least one command | behavior |
| `ctx_chars_submitted` | Sum over the look-back | command content |
| `ctx_cmd_len_max` | Longest command in the look-back | command content |
| `ctx_cmd_diversity`, `ctx_transition_entropy` (H1) | The two H1 features over the commands of the look-back and the window together, in order | command content |
| `ctx_entry_typed`, `ctx_entry_paste`, `ctx_entry_recall`, `ctx_entry_line` | Sums of the entry-style counts over the look-back | input channel |

### 4.4 Input channel (16): how commands reached the shell
Reported separately, never in the main configuration. Raw output bytes stay out, and the Enter byte stays normalized, as in 2b.

| Column | Definition | Undefined when |
|---|---|---|
| `entry_typed`, `entry_paste`, `entry_recall`, `entry_line` | Commands by entry style (§4.5) | never |
| `typed_ratio`, `paste_ratio`, `line_ratio` | Those counts ÷ `cmd_count` | no command |
| `interkey_median`, `interkey_cv` | Time between keystrokes in typed commands: median, and standard deviation ÷ mean | fewer than 3 intervals |
| `backspace_rate` | Backspaces ÷ characters typed, in typed commands | no typed characters |
| `paste_enter_latency` | Median time from the end of a paste to its Enter | no pasted command |
| `multi_cmd_write_ratio` | Share of commands that arrived several to one write | no command |
| `fullscreen_keys` | Input records while a full-screen program is open | never |
| `compose_time_median` | Median time from a command's first keystroke to its Enter | no command with a first keystroke |
| `input_writes_per_cmd` | Input records ÷ `cmd_count` | no command |
| `input_bytes` | Raw input bytes | never |

### 4.5 Patterns and constants, written out for review
The synthetic project's lists are not used. These are defined here; the ones marked "study 2" are the values in the study 2 code.

| Item | Definition |
|---|---|
| Program name | The first word of the command's first line, after any leading `NAME=value` words and `sudo`. If it holds a `/`, the part after the last one |
| Quoted text | Text between single quotes is set aside before pipes, chaining and redirects are counted (study 2) |
| Here-document body | The lines between a here-document's opening line and its closing word. Set aside before flags, pipes, chaining and redirects are counted. Its characters still count in `chars_submitted`; the length columns read the first line, as before (F12) |
| Flag | A space followed by a hyphen (study 2) |
| Pipe | `\|` that is not part of `\|\|` (study 2) |
| Help | ` --help`, ` -h` as a whole word, or a line starting with `man ` or `help ` (study 2) |
| Error line | Output that contains, in any letter case: `command not found`, `No such file or directory`, `Permission denied`, `syntax error`, `error:`, `failed`, `denied`, `refused`, `timed out`, `Traceback (most recent call last)` |
| Shell error line | `command not found`, `No such file or directory`, `Permission denied`, `syntax error`, `cannot access`, `Is a directory`, `Not a directory`, `invalid option` |
| Failed command | A command whose own output holds an error line. There are no exit codes in the data |
| Similar command | Text similarity (Python `difflib` ratio on the first 200 characters) above 0.6 when the program name is the same, above 0.8 otherwise (study 2) |
| Retry | A failed command whose next command in the login is similar. Counted in the failed command's window |
| Transition entropy | With program names p1 … pn in order, the n − 1 transitions (pi → pi+1) are counted by pair. The value is the Shannon entropy of those counts, in bits |
| Gap autocorrelation | Pearson correlation between gaps 1 … m − 1 and gaps 2 … m. Needs at least four gaps: three give two points, which is always +1 or −1 (F14). Undefined when either has no variation |
| Entry style | In this order: **recalled** when the line's keystrokes include a history key; **pasted** when its text arrived inside the terminal's paste markers; **whole line** when the command and its Enter arrived in one write; **typed** otherwise |
| Full-screen program | Between the terminal's alternate-screen on and off sequences |

### 4.6 What left the 2b list
| Left out | Why |
|---|---|
| Five attack-phase ratios; privilege-escalation, cover-tracks and sensitive-file flags; four engineered columns built on them | P6 |
| Tool count, file-transfer count, `wget`/`curl` flag | Word lists. The tool list is in the synthetic module, and a list written for this exercise would name each stage's tools (F2, approved) |
| Sentinel ratio, `bash -c` ratio, "any wrapper" | Zero once the wrapper is removed |
| Longest idle gap, command bigram entropy, repeated-command ratio, latency variability | Repeats of `gap_max`, `transition_entropy`, `cmd_diversity`, `gap_cv` |
| Four per-second rates | Repeats of counts. Execs are kept as a count |
| The other engineered columns | P7 |
| Burst ratio, idle-gap count, latency entropy | Each needs a cut-off that was set in the synthetic module. `gap_min`, `gap_max` and `gap_cv` carry the same information without one (F1, approved) |

### 4.7 Readings approved at implementation (F15)
Where §3 to §4.5 left a detail open, the feature code applies these. The user approved them on Nov 13, between 05:51 and 05:57 EST. None looks at a label. The record of the build is `real_lab3_eda_pass1_feature_run.md`.

| # | Reading | Where in the design |
|---|---|---|
| R1 | **Program output is counted as text:** escape sequences and carriage returns are removed, as in the command list's own figure. Each byte goes to the window of the output record that carried it | §3, `output_bytes` |
| R2 | **A command belongs to the window of its Enter's recorder record** | §3 |
| R3 | **Standard deviations divide by n.** One gap gives `gap_std` 0 and `gap_cv` 0, which is what "undefined when no gap" implies | §4.1 |
| R4 | **A program start is a successful exec record of the window file.** Its name is the last part of the path that was executed, or of the binary if there is none (`python3`, not `python3.13`) | `exec_count`, `exec_distinct` |
| R5 | **Process depth is followed inside the window.** The parent is the latest start of the parent's process number at or before the child's (D29a). A parent with no start in the window counts as the login shell. Process numbers are per-window, so a chain cannot be followed into an earlier window | `proc_depth_max` |
| R6 | **A failed command** has an error-list phrase anywhere in its output, in any letter case. **A shell error line** is an output line holding a shell-list phrase, matched as written | §4.5 |
| R7 | **A retry** compares a failed command with the next command of the login that is not `exit`, in whatever window it falls | §4.5 |
| R8 | **Here-document bodies are set aside for flags, pipes, chaining and redirects. Single-quoted text is set aside for pipes, chaining and redirects** and not for flags, as §4.5 lists them. Help is searched in the whole command text | §4.5 |
| R9 | **A flag** is each occurrence of a space followed by a hyphen, capped at 12 a command | §4.5 |
| R10 | **Entry style** is read from the command list: recalled when the line has a history key, pasted when it has a paste, whole line when it arrived in one write, typed otherwise | §4.5 |
| R11 | **Keystroke intervals** are the times between the input records of a typed command, first key to Enter, pooled over the window's typed commands | `interkey_*` |
| R12 | **Paste to Enter** runs from the last input record holding the paste-end marker to the Enter, for commands whose entry style is pasted | `paste_enter_latency` |
| R13 | **Several commands to one write:** the command's Enter record also holds another line's Enter | `multi_cmd_write_ratio` |
| R14 | **A full-screen program** is open between the alternate-screen on and off sequences; a shell prompt also closes it, as in the command reconstruction | `fullscreen_keys` |
| R15 | **Compose time** is the Enter time minus the first-key time of the command list. A line that arrived in one write has 0, so the column is defined for every command | `compose_time_median` |
| R16 | **`ctx_cmd_len_max` is undefined when the look-back holds no command.** The look-back forms of the H1 features use the commands of the kept look-back windows and of the window, in order | §4.3 |
| R17 | **Per-command table:** one row for each command of a kept window. Its programs are the successful starts in kept windows from its Enter until the Enter of the next line in the login, each with the window it fell in | §3 |
| R18 | **The feature table holds `window_id` and the 60 columns only.** No session, stage, time or position column | §8, column guard |
| R19 | **Commands in windows that were not kept** (5 at 30 s, 2 at 60 s) are in no row. They still count as the previous command for the next command's gap | §3 |
| R20 | **The feature code imports two things from the frozen preprocessing code:** the terminal tokens, so program output is defined the same way in both steps, and the leak-audit patterns | §3 |

## 5. Configurations
| Configuration | Tiers | Columns | Role |
|---|---|---|---|
| **Main** | Behavior, command content, and their context columns | 40 | Main result |
| No command content | Behavior and its context columns | 22 | Reported beside the main result |
| No context | Behavior, command content | 32 | Shows what the context adds |
| Input channel | Main, input channel and its context columns | 60 | Reported separately |
| H1 ablation | Main without the four H1 columns (36); the window form re-added (38); the look-back form re-added (38); both, which is Main | 36 to 40 | Tests H1 |

Each configuration is also scored within each stage group (§7.5).

## 6. Models
- **Five models:** logistic regression, random forest, gradient boosting, histogram gradient boosting, XGBoost. All get the same feature table, folds and weights.
- **Settings: library defaults (P5).** The values are read from the installed libraries and written to the run record. In scikit-learn 1.7 and XGBoost 3 the main ones are:

| Model | Default |
|---|---|
| Logistic regression | C = 1.0, L2 penalty |
| Random forest | 100 trees, no depth limit, leaf size 1 |
| Gradient boosting | learning rate 0.1, depth 3, 100 trees |
| Histogram gradient boosting | learning rate 0.1, 100 rounds, 31 leaves, no depth limit |
| XGBoost | learning rate 0.3, depth 6, 100 trees |

- **Departures from the defaults, with reasons:**
  - Random seed 42 everywhere, so a rerun gives the same numbers.
  - Logistic regression may run up to 1,000 iterations, so the fit converges. This does not change the model being fitted.
  - XGBoost runs on one thread, for the same reason as the seed.
- **Weights.** A training window's weight is 1 ÷ (2 × the number of training sessions in its class × the number of training windows in its session). Each class then has half the total weight, and each session an equal share of its class. The same weights are used for fitting and for calibration. The threshold and the reported metrics are not weighted.
- **Undefined values.** Random forest, histogram gradient boosting and XGBoost take them as they are. Logistic regression and gradient boosting get the training median and one extra column, "the window has commands". If the installed version of a model does not accept undefined values, it is treated like the second group.
- **Scaling, logistic regression only.** Counts, sizes and times get log(1 + x); ratios, shares, entropies and correlations are left alone. Then every column is standardized. The kind of each column is recorded in the column file.
- **Fitted inside training sessions only:** medians, scaling, weights, the model, the calibration and the threshold.
- **No search and no selection.** No setting is tuned and no model is chosen on any score.

## 6a. Readings applied by the trial code (F17)
Where §6 to §9 left a detail open, the trial code (`code/trials/`, version `study3-trials-1.0`) applies these. None looks at a score: each was fixed before the plumbing run and is frozen with the code in Freeze 2. They were applied on the user's instruction of Nov 13, 06:11 EST, to go on to Freeze 2 and the trials, and were not put to the user one by one first. The record of the run is `real_lab3_trial_run.md`.

| # | Reading | Where in the design |
|---|---|---|
| T1 | **Weights are multiplied by the number of training rows, so they average 1.** The shares are as §6 says. The library defaults assume weights near 1: with weights that sum to 1, logistic regression's penalty would weigh about 900 times more against the data, and histogram gradient boosting and XGBoost could not split at all (each has a floor on the weight in a leaf) | §6, weights; P5 |
| T2 | **Platt scaling is fitted as scikit-learn fits it** (Platt's targets), with the weights of §6. Its input is what scikit-learn's own calibration reads from each model: the decision value for logistic regression, gradient boosting and histogram gradient boosting; the predicted probability of AI for random forest and XGBoost, which have no decision value | §7.1, step 3 |
| T3 | **Threshold.** The candidate cuts are the midpoints between neighbouring distinct calibrated values of the calibration predictions. A window is called AI at or above the cut. Among cuts with the same macro-F1, the one nearest 0.5, then the lower. Macro-F1 is not weighted here (§6) | §7.1, step 4 |
| T4 | **p-value of a paired difference:** one-sided, (1 + resamples in which the difference is zero or below) ÷ (resamples + 1). "Above zero, Holm-adjusted" means the observed difference is positive and its Holm-adjusted p is 0.05 or below | §9, H1 and H3 |
| T5 | **The training median** is taken over the defined values of the training rows and is not weighted; a column undefined in every training row gets 0. "The window has commands" is `cmd_count` above 0 | §6, undefined values |
| T6 | **Standardizing is not weighted.** A column that is constant in the training rows stays at 0 | §6, scaling |
| T7 | **Inside sessions:** main configuration, 30 s windows. The weights of §6 are computed on the rows that are fitted, and again on the validation rows for the calibration. The look-back is counted in window indexes of the login (4 windows at 30 s): 8 training rows and no validation row fall inside it | §7.6 |
| T8 | **Input-bearing windows** are kept windows with at least one input record in the window table: 818 of 951. They are used for training and for scoring alike. Their context columns are those of the full table | §7.7 |
| T9 | **Chance baseline.** A relabeling changes a session's class everywhere: weights, fitting, calibration, threshold and scoring. 30 s windows. The 126 relabelings are numbered in the order of the session labels | §8, control 2 |
| T10 | **Shared fits.** The model that leaves out sessions s and t is the same fit whether s is held out and t is its calibration fold, or the other way round. It is made once: 36 such fits and 9 final fits for a model, 45 in place of 81. The self-test shows the predictions are identical to the long way | §7.1 |
| T11 | **One thread a process, for every library,** so that a rerun gives the same numbers on any machine. This extends the XGBoost departure of F7 and changes no model | §6, departures |
| T12 | **Every task carries a hash of its fitted calibrations and thresholds.** The plumbing run writes it and the scored run recomputes and compares it, so the fit that is scored is the fit that was frozen. A hash is not a score. The plumbing run also writes each task's run time (§10) | §10, plumbing run |
| T13 | **The stage group is joined to the predictions after scoring,** from the description file, and never enters a model. A stage group in which one class has no window gets no macro-F1 or AUC | §7.5 |
| T14 | **Intervals are percentile intervals.** One set of 2,000 draws of whole sessions (seed 42) is used for every model and trial, which is what makes the differences paired | §7.4, §9 |
| T15 | **PR-AUC is average precision** with AI as the positive class. The AUCs and the Brier score are computed on calibrated P(AI), pooled over the folds | §7.2 |
| T16 | **Freeze 2 keeps a byte copy of this document and of the EDA handoff** in `reports/freeze2/`. Status lines added to the living documents afterwards do not touch what was frozen, and the scored run checks the copies | §10, Freeze 2 |

The scored part of the code was tried before the freeze on a made-up study tree only (`code/trials/selftest_fixture.py`, `selftest_checks.py`). No real window was scored before Freeze 2.

## 7. Evaluation

### 7.1 Main evaluation: leave one session out
For each of the nine sessions in turn:
1. The session is held out. The other eight are the training sessions.
2. **Calibration folds.** Each training session is left out once; a model fitted on the other seven predicts it. This gives one prediction for every training window from a model that did not see its session.
3. **Calibration.** Platt scaling is fitted on those predictions, with the weights of §6.
4. **Threshold.** The cut on calibrated P(AI) that gives the highest macro-F1 on those predictions.
5. **Final model.** Fitted on all eight training sessions. It scores the held-out session's windows once; the calibration and the threshold are applied.

- Over the nine folds every window is scored exactly once.
- Each calibration model needs at least one AI session to train on. With four AI sessions it always has two or three. With three it can have one. With two the design cannot run.

### 7.2 Metrics
- All are computed on the held-out predictions of the nine folds taken together, because a single fold holds one class.
- **Main result: macro-F1,** the mean of the F1 of the two classes.
- Reported with it: F1, precision and recall of each class, balanced accuracy, ROC-AUC, PR-AUC, Brier score.
- Precision is reported at the one threshold of §7.1. No threshold is set for a precision target.
- **Reference line: 0.809,** the best macro-F1 in Alt (2026) (gradient boosting; random forest 0.808). The main table says for each model whether its held-out macro-F1 is above it. It is a goal declared in advance, not a hypothesis test, and it is reported with the differences between the two studies: three classes there and two here; whole sessions there and 30-second windows here; session duration and login behavior among the features there and ruled out here; 5-fold cross-validation there and whole sessions held out here; tuned settings with SMOTE there and library defaults without it here.
- Accuracy is not used: calling every window human would score about 74%.

### 7.3 By session
For every session and model: kept windows, the session score, and the share of windows called AI.
- All nine sessions are shown. Nothing is fitted at the session level.
- A session reads as AI when its session score is 0.5 or above. This is a fixed line, not a fitted one.

### 7.4 Intervals
- 95% intervals from a bootstrap that resamples whole sessions, within each class, 2,000 times. It reuses the held-out predictions; nothing is refitted.
- With five and four sessions the interval is coarse. The by-session table stands beside every interval for that reason.

### 7.5 By stage group
- The metrics of §7.2 on the held-out predictions of each stage group (1–4, 5, 6, 7), with the thresholds unchanged.
- A value that rests on fewer than 10 windows of either class is marked indicative.
- Known going in (Nov 13): AI stages 1–4 rest almost entirely on P011 (110 of 118 windows), and the AI class has almost no stage 6 work (8 windows; stage 6 was an unlock string for P010 and P011).

### 7.6 Secondary evaluation: inside sessions
- Uses the frozen split file. Models are fitted on the rows marked train, calibrated and given their threshold on the rows marked validation, and score the rows marked test once.
- Training and validation rows within the look-back after a test row of the same login are not used.
- Reported as within-session: it tests later minutes of sessions whose earlier minutes were in training.
- This differs from the note in the pipeline register, which said to calibrate by cross-validation as 2b did. The validation rows come from the same sessions as the test rows, so they match what is being tested (F8, approved).

### 7.7 Sensitivities
| Run | Change |
|---|---|
| 60 s windows | Main configuration; look-back of 2 windows |
| Input-bearing windows | Main configuration on windows with at least one input record |

## 8. Controls
1. **Shortcut audit.** EDA Pass 2: any single column with AUC 0.95 or above is checked against the recordings. Since F16 it runs after the trials and is a report only: it can no longer correct a feature, and whatever it flags is stated beside the results.
2. **Chance baseline (P8).** Every way of calling 4 of the 9 sessions "AI" is run through §7.1 in full, the true labeling included: 126 runs. For each model, p is the share of the 126 whose macro-F1 is at least the true labeling's. The smallest possible p is 1/126 (0.008). Run for the main configuration and for no command content.
3. **Leak audit** of the cleaned files (preprocessing design §6.6).
4. **Column guard.** The trial code refuses any column that is not in §4, and any column named for a duration, position, session, stage or label.

## 9. Hypothesis tests
All on held-out-session macro-F1. Differences are paired: the same resampled sessions for both sides.

| | Test | Supported when |
|---|---|---|
| **H1** | Main without the four H1 columns against Main, for each model. The window form and the look-back form are also re-added one at a time and reported | The gain from the four columns is above zero, Holm-adjusted over the five models, in at least three of the five (F10, approved) |
| **H2** | Logistic regression in the main configuration against the chance baseline of §8. Also reported without command content | p ≤ 0.05 |
| **H3** | Random forest minus each of the other four models, Holm-adjusted over the four | Random forest is highest and all four differences are above zero. A higher value alone is not support |

With nine sessions these tests have little power. A result that does not reach its rule is reported as not supported by this data, not as evidence of no difference.

**H1's baseline (user, Nov 12 22:18).** The baseline in H1 is the same model without the two features. Alt (2026)'s macro-F1 is not the rule for H1: a model can pass it without those features contributing. It is kept as the reference line of §7.2.

## 10. Review, plumbing run and freeze
- **Review of the feature table** (no labels read): the column list equals §4; undefined shares for each session; five windows from each session read beside their feature rows. **Closed on Nov 13:** the column list and the undefined shares were checked in the feature step, and the user read the five windows of each session and found no issue (06:11 EST).
- **EDA Pass 2** on rows marked train, as the EDA handoff sets out. **Moved after the trials by F16, as a report only.** The rule that a flagged column recording the collection is corrected and logged before Freeze 2 no longer applies: such a column is reported with the results, and an analysis with a corrected feature would be a new protocol (3b, P10). Nothing is dropped for being strong or weak.
- **Plumbing run.** Every fold of every trial is fitted and calibrated, and no held-out session is predicted. It writes row counts, column counts and hashes only. No score of any kind is printed or saved, including scores inside calibration folds: those are predictions for sessions that are held out in another fold.
- **Freeze 2:** hashes of this document, the feature and trial code, the feature table and column file, the per-command table, the EDA code and outputs, the library versions and the plumbing log. The EDA outputs are those of Pass 1 (F16). A byte copy of this document is kept with the freeze (T16).
- **Trials.** Run in the foreground, each scored once, into a new folder `results/`. The chance baseline is long; its run time is measured in the plumbing run and it is run in numbered parts so a stopped part can be repeated.
- **After the trials:** EDA Pass 2 as a report (F16), and EDA Pass 3, with SHAP for the random forest (F11, approved).

## 11. What is reported
| Table | Holds |
|---|---|
| Main | Five models, main configuration: macro-F1 with its interval, whether it is above the reference line, and the other metrics of §7.2 |
| Configurations | Macro-F1 for each model in each configuration of §5 |
| By session | §7.3, main configuration |
| By stage group | §7.5, main configuration and no command content |
| Chance baseline | For each model: the true labeling's macro-F1, the range over the 126, and p |
| Hypotheses | §9, with the paired differences and their intervals |
| Inside sessions | §7.6 |
| Sensitivities | §7.7 |

## 12. For approval
These go beyond the decisions in §1. Approvals are the user's, Nov 12 at 22:05 EST unless the row gives another time.

| # | Proposal | Where | Status |
|---|---|---|---|
| F1 | Retire burst ratio, idle-gap count and latency entropy, which need cut-offs from the synthetic module | §4.6 | Approved |
| F2 | Retire the tool count, the file-transfer count and the `wget`/`curl` flag with the other word-list columns | §4.6 | Approved |
| F3 | The error-line and shell-error lists, written fresh | §4.5 | Approved |
| F4 | Transition entropy over program names; the look-back form of the H1 features covers the look-back and the window together | §4.3, §4.5 | Approved |
| F5 | The entry-style rules and their order | §4.5 | Approved |
| F6 | Counts instead of per-second rates | §3 | Approved |
| F7 | The three departures from the library defaults | §6 | Approved |
| F8 | Inside-session evaluation calibrated on the validation rows | §7.6 | Approved |
| F9 | The chance baseline is run for two configurations | §8 | Approved |
| F10 | The rule for H1: the ablation decides it. Alt (2026)'s 0.809 is a reference line beside the main result | §7.2, §9 | Approved (22:18) |
| F11 | From the EDA handoff §11 (its decisions 1, 3 and 4): a shortcut flag may correct a feature before Freeze 2; the stage analysis uses training rows; SHAP for the random forest after the trials | §10 | Approved |
| F12 | Here-document bodies are set aside before flags, pipes, chaining and redirects are counted. Their characters still count in `chars_submitted` | §4.2, §4.5 | Approved (Nov 13, 03:05) |
| F13 | Programs that ran before a login's first submitted line are not counted in `exec_count`, `exec_distinct` and `proc_depth_max`. Every login runs about 20 to 30 on its own, 488 in all, and the AI class has more logins for its size (11 in 250 windows against 9 in 701) | §3, §4.1 | Approved (Nov 13, between 05:51 and 05:57) |
| F14 | `gap_autocorr` needs four gaps. With three it is a correlation of two points and is always +1 or −1 | §4.1, §4.5 | Approved (Nov 13, between 05:51 and 05:57) |
| F15 | The readings R1 to R20 of the feature step | §4.7 | Approved (Nov 13, between 05:51 and 05:57) |
| F16 | EDA Pass 2 is run after the trials, as a report only. The shortcut audit (§8, control 1) then cannot correct a feature before Freeze 2, so that part of F11 lapses; Freeze 2 holds the Pass 1 code and outputs | §0, §8, §10 | Decided by the user, against the recommendation (Nov 13, 06:11) |
| F17 | The readings T1 to T16 of the trial code | §6a | Applied on the user's instruction to go on to Freeze 2 and the trials (Nov 13, 06:11). Not reviewed item by item |

## 13. Known going in
- **The AI class is narrow.** All four AI sessions are one model in one harness. The harness's command wrapper has two forms, and in P011's last minutes commands were sent without it (preprocessing design A11, A14).
- **Stage coverage** (kept 30-second windows before the closing-exit and validator-only rules, human against AI). Stages 1–4: 484 against 118, of which 110 are P011's, mostly its 55 minutes on stage 2. Stage 5: 186 against 88. Stage 6: 79 against 8, with no real AI stage 6 work. Stage 7: 72 against 70, from P002, P010 and P011. When P011 is held out, the models have 8 AI windows of stages 1–4 to learn from.
- **P011 holds 45% of the AI windows.** The weights of §6 already give each session an equal share of its class.
- **Here-documents.** The AI sessions write scripts inside commands (4% of P002's commands, 46% of P009's, 12% of P010's, 26% of P011's); the typed input of P004 to P006 holds none. F12 keeps the script bodies out of the shape counts. Their characters still count in `chars_submitted`, so that column and `io_ratio` carry the difference.
- **P001 and P002 are not new.** Their windows were scored in studies 1, 2 and 2b, and the counts behind several choices here come from them.
- **Nine sessions.** Intervals are coarse and the hypothesis tests have little power.
- **No shortcut audit before scoring (F16).** No single-column AUC has been computed on study 3 data. If a column separates the classes because of how a session was recorded, the trials will have used it, and Pass 2 can only report it afterwards. Known from the feature step without reading a label: four input-channel columns are undefined in every window of four sessions; that tier is never in the main configuration.
- **Paper sections to bring in line** once this is approved: 3.5 (Tables 3-7 and 3-8), 3.6 (settings, the threshold, the SMOTE sentence), 3.7 (evaluation, controls, hypothesis tests), 4.6, and Appendix A.

## 14. Change log
| When (EST) | Change |
|---|---|
| Nov 12, 02:50 | First draft |
| Nov 12, 22:15 | User (22:05): F1 to F9 and F11 approved. F10 open: the user's reading of H1's baseline is the macro-F1 reported by Alt (2026) (§9) |
| Nov 12, 22:25 | User (22:18): F10 approved. H1 stays the claim that the two features improve classification and is decided by the ablation; Alt (2026)'s macro-F1 of 0.809 becomes a reference line reported beside the main result (§1, §7.2, §9, §11). The design is approved |
| Nov 13, 03:15 | P010 and P011 are in; all nine sessions in hand (§0; preprocessing design §2). User (03:05): F12 approved, here-document bodies are set aside before the shape counts (§4.2, §4.5, §12). Known-going-in notes updated for four AI sessions (§7.5, §13) |
| Nov 13, 03:30 | User (03:26): preprocessing design A15 approved. Program output ends when the shell prompt comes back or the operator starts the next line, and a line typed into a waiting program is a command in both classes (§3) |
| Nov 13, 06:00 | EDA Pass 1 was run and the feature table built (05:12–05:41; `real_lab3_eda_pass1_feature_run.md`). User (between 05:51 and 05:57): F13 approved, programs that ran before a login's first submitted line are not counted (§3, §4.1); F14 approved, `gap_autocorr` needs four gaps (§4.1, §4.5); F15 approved, the readings R1 to R20 (§4.7). The table was rebuilt at 05:57 with feature code version 1.1. Status brought up to date |
| Nov 13, 07:05 | User (06:11): **F16**, EDA Pass 2 is run after the trials as a report only, against the recommendation; the user read the five review windows of each session and found no issue, which closes the review of the feature table (§0, §8, §10, §13). **F17**: the readings T1 to T16 of the trial code, applied on the same instruction (new §6a). The trial code was written, tried on a made-up study tree, and the plumbing run made (`real_lab3_trial_run.md`). Status brought up to date. This is the text frozen in Freeze 2 |
