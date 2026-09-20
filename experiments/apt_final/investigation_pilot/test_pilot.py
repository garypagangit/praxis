"""Synthetic semantic checks; never load the registered source or case files."""

import json
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import methods
    import prepare
    import run_pilot
finally:
    sys.path.pop(0)


G1 = "11111111-1111-1111-1111-111111111111"
G2 = "22222222-2222-2222-2222-222222222222"
G3 = "33333333-3333-3333-3333-333333333333"
ZERO = "00000000-0000-0000-0000-000000000000"


def creation(ref, guid, **updates):
    event = {
        "ref": ref, "kind": "creation", "host": "host-a", "guid": guid,
        "parent_guid": "", "image": r"C:\Windows\shell.exe",
        "parent_image": "", "utc": "2020-01-01T00:00:01.000000",
        "pid": "11", "parent_pid": "",
    }
    event.update(updates)
    return event


def child(**updates):
    event = creation(
        "anchor", G2, parent_guid=G1, parent_image=r"C:\Windows\shell.exe",
        image=r"C:\Apps\child.exe", pid="22", parent_pid="11",
        utc="2020-01-01T00:00:10.000000",
    )
    event.update(updates)
    return event


def question(kind="parent_creation"):
    return {
        "question_id": "synthetic-question", "anchor_ref": "anchor",
        "kind": kind, "stratum": "synthetic",
    }


def prediction(method, records, *, kind="parent_creation", budget=2):
    events = {row["ref"]: row for row in records}
    index = methods.build_index([r for r in records if r["kind"] == "creation"])
    return methods.retrieve(method, question(kind), events, index, budget)


def evaluated(method, records, *, kind="parent_creation", budget=2):
    q = question(kind)
    pred = prediction(method, records, kind=kind, budget=budget)
    gold = prepare.gold_by_scan(q, records)
    return run_pilot.evaluate_prediction(
        q, gold, pred, {row["ref"]: row for row in records}, budget,
    )


