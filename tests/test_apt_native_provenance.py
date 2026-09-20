"""Independent negative checks for the native pilot's frozen input boundary."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.apt_final.native_graph import provenance as p


class NativeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        temporary = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.repo = Path(temporary) / "repo"
        self.here = self.repo / "experiments" / "apt_final" / "native_graph"
        self.here.mkdir(parents=True)
        self.data = Path(temporary) / "data"
        (self.data / "cadets").mkdir(parents=True)
        self.stack.enter_context(patch.object(p, "HERE", self.here))
        self.stack.enter_context(patch.object(p, "REPO", self.repo))
        self.stack.enter_context(patch.dict("os.environ", {"APT_FROZEN_BUNDLE_SHA256": "a" * 64}))
        (self.here / "data.py").write_text("# Fixture adapter identity\n", encoding="utf-8")
        (self.here / "pilot.py").write_text("# Fixture pilot identity\n", encoding="utf-8")
        (self.here / "PROTOCOL.md").write_text("Development only.\n", encoding="utf-8")
        (self.here / "run_cloud.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.config = self.here / "config.json"
        self.write(self.config, {"scope": "DEVELOPMENT_ONLY"})
        self.graph = self.data / "cadets" / "train0.npz"
        np.savez(self.graph, node_type=np.array([0, 1]), src=np.array([0]),
                 dst=np.array([1]), relation=np.array([0]), y=np.array([0, 0]))
        self.manifest = {"schema": "apt-final-native-graph-data-v1", "status": "STATIC_DEVELOPMENT_ONLY",
            "adapter_sha256": p.digest(self.here / "data.py"),
            "datasets": [{"dataset": "cadets", "status": "STATIC_DEVELOPMENT_ONLY",
                "matches_upstream_git_blob": True,
                "graphs": [{"npz": "cadets/train0.npz", "npz_sha256": p.digest(self.graph)}]}]}
        self.save_manifest()
        self.registration = self.here / "REGISTRATION.json"
        self.record = {"scope": "DEVELOPMENT_ONLY", "status": "FROZEN_NATIVE_GRAPH_PILOT",
            "git_commit": "b" * 40, "config_sha256": p.digest(self.config),
            "code_hashes": {x.relative_to(self.repo).as_posix(): p.digest(x) for x in p.code_paths(self.config)},
            "data_manifest_sha256": p.digest(self.data / "MANIFEST.json"),
            "data_files": p.data_inventory(self.data)}
        self.write(self.registration, self.record)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def save_manifest(self):
        self.write(self.data / "MANIFEST.json", self.manifest)

    def verify(self):
        return p.verify_registration(self.config, self.data, self.registration)

    def test_matching_frozen_artifacts_verify(self):
        self.assertEqual(self.verify()["status"], "FROZEN_NATIVE_GRAPH_PILOT")

    def test_changed_model_code_refused(self):
        (self.here / "pilot.py").write_text("# Changed model\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Registered source changed"):
            self.verify()

    def test_added_executable_file_refused(self):
        (self.here / "extra.py").write_text("# New dependency\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.verify()

    def test_changed_config_refused(self):
        self.write(self.config, {"scope": "DEVELOPMENT_ONLY", "epochs": 999})
        with self.assertRaisesRegex(ValueError, "Configuration changed"):
            self.verify()

    def test_changed_manifest_refused_even_if_arrays_match(self):
        self.manifest["claimed_scope"] = "confirmation"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.verify()

    def test_changed_array_refused(self):
        np.savez(self.graph, node_type=np.array([9]))
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_added_unregistered_array_refused(self):
        np.savez(self.data / "surprise.npz", data=np.array([1]))
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_missing_array_refused(self):
        self.graph.unlink()
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_stale_adapter_manifest_refused(self):
        self.manifest["adapter_sha256"] = "0" * 64
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "matching native"):
            p.validate_manifest(self.data)

    def test_unqualified_data_status_refused(self):
        self.manifest["status"] = "HOLD"
        self.save_manifest()
        with self.assertRaises(ValueError):
            p.validate_manifest(self.data)

    def test_upstream_match_requires_true_boolean(self):
        for value in (False, "false", 1, None):
            with self.subTest(value=value):
                self.manifest["datasets"][0]["matches_upstream_git_blob"] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "provenance"):
                    p.validate_manifest(self.data)

    def test_duplicate_or_escaping_graph_paths_refused(self):
        graphs = self.manifest["datasets"][0]["graphs"]
        graphs.append(dict(graphs[0]))
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Duplicate or escaping"):
            p.validate_manifest(self.data)
        graphs.pop()
        graphs[0]["npz"] = "../outside.npz"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Duplicate or escaping"):
            p.validate_manifest(self.data)

    def test_empty_graph_inventory_refused(self):
        self.manifest["datasets"] = []
        self.save_manifest()
        with self.assertRaises(ValueError):
            p.validate_manifest(self.data)

    def test_remote_bundle_marker_required(self):
        with patch.dict("os.environ", {"APT_FROZEN_BUNDLE_SHA256": ""}):
            with self.assertRaisesRegex(ValueError, "bundle marker"):
                self.verify()

    def test_recorded_git_blob_mismatch_refused(self):
        # No test creates a commit or modifies the user's Git state.
        (self.repo / ".git").mkdir()
        with patch.object(p.subprocess, "check_output", return_value=b"wrong committed bytes"):
            with self.assertRaisesRegex(ValueError, "recorded commit"):
                self.verify()


if __name__ == "__main__":
    unittest.main()
