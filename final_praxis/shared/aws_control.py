"""Explicit, file-backed AWS control for authorized Final Praxis jobs."""
import argparse
import datetime as dt
import json
from pathlib import Path

import boto3
from botocore.config import Config

BUCKET = "praxis-garypagan-272615233626-us-east-1"
DEFAULT_INSTANCE = "i-039ed976444ade397"
RECEIPTS = Path(__file__).resolve().parents[1] / "execution" / "20260908"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["send", "poll", "upload", "download", "list", "pricing"])
    parser.add_argument("target", nargs="?")
    parser.add_argument("--instance", default=DEFAULT_INSTANCE)
    parser.add_argument("--key")
    args = parser.parse_args()
    session = boto3.Session(profile_name="praxis-build", region_name="us-east-1")
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2})
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    if args.action == "send":
        script = Path(args.target)
        response = session.client("ssm", config=cfg).send_command(
            InstanceIds=[args.instance], DocumentName="AWS-RunShellScript",
            Parameters={"commands": [script.read_text(encoding="utf-8")], "executionTimeout": ["21600"]},
            Comment="Authorized Final Praxis 001-003: " + script.name,
            OutputS3BucketName=BUCKET,
            OutputS3KeyPrefix="final-praxis/20260908/ssm",
        )
        command_id = response["Command"]["CommandId"]
        result = {"command_id": command_id, "instance": args.instance, "script": str(script),
                  "submitted_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        (RECEIPTS / (command_id + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    elif args.action == "poll":
        response = session.client("ssm", config=cfg).get_command_invocation(CommandId=args.target, InstanceId=args.instance)
        result = {k: response.get(k) for k in ["CommandId", "Status", "ResponseCode", "ExecutionElapsedTime", "StandardOutputContent", "StandardErrorContent", "StandardOutputUrl", "StandardErrorUrl"]}
        (RECEIPTS / (args.target + "-status.json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    elif args.action == "upload":
        if not args.key or not args.key.startswith("final-praxis/20260908/"):
            raise SystemExit("Upload must have a new Final Praxis run prefix")
        session.client("s3", config=cfg).upload_file(args.target, BUCKET, args.key)
        result = {"uploaded": args.target, "uri": "s3://" + BUCKET + "/" + args.key}
    elif args.action == "download":
        if not args.key or not args.key.startswith("final-praxis/20260908/"):
            raise SystemExit("Expected Final Praxis key")
        dest = Path(args.target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        session.client("s3", config=cfg).download_file(BUCKET, args.key, str(dest))
        result = {"downloaded": str(dest)}
    elif args.action == "list":
        response = session.client("s3", config=cfg).list_objects_v2(Bucket=BUCKET, Prefix=args.key or "final-praxis/20260908/", MaxKeys=100)
        result = [{"key": x["Key"], "size": x["Size"]} for x in response.get("Contents", [])]
    else:
        filters = [{"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in
                   [("instanceType", "g5.xlarge"), ("location", "US East (N. Virginia)"),
                    ("operatingSystem", "Linux"), ("tenancy", "Shared"), ("preInstalledSw", "NA"), ("capacitystatus", "Used")]]
        response = session.client("pricing", config=cfg).get_products(ServiceCode="AmazonEC2", Filters=filters, MaxResults=10)
        result = []
        for raw in response["PriceList"]:
            product = json.loads(raw)
            for offer in product.get("terms", {}).get("OnDemand", {}).values():
                for rate in offer["priceDimensions"].values():
                    result.append({"description": rate["description"], "unit": rate["unit"], "USD": rate["pricePerUnit"]["USD"]})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
