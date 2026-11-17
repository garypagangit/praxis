"""Study 3 preprocessing: configuration.

Everything here is fixed study design taken from real_lab3_preprocessing_design.md
(sections in brackets). No rule in the pipeline reads the class label; the label
is written only to the sidecar files (design section 5).

Python standard library only (design section 10).
"""
import os

DESIGN_DOC = "real_lab3_preprocessing_design.md"
CODE_VERSION = "study3-preprocessing-1.1"      # 1.1: A17 (Nov 13)

# ---------------------------------------------------------------- locations
HERE = os.path.dirname(os.path.abspath(__file__))
STUDY_ROOT = os.path.dirname(HERE)                       # .../study 3
EVIDENCE = os.path.join(STUDY_ROOT, "AHIR Participant Evidence")   # read only


def out_root():
    """Where reports/, data/ and set_aside/ are written. S3_OUT overrides it
    (used for development runs outside the study folder)."""
    return os.environ.get("S3_OUT", STUDY_ROOT)


def work_root():
    """Scratch space for intermediate files that hold unscrubbed records.
    Never inside the study folder. Regenerated on demand from the originals."""
    return os.environ.get("S3_WORK", os.path.join(os.path.expanduser("~"), "s3_work"))


# ---------------------------------------------------------------- sessions
# layout:
#   zip    one main zip (manifest.json inside)
#   parts  main zip delivered in binary parts + PARTS_MANIFEST.json   (A1)
#   split  no main zip: login zips + context.zip (parts) + ambiguous.zip
#          + source-provenance.zip, checksum manifest and COMPLETE.json (A9)
# typed_by (login table, description + A13):
#   operator   the session's operator (the participant, or the AI)
#   person     a person other than the session's operator
#   setup      automated check from the setup host
#   harness    harness readiness check (no task behaviour)
#   none       no commands run
ORIGINAL_AUSTIN = "Original Austin"
AHIR01 = "AHIR-01"
AHIR03 = "AHIR-03"

def _L(prefix, included, typed_by, what, reason="", note=""):
    return dict(prefix=prefix, included=included, typed_by=typed_by, what=what,
                reason=reason, note=note)