class RetrievalSemanticsTests(unittest.TestCase):
    def test_exact_host_scope_prevents_cross_host_matching(self):
        foreign = creation("foreign", G1, host="host-b")
        records = [foreign, child()]
        for method in ("exact_guid_join", "compact_guid_join"):
            with self.subTest(method=method, local=False):
                result = prediction(method, records)
                self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
                self.assertIsNone(result["answer_ref"])
            with self.subTest(method=method, local=True):
                result = prediction(method, records + [creation("local", G1)])
                self.assertEqual(result["answer_ref"], "local")

    def test_absent_creation_cannot_be_invented_from_basename(self):
        records = [creation("lookalike", G3), child()]
        for method in ("exact_guid_join", "compact_guid_join"):
            with self.subTest(method=method):
                result = evaluated(method, records)
                self.assertTrue(result["correct_abstention"])
                self.assertFalse(result["answered"])

    def test_time_inversion_does_not_disqualify_exact_identity(self):
        records = [creation("parent", G1, utc="2020-01-01T00:00:20"), child()]
        for method in ("exact_guid_join", "compact_guid_join"):
            with self.subTest(method=method):
                self.assertTrue(evaluated(method, records)["correct_supported_answer"])
        self.assertFalse(evaluated("name_time_abstain", records)["answered"])

    def test_equivalent_duplicate_references_are_acceptable(self):
        first = creation("parent-first", G1)
        second = creation("parent-copy", G1, image=first["image"].upper())
        records = [first, second, child()]
        gold = prepare.gold_by_scan(question(), records)
        self.assertEqual(set(gold["acceptable_refs"]), {first["ref"], second["ref"]})
        for method in methods.METHODS:
            with self.subTest(method=method):
                self.assertTrue(evaluated(method, records)["correct_supported_answer"])

    def test_conflicting_creation_metadata_requires_ambiguity(self):
        records = [creation("parent-a", G1), creation("parent-b", G1, pid="99"), child()]
        for method in methods.METHODS:
            with self.subTest(method=method):
                result = evaluated(method, records)
                self.assertEqual(result["prediction_status"], "AMBIGUOUS")
                self.assertTrue(result["correct_abstention"])
                self.assertTrue(result["correct_reason"])

    def test_zero_and_missing_target_guids_do_not_match_names(self):
        for missing in (None, "", ZERO):
            for method in ("exact_guid_join", "compact_guid_join"):
                with self.subTest(method=method, missing=missing):
                    records = [creation("lookalike", G1), child(parent_guid=missing)]
                    result = prediction(method, records)
                    self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
                    self.assertIsNone(result["answer_ref"])

    def test_name_nearest_can_answer_wrong_identity_and_is_penalized(self):
        records = [
            creation("real-parent", G1),
            creation("recent-lookalike", G3, utc="2020-01-01T00:00:09", pid="33"),
            child(),
        ]
        result = evaluated("name_nearest_time", records)
        self.assertEqual(result["answer_ref"], "recent-lookalike")
        self.assertTrue(result["incorrect_or_unsupported_answer"])
        self.assertFalse(result["correct_supported_answer"])
        self.assertTrue(evaluated("exact_guid_join", records)["correct_supported_answer"])

    def test_budget_one_abstains_and_retains_anchor(self):
        records = [creation("parent", G1), child()]
        for method in methods.METHODS:
            with self.subTest(method=method):
                result = prediction(method, records, budget=1)
                self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
                self.assertIsNone(result["answer_ref"])
                self.assertEqual(result["evidence_refs"], ["anchor"])

    def test_compact_serialization_charges_alias_dictionary_and_utf8(self):
        parent = creation("parent", G1, image="C:\\工具\\shell.exe")
        anchor = child(parent_image=parent["image"])
        result = prediction("compact_guid_join", [parent, anchor])
        alias_anchor = {**anchor, "guid": "P2", "parent_guid": "P1"}
        alias_parent = {**parent, "guid": "P1"}
        full_payload = {
            "evidence": [alias_anchor, alias_parent],
            "guid_aliases": {"P1": G1, "P2": G2},
        }
        encoded = json.dumps(full_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        without_map = json.dumps(
            {"evidence": full_payload["evidence"]}, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(result["serialized_bytes"], len(encoded.encode("utf-8")))
        self.assertGreater(result["serialized_bytes"], len(without_map))
        self.assertGreater(result["serialized_bytes"], len(encoded))

    def test_network_owner_lookup_does_not_use_parent_identity(self):
        owner = creation("owner", G1)
        anchor = child(kind="network", guid=G1, parent_guid=G3, image=owner["image"])
        records = [owner, creation("unrelated-parent", G3), anchor]
        for method in ("exact_guid_join", "compact_guid_join"):
            with self.subTest(method=method):
                result = evaluated(method, records, kind="owner_creation")
                self.assertEqual(result["answer_ref"], "owner")
                self.assertTrue(result["correct_supported_answer"])


class ScoringSemanticsTests(unittest.TestCase):
    def test_same_image_wrong_source_reference_cannot_pass(self):
        records = [creation("parent", G1), creation("other", G3, pid="33"), child()]
        q = question()
        gold = prepare.gold_by_scan(q, records)
        events = {r["ref"]: r for r in records}
        pred = prediction("exact_guid_join", records)
        pred.update(answer_ref="other", evidence_refs=["anchor", "other"])
        result = run_pilot.evaluate_prediction(q, gold, pred, events, 2)
        self.assertTrue(result["incorrect_or_unsupported_answer"])
        self.assertFalse(result["correct_supported_answer"])
        pred.update(answer_ref="fabricated-reference", evidence_refs=["anchor", "fabricated-reference"])
        with self.assertRaises(AssertionError):
            run_pilot.evaluate_prediction(q, gold, pred, events, 2)

    def test_answer_without_its_anchor_is_rejected(self):
        records = [creation("parent", G1), child()]
        pred = prediction("exact_guid_join", records)
        pred["evidence_refs"] = ["parent"]
        with self.assertRaises(AssertionError):
            run_pilot.evaluate_prediction(
                question(), prepare.gold_by_scan(question(), records), pred,
                {r["ref"]: r for r in records}, 2,
            )

    def test_abstention_reason_is_not_hidden_by_correct_abstention(self):
        records = [child()]
        pred = prediction("exact_guid_join", records)
        pred["status"] = "AMBIGUOUS"
        result = run_pilot.evaluate_prediction(
            question(), prepare.gold_by_scan(question(), records), pred,
            {r["ref"]: r for r in records}, 2,
        )
        self.assertTrue(result["correct_abstention"])
        self.assertFalse(result["correct_reason"])


class SourceNormalizationTests(unittest.TestCase):
    def message_record(self):
        return {
            "Channel": "Microsoft-Windows-Sysmon/Operational",
            "SourceName": "Microsoft-Windows-Sysmon", "EventID": 1,
            "Hostname": "Host-A", "ProcessID": 999,
            "Message": "\n".join([
                "Process Create:", "UtcTime: 2020-01-01 00:00:10.000",
                f"ProcessGuid: {{{G2}}}", "ProcessId: 22",
                r"Image: C:\Apps\child.exe", f"ParentProcessGuid: {{{G1}}}",
                "ParentProcessId: 11", r"ParentImage: C:\Windows\shell.exe",
            ]),
        }

    def test_message_fallback_uses_event_pid_instead_of_header_pid(self):
        record = prepare.normalize(self.message_record(), "synthetic-source")
        self.assertEqual(record["pid"], "22")
        self.assertEqual(record["parent_pid"], "11")
        self.assertEqual(record["guid"], G2)
        self.assertEqual(record["parent_guid"], G1)
        self.assertEqual(record["host"], "host-a")
        self.assertTrue(record["message_recovered"])

    def test_generic_event_id_one_from_other_provider_is_rejected(self):
        for field, value in (
            ("SourceName", "Other-Provider"), ("Channel", "SomeOther/Operational"),
        ):
            with self.subTest(field=field):
                raw = self.message_record()
                raw[field] = value
                with self.assertRaises(AssertionError):
                    prepare.normalize(raw, "not-sysmon")

    def test_null_zero_guids_remain_missing_not_fabricated(self):
        for value in (None, "", "-", ZERO, "{" + ZERO + "}"):
            with self.subTest(value=value):
                self.assertEqual(prepare.canonical_guid(value), "")
        raw = self.message_record()
        raw["Message"] = raw["Message"].replace(G2, ZERO)
        with self.assertRaises(AssertionError):
            prepare.normalize(raw, "zero-source-identity")

    def test_conflicting_duplicate_message_fields_are_rejected(self):
        raw = self.message_record()
        raw["Message"] += "\nProcessId: 777"
        with self.assertRaises(AssertionError):
            prepare.normalize(raw, "conflicting-pids")


if __name__ == "__main__":
    unittest.main()
