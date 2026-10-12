CONTROLLED SOC ATTRIBUTION PILOT -- 2026-10-12

Deliverable: runnable restricted microtask environment, common recorder, four task
templates, recruitment draft, operator instructions, annotation codebook and a
frozen pilot decision rule. No people recruited, paid inference run or human/AI
effect measured. See VALIDATION.json for actual engineering checks.

Objective: find a reproducible difference in response-to-feedback behavior between
human and runtime-AI operators that could eventually help SOC triage. Shared
adaptive behavior is eligible evidence. Small useful gains count.

Scope amendment
This is an initial controlled microtask pilot, not real attack traffic or a full
Linux penetration-testing range. The restricted target models discovery, returned
constraints, conflicting evidence and recovery. It exposes identical text commands
and results to every controller. It does not establish defender visibility into an
attacker's local shell. The claimed SOC setting requires managed command/result
recording at a defender-observed interface. Realistic attack-session transfer and
analyst benefit are separate later milestones. Do not publish toy discrimination
as AI-APT detection. Existing published evidence remains development material.

Run (Python standard library; no cloud, Docker or external dependencies)
  python lab.py --task discovery --seed 101 --output sessions/practice --interactive
Other tasks: constraint, conflict, recovery. Use a fresh output directory for each
session. Commands: help, status, list, read, query, verify, export, submit. This is
NOT a host shell; the target never runs a submitted operating-system command.
The researcher runs the process; participants receive only its text interface.
Do not give participants filesystem access, source, seed, task label or solutions.
For AI, omit --interactive and connect the controller to the same stdin/stdout
interface. Controller submits one line, receives one JSON result, then chooses
the next action. Its prompts/provider logs stay outside defender.json.
An actual provider adapter is not included or tested; model/API choice and budget
must be set before live AI collection. No AI sessions are implied by our tests.

Files produced
defender.json: command, completed stdout/stderr, exit status, explicit truncation,
monotonic acceptance/completion times. No origin/task/seed/final-score labels.
provenance.json: session id, task, seed, success and stop reason, initially U/unknown
origin. Researcher must add verified provenance using PROVENANCE_TEMPLATE.json.
Never infer origin from behavior. Keep both files private; share redacted defender
views for annotation. The same 16 KiB combined output cap applies to every arm.
Target output is deterministic; timing reflects input/controller and local runtime,
not an independent reasoning-speed measure. Timing is excluded from primary analysis.

Budget and interruptions
20 accepted submissions or 10 minutes, whichever occurs first; stop on success.
The CLI checks elapsed time when a line arrives; a waiting input does not produce
another accepted action after deadline. Coordinator ends idle sessions at ten
minutes. Five completed submissions is the retained primary observation boundary.
Short sessions remain in coverage; do not require extra commands to pad them.
No partial output is exposed. EOF or interruption remains an incomplete session.

Start here
1. Run the engineering tests and one coordinator practice session.
2. Review PILOT_PROTOCOL.txt and TASK_PACK.txt; appoint a recruitment coordinator.
3. Recruit eight genuine human operators using RECRUITMENT.txt (not sent).
4. Select two AI configurations and record budget, versions and controller policy.
5. Qualify capture with the actual human and AI interfaces using practice cases.
6. Freeze code/config/assignment hashes, then begin pilot collection.
7. Annotate blind to origin, apply DECISION_RULE.txt, and decide whether to fund
   a larger held-task/held-operator confirmation. No positive result is guaranteed.

What remains before collection
Participant scheduling, applicable institutional research review, two independent
annotators, actual AI controller integration, and no-AI-authored script controls.
Consent language here is a coordinator draft, not institutional approval. Confirm
local requirements with your university before research recruitment/collection.
This is a practical dependency, not a request to approve code already authorized.
