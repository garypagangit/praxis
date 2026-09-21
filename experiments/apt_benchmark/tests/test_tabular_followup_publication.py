"""Synthetic publication artifacts and mocked Git; never push or read model outcomes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.apt_benchmark.tabular_followup import publish_followup as publish
from experiments.apt_benchmark.tabular_followup import promote_publication as promote


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def synthetic_values():
    seeds = sorted(publish.SEEDS)
    source = Path(publish.__file__).parent
    batch = source.parent / "tabular_batch"
    original = publish.read(batch / "protocol.json")
    common = {"data_sha256": original["data_npz_sha256"], "manifest_sha256": original["manifest_sha256"],
              "protocol_sha256": publish.sha(batch / "protocol.json"),
              "code_sha256": {name: publish.sha(batch / name) for name in ["run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"]}}
    primary = {"matched_seed_count": 10, "expected_seed_count": 10, "all_ten_registered_seeds_present": True,
               "e1": {"status": "FAIL", "mean_paired_macro_f1_delta": {"mean": .025}}, "e4": {"status": "FAIL"}}
    e1 = {"audit_status": "PASS", "all_registered_cells_complete": True, "completed_cell_count": 50,
          "missing_registered_cells": [], "common_binding": common, "primary": primary,
          "cells": [{"model": model, "seed": seed} for model in sorted(publish.E1_MODELS) for seed in seeds],
          "model_summaries": {model: {"seeds": seeds, "macro_f1": {"mean": .65, "seed_count": 10}} for model in sorted(publish.E1_MODELS)}}
    comparisons = {"audit_status": "PASS", "strong_batch_complete": True, "complete_strong_cells": 60,
                   "expected_strong_cells": 60, "full_e1_completed_cells": 50, "full_e1_primary": deepcopy(primary),
                   "protocol_sha256": publish.sha(source / "protocol_strong_baselines.json"), "auditor_sha256": publish.sha(source / "audit_comparisons.py"),
                   "cells": [{"condition": condition, "model": model, "seed": seed} for condition in sorted(publish.CONDITIONS) for model in sorted(publish.TREE_MODELS) for seed in seeds],
                   "comparisons": {condition: {"status": "FAIL" if condition == "equal_32_per_class" else "DESCRIPTIVE_UNEQUAL_LABEL_BUDGET", "matched_seeds": 10,
                                                   "pairs": [{"seed": seed} for seed in seeds], "mean_macro_f1_delta": -.035} for condition in sorted(publish.CONDITIONS)},
                   "model_summaries": {condition: {model: {"seeds": 10, "macro_f1": {"mean": .6, "seed_count": 10}, "normal_fpr": {"mean": .01, "seed_count": 10}} for model in sorted(publish.TREE_MODELS)} for condition in sorted(publish.CONDITIONS)}}
    gate_primary = {"status": "DEVELOPMENT_NEGATIVE", "paired_seed_count": 10, "required_paired_seeds": 10,
                    "guards": {"example_guard": False}, "mean_minimum_rare_recall_deltas": {"single_tabicl": .03, "single_tree": -.02}}
    gate = {"missing_pairs": [], "rows": [{"seed": seed} for seed in seeds], "primary": gate_primary,
            "policy_protocol_sha256": publish.sha(source / "protocol_rare_stage_gate.json")}
    gate_audit = {"audit_status": "PASS", "run_status": "COMPLETE", "audited_pair_count": 10, "primary": deepcopy(gate_primary),
                  "protocol_sha256": gate["policy_protocol_sha256"], "runner_sha256": publish.sha(source / "run_rare_stage_gate.py"),
                  "audit_source_sha256": publish.sha(source / "audit_rare_stage_gate.py"), "artifact_hashes": {}}
    return e1, comparisons, gate, gate_audit


def final_fixture(root):
    e1, comparisons, gate, gate_audit = synthetic_values()
    write(root / "e1/ANALYSIS.json", e1)
    write(root / "COMPARISONS.json", comparisons)
    write(root / "gate/AGGREGATE.json", gate)
    write(root / "gate/SOURCE_ANALYSIS.json", e1)
    write(root / "gate/PREFIT_RECEIPT.json", {"synthetic_test_only": True})
    write(root / "gate/COMPLETE.json", {"synthetic_test_only": True})
    (root / "gate/ROUTING_PRIVATE.npz").write_bytes(b"synthetic private placeholder; not scientific data")
    gate_audit["artifact_hashes"] = {name: publish.sha(root / "gate" / name) for name in ["AGGREGATE.json", "PREFIT_RECEIPT.json", "COMPLETE.json", "SOURCE_ANALYSIS.json", "ROUTING_PRIVATE.npz"]}
    write(root / "gate_audit/AUDIT.json", gate_audit)
    return e1, comparisons, gate, gate_audit


class PublicationTests(unittest.TestCase):
    def test_counts_and_exact_model_seed_rosters_are_required(self):
        values = synthetic_values()
        publish.verify(*values)
        for index, key, replacement in [(0, "completed_cell_count", 49), (1, "complete_strong_cells", 59), (3, "audited_pair_count", 9)]:
            changed = deepcopy(values)
            changed[index][key] = replacement
            with self.assertRaises(ValueError):
                publish.verify(*changed)
        for index, key in [(0, "cells"), (1, "cells"), (2, "rows")]:
            changed = deepcopy(values)
            changed[index][key][0] = deepcopy(changed[index][key][1])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                publish.verify(*changed)

    def test_independent_roundoff_allowed_but_counts_and_meaning_exact(self):
        values = synthetic_values()
        values[3]["primary"]["mean_minimum_rare_recall_deltas"]["single_tabicl"] += 1e-16
        publish.verify(*values)
        for key, value in [("paired_seed_count", 9), ("status", "DEVELOPMENT_PROMISING"), ("required_paired_seeds", 10.0)]:
            changed = deepcopy(values)
            changed[3]["primary"][key] = value
            with self.assertRaisesRegex(ValueError, "outcomes disagree"):
                publish.verify(*changed)
        values[3]["primary"]["mean_minimum_rare_recall_deltas"]["single_tabicl"] += 1e-4
        with self.assertRaises(ValueError):
            publish.verify(*values)

    def test_mixed_e1_or_unequal_budget_winner_claim_rejected(self):
        values = synthetic_values()
        changed = deepcopy(values)
        changed[1]["full_e1_primary"]["e1"]["status"] = "PASS"
        with self.assertRaises(ValueError):
            publish.verify(*changed)
        values[1]["comparisons"]["abundant_benign_1024"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "interpretation"):
            publish.verify(*values)

    def test_percent_differences_use_signed_percentage_points_and_links(self):
        e1, comparisons, gate, _ = synthetic_values()
        text = publish.report(e1, comparisons, gate)
        self.assertIn("+2.50 percentage points", text)
        self.assertIn("-3.50 percentage points", text)
        self.assertNotIn("% (percentage points)", text)
        self.assertIn("65.00%", text)
        self.assertIn("../../tabular_followup/NOVELTY_POSITION.md", text)
        self.assertIn("no first-method claim", text)
        self.assertIn("No human review was performed", text)

    def test_publication_checks_source_hashes_and_private_gate_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = final_fixture(root)
            names = ["E1_ANALYSIS.json", "COMPARISONS.json", "GATE_AGGREGATE.json", "GATE_AUDIT.json"]
            published_values = dict(zip(names, values))
            publish.verify_sources(root, published_values)
            changed = deepcopy(published_values)
            changed["COMPARISONS.json"]["auditor_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "audit/source binding"):
                publish.verify_sources(root, changed)
            (root / "gate/ROUTING_PRIVATE.npz").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "Gate artifact changed"):
                publish.verify_sources(root, published_values)

    def test_row_arrays_and_absolute_paths_cannot_be_published(self):
        for value in [{"selected_fit_indices": [1, 2]}, {"data": {"test_probabilities": [[.2, .8]]}}, {"note": "C:/private/cache"}, {"note": "/home/user/data"}, {"accidental_rows": [0] * 2091}]:
            with self.assertRaises(ValueError):
                publish.aggregate_only(value)
        publish.aggregate_only({"artifact_hashes": {"PREDICTIONS.npz": "a" * 64}, "link": "https://example.org/paper"})

    def test_optional_transfer_needs_twenty_unique_cells_and_same_source(self):
        e1, _, _, _ = synthetic_values()
        transfer = {"audit_status": "PASS", "all_cells_complete": True, "run_status": "COMPLETE", "verified_cells": 20,
                    "paired_seed_count": 10, "decision": "DESCRIPTIVE_ONLY_NO_PASS_GATE",
                    "per_seed": [{"model": model, "seed": seed} for model in ["selected_gbdt", "tabicl_v2"] for seed in sorted(publish.SEEDS)],
                    "source_data_npz_sha256": e1["common_binding"]["data_sha256"], "source_manifest_sha256": e1["common_binding"]["manifest_sha256"],
                    "e1_protocol_sha256": e1["common_binding"]["protocol_sha256"]}
        publish.verify_transfer(transfer, e1)
        for key, value in [("verified_cells", 19), ("source_data_npz_sha256", "wrong"), ("decision", "PASS")]:
            changed = deepcopy(transfer)
            changed[key] = value
            with self.assertRaises(ValueError):
                publish.verify_transfer(changed, e1)

    def test_publish_roundtrip_only_aggregates_and_bound_source_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "private_final"
            final_fixture(final)
            repo = root / "repo"
            output = repo / promote.OUTPUT_RELATIVE
            receipt = publish.publish(final, output)
            self.assertEqual(set(path.name for path in output.iterdir()), promote.ALLOWED - {"TRANSFER_SUMMARY.json"})
            self.assertEqual(len(promote.verify_publication(repo)), 6)
            self.assertEqual(receipt["source_sha256"]["GATE_AGGREGATE.json"], publish.sha(final / "gate/AGGREGATE.json"))
            report = (output / "REPORT.md").read_text()
            import re
            for target in re.findall(r"\]\(([^)]+)\)", report):
                self.assertTrue((output / target).resolve().is_file(), target)
            (output / "REPORT.md").write_text("changed after audit")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                promote.verify_publication(repo)

    def test_promotion_rejects_unbound_extra_file_and_wrong_publisher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final_fixture(root / "final")
            output = root / "repo" / promote.OUTPUT_RELATIVE
            publish.publish(root / "final", output)
            receipt = publish.read(output / "PUBLICATION.json")
            receipt["publisher_sha256"] = "0" * 64
            write(output / "PUBLICATION.json", receipt)
            with self.assertRaisesRegex(ValueError, "publisher source"):
                promote.verify_publication(root / "repo")
            receipt["publisher_sha256"] = publish.sha(publish.__file__)
            write(output / "PUBLICATION.json", receipt)
            (output / "RAW.npz").write_bytes(b"must remain private")
            with self.assertRaisesRegex(ValueError, "Unexpected file"):
                promote.verify_publication(root / "repo")


class PromotionGitTests(unittest.TestCase):
    def mocked_git(self, *, branch=None, fetch=None, push=None, staged="", remote_head=None):
        calls = []
        files = [promote.OUTPUT_RELATIVE + "/REPORT.md", promote.OUTPUT_RELATIVE + "/PUBLICATION.json"]
        def fake(repo, *args):
            calls.append(args)
            if args == ("branch", "--show-current"):
                return branch or promote.EXPECTED_BRANCH
            if args == ("remote", "get-url", "--all", "origin"):
                return fetch or promote.EXPECTED_REMOTE
            if args == ("remote", "get-url", "--push", "--all", "origin"):
                return push or promote.EXPECTED_REMOTE
            if args == ("diff", "--cached", "--name-only"):
                return staged
            if args[:3] == ("diff", "--cached", "--name-only"):
                return files[0]
            if args[0] in {"add", "commit", "push"}:
                return ""
            if args == ("rev-parse", "HEAD"):
                return "a" * 40
            if args == ("ls-remote", "origin", "refs/heads/apt-benchmark"):
                return (remote_head or "a" * 40) + "\trefs/heads/apt-benchmark"
            raise AssertionError(args)
        return fake, calls, files

    def test_mock_commit_is_allowlisted_and_push_has_no_force(self):
        fake, calls, files = self.mocked_git()
        with patch.object(promote, "verify_publication", return_value=files), patch.object(promote, "git", side_effect=fake):
            result = promote.promote(Path("."))
        self.assertEqual(result["status"], "PUSHED_AND_VERIFIED")
        self.assertIn(("add", "-f", "--", *files), calls)
        commit = next(call for call in calls if call[0] == "commit")
        self.assertIn("--only", commit)
        self.assertEqual(list(commit[commit.index("--") + 1:]), files)
        self.assertIn(("push", "origin", "HEAD:refs/heads/apt-benchmark"), calls)
        self.assertFalse(any("--force" in argument or argument == "+HEAD" for call in calls for argument in call))

    def test_mock_remote_branch_and_unrelated_staging_blocks_all_mutation(self):
        cases = [{"branch": "main"}, {"fetch": "https://other/repo.git"}, {"push": "https://other/push.git"},
                 {"push": promote.EXPECTED_REMOTE + "\nhttps://second/repo.git"}, {"staged": "unrelated.txt"}]
        for case in cases:
            fake, calls, files = self.mocked_git(**case)
            with patch.object(promote, "verify_publication", return_value=files), patch.object(promote, "git", side_effect=fake):
                with self.assertRaises(ValueError):
                    promote.promote(Path("."))
            self.assertFalse(any(call[0] in {"add", "commit", "push"} for call in calls))

    def test_mock_remote_commit_verification_is_required(self):
        fake, calls, files = self.mocked_git(remote_head="b" * 40)
        with patch.object(promote, "verify_publication", return_value=files), patch.object(promote, "git", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "Remote verification"):
                promote.promote(Path("."))


if __name__ == "__main__":
    unittest.main()
