"""Create/attach only this authorized campaign's 100GB encrypted scratch volume."""
import json
from datetime import datetime, timezone
from pathlib import Path
import boto3
from botocore.config import Config

INSTANCE = "i-039ed976444ade397"
NAME = "praxis-20260912-005-scratch"
ROOT = Path(__file__).resolve().parent / "execution"
ROOT.mkdir(parents=True, exist_ok=True)
ec2 = boto3.Session(profile_name="praxis-build", region_name="us-east-1").client(
    "ec2", config=Config(connect_timeout=10, read_timeout=30, retries={"total_max_attempts": 2}))
host = ec2.describe_instances(InstanceIds=[INSTANCE])["Reservations"][0]["Instances"][0]
if host["State"]["Name"] != "running" or host["InstanceType"] != "g5.xlarge":
    raise RuntimeError("Unexpected host state/type")
zone = host["Placement"]["AvailabilityZone"]
volumes = ec2.describe_volumes(Filters=[{"Name": "tag:Name", "Values": [NAME]},
    {"Name": "tag:PraxisCampaign", "Values": ["20260912"]},
    {"Name": "tag:FinalPraxis", "Values": ["005"]}])["Volumes"]
if len(volumes) > 1:
    raise RuntimeError("Ambiguous campaign volumes")
if volumes:
    volume = volumes[0]
else:
    volume = ec2.create_volume(AvailabilityZone=zone, Size=100, VolumeType="gp3", Encrypted=True,
        ClientToken="praxis-20260912-005-scratch-100gb",
        TagSpecifications=[{"ResourceType": "volume", "Tags": [
            {"Key": "Name", "Value": NAME}, {"Key": "PraxisCampaign", "Value": "20260912"},
            {"Key": "FinalPraxis", "Value": "005"},
            {"Key": "Lifecycle", "Value": "archive-results-before-cleanup"}]}])
if not (volume["Encrypted"] and volume["Size"] == 100 and volume["VolumeType"] == "gp3"
        and volume["AvailabilityZone"] == zone and not volume.get("SnapshotId")):
    raise RuntimeError("Volume does not match the authorized blank scratch allocation")
record = {"recorded_utc": datetime.now(timezone.utc).isoformat(), "instance": INSTANCE,
          "volume": volume, "price_usd_per_gb_month": 0.08, "allocation_monthly_usd": 8.0,
          "price_receipt": "Final Praxis004 new-scratch-volume-004.json, same region and gp3 service; verified 2026-09-12"}
(ROOT / "scratch_volume.json").write_text(json.dumps(record, indent=2, default=str))
identifier = volume["VolumeId"]
if not volume.get("Attachments"):
    ec2.get_waiter("volume_available").wait(VolumeIds=[identifier], WaiterConfig={"Delay": 2, "MaxAttempts": 30})
    attachment = ec2.attach_volume(VolumeId=identifier, InstanceId=INSTANCE, Device="/dev/sdf")
else:
    if any(a["InstanceId"] != INSTANCE for a in volume["Attachments"]):
        raise RuntimeError("Scratch attached to an unexpected host")
    attachment = volume["Attachments"]
(ROOT / "scratch_attachment.json").write_text(json.dumps(attachment, indent=2, default=str))
print(json.dumps({"volume_id": identifier, "serial": identifier.replace("-", ""), "zone": zone,
                  "size_gb": 100, "encrypted": True, "instance": INSTANCE}))
