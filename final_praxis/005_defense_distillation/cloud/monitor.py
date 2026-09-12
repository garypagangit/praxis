"""Read private experiment status without printing benchmark generations."""
import json
from pathlib import Path
import boto3
from botocore.config import Config

bucket = "praxis-garypagan-272615233626-us-east-1"
prefix = "final-praxis/20260912/runs/fp005-20260912-37fdd3f/"
s3 = boto3.Session(profile_name="praxis-build", region_name="us-east-1").client(
    "s3", config=Config(connect_timeout=10, read_timeout=30, retries={"total_max_attempts": 2}))
result = {"s3_uri": "s3://" + bucket + "/" + prefix}
for name in ("cloud_status.json", "launch.json", "outputs/teacher_complete.json", "outputs/summary.json"):
    try:
        body = s3.get_object(Bucket=bucket, Key=prefix + name)["Body"].read()
        parsed = json.loads(body)
        result[name] = parsed
    except s3.exceptions.NoSuchKey:
        result[name] = {"not_yet_present": True}
try:
    body = s3.get_object(Bucket=bucket, Key=prefix + "driver.log", Range="bytes=-20000")["Body"].read().decode("utf-8", errors="replace")
    events = []
    for line in body.splitlines():
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and "event" in item:
            events.append(item)
    result["latest_events"] = events[-8:]
    result["driver_log_bytes_read"] = len(body)
    result["traceback_present"] = "Traceback (most recent call last):" in body
except s3.exceptions.NoSuchKey:
    result["driver_log_not_yet_present"] = True
path = Path(__file__).resolve().parent / "execution" / "latest_status.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(result, indent=2))
status = result.get("cloud_status.json", {})
print(json.dumps({"s3_uri": result["s3_uri"], "state": status.get("state"),
    "updated_utc": status.get("updated_utc"), "elapsed_seconds": status.get("elapsed_seconds"),
    "sync_errors": status.get("sync_errors"), "latest_events": result.get("latest_events"),
    "traceback_present": result.get("traceback_present"),
    "teacher": result["outputs/teacher_complete.json"],
    "summary_status": result["outputs/summary.json"].get("status"), "receipt": str(path)}, indent=2))
