# Real lab logs, study 3: preprocessing design

Drafted 2026-11-11 00:50 EST from the decision review in `real_lab3_decision_register.md`. It replaces `real_lab_preprocessing_design.md` (study 1) and `real_lab2_preprocessing_design.md` (study 2) for all work from here on; those two stay as the record of studies 1, 2 and 2b.

**Status: approved by the user on 2026-11-11 at 01:09 EST. Amended at 01:27 EST with A1–A5 after P003 and P009 arrived; at 01:51 EST, P009 uses only its last login (§2); at 02:04 EST with A6 (§6.3, §6.4); on 2026-11-12 at 02:13 EST with A7 and A8 (§6.7, §9, §10); on 2026-11-13 at 03:05 EST with A9–A14 after P010 and P011 arrived (§2, §3, §4, §5, §6.2, §6.3, §6.7, §7), at 03:26 EST with A15, which also corrects A14 (§6.7); and at 04:43 and 04:52 EST with A16, A17 and the implementation readings, after the preprocessing ran (§4, §6.3, §6.4, §6.5, §6.7, §8).** Changes are listed in §13. No amendment is waiting for approval.

The preprocessing ran on Nov 13 and was rerun the same morning after A17; the record is `real_lab3_preprocessing_run.md`. **Freeze 1 was written on Nov 13 at 05:04 EST, on the user's word (05:00):** `reports/FREEZE_1.json`, code version 1.1. From here the rules of §10 for work after Freeze 1 apply. All nine sessions are in hand as of Nov 13 (§0, §2).

## 0. Plan
1. Design approved (done).
2. **Wait** for the remaining AI sessions. Done on Nov 13: 5 human and 4 AI sessions are in hand, the target the user set on Nov 12.
3. Run the preprocessing once, on all sessions together. Done on Nov 13; rerun before the freeze after A17, and run once more on the user's word at 05:00 with byte-identical output.
4. Freeze 1: code, processed data, labels, split file. Done on Nov 13 at 05:04 EST.
5. In a separate document: features and the trial plan (Freeze 2).
6. Classifier trials, only after both freezes.

No code was written or tested while waiting (user, Nov 11). Writing the code for step 3 starts on the user's word. The word was given on Nov 13 at 03:33 EST.

## 1. Terms
| Term | Meaning |
|---|---|
| **Session** | One participant's whole attempt at the exercise (P001, P002, …). The unit the study counts |
| **Login** | One SSH connection inside a session. The recorder gives each its own id (`eng-…`). Earlier docs called these "sessions" |
| **Window** | 30 seconds of one login. One window is one row of classifier data |
| **Classifier data** | What the trials will use: the operator's terminal recording and the programs that login started |
| **Set aside** | Kept on disk in its own files, never an input to the classifier |

## 2. Sessions and logins in scope

| Session | Class | Lab range (build) | Package read | Logins used | Logins left out |
|---|---|---|---|---|---|
| P001 | human | Original Austin (Oct 31 build) | `P001-recorded-session-raw-tagged.zip` | 2 work logins | 2 automated setup checks (supplement zip, not read) |
| P002 | ai | AHIR-03 (Nov 7 build) | `P002-original-bounded-snapshot-raw-tagged.zip` | 5 task logins | 13 automated setup checks, 1 readiness check, 1 person's status check, 1 post-task check |
| P003 | human | Original Austin | `P003-session-raw-and-tagged-20261110.zip`, delivered in three parts | 2 work logins | 2 automated status checks; 1 setup check (supplement zip, not read) |
| P004 | human | AHIR-03 | `P004-session-raw-and-tagged-20261110.zip` | 3 work logins | 2 status checks from the setup host |
| P005 | human | AHIR-01 (Nov 7 build) | `P005-session-raw-and-tagged-20261110.zip` | 1 work login | 2 from the setup host |
| P006 | human | AHIR-03 | `P006-combined-bounded.zip` (final package; stage markers in `sources/tail/8.bin`) | 1 work login | 2 status checks from the setup host |
| P009 | ai | Original Austin | `P009-session-raw-and-tagged-20261110.zip` | **1 task login** (`eng-1d89…`) | 4 task logins run under revised prompts; 1 person launching the AI tool; 2 readiness checks; 1 login holding only status and resubmission attempts |
| P010 | ai | AHIR-01 | Split delivery in `P010/` (A9): 13 login zips, `context.zip` in 5 parts, `ambiguous.zip`, `source-provenance.zip` | **3 task logins** (`eng-3852…`, `eng-b030…`, `eng-13cd…`) | 1 qualification recording; 3 logins typed by a person (a commissioning test through stage 6, two diagnostics); 1 login stopped by a validator policy error; 3 logins of status retries during the validator outage; 2 diagnostic logins run on the supervisor's instructions |
| P011 | ai | AHIR-03 | Split delivery in `P011/P011 - Restricted Raw Logs/` (A9): 8 login zips, `context.zip` in 11 parts, `ambiguous.zip`, `source-provenance.zip` | **2 task logins** (`eng-2a1f…`, `eng-6366…`) | 6 short logins typed by a person before the run (4 hold only `exit`, 2 a status check) |

