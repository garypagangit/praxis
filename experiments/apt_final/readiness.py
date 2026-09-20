"""Fail-closed data release boundary; inventory success is not modeling readiness.

No real-data normalization/review adapter has yet qualified for this experiment.
Add a release adapter only after implementing and testing its evidence validator;
editing an E0 HOLD receipt into PASS must never unlock scientific runs.
"""
from pathlib import Path
import hashlib
import json

QUALIFIED_RELEASE_ADAPTERS = ()


def require_data_release(receipt, rows=None, edges=None):
    record = json.loads(Path(receipt).read_text(encoding="utf-8-sig"))
    if record.get("status") != "PASS":
        raise ValueError("E0 has not released normalized data: " + str(record.get("status")))
    if record.get("scope") != "REAL_NORMALIZED_DATA" or record.get("real_telemetry") is not True:
        raise ValueError("Receipt is not an audited real normalized dataset")
    if record.get("schema") != "APT_FINAL_DATA_RELEASE_V1":
        raise ValueError("Unsupported data-release schema")
    if not isinstance(record.get("group_evidence"), dict) or not record["group_evidence"]:
        raise ValueError("Missing independently grounded group evidence")
    for key in ("rows_sha256", "edges_sha256", "validator_sha256", "evidence_manifest_sha256"):
        value = record.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Missing valid release hash: " + key)
    for key, path in (("rows_sha256", rows), ("edges_sha256", edges)):
        if path is not None:
            with Path(path).open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != record[key]:
                raise ValueError("Released input changed: " + key)
    if record.get("release_adapter") not in QUALIFIED_RELEASE_ADAPTERS:
        raise ValueError("HOLD_DATA_CONTRACT: no normalized-data evidence validator is qualified yet; "
                         "complete the documented E0 mapping/review and qualify its adapter. A hand-edited PASS cannot release modeling.")
    # Each future adapter must validate full evidence and return the verified record.
    raise ValueError("Release adapter implementation is missing")
