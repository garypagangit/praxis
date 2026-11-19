"""Correlate selected rejected flows with Sysmon process categories locally."""

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import gzip
import ipaddress
import json
import ntpath
from pathlib import Path
import xml.etree.ElementTree as ET

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


FIELDS = {"SourceIp", "DestinationIp", "SourcePort", "DestinationPort", "Protocol", "Image"}


def connection_index(inp, participant):
    index = defaultdict(list)
    stats = Counter()
    for host in base.HOSTS:
        path = inp.get(f"set_aside/{participant}/{host}/sysmon.jsonl.gz")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                message = record["message"]
                match = base.EVENT_ID.search(message)
                if not match or int(match.group(1)) != 3:
                    continue
                root = ET.fromstring(message)
                fields = {e.attrib["Name"]: (e.text or "") for e in root.iter()
                          if e.attrib.get("Name") in FIELDS}
                if fields.get("Protocol", "").lower() != "udp":
                    continue
                srcport, dstport = fields.get("SourcePort", ""), fields.get("DestinationPort", "")
                if not srcport.isdigit() or not dstport.isdigit():
                    stats["unusable_ports"] += 1
                    continue
                srcport, dstport = int(srcport), int(dstport)
                if srcport != 41641 and dstport != 3478:
                    continue
                try:
                    srcip = str(ipaddress.ip_address(fields.get("SourceIp", "")))
                    dstip = str(ipaddress.ip_address(fields.get("DestinationIp", "")))
                except ValueError:
                    stats["unusable_addresses"] += 1
                    continue
                image = ntpath.basename(fields.get("Image", "")).lower()
                kind = "tailscale_named" if "tailscale" in image else ("other_named" if image and image != "-" else "unknown")
                moment = int(float(record["timestamp"]) / 1000)
                index[(srcip, dstip, srcport, dstport)].append((moment, kind, host))
                stats["selected_events"] += 1
                stats[f"process_{kind}"] += 1
    for events in index.values():
        events.sort()
    return index, dict(stats)


def match_events(index, fields):
    try:
        key = (str(ipaddress.ip_address(fields[3])), str(ipaddress.ip_address(fields[4])),
               int(fields[5]), int(fields[6]))
    except ValueError:
        return "unusable_address_or_port"
    events = index.get(key, [])
    start, end = int(fields[10]), int(fields[11])
    left = bisect_left(events, (start, "", ""))
    right = bisect_right(events, (end, "\uffff", "\uffff"))
    matches = events[left:right]
    if not matches:
        return "unmatched"
    kinds = {event[1] for event in matches}
    if kinds == {"tailscale_named"}:
        return "matched_tailscale_named"
    if "tailscale_named" in kinds:
        return "matched_mixed_processes"
    if "other_named" in kinds:
        return "matched_other_named"
    return "matched_unknown_process"


def run(source, prior, output):
    source, prior = source.resolve(), prior.resolve()
    output = expanded.safe_output(output, source, prior)
    script_hash = base.sha256(Path(__file__).resolve())
    manifest_path = prior / "extraction.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    features_path = prior / "features.csv"
    if (manifest["script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or manifest["features_sha256"] != base.sha256(features_path)):
        raise ValueError("Prior feature or script hash mismatch")
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != manifest["freeze1_sha256"]:
        raise ValueError("Study freeze mismatch")
    features = base.rows(features_path)
    lookup = {(r["session"], r["window"]): r for r in features}
    if len(lookup) != len(features):
        raise ValueError("Duplicate prior feature windows")
    totals = defaultdict(Counter)
    session_stats = {}
    found = set()
    for participant, all_windows in base.make_windows(inp).items():
        windows = [w for w in all_windows if (w["session"], w["window"]) in lookup]
        if not windows:
            raise ValueError("Session has no eligible windows")
        starts = [w["start"] for w in windows]
        session, label = windows[0]["session"], windows[0]["label"]
        found.update((session, w["window"]) for w in windows)
        index, sysmon = connection_index(inp, participant)
        counts = Counter()
        path = inp.get(f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                fields = json.loads(line)["message"].split()
                if len(fields) != 14 or fields[0] != "2":
                    raise ValueError("Unexpected flow record")
                if fields[13] != "OK":
                    if fields[13] not in ("NODATA", "SKIPDATA"):
                        raise ValueError("Unexpected flow status")
                    continue
                if base.locate(windows, starts, int(fields[11])) is None:
                    continue
                counts["flow_records"] += 1
                if fields[7] not in ("6", "17"):
                    counts["flow_other_protocol"] += 1
                if fields[12] != "REJECT":
                    if fields[12] != "ACCEPT":
                        raise ValueError("Unexpected flow action")
                    continue
                counts["flow_reject"] += 1
                if fields[7] != "17":
                    continue
                counts["rejected_udp"] += 1
                srcport, dstport = int(fields[5]), int(fields[6])
                if srcport == 41641:
                    counts["udp_source_41641"] += 1
                if dstport == 3478:
                    counts["udp_destination_3478"] += 1
                if srcport == 41641 and dstport == 3478:
                    counts["udp_both_ports"] += 1
                if srcport == 41641 or dstport == 3478:
                    counts["udp_selected"] += 1
                    counts["udp_selected_" + match_events(index, fields)] += 1
        expected = [lookup[(session, w["window"])] for w in windows]
        for key in ("flow_records", "flow_reject", "flow_other_protocol"):
            if counts[key] != sum(int(row[key]) for row in expected):
                raise ValueError(f"Flow totals do not match previous extraction: {key}")
        totals[label].update(counts)
        session_stats[session] = {"class": label, "flow": dict(counts), "sysmon": sysmon}
        print(f"Correlated flow records for {session}", flush=True)
    if found != set(lookup):
        raise ValueError("Prior windows do not match the study")
    if base.sha256(Path(__file__).resolve()) != script_hash:
        raise ValueError("Attribution code changed during analysis")
    output.mkdir(parents=True)
    result = {
        "version": 1, "script_sha256": script_hash, "freeze1_sha256": inp.freeze_hash,
        "prior_extraction_sha256": base.sha256(manifest_path), "inputs_sha256": inp.verified,
        "totals_by_class": {k: dict(v) for k, v in totals.items()}, "sessions": session_stats,
    }
    (output / "attribution.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved restricted aggregate attribution to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.prior, args.output)