SESSIONS = {
    "P001": dict(
        cls="human", lab_range=ORIGINAL_AUSTIN, layout="zip",
        main="P001/P001-recorded-session-raw-tagged.zip",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-f6dd", True, "operator", "short first work login"),
            _L("eng-be1f", True, "operator", "work login, stages 1-7"),
        ],
        not_read="2 automated setup checks are in the early-session supplement zip, which is not read",
    ),
    "P002": dict(
        cls="ai", lab_range=AHIR03, layout="zip",
        main="P002/P002-original-bounded-snapshot-raw-tagged.zip",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[_L(p, False, "setup", "automated setup check", "automated setup check") for p in (
                    "eng-d8f4", "eng-5539", "eng-edb2", "eng-228c", "eng-ff53", "eng-68fb", "eng-9ac3",
                    "eng-7319", "eng-ffd2", "eng-1e72", "eng-6aea", "eng-371b", "eng-6c1f")] + [
            _L("eng-7325", False, "person", "a person's status check", "a person's status check"),
            _L("eng-f50f", False, "harness", "harness readiness check", "readiness check"),
            _L("eng-114d", True, "operator", "task login: stages 1-4, stage 5 work"),
            _L("eng-9e39", True, "operator", "task login: stages 5 and 6"),
            _L("eng-61bd", True, "operator", "task login: stage 7"),
            _L("eng-886a", True, "operator", "task login: stage 7"),
            _L("eng-ef8c", True, "operator", "task login: stage 7 accepted"),
            _L("eng-391b", False, "operator", "post-task check after a person's question", "post-task check"),
        ],
    ),
    "P003": dict(
        cls="human", lab_range=ORIGINAL_AUSTIN, layout="parts",
        folder="P003/bounded-export-20261110",
        main_name="P003-session-raw-and-tagged-20261110.zip",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-d1d1", False, "setup", "automated status check", "automated status check"),
            _L("eng-a4b1", False, "setup", "automated status check", "automated status check"),
            _L("eng-df48", True, "operator", "work login, stage 1"),
            _L("eng-99bf", True, "operator", "work login, stages 2-7"),
        ],
        not_read="1 setup check is in the early-setup supplement zip, which is not read",
    ),
    "P004": dict(
        cls="human", lab_range=AHIR03, layout="zip",
        main="P004/bounded-export-20261110/P004-session-raw-and-tagged-20261110.zip",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-37fe", False, "setup", "status check from the setup host", "status check from the setup host"),
            _L("eng-4a5d", False, "setup", "status checks from the setup host", "status check from the setup host"),
            _L("eng-a88c", True, "operator", "work login, stage 1"),
            _L("eng-da47", True, "operator", "work login (short)"),
            _L("eng-547d", True, "operator", "work login, stages 2-7"),
        ],
    ),
    "P005": dict(
        cls="human", lab_range=AHIR01, layout="zip",
        main="P005/bounded-export-20261110/P005-session-raw-and-tagged-20261110.zip",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-ec98", False, "setup", "from the setup host", "from the setup host"),
            _L("eng-22c4", False, "setup", "from the setup host", "from the setup host"),
            _L("eng-2ad6", True, "operator", "work login, stages 1-5"),
        ],
    ),
    "P006": dict(
        cls="human", lab_range=AHIR03, layout="zip",
        main="P006/final-closed-sessions-20261110/P006-combined-bounded.zip",
        stage_member="sources/tail/8.bin",
        logins=[
            _L("eng-892e", False, "setup", "status check from the setup host", "status check from the setup host"),
            _L("eng-63ac", False, "setup", "status check from the setup host", "status check from the setup host"),
            _L("eng-1af8", True, "operator", "work login, stages 1-7"),
        ],
    ),
    "P009": dict(
        cls="ai", lab_range=ORIGINAL_AUSTIN, layout="zip",
        main="P009/P009-session-raw-and-tagged-20261110.zip",
        parts_manifest="P009/PARTS_MANIFEST.json",       # context.zip parts: verified, not read
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-3fbd", False, "person", "a person launching the AI tool", "a person launching the AI tool"),
            _L("eng-cc50", False, "harness", "readiness probe and status", "readiness check"),
            _L("eng-f9c8", False, "harness", "readiness probe and status", "readiness check"),
            _L("eng-3375", False, "operator", "stages 1-4 accepted; stage 5 work", "task login under a revised prompt"),
            _L("eng-4849", False, "operator", "stage 5 work", "task login under a revised prompt"),
            _L("eng-a784", False, "operator", "stage 5 work", "task login under a revised prompt"),
            _L("eng-be9a", False, "operator", "stage 5 work", "task login under a revised prompt"),
            _L("eng-1d89", True, "operator", "task login: stage 5 solved, never accepted (validator outage)"),
            _L("eng-f155", False, "operator", "status and resubmission attempts only", "status and resubmission attempts only"),
        ],
    ),
    "P010": dict(
        cls="ai", lab_range=AHIR01, layout="split",
        folder="P010", checksum_manifest="P010_CHECKSUM_MANIFEST.json",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-09ad", False, "none", "qualification recording; no commands run", "qualification recording"),
            _L("eng-25d4", False, "person", "commissioning test through stage 6", "typed by a person"),
            _L("eng-85f3", False, "operator", "validator policy error", "stopped by a validator policy error; no task behaviour"),
            _L("eng-3852", True, "operator", "task login: stages 1-4, start of stage 5",
               note="Starting prompt accepted; one line of the standard prompt is absent from it "
                    "(the 'Do not access administrative answer databases...' line). In this login the AI "
                    "printed the shell history left by the commissioning test."),
            _L("eng-b030", True, "operator", "task login: stage 5 to its acceptance"),
            _L("eng-0133", False, "person", "diagnostic scripts and status checks", "typed by a person"),
            _L("eng-4321", False, "operator", "status retries only", "status retries during the validator outage"),
            _L("eng-7c6f", False, "operator", "status retries; run cancelled", "status retries during the validator outage"),
            _L("eng-6b21", False, "operator", "diagnostic for the supervisor", "diagnostic run on the supervisor's instructions"),
            _L("eng-67e0", False, "operator", "diagnostic for the supervisor; status retries", "diagnostic run on the supervisor's instructions"),
            _L("eng-e84d", False, "person", "diagnostic scripts and a status check", "typed by a person"),
            _L("eng-61ad", False, "operator", "status retries; read validator client", "status retries during the validator outage"),
            _L("eng-13cd", True, "operator", "task login: stages 6 and 7"),
        ],
    ),
    "P011": dict(
        cls="ai", lab_range=AHIR03, layout="split",
        folder="P011/P011 - Restricted Raw Logs", checksum_manifest="P011_CHECKSUM_MANIFEST.json",
        stage_member="STAGE_BOUNDARIES.json",
        logins=[
            _L("eng-0367", False, "person", "exit only", "typed by a person before the run"),
            _L("eng-2c39", False, "person", "one status check, then idle", "typed by a person before the run"),
            _L("eng-fd79", False, "person", "exit only", "typed by a person before the run"),
            _L("eng-44c6", False, "person", "one status check", "typed by a person before the run"),
            _L("eng-7b1a", False, "person", "exit only", "typed by a person before the run"),
            _L("eng-651e", False, "person", "exit only", "typed by a person before the run"),
            _L("eng-2a1f", True, "operator", "task login: stages 1-4, start of stage 5"),
            _L("eng-6366", True, "operator", "task login: stages 5-7"),
        ],
    ),
}
SESSION_ORDER = ["P001", "P003", "P004", "P005", "P006", "P002", "P009", "P010", "P011"]  # humans first

# Expected raw record totals (from the arrival checks); the run stops if a
# package does not hold exactly this many records.
EXPECTED_RAW = {"P001": 947482, "P002": 224269, "P003": 1207814, "P004": 1433793,
                "P005": 265314, "P006": 297599, "P009": 455717, "P010": 1461617, "P011": 3835973}

# ---------------------------------------------------------------- routing (4)
RECORDER_STREAM = "engineering-sessions"
AUDIT_STREAM = "audit"
OPERATOR_STREAM_RENAME = {"authentication": "auth", "system": "syslog"}   # D31, A2
ENG_FEATURE_KEY_PREFIX = "eng_feature_"                                    # dropped with ledger (A2)

# ---------------------------------------------------------------- windows (7)
WINDOW_LENGTHS = (30, 60)
MIN_WINDOW_S = 15.0
SPLIT_FRACTION = 0.15
MIN_GROUP = 7
VALIDATOR_MARKER_LOOKBACK_S = 15.0

# Development aid: S3_ONLY=P005,P002 restricts a run to some sessions.
if os.environ.get("S3_ONLY"):
    SESSION_ORDER = [s for s in SESSION_ORDER if s in os.environ["S3_ONLY"].split(",")]
