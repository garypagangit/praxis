"""Run SecAlertBench G0 schema/eligibility audit and prepare a real review packet.

No scorer fitting, no inferred provenance, no human agreement fabricated.
Original alerts and the interactive packet stay in a private local directory.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

from eligibility import check_eligibility

EXPECTED_SHA = "33f95305d1c42f8e615e4f94066119570859dee7eb086dff7c2273536c932ea3"
LABELS = {"Attack", "Non-Attack"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def packet_html(cases):
    cases = [{"case_id": c["case_id"], "alert": {k: v for k, v in c["alert"].items()
              if k.casefold() not in {"label", "ground_truth", "true_label", "expected"}}} for c in cases]
    # Escape '<' in embedded JSON: alert bodies cannot terminate this script tag.
    payload = json.dumps(cases, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>SOC alert review</title>
<style>body{font:17px system-ui;max-width:1000px;margin:32px auto;padding:0 20px;background:#f5f7fa;color:#172331}h1{font-size:28px}article{background:white;border:1px solid #ccd5df;border-radius:8px;margin:24px 0;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px ui-monospace;max-height:480px;overflow:auto;background:#eef2f6;padding:14px}label{display:block;margin:10px 0}select,textarea,input,button{font:inherit;padding:9px;max-width:95%}textarea{width:95%;height:72px}button{background:#173e68;color:white;border:0;border-radius:5px;cursor:pointer}.note{padding:15px;background:#fff3cd}small{overflow-wrap:anywhere}</style>
<h1>Blinded SOC alert label review</h1><p>Review the displayed alert evidence. The dataset labels are hidden. This page works locally and sends nothing to a server.</p>
<p class="note">Use <b>Unable to verify</b> when the visible fields cannot establish the answer. Complete raw logs were not released. Agreement with the dataset label does not independently establish ground truth.</p>
<label>Reviewer name or study ID <input id="reviewer" autocomplete="off"></label><label>Relevant experience <input id="experience" autocomplete="off"></label><div id="cases"></div>
<button id="save">Download review responses</button><p id="status"></p>
<script type="application/json" id="data">__DATA__</script><script>
const cases=JSON.parse(document.getElementById('data').textContent);const root=document.getElementById('cases');
for(let i=0;i<cases.length;i++){let c=cases[i], a=document.createElement('article');a.id='case_'+i;
let h=document.createElement('h2');h.textContent='Alert '+(i+1)+' of '+cases.length;a.append(h);
let id=document.createElement('small');id.textContent=c.case_id;a.append(id);
let pre=document.createElement('pre');pre.textContent=JSON.stringify(c.alert,null,2);a.append(pre);
let select=document.createElement('select');select.className='decision';for(const [v,t] of [['','Choose a finding'],['Attack','Attack'],['Non-Attack','Non-attack'],['Unable to verify','Unable to verify']]){let o=document.createElement('option');o.value=v;o.textContent=t;select.append(o)}a.append(select);
let reason=document.createElement('textarea');reason.className='reason';reason.placeholder='Which visible facts support your finding, or what evidence is missing?';a.append(reason);root.append(a)}
document.getElementById('save').onclick=()=>{let reviewer=document.getElementById('reviewer').value.trim();let experience=document.getElementById('experience').value.trim();let responses=cases.map((c,i)=>({case_id:c.case_id,decision:document.querySelector('#case_'+i+' .decision').value,reason:document.querySelector('#case_'+i+' .reason').value.trim()}));if(!reviewer||responses.some(r=>!r.decision||!r.reason)){document.getElementById('status').textContent='Enter a reviewer ID, and a finding and reason for every alert.';return;}let blob=new Blob([JSON.stringify({reviewer,experience,completed_utc:new Date().toISOString(),responses},null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='soc_label_review_responses.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);document.getElementById('status').textContent='Responses downloaded. They have not been scored or sent anywhere.'};
</script></html>'''
    return template.replace("__DATA__", payload)


def run(source, private, output):
    raw = source.read_bytes()
    assert digest(raw) == EXPECTED_SHA
    rows = json.loads(raw)
    assert len(rows) == 8322 and all(isinstance(r, dict) and r.get("Label") in LABELS for r in rows)
    registration_path = Path(__file__).with_name("REGISTRATION.json")
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    assert not output.exists() and not private.exists(), "Preserve previous attempts"
    private.mkdir(parents=True)
    groups = defaultdict(list)
    failures = Counter()
    field_presence = Counter()
    sample_order = []
    eligible = 0
    for ordinal, row in enumerate(rows):
        for key in row:
            field_presence[key] += 1
        check = check_eligibility(row)  # No independent evidence supplied by the release.
        eligible += check["eligible"]
        failures.update(check["failed_predicates"])
        stripped = {k: v for k, v in row.items() if k not in {"Label", "sip", "dip", "sport", "dport"}}
        group = digest(canonical(stripped))
        groups[group].append(row["Label"])
        content_sha = digest(canonical({k: v for k, v in row.items() if k != "Label"}))
        case_id = digest(f"{ordinal}|{content_sha}".encode())
        rank = digest(f"{registration['human_review']['sampling_salt']}|{case_id}".encode())
        sample_order.append((rank, case_id, ordinal, content_sha))
    selected = sorted(sample_order)[:registration["human_review"]["sample_size"]]
    cases = [{"case_id": cid, "alert": {k: v for k, v in rows[ordinal].items() if k != "Label"}}
             for _, cid, ordinal, _ in selected]
    key = {cid: rows[ordinal]["Label"] for _, cid, ordinal, _ in selected}
    (private / "REVIEW_CASES.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    (private / "ANSWER_KEY.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    (private / "REVIEW.html").write_text(packet_html(cases), encoding="utf-8")
    receipt = {
        "status": "G0_HOLD_FULL_EXPERIMENT_REQUIREMENTS_UNMET",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_sha256": EXPECTED_SHA,
        "registration_sha256": digest(registration_path.read_bytes()),
        "code_sha256": {name: digest(Path(__file__).with_name(name).read_bytes()) for name in ("g0_audit.py", "eligibility.py")},
        "rows": len(rows), "labels": dict(Counter(r["Label"] for r in rows)),
        "field_presence": dict(sorted(field_presence.items())), "unique_rules": len({r["rule_name"] for r in rows}),
        "full_predicate_eligible": eligible, "failed_predicate_counts": dict(failures),
        "content_groups_excluding_labels_addresses_ports": len(groups),
        "duplicate_excess_rows": sum(len(v)-1 for v in groups.values()),
        "mixed_label_content_groups": sum(len(set(v)) > 1 for v in groups.values()),
        "sample": [{"case_id": cid, "source_row_zero_based": ordinal, "input_content_sha256": csha} for _, cid, ordinal, csha in selected],
        "human_review": {"status": "PENDING", "cases": len(cases), "reviewer": None, "agreement": None,
                         "qualification": "Visible-alert review only; independent raw provenance unavailable"},
        "private_review_files": {p.name: {"sha256": digest(p.read_bytes()), "bytes": p.stat().st_size} for p in private.iterdir() if p.is_file()},
        "no_scorer_fitted": True, "no_efficacy_hypothesis_tested": True,
        "release_constraints": ["Research-use license not located in inspected SecAlertBench release", "No alert timestamps or enterprise/campaign IDs", "No complete independent raw logs", "No severity or complete incident-cluster state", "No completed human label audit", "Independent attack calibration unit not established"],
        "interpretation": "Zero full-predicate eligibility is a contract/data feasibility result, not successful suppression, evidence of scorer failure, or a certified operational guarantee. All alerts would be retained under missing evidence. Randomized addresses do not establish independent samples.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("status", "rows", "labels", "full_predicate_eligible", "failed_predicate_counts", "content_groups_excluding_labels_addresses_ports", "mixed_label_content_groups", "human_review")}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--private-review-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.source, a.private_review_dir, a.output)
