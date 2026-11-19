"""Investigate defender-visible flow patterns without exporting addresses or commands."""

import argparse
from collections import Counter, defaultdict
import gzip
import ipaddress
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


def local_host_mapping(inp, participant):
    observed = defaultdict(Counter)
    stats = Counter()
    wanted = {"Initiated", "SourceIp", "DestinationIp"}
    for host in base.HOSTS:
        path = inp.get(f"set_aside/{participant}/{host}/sysmon.jsonl.gz")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                message = json.loads(line)["message"]
                match = base.EVENT_ID.search(message)
                if not match or int(match.group(1)) != 3:
                    continue
                stats["network_events"] += 1
                root = ET.fromstring(message)
                fields = {e.attrib["Name"]: (e.text or "") for e in root.iter()
                          if e.attrib.get("Name") in wanted}
                initiated = fields.get("Initiated", "").lower()
                address = fields.get("SourceIp" if initiated == "true" else "DestinationIp", "")
                if initiated not in ("true", "false"):
                    stats["unresolved_events"] += 1
                    continue
                try:
                    address = str(ipaddress.ip_address(address))
                except ValueError:
                    stats["unresolved_events"] += 1
                    continue
                observed[address][host] += 1
                stats["mapped_events"] += 1
    stats["unambiguous_local_addresses"] = sum(len(hosts) == 1 for hosts in observed.values())
    stats["ambiguous_local_addresses"] = sum(len(hosts) > 1 for hosts in observed.values())
    mapping = {address: next(iter(hosts)) for address, hosts in observed.items() if len(hosts) == 1}
    return mapping, dict(stats)


def context_windows(session, label, first_start, last_end):
    windows = []
    for phase, start in (("before", first_start - 300), ("after", last_end)):
        for i in range(10):
            begin = start + i * 30
            windows.append({"session": session, "label": label, "window": f"{phase}_{i}",
                            "start": begin, "end": begin + 30,
                            "values": {name: 0 for name in base.FEATURES["combined"]},
                            "covered": set(), "skipped_flow": False, "phase": phase})
    return windows


def login_extent(inp, participant, included):
    report = json.loads(inp.get("reports/05_windows_report.json").read_text(encoding="utf-8"))
    info = report["sessions"][participant]
    extents = []
    for login in info["logins"].values():
        key = login["login_key"]
        if key not in included:
            continue
        path = inp.get(f"data/cleaned/{info['session_key']}/{key}.recorder.jsonl")
        with path.open(encoding="utf-8") as stream:
            start = json.loads(json.loads(next(stream))["message"])
        if start["kind"] != "start":
            raise ValueError("Recorder does not begin with a start record")
        t0 = base.timestamp(start["time"])
        duration = float(login["w30"]["duration_s"])
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("Invalid login duration")
        extents.append((t0, t0 + duration))
    if not extents:
        raise ValueError("No included login periods")
    return min(x[0] for x in extents), max(x[1] for x in extents)


def endpoint_name(address, hostmap):
    try:
        return hostmap.get(str(ipaddress.ip_address(address)), "unmapped")
    except ValueError:
        return "invalid_or_missing"


def analyze_flow(path, windows, hostmap):
    eligible = [w for w in windows if "flow" in w["covered"] and not w["skipped_flow"]]
    starts = [w["start"] for w in eligible]
    ports = defaultdict(Counter)
    hosts = defaultdict(Counter)
    for w in eligible:
        w["diagnostic"] = Counter()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            fields = json.loads(line)["message"].split()
            if len(fields) != 14 or fields[0] != "2":
                raise ValueError("Unexpected flow record")
            if fields[13] != "OK":
                if fields[13] not in ("SKIPDATA", "NODATA"):
                    raise ValueError("Unexpected flow status")
                continue
            window = base.locate(eligible, starts, int(fields[11]))
            if window is None:
                continue
            if fields[12] not in ("ACCEPT", "REJECT"):
                raise ValueError("Unexpected flow action")
            phase, proto = window["phase"], fields[7]
            d = window["diagnostic"]
            d["records"] += 1
            if proto not in ("6", "17"):
                d["other_protocol"] += 1
                if proto == "1":
                    d["other_icmp"] += 1
            if fields[12] != "REJECT":
                continue
            d["rejected"] += 1
            if proto == "1":
                d["rejected_icmp"] += 1
            elif proto == "17":
                d["rejected_udp"] += 1
            elif proto == "6":
                d["rejected_tcp"] += 1
            hosts[phase]["source:" + endpoint_name(fields[3], hostmap)] += 1
            hosts[phase]["destination:" + endpoint_name(fields[4], hostmap)] += 1
            if proto in ("6", "17"):
                name = "tcp" if proto == "6" else "udp"
                for position, field in (("source", fields[5]), ("destination", fields[6])):
                    port = int(field)
                    if not 0 <= port <= 65535:
                        raise ValueError("Invalid flow port")
                    ports[phase][f"{name}/{port}/{position}"] += 1
    for w in eligible:
        d = w["diagnostic"]
        if (d["records"] != w["values"]["flow_records"]
                or d["rejected"] != w["values"]["flow_reject"]
                or d["other_protocol"] != w["values"]["flow_other_protocol"]):
            raise ValueError("Diagnostic records do not match extracted flow features")
    return eligible, ports, hosts


