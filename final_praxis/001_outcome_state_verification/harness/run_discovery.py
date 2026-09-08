"""Scientific runner skeleton. Intentionally refuses to run until fixture gate marker exists."""
from pathlib import Path

ROOT=Path(__file__).parents[1]
MARKER=ROOT/"artifacts"/"fixtures"/"FIXTURE_GATE_PASS"
if not MARKER.exists():
    raise SystemExit("BLOCKED: fixture gate has not passed")
print("READY: fixture gate marker present. Connect frozen agent/judge adapters before scientific execution.")