- Labels confirmed by the user: P003 human, P009 AI (Nov 11); P010 and P011 AI (Nov 13).
- All sessions are in: 5 human and 4 AI, the target the user set on Nov 12.
- Not in scope: AI Lab 1; every synthetic set (v1–v4).
- The range was reset after every session (user).
- All three ranges hold both classes: Original Austin has P001, P003 (human) and P009 (AI); AHIR-03 has P004, P006 (human) and P002, P011 (AI); AHIR-01 has P005 (human) and P010 (AI).
- **Location:** `Log Collection/study 3/AHIR Participant Evidence/`.
- From each package only `raw/events.jsonl`, `SESSION_BOUNDARIES.json` and the stage-boundary file are read. For a package delivered as a split (A9), the raw records are the `raw/events.jsonl` files of the login zips, `context.zip` and `ambiguous.zip`, and the two boundary files are read from `source-provenance.zip`. The tagged layer, classification overlays, provenance and lineage files, validator history and the harness archives are never read by the preprocessing.

### P009: only the last login is used (user, Nov 11 01:51)
- **Why.** P009's harness records show the same model, harness and starting prompt as P002, but the session was 11 runs in 3 chats. Four of its five task logins ran under revised prompts carrying a restriction P002's prompt did not have (do not place the password in commands or logs), and between them the supervisor sent instructions, all of which the AI declined. Only the last login, `eng-1d89…`, ran under the starting prompt. Details: `real_lab3_p003_p009_check.md` §6–§7.
- **Rule, so the remaining AI sessions are judged the same way:** an AI login is used only when it ran under the standard starting prompt (connection details may differ). The study team decides this from the harness record and writes it in the login table; the preprocessing reads the login table, never the harness record. P002's five task logins all meet the rule.
- **The login used** (description only, never a feature):
  - 44 minutes, 98 wrapped commands, 58 kept windows before the validator-only rule (about 40 after).
  - It starts at stage 5. Stages 1–4 were accepted in a left-out login, so P009 contributes stage 5 work only.
  - The validator answered one status call at 03:14:19 UTC and was unavailable from 03:14:37 to the end. No hint was delivered and no submission was accepted. A cancel was requested at 03:58:46.
  - In its first minute the AI read the shell history left on the machine by the earlier logins. The wrapper and validator text this puts into the output is handled by A6.

### P010: three task logins (user, Nov 13)
- **What happened.** The validator went down after stage 5 was accepted and held the session from moving on to stage 6 for about two and a half hours. A person also used the account: a commissioning test through stage 6 before the AI's run, and two diagnostic logins during the outage. Details: `real_lab3_p010_check.md`.
- **Used (02:21):** the exercise work only. `eng-3852…` holds stages 1–4 and the start of stage 5, `eng-b030…` stage 5 to its acceptance, `eng-13cd…` stages 6 and 7. 52 kept windows, about 44 after the closing-exit and validator-only rules.
- **Left out:** the person's logins, because they are not the AI; and six AI logins with no exercise work (a validator policy error, status retries during the outage, diagnostics run on the supervisor's instructions). P009's status-only and supervisor-directed logins were treated the same way.
- **Prompt (03:05).** P010's starting prompt is accepted under the AI login rule. One line of the standard prompt is absent from it: "Do not access administrative answer databases, application source code, hidden validator files, or another participant's environment." Because that showed in the recording, the login table carries a one-line note.
- **Shell history (02:29).** In `eng-3852…` the AI printed the shell history left by the commissioning test, which held that test's accepted answers for stages 1–6. Stages 1–4 were already accepted, and the AI reached the stage 5 answer through its own query. Stage 5 stays in. Description only, never a feature.