def run(source, prior, output):
    source, prior = source.resolve(), prior.resolve()
    output = expanded.safe_output(output, source, prior)
    own_hash = base.sha256(Path(__file__).resolve())
    prior_manifest_path = prior / "extraction.json"
    prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    features_path = prior / "features.csv"
    if (prior_manifest["features_sha256"] != base.sha256(features_path)
            or prior_manifest["script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or prior_manifest["window_seconds"] != 30):
        raise ValueError("Prior features or extraction script changed")
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != prior_manifest["freeze1_sha256"]:
        raise ValueError("Study freeze does not match the previous experiment")
    by_session = base.make_windows(inp)
    included = {r["login_key"] for r in base.rows(inp.get("data/labels/logins.csv"))
                if r["included"] == "1"}
    prior_features = base.rows(features_path)
    lookup = {(r["session"], r["window"]): r for r in prior_features}
    if len(lookup) != len(prior_features):
        raise ValueError("Duplicate prior feature windows")
    sessions = {}
    found = set()
    aggregate = defaultdict(Counter)
    port_totals = defaultdict(Counter)
    host_totals = defaultdict(Counter)
    for participant, candidates in by_session.items():
        retained = []
        for w in candidates:
            key = (w["session"], w["window"])
            if key in lookup:
                if w["label"] != lookup[key]["label"]:
                    raise ValueError("Prior labels differ")
                w["phase"] = "during"
                retained.append(w)
                found.add(key)
        if not retained:
            raise ValueError("Session has no prior eligible windows")
        session, label = retained[0]["session"], retained[0]["label"]
        first, last = login_extent(inp, participant, included)
        windows = sorted(retained + context_windows(session, label, first, last), key=lambda x: x["start"])
        if any(a["end"] > b["start"] for a, b in zip(windows, windows[1:])):
            raise ValueError("Context windows overlap study windows")
        hostmap, mapping_stats = local_host_mapping(inp, participant)
        path = inp.get(f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz")
        flow_stats = base.flow_stream(path, windows)
        eligible, ports, hosts = analyze_flow(path, windows, hostmap)
        if any(w not in eligible for w in retained):
            raise ValueError("A previous eligible window lost flow coverage")
        per_phase = defaultdict(Counter)
        for w in eligible:
            phase = w["phase"]
            per_phase[phase]["windows"] += 1
            per_phase[phase].update(w["diagnostic"])
            if phase == "during":
                old = lookup[(session, w["window"])]
                for key in ("flow_records", "flow_reject", "flow_other_protocol"):
                    if int(old[key]) != w["values"][key]:
                        raise ValueError("Re-extracted flow values differ from previous experiment")
        for phase in ("before", "during", "after"):
            aggregate[(label, phase)].update(per_phase[phase])
            port_totals[(label, phase)].update(ports[phase])
            host_totals[(label, phase)].update(hosts[phase])
        sessions[session] = {"class": label, "periods": {k: dict(v) for k, v in per_phase.items()},
                             "host_mapping": mapping_stats, "flow_stream": flow_stats,
                             "prior_coverage": prior_manifest["coverage_by_session"][session]}
        print(f"Investigated flow and Sysmon records for {session}", flush=True)
    if found != set(lookup):
        raise ValueError("Prior windows do not match frozen login metadata")
    if base.sha256(Path(__file__).resolve()) != own_hash:
        raise ValueError("Flow investigation script changed during analysis")
    output.mkdir(parents=True)
    document = {
        "version": 1, "script_sha256": own_hash, "freeze1_sha256": inp.freeze_hash,
        "prior_extraction_sha256": base.sha256(prior_manifest_path), "inputs_sha256": inp.verified,
        "periods": {f"{label}_{phase}": dict(counter) for (label, phase), counter in aggregate.items()},
        "top_ports": {f"{label}_{phase}": counter.most_common(20)
                      for (label, phase), counter in port_totals.items()},
        "host_endpoints": {f"{label}_{phase}": dict(counter)
                           for (label, phase), counter in host_totals.items()},
        "sessions": sessions,
    }
    (output / "investigation.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved restricted aggregate investigation to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.prior, args.output)
