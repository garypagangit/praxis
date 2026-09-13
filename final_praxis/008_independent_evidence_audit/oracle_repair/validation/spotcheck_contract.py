"""Independent source-only checks of entity counts, ties and name multiplicity.

Reads clean tables and contract metadata, never model outputs or correctness scores.
Publishes counts and hashes, not source rows, task text, names or reference answers.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(__file__).resolve().parent.parent / "contract" / "TASK_CONTRACTS.json")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    tasks = {task["id"]: task for task in contract["tasks"]}
    sources = []

    def read(identifier):
        metadata = tasks[identifier]["tables"]["clean"]
        path = args.cache / metadata["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != metadata["sha256"]:
            raise RuntimeError("Clean-source hash mismatch")
        sources.append({"id": identifier, "path": metadata["path"], "sha256": actual})
        return pd.read_csv(path)

    findings = []
    d = read(42)
    selected = d[(d["Facility Type"].str.lower() == "grocery store") & d["Risk"].str.contains("risk 1", case=False)]
    findings.append({"id": 42, "selected_inspection_rows": len(selected), "distinct_licenses": int(selected["License #"].nunique()),
                     "distinct_business_names": int(selected["DBA Name"].nunique()), "issue": "Inspection row count differs from distinct store count."})
    d = read(48)
    counts = d.groupby("DBA Name")["Inspection ID"].count()
    findings.append({"id": 48, "businesses": len(counts), "tied_maximum_businesses": int((counts == counts.max()).sum()),
                     "issue": "One idxmax answer arbitrarily selects among multiple valid tied maxima."})
    d = read(40)
    groups = d.groupby("Facility Type")["Risk"].apply(lambda x: int((x.value_counts() == x.value_counts().max()).sum()))
    findings.append({"id": 40, "facility_types": len(groups), "groups_with_tied_modes": int((groups > 1).sum()),
                     "issue": "One mode per group plus literal JSON scoring does not credit all semantically valid ties/serializations."})
    d = read(130)
    counts = d[(d.HospitalType.str.lower() == "acute care hospitals") & (d.EmergencyService.str.lower() == "yes")].CountyName.value_counts()
    findings.append({"id": 130, "requested_top_k": 3, "counties_tied_at_cutoff": int((counts == counts.iloc[2]).sum()),
                     "issue": "Top-k boundary is tied; multiple valid top-three subsets exist."})
    d = read(68)
    counts = d.BusinessType.value_counts()
    findings.append({"id": 68, "business_types": len(counts), "frequency_counts_in_rank_order": [int(x) for x in counts],
                     "issue": "Ordered reference treats arbitrary within-tie order as mandatory."})
    d = read(109)
    counts = d.times_appeared.sort_values(ascending=False)
    findings.append({"id": 109, "top_five_appearance_counts": [int(x) for x in counts.head(5)],
                     "issue": "Ranked top-five selection has an unspecified within-tie order."})
    d = read(93)
    spans = (pd.to_datetime(d.last_appeared, errors="coerce") - pd.to_datetime(d.first_appeared, errors="coerce")).dt.days
    chosen = d[spans == spans.min()]
    findings.append({"id": 93, "returned_name_records": len(chosen), "distinct_names": int(chosen.name.nunique()),
                     "distinct_record_ids": int(chosen.id.nunique()), "issue": "Name-list multiplicity is not explicitly required by the purpose wording."})
    d = read(133)
    chosen = d[(d.HospitalType.str.lower() == "acute care hospitals") & (d.EmergencyService.str.lower() == "yes")]
    findings.append({"id": 133, "selected_hospital_rows": len(chosen), "distinct_provider_numbers": int(chosen.ProviderNumber.nunique()),
                     "issue": "Hospital row count differs from the number of distinct hospital provider identifiers."})
    for identifier, meal in ((16, "lunch"), (17, "dinner")):
        d = read(identifier)
        exact = set(d.loc[d.event.str.lower() == meal, "sponsor"].dropna())
        broader = set(d.loc[d.event.str.contains(r"\b" + meal + r"\b", case=False, na=False), "sponsor"].dropna())
        findings.append({"id": identifier, "exact_event_sponsors": len(exact), "word_matching_sponsors": len(broader),
                         "additional_sponsors_with_compound_event_labels": len(broader - exact),
                         "issue": "Broad meal-offering purpose does not explicitly authorize exclusion of compound event labels; this is evidence of ambiguity, not replacement gold."})
    positive_checks = []
    d = read(23)
    ranks = d.groupby("venue").dish_count.mean().sort_values(ascending=False)
    positive_checks.append({"id": 23, "within_top_three_ties": int(ranks.head(3).duplicated().sum()), "third_cutoff_ties": int((ranks == ranks.iloc[2]).sum())})
    d = read(47)
    rates = d.assign(failed=d.Results.str.lower() == "fail").groupby("Facility Type").failed.mean()
    positive_checks.append({"id": 47, "maximal_failure_rate_ties": int((rates == rates.max()).sum())})
    d = read(89)
    amounts = d.groupby(["City", "Zip"]).LoanAmount.sum()
    positive_checks.append({"id": 89, "maximal_aggregate_amount_ties": int((amounts == amounts.max()).sum())})
    d = read(92)
    positive_checks.append({"id": 92, "rows": len(d), "unique_record_ids": int(d.id.nunique()), "unique_names": int(d.name.nunique())})
    d = read(7)
    chosen = d[d.occasion.str.lower() == "daily"]
    positive_checks.append({"id": 7, "selected_rows": len(chosen), "unique_record_ids": int(chosen.id.nunique())})
    report = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Independent source-only semantic spot check; no model outputs, aggregate scores or inference.",
              "contract_sha256_at_review": hashlib.sha256(args.contract.read_bytes()).hexdigest(),
              "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "pandas_version": pd.__version__, "sources": sources, "findings": findings, "positive_controls": positive_checks,
              "recommendation": "Retain diagnostic agreement; exclude unresolved entity, tie, serialization and multiplicity contracts from purpose-success claims until independently resolved."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"findings": len(findings), "output": str(args.output)}))


if __name__ == "__main__":
    main()