### P011: two task logins (user, Nov 13)
- One starting prompt and one "Ok, continue where you left off"; no validator outage and no instruction mid-run; all seven stages. Details: `real_lab3_p011_check.md`.
- **Used (03:05):** `eng-2a1f…` (stages 1–4 and the start of stage 5) and `eng-6366…` (stages 5–7). 129 kept windows, about 125 after the two rules.
- **Left out:** six short logins typed by a person before the run.
- **Prompt (02:58).** The prompt carries one added line ("Stop when you get to stage 6 and provide me the prompt for further direction"), put there so the run would not meet the validator problem P010 had. The AI ignored it. The prompt counts as the standard starting prompt and the line is not carried into the login table.

## 3. Evidence chain
The original packages are the evidence of record. The processed data is a derived dataset: it will not match the original manifests and is not meant to. What is checked is that the originals still verify and that the processed data is exactly what these rules produce from them.

| Step | What | Status |
|---|---|---|
| Verify first | Before anything is read, every file listed in each package's manifest is checked against its recorded size and SHA-256. For a package delivered in parts, every part and the rebuilt archive are first checked against `PARTS_MANIFEST.json` (A1). For a package delivered as a split (A9), the files are checked against its checksum manifest, the parts of `context.zip` against that manifest's part entries, the contents of each zip against the zip's own manifest, and the record count against `COMPLETE.json`. The run stops on any mismatch. Result written to a verification report | In. Checked by hand on Nov 11 and Nov 13: all nine packages match |
| Step reports | Every step writes a report: input hashes, output hashes, and a count for each rule of what it changed or dropped. The first step's input hashes equal the manifest hashes. Counts must add up to the package total | In |
| Record-level trace | Normalised and scrubbed records keep their original event id. Every dropped record's event id is written to a ledger with the rule that dropped it. Ids are removed only when windows are built | In |
| Freeze file | Hashes of code, reports and outputs | In. Freeze 1 was written on Nov 13 (`reports/FREEZE_1.json`, 498 files) |
| Run twice and compare | Shows the outputs are reproducible byte for byte | Deferred (user). Done in effect on Nov 13: version 1.1 was run twice from the originals, at 04:53 and at 05:02, and every output file was byte-identical (run document §5b). Can be run again at any time, since originals and code are kept |

- The code only reads from `study 3/AHIR Participant Evidence/` and never writes inside it. No file permissions on disk are changed.
- Parts are read in place as one file; no rebuilt archive is written to disk. A first part that arrived named `…part001.zip` is accepted when its size and hash match the parts manifest's `…part001` entry (A1).
- **Split packages (A9).** P010 and P011 arrived without their main zip. On Nov 13 the main raw file of each was rebuilt from the split and matched the size and SHA-256 recorded for it, so the split holds the same records. The line order for that check came from the `lineage.jsonl` files; the preprocessing itself does not read them.

## 4. Where every record goes
No time cut is applied (D3 retired). Rows come only from records that belong to an included login, so nothing outside those logins can become a row. Every record in a package ends in exactly one of three places:

| Destination | What | Why |
|---|---|---|
| **Classifier input** | Operator machine: the terminal recorder stream and the audit stream | The operator's own actions |
| **Set aside** | Operator login and system logs; management; the five Windows machines (Sysmon in its own files); network flow; collector, connector and sensor (Original Austin range); validator service logs | Other machines' logs are not part of the classifier data. They are kept for a later description of the sessions that share a range |
| **Dropped, with ledger** | `eng_feature_*` audit record groups (sessions on the Original Austin range: P001, P003, P009) (A2) | Only that range records them; they would give its sessions process start and exit information the others lack |

- Set-aside files are stored as collected, split by machine, with one change: operator streams named `authentication` and `system` (Original Austin range) are renamed to the standard `auth` and `syslog` (D31, A2).
- **Storage and routing at implementation (user, Nov 13 04:43).** Set-aside files are written as gzip-compressed JSONL, one file for each machine and stream. Operator recorder records of logins that are not used, and operator audit records that are not exec record groups bound to a login used, are kept with the set-aside files; they are never cleaned and never reach `data/`.
- Set-aside files are **not scrubbed**. They contain names and addresses and stay in the protected location.
- Rules that act only on set-aside logs stay on the books and apply if those logs are ever used: the time filter, the maintenance drop (`APT29-Research-ACL`, with `worker.ps1` added), the stream and event-kind selection rules (D7, D26, D32), and a drop for the account services `ahir-pNNN-production-…`, `ahir-pNNN-application-…` and `ahir-pNNN-fixed-expiry-…` (A10).

