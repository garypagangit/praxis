"""Replay two acquired captures offline; assess provenance, never label efficacy."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import time

import yaml
from tier3_linkage import audit


EXPECTED_PCAPS = {
    "s2": "a540ea3c71406e881051706cde8433a9f7c38dfce58c591a64037b10934b86c1",
    "fs1": "ce7e03921cf52174d874251a279c96c20db7e6155e3636b04a11bf14cf295658",
}
EXPECTED_RULES = "8004ed9bfaa518d8aa5418c49e935201236f213c83232889c174c9bd03c3d1da"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def run(suricata_dir, rules_archive, pcaps, private, output, instrumentation_only=False):
    root = Path(__file__).resolve().parent
    repo = root.parents[1]
    for name in ("run_tier3_provenance.py", "tier3_linkage.py", "PILOT_PROTOCOL.json"):
        relative = (root/name).relative_to(repo).as_posix()
        if subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=repo) != (root/name).read_bytes():
            raise ValueError("Commit the prospective operative files before running")
    private, output = private.resolve(), output.resolve()
    if private.exists() or output.exists() or private.is_relative_to(repo):
        raise ValueError("Use new private/output paths; raw artifacts must stay outside Git")
    if sha(rules_archive) != EXPECTED_RULES:
        raise ValueError("Rules archive differs from prospective freeze")
    for scenario, expected in EXPECTED_PCAPS.items():
        if sha(pcaps/scenario/"capture.pcap") != expected:
            raise ValueError("Capture differs from verified acquisition")
    binary = suricata_dir/"suricata.exe"
    version = subprocess.run([str(binary), "-V"], cwd=suricata_dir, capture_output=True, text=True, check=True)
    if "8.0.7 RELEASE" not in version.stdout:
        raise ValueError("Unexpected engine version")
    private.mkdir(parents=True)
    output.mkdir(parents=True)
    # Read only archive members; do not extract paths supplied by an archive.
    with tarfile.open(rules_archive) as archive:
        names = sorted(m.name for m in archive.getmembers() if m.isfile() and m.name.endswith(".rules"))
        merged = b"".join(b"\n# Source: "+name.encode()+b"\n"+archive.extractfile(name).read()+b"\n" for name in names)
        if instrumentation_only:
            names = ["INSTRUMENTATION_ONLY_NOT_SECURITY_DETECTIONS"]
            merged = (b'alert tcp any any -> any any (msg:"PROVENANCE ONLY TCP packet - no attack judgment"; sid:9900001; rev:1;)\n'
                      b'alert udp any any -> any any (msg:"PROVENANCE ONLY UDP packet - no attack judgment"; sid:9900002; rev:1;)\n')
        (private/"all.rules").write_bytes(merged)
        (private/"classification.config").write_bytes(archive.extractfile("rules/classification.config").read())
    config = yaml.safe_load((suricata_dir/"suricata.yaml").read_text(encoding="utf-8"))
    config["default-rule-path"] = str(private)
    config["rule-files"] = ["all.rules"]
    config["classification-file"] = str(private/"classification.config")
    config["reference-config-file"] = str(suricata_dir/"reference.config")
    config.pop("threshold-file", None)
    config["default-log-dir"] = str(private)
    config["unix-command"] = {"enabled": False}
    config["outputs"] = [{"eve-log": {"enabled": True, "filetype": "regular", "filename": "eve.json",
                                       "pcap-file": True, "types": [{"alert": {"metadata": True}}, "flow", "stats"]}}]
    config["logging"] = {"default-log-level": "info", "outputs": [{"console": {"enabled": True}}]}
    config_path = private/"suricata.yaml"
    config_path.write_text("%YAML 1.1\n---\n"+yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    freeze = {"scope": "OFFLINE_PACKET_PROVENANCE_ONLY_NO_SUPPRESSION_OR_ATTACK_LABELS",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
              "code_sha256": {name: sha(root/name) for name in ("run_tier3_provenance.py", "tier3_linkage.py")},
              "pcap_sha256": EXPECTED_PCAPS, "rules_archive_sha256": sha(rules_archive),
              "rules_members": names, "instrumentation_only": instrumentation_only,
              "merged_rules_sha256": sha(private/"all.rules"),
              "classification_sha256": sha(private/"classification.config"),
              "configuration_sha256": sha(config_path), "engine_version": version.stdout.strip(),
              "portable_runtime_sha256": {p.name: sha(p) for p in sorted(suricata_dir.iterdir()) if p.is_file() and p.suffix.lower() in (".exe", ".dll")},
              "portable_runtime_note": "Official MSI extracted without installation. Missing wpcap.dll supplied by MSYS2 libpcap1.10.6-3 under the required DLL name, plus existing Git OpenSSL libraries; exact binaries pinned. Offline -r only; no service or capture driver installed.",
              "checksum_policy": "-k none: explicit offline capture-offload accommodation; no detection-accuracy claim",
              "scenario_label_policy": "Existing SIABench labels describe original Snort scenarios; never propagate them to all packets or regenerated Suricata alerts."}
    write(output/"GENERATION_FREEZE.json", freeze)
    runs = {}
    for scenario in EXPECTED_PCAPS:
        capture = (pcaps/scenario/"capture.pcap").resolve()
        run_dir = private/scenario
        run_dir.mkdir()
        command = [str(binary), "-c", str(config_path), "-r", str(capture), "-l", str(run_dir), "--runmode", "single", "-k", "none"]
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=suricata_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, errors="replace", timeout=180)
        (run_dir/"EXECUTION.txt").write_text(completed.stdout, encoding="utf-8")
        rule_counts = re.search(r"(\d+) rules successfully loaded, (\d+) rules failed, (\d+) rules skipped", completed.stdout)
        execution = {"command": command, "exit_code": completed.returncode, "elapsed_seconds": time.perf_counter()-started,
                     "rule_loading": None if rule_counts is None else dict(zip(("loaded", "failed", "skipped"), map(int, rule_counts.groups())))}
        write(run_dir/"EXECUTION.json", execution)
        if completed.returncode:
            raise RuntimeError(f"Suricata failed for {scenario}; preserved execution log")
        eve = run_dir/"eve.json"
        if not eve.is_file():
            raise RuntimeError("Suricata did not create EVE output")
        counters, signatures, severities = Counter(), Counter(), Counter()
        for line in eve.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            counters[row.get("event_type", "MISSING")] += 1
            if row.get("event_type") == "alert":
                signatures[str(row.get("alert", {}).get("signature_id"))] += 1
                severities[str(row.get("alert", {}).get("severity"))] += 1
        linkage = audit(capture, eve)
        write(output/f"{scenario}_LINKAGE.json", linkage)
        runs[scenario] = {**execution, "events": dict(counters), "alert_signature_counts": dict(signatures),
                          "alert_severity_counts": dict(severities), "eve_sha256": sha(eve),
                          "execution_log_sha256": sha(run_dir/"EXECUTION.txt"), "linkage": linkage}
    result = {"status": "INSTRUMENTATION_PACKET_LINKAGE_ONLY_NOT_THREAT_DETECTION" if instrumentation_only else "REAL_CAPTURE_REPLAY_AND_PROVENANCE_COMPLETE_NOT_FULL_GATE_EFFICACY",
              "created_utc": datetime.now(timezone.utc).isoformat(), "freeze_sha256": sha(output/"GENERATION_FREEZE.json"),
              "runs": runs, "attack_alert_truth_derived": False, "suppression_evaluated": False,
              "population_certificate": False, "cloud_used": False, "instrumentation_only": instrumentation_only,
              "limitations": ["Two author-selected scenario captures, not independent attack calibration evidence",
                              "Packet linkage proves field agreement, not benign intent or LLM injection resistance",
                              "No authenticated user identity or complete enterprise incident state is derived",
                              "Rules and engine differ from original scenario labeling; new alert labels require validation"]}
    write(output/"RESULTS.json", result)
    print(json.dumps({"status": result["status"], "events": {key: row["events"] for key, row in runs.items()}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("suricata-dir", "rules-archive", "pcaps", "private", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--instrumentation-only", action="store_true", help="Diagnostic TCP/UDP packet rules; these events make no attack judgment")
    args = parser.parse_args()
    run(args.suricata_dir.resolve(), args.rules_archive.resolve(), args.pcaps.resolve(), args.private, args.output, args.instrumentation_only)