## 5. Labels
- Labels are assigned after collection from the study design: **`human`** or **`ai`**, one per session.
- The label names are ours; they are not in the session data. `ai_assisted` was the name used in studies 1, 2 and 2b (carried over from the synthetic work) and stays in those studies' files. Study 3 uses `ai`: every AI session so far is an AI agent issuing its own commands. A session where a person works with an AI assistant would need its own label.
- Labels live in a sidecar file, never in records, and test labels are written to a separate file that only the scorer reads.
- Files: a session table (session key, class, included); a login table (login key, session key, included, reason if not, duration, inputs, Enter presses, **how the login ended**); a private map from keys to original ids.
- "How the login ended" (typed `exit`, harness `exit`, left open and closed by an administrator, ended without `exit`) is description only, never a feature.
- The login table also has a free-text note for description, such as the line absent from P010's prompt and its shell-history exposure (§2). Description only, never a feature.
- Only records bound to a login carry the label.

## 6. Cleaning the classifier input
All rules are fixed patterns, applied the same way to every session, and none looks at the label.

### 6.1 Enter key
In recorder input, CRLF and LF become CR, the byte a keyboard Enter sends. Humans already send CR only; the harness sends LF only.

### 6.2 Identity
Found by pattern, not by a list of names, so new participants need no edits.

| Identity | Pattern (example) | Becomes |
|---|---|---|
| Account name | `ahir-p` + three digits (`ahir-p004`) | `op_user` |
| User number | 24 followed by three digits (`24004`, `24010`) in user and group fields, and bare in recorder text (A10) | `10001` |
| Home directory | `/home/ahir-pNNN` | `/home/op_user` |
| Participant paths | `/opt/goad-autonomy/participants/ahir-pNNN/`, `/etc/goad-autonomy/ahir-pNNN….json`, `/var/lib/ahir-participants/ahir-pNNN/`, client release folders | same path with the placeholder |
| Participant and attempt codes | `P0NN`, `p0NN_…` (`P004`, `p010_`) (A10); attempt codes such as `ahir03` | placeholder |
| Client address | any address in 100.64.0.0/10; the recorder's `connection` field | removed |

Applied to decoded recorder input and output, audit fields and hex-encoded audit arguments. Kept, because they are shared environment or behaviour: target machine names and addresses, the GOAD accounts used in the attack, the operator machine's hostname, files the operator created.

### 6.3 AI harness wrapper
- A wrapped input, `printf AO_<id>_BEGIN; timeout … bash -c '<command>'; …; printf AO_<id>_END…`, becomes `<command>`. P002 (118 commands) and P009 (98 in the login used) use this form.
- **Wrapper without `timeout` (A11).** The harness changed its wrapper during P010 and again between P011's two logins, to `printf AO_<id>_BEGIN; bash -c '<command>'; …; printf AO_<id>_END…`. Both forms are unwrapped. In the logins used, P010 has 37 wrapped inputs in the first form and 58 in the second; P011 has 118 and 9.
- The harness's readiness probe is dropped.
- Marker lines and the wrapper's echo are removed from the output, including the scrolled-off tail fragments.
- **Wrapper text inside program output (A6).** Wrapper text can also reach the screen as ordinary program output: in P009's used login the AI printed the shell history left by its earlier logins, which holds their wrapped commands. The same unwrapping is applied to wrapper text wherever it appears in recorder output, not only at a command's own echo.
- The wrapper's own processes (`timeout`, `bash -c`, the probe) are dropped from audit as whole record groups; a command's programs then have the same depth as if it had been typed. Without `timeout` the `bash -c` process hangs directly off the login shell, which D29 already covers.
- A different harness's format must be supplied before its sessions are recorded.
- **Failed look-ups (user, Nov 13 04:43).** The wrapper's `timeout` searches the path for `bash` and fails several times before it finds it. Those failed program starts are dropped with the wrapper's processes.
- **Wrapper text printed cut short (A16).** When a program prints wrapper text cut at a column (a history line cut short), the pieces that remain are removed: the head up to `bash -c`, the tail from `ao_status=`, and the `timeout` options.

### 6.4 Validator calls
- Both classes call the validator (`goad-apt29 status`, `submit`, `hint`, …). Every audit record group of the validator family is dropped: `goad-apt29`, `/opt/goad-autonomy/`, `/etc/goad-autonomy/`, `goad-challenge`, `/opt/goad-exercise/`.
- Each successful validator exec that is not a wrapper process leaves a marker (login, time). The command that made the call is removed, with its output, at the command level, using the marker; a command whose program is `goad-apt29*` or `goad-challenge` is removed as well.
- The whole command is removed even when it combines the call with something else on the same line (7 of the 16 validator commands in P009's used login do).
- A marker with no command in the 15 seconds before it belongs to a command still running (P009's retry loops) and is counted, not treated as an error.
- **Commands that only name the validator (A6).** A command is removed only when it calls the validator. A command that names it without calling it (searching the shell history for it, for example) is kept. Validator-family names left in kept command and output text are replaced with the placeholder `validator`. Target content is not touched (the target web server has a `/goad-autonomy/` path).
- At implementation, the successful execs under each participant's `bin` directory are listed for review.
- **How the marker and the removal work (user, Nov 13 04:43).**
  - A marker comes only from a successful exec of the client file itself, or of an interpreter given a family script. Listing, searching or reading the validator's folder leaves none.
  - The command is cut out of the recording: its keystrokes, its echo, its output and the prompt that followed. The stream then reads as if it had not been typed.
  - A marker with no command in the 15 seconds before it removes the command still running, when that command was not removed already (P010's `sleep N; goad-apt29 status`).
  - When the operator typed while a validator call was still printing, the cut still runs to the prompt that closes the call.

### 6.5 Scaffolding
- Scratch directory names become `workdir` (`~/ok`, `~/stageNN`). New participants worked in their home directory.
- Collection and acceptance tooling is dropped from audit (`/PinnedCollector/`, `/exercise_autonomy/`).
- The AI's evidence-log writes and its hint waits stay as behaviour.
- **Tooling names in recorder text (A16).** When a program prints the collection tooling's folder name in kept recorder text (a validator-client traceback, a directory listing), `/PinnedCollector/` and `/exercise_autonomy/` become `/tooling/`. The leak audit searches for both.

### 6.6 Leak audit
After cleaning, every output file is searched for everything 6.2–6.5 should have removed, using the same patterns. This includes wrapper text anywhere in the output and validator-family names in kept text (A6). Audit arguments are checked one by one. The count must be zero. The search must not flag target content (the target web server has a `/goad-autonomy/` path).

### 6.7 Command reconstruction (A7)
- **What it is.** The code that turns a login's keystrokes and screen output into a list of commands: when each was submitted, its text, and where its output ends.
- **Why it is here.** The validator rules (§6.4) and the validator-only window rule (§7, A4) cannot run without it, and the kept windows decide the split file. It is therefore part of the preprocessing and of Freeze 1. In studies 2 and 2b it sat in the feature step.
- **Text.** It applies the per-line rule of §9: screen text when the keystrokes include history recall, Tab or cursor movement; keystrokes otherwise; where the screen cannot be read reliably the line keeps its keystrokes and is counted.
- **One list.** The command list is written to `data/`. The feature step reads it and does not find commands again.
- **End of a command's output (A15).** One rule for every login of both classes: a command's output starts after its Enter and ends when the shell prompt comes back or when the operator starts the next line, whichever comes first.
  - The shell prompt is recognized by its visible text, the lab's two-line prompt, with colors stripped. Every login used, in all nine sessions, prints it (checked Nov 13).
  - Two other signals are cross-checks only, counted and reported before Freeze 1. The wrapper's END line: in the AI logins checked, every END line is followed directly by the prompt, and an interrupted command prints none. The shell's paste-mode marker in human logins: it also fires at the smbclient prompt and not at the SQL client's prompt, and AI logins never print it.
- **Commands outside the wrapper (A14, corrected by A15).** Not every AI input is wrapped.
  - The wrapper's END line does not decide where a command ends; the rule above does. The END line is removed with the other marker lines (§6.3).
  - **A line typed into a waiting program is a command in both classes.** A line submitted while a program is waiting for input (a SQL statement in the SQL client, an smbclient command, a reply at a password prompt) is a command that starts no program, whether a person typed it or the AI sent it. P010's used logins hold such lines. The wording approved at 03:05 called the AI's lines input to the running command; that would have counted a person's SQL line as a command and the AI's as nothing.
  - An unwrapped line that arrives at a shell prompt is a command (P011: the last 13 lines of `eng-6366…`).
  - A reply at a password prompt is such a line, and its text is the lab credential. The EDA's credential check covers every output that shows command text (EDA handoff §10, check 4).
  - A here-document sent to the shell is one command.
  - The same end-of-output rule (A15) therefore serves AI and human logins alike.
- **Checks before Freeze 1:** agreement between screen text and keystrokes on plain lines, for each session; program output per command, by class; the list of removed validator commands, read by a person; the two cross-checks of A15.
- **One write at the shell prompt is one command (user, Nov 13 04:43).** Every line of one write that arrives at the shell prompt belongs to one command, wrapped or not. Its echo is counted up to the point where the shell would run the text.
- **Where the next line starts (A17).** "The operator starts the next line" means the first key of a line that has content. Ctrl-C, Ctrl-D and Enter on an empty line are not lines and do not end a command's output. Before A17, an interrupt pressed during a long scan in P006 left about 1 MB of that scan's output outside any command.
- **Full-screen programs.** Keys pressed inside a full-screen program are not lines.
- **Screen text.** Text read from the screen is read from the display as it was shown and is scrubbed afterwards.
- **The checks were run and closed on Nov 13 (04:43):** 146 of 148 plain typed lines agree; all 438 END lines are followed directly by the prompt; the removed validator commands were read by the user.

## 7. Windows
| Rule | Detail |
|---|---|
| Length | 30 s (main) and 60 s (sensitivity), non-overlapping, aligned to the login's recorder start |
| Kept | A window with at least one terminal input or output record and at least 15 s long |
| Closing exit | A window holding only the login's closing `exit` is dropped |
| Validator only (A4) | A window with nothing left once validator commands and their output are removed is dropped. Uses the command list of §6.7 (A7) |
| Time | Every time becomes seconds since the login's start. Position in the login, login duration and window number are never features |
| Ids | Event, login, boot, instance and audit ids are dropped here; process ids become per-window local numbers, the login shell always 1 |
| Gaps | Measured inside a login only, so nothing spans a cancel and resume |
| Stage group (A3, A13) | A window belongs to the first stage whose acceptance comes after the window starts, on one timeline per session. The timeline uses every acceptance by the session's operator in its stage-boundary file, including one that happened in a left-out login. Acceptances made in a login that was not the session's operator are left out (A13; P010's file begins with six from a person's commissioning test). The timeline is read in time order, and a stage number may appear more than once in a file. After the last acceptance: if the session finished stage 7, the window joins stage 7; if it did not, the window belongs to the next stage, the one being worked on. Used for splitting and reporting only |

Each kept window has the login's recorder records and the audit exec events of that login (matched by user number and audit session number).

## 8. Split
- **One split file**, written per session: train, validation, test or unused for every kept window.
- **Method:** inside each session, windows are grouped by stage. Within each group, in time order: the last 15% are test, the 15% before them validation, the rest train, with one unused window at every block boundary and where one group's test block meets the next group's training block.
- **Sizes:** 15% rounded to the nearest whole window (halves up), never fewer than one.
- **Small groups:** a group under 7 windows is merged with the previous stage's group in the same session (the next if there is none), smallest first, and split with it.
- **Groups are single stages (user, Nov 13 04:43).** The split groups windows by stage 1 to 7, not by the four stage groups used for reporting.
- **Written once:** each session's split depends only on its own windows. The file is written when the preprocessing runs; a session added later is appended; existing rows never change. The writer refuses to overwrite.
- **Holding out whole sessions needs no file.** "Leave out every window of session X" is defined by the session column. Whether and how it is used is a trial-plan decision. No leave-one-login-out version is written.
- **Look-back rule (for the trial plan):** if a feature looks back over earlier windows, training and validation windows inside that look-back after a test window are not used. This is applied in the pipeline, so the split file does not depend on the look-back length.
- This split tests later minutes of sessions whose earlier minutes are in training. Results from it are reported as within-session.

## 9. Decisions already taken for the feature step (Freeze 2)
Recorded here so they are not lost; the details go in the feature and trial document.
- **Command text, per line:** when the keystrokes include history recall, Tab or cursor movement, the submitted text is read from the screen (the recorder's output records); otherwise it is the keystrokes. Where the screen cannot be read reliably, the line keeps its keystrokes and the report counts how often. Agreement on plain lines is reported per session before the freeze. Under A7 the command reconstruction in the preprocessing applies this rule (§6.7), so the freeze meant here is Freeze 1.
- **Self-contained:** study 3 code imports nothing from the synthetic project. The reconstruction is written fresh. The old extractor may be read as a reference; it holds no synthetic data. Word lists and timing cut-offs are listed in the feature document for review. Model settings are fixed without reference to synthetic results.
- Successful execs only. Gaps are time since the previous command in the login. Program output is counted instead of raw terminal bytes. Typing and paste columns are computed but kept in a separate tier.
- Left for the trial plan: class weights (balance classes and sessions), no model selection, calibration, context length, reported configurations, results by stage. SMOTE is not used and there is no side comparison (user, Nov 12).
- **Known going in** (kept 30-second windows, before the closing-exit and validator-only rules): human 821, AI 284, about 3 to 1. By stage, human against AI: stages 1–4, 484 against 118; stage 5, 186 against 88; stage 6, 79 against 8; stage 7, 72 against 70. Of the 118 AI windows in stages 1–4, 110 are P011's, most of them from its 55 minutes on stage 2; P002 and P010 cleared those stages in under three minutes, and P009's are in a left-out login. P009 contributes stage 5 only. Stage 7 AI data comes from P002, P010 and P011. There is almost no AI stage 6 work: on the validator build that P010 and P011 met, stage 6 is an unlock string.

## 10. Freezes, folders and adding sessions
- **Freeze 1** (after the preprocessing): code, verification report, step reports, ledgers, cleaned and windowed outputs, the command list (A7), labels, split file. Written on Nov 13 at 05:04 EST; the set-aside files are listed in it with their hashes as well.
- **Freeze 2** (before any score): features and the trial plan.
- **After both:** the trials run. The 2b model is not run on the new sessions (A8).
- **A session that arrives after Freeze 1:** the same frozen code is run on it. The only changes allowed are in reading a different package layout, a new identity form caught by the leak audit, or a new harness wrapper format. Each is logged as an amendment with its reason, and all earlier sessions are re-run to show their outputs are unchanged.
- **Folder layout** in `Log Collection/study 3/`:

| Folder | Holds |
|---|---|
| `AHIR Participant Evidence/` | The original packages. Read only by the code; nothing is ever written here |
| `code/` | Study 3 scripts (Python standard library only) |
| `reports/` | Verification report, step reports, ledgers, freeze files |
| `data/` | Cleaned classifier input, command list, windows, labels, split file |
| `set_aside/` | Other machines' logs, unscrubbed |

## 11. Open
1. **Remaining AI sessions: closed on Nov 13.** P010 and P011 are in. All four AI sessions are the same model and harness; the harness's wrapper has two forms (A11). P011 gave the clean run from stage 1 that was asked for here.
2. **For interpretation later, not blocking:** whether the human participants had the same hint timing rules as the AI's prompt, and how they received the stage 7 credential.
3. **For the feature document:** the honeypot word lists are retired (pipeline register P6), so this now concerns only the error-text patterns and timing cut-offs. Either the old extractor's folder is connected so they can be read as a reference, or they are defined fresh.
4. **Prompt rule (§6.7): settled on Nov 13 as A15.** A command's output ends when the shell prompt comes back or when the operator starts the next line. The exact prompt pattern is listed for review when the code is written, before any session is processed.
5. **Implementation notes from the P010 and P011 checks** (§9 of `real_lab3_p010_check.md` and of `real_lab3_p011_check.md`): the empty second Enter, terminal replies, the interrupt key, the typed-ahead `exit`, the AI's own `timeout`, commands that name the validator without calling it, the range code in a flag, program starts before the login shell, the echo of multi-line commands, stage-named temporary files. They were gone through when the code was written (Nov 13). None changes a rule in this document.

## 12. Decision index
| Kept | D1, D2, D4, D5, D5a, D6, D6a, D8, D9, D11, D12, D12b, D13, D13a, D13b, D14, D16 (operator machine), D17, D18, D19, D20, D21, D22a, D23, D24, D27, D28, D29, D29a, D30, D31, D33, D34 (as amended by A3 and A13), D35, D36, D37, D38a–c, Q2–Q5, Q7–Q9, 2b-2, 2b-3, 2b-4 (as the look-back rule) |
|---|---|
| **Retired** | D3, D3a, D12a, D22b, Q10 |
| **On the books, not built** | D7, D16 (other machines), D26, D32, D38d, Q6 (Sysmon set aside), Q11 |
| **Trial plan** | D10, D10a, D15, D25, D39, 2b-1, 2b-5 to 2b-8 |
| **Added in study 3** | A1 split packages, A2 range wording, A3 unfinished stage, A4 validator-only windows, A5 login tables for P003 and P009 (P009's changed at 01:51), the AI login rule (§2), A6 wrapper and validator text in output, A7 command reconstruction in the preprocessing, A8 no 2b run on the new sessions, A9 packages delivered as a per-login split without the main zip, A10 two-digit participant numbers, A11 wrapper without `timeout`, A12 login tables for P010 and P011, A13 other operators' acceptances left out of the stage timeline, A14 commands outside the wrapper (corrected by A15), A15 end of a command's output and lines typed into a waiting program, A16 tooling names in recorder text and wrapper text printed cut short, A17 where the next line starts, and the implementation readings approved on Nov 13 at 04:43 (run document §3) |

## 13. Change log
| When (EST) | Change |
|---|---|
| Nov 11, 00:50 | First draft |
| Nov 11, 01:15 | Approved by the user. Run postponed until all sessions are in (§0). Label `ai_assisted` → `ai` (§5). Evidence location and folder layout updated after the user moved the packages into `study 3` (§2, §10) |
| Nov 11, 01:27 | No code written or tested while waiting (§0). P003 (human) and P009 (AI) added; labels confirmed; P009 used as it is (§2). Amendments A1–A5 approved: split packages (§3), range wording (§4), unfinished stage and validator-only windows (§7), login tables (§2) |
| Nov 11, 01:50 | P009's harness records read (QA only). The "same prompt and setup" note in §2 replaced with what the records show |
| Nov 11, 01:55 | User (01:51): P009 uses only its last login, `eng-1d89…`; the four task logins under revised prompts are left out, and the AI login rule is recorded (§2). Stage timeline wording for left-out logins (§7). Counts updated (§6.3, §6.4, §9). Correction: P009's validator outage began at 03:14:37 UTC, not at 03:41 as earlier versions said; 03:41 was the first submission (§2) |
| Nov 11, 02:10 | User (02:04): A6 approved. Wrapper text is unwrapped wherever it appears in output (§6.3); commands that only name the validator are kept and validator-family names in kept text become a placeholder (§6.4); the leak audit covers both (§6.6) |
| Nov 12, 02:25 | Decisions from the pipeline review (`real_lab3_pipeline_register.md`). User (02:13): A7 approved; the command reconstruction is part of the preprocessing and of Freeze 1 (§6.7, §7, §9, §10, folder layout), and the prompt rule is open (§11). User (01:24): A8; the 2b model is not run on the new sessions (§10). User (01:24): the target is 5 human and 4 AI sessions (§0, §2). User (02:13): no SMOTE side comparison (§9). §11 item 3 narrowed after the honeypot word lists were retired |
| Nov 13, 03:15 | P010 and P011 (both AI) checked and added (`real_lab3_p010_check.md`, `real_lab3_p011_check.md`). User decisions of Nov 13: P010 uses its three task logins (02:21) and its stage 5 stays in (02:29); P011 uses its two AI logins (03:05); P010's prompt is accepted with a one-line note (03:05) and P011's added line is ignored (02:58); the split package layout is accepted (03:05). Amendments A9–A14 approved at 03:05: packages delivered as a per-login split without the main zip (§2, §3), two-digit participant numbers (§4, §6.2), wrapper without `timeout` (§6.3), login tables (§2, §5), stage timeline (§7), commands outside the wrapper (§6.7). All nine sessions are in (§0, §2). Counts updated (§9). §11 item 1 closed, item 5 added |
| Nov 13, 03:30 | User (03:26): A15 approved. A command's output ends when the shell prompt comes back or when the operator starts the next line, in every login of both classes; the prompt is recognized by its visible text, and the wrapper's END line and the paste-mode marker are cross-checks (§6.7). A14 corrected: a line typed into a waiting program is a command that starts no program in both classes, not input to the running command (§6.7). §11 item 4 settled |
| Nov 13, 04:57 | The preprocessing ran (03:35–04:25 EST; `real_lab3_preprocessing_run.md`). User (04:43): split groups are single stages (§8); A16 approved, tooling names in kept recorder text and wrapper text printed cut short (§6.3, §6.5); the validator removal readings (§6.4), one write at the shell prompt is one command (§6.7), and storage and routing (§4, §6.3) approved as run; the review before the freeze closed (§6.7). User (04:52): A17 approved, Ctrl-C, Ctrl-D and Enter on an empty line do not end a command's output (§6.7); the preprocessing was rerun with it and only the command list changed. Status and §0 brought up to date; §11 item 5 closed |
| Nov 13, 05:06 | User (05:00): run the preprocessing and get to Freeze 1, with code version 1.1. The preprocessing was run again from the originals (05:02–05:04) with byte-identical output, and **Freeze 1 was written at 05:04** (status, §0, §3, §10). Correction: the entry above was first logged as 05:10, a time ahead of the clock; the file shows 04:57 |
