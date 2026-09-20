"""Security, index preservation, and label provenance checks for native graphs."""
import hashlib
import io
from pathlib import Path
import pickle
import struct
import tempfile
import unittest

import numpy as np

from experiments.apt_final.native_graph.data import (
    DataError, Symbol, assert_one_hot, binary_labels, checked_bytes,
    legacy_storage, passive_pickle, source_split_manifest, tensor_array,
    validate_graph_arrays,
)


def storage_blob(values, dtype="LongStorage"):
    arr = np.asarray(values, dtype="<i8" if dtype == "LongStorage" else "<f4")
    # Build legacy storage pickle records without invoking Torch or DGL.
    prefix = b"".join(pickle.dumps(x, protocol=2) for x in (
        119547037146038801333356, 1001,
        {"protocol_version": 1001, "little_endian": True},
    ))
    descriptor = (b"\x80\x02(X\x07\x00\x00\x00storagectorch\n" + dtype.encode() + b"\n"
                  b"X\x03\x00\x00\x00keyX\x03\x00\x00\x00cpuJ" + struct.pack("<i", arr.size) + b"NtQ.")
    return prefix + descriptor + pickle.dumps(["key"], protocol=2) + struct.pack("<Q", arr.size) + arr.tobytes()


def symbol_call(name, args):
    return Symbol("reduce", Symbol("global", name), args)


class NativeDataTests(unittest.TestCase):
    def test_primitive_only_roundtrip(self):
        obj = {"rows": [0, 2, -4, (True, None, "node")], "bytes": b"abc"}
        # Protocol 2 encodes bytes through codecs reducers; that is intentionally
        # outside the primitive subset, while protocol 4 has native BINBYTES.
        self.assertEqual(passive_pickle(pickle.dumps(obj, protocol=4)), obj)

    def test_arbitrary_global_and_reduce_refused(self):
        payload = b"cos\nsystem\n(S'echo should never execute'\ntR."
        for symbolic in (False, True):
            with self.subTest(symbolic=symbolic), self.assertRaises(DataError):
                passive_pickle(payload, symbolic=symbolic)

    def test_known_constructor_is_passive_not_called(self):
        payload = b"\x80\x04cbuiltins\nbytearray\nC\x03abc\x85R."
        with self.assertRaises(DataError):
            passive_pickle(payload)
        result = passive_pickle(payload, symbolic=True)
        self.assertIsInstance(result, Symbol)
        self.assertEqual(result.args, (b"abc",))
        self.assertEqual(result.target.target, "builtins.bytearray")

    def test_persistent_reference_not_primitive(self):
        with self.assertRaises(DataError):
            passive_pickle(b"\x80\x02NQ.")

    def test_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.bin"
            path.write_bytes(b"original")
            digest = hashlib.sha256(b"original").hexdigest()
            self.assertEqual(checked_bytes(path, digest), b"original")
            path.write_bytes(b"changed")
            with self.assertRaises(DataError):
                checked_bytes(path, digest)

    def test_bad_indices_or_duplicates_refused(self):
        for indices in ([-1], [3], [1, 1], [True], [1.0]):
            with self.subTest(indices=indices), self.assertRaises(DataError):
                binary_labels(3, indices)

    def test_labels_preserve_original_row_indices(self):
        np.testing.assert_array_equal(binary_labels(5, [4, 1]), [0, 1, 0, 0, 1])

    def test_training_zeros_require_explicit_assumption(self):
        with self.assertRaises(DataError):
            binary_labels(3, [], training=True)
        with self.assertRaises(DataError):
            binary_labels(3, [1], training=True, accept_upstream_benign_assumption=True)
        np.testing.assert_array_equal(binary_labels(3, [], training=True,
            accept_upstream_benign_assumption=True), np.zeros(3, dtype=np.int8))

    def test_edge_bounds_and_integer_types(self):
        types = np.array([1, 0, 1], dtype=np.int64)
        src, dst, relation = np.array([2, 0]), np.array([0, 1]), np.array([0, 1])
        validate_graph_arrays(types, src, dst, relation, 2, 2)
        np.testing.assert_array_equal(src, [2, 0])
        with self.assertRaises(DataError):
            validate_graph_arrays(types, np.array([3, 0]), dst, relation, 2, 2)
        with self.assertRaises(DataError):
            validate_graph_arrays(types, src.astype(float), dst, relation, 2, 2)

    def test_one_hot_must_match_type(self):
        types = np.array([0, 1])
        assert_one_hot(types, np.array([[1., 0.], [0., 1.]]), 2)
        with self.assertRaises(DataError):
            assert_one_hot(types, np.array([[0., 1.], [1., 0.]]), 2)
        with self.assertRaises(DataError):
            assert_one_hot(types, np.array([[1., 1.], [0., 1.]]), 2)

    def test_legacy_storage_decodes_without_torch(self):
        blob = storage_blob([3, 0, 11])
        np.testing.assert_array_equal(legacy_storage(blob), [3, 0, 11])
        with self.assertRaises(DataError):
            legacy_storage(blob[:-1])

    def test_tensor_noncontiguous_or_wrong_shape_refused(self):
        storage = symbol_call("torch.storage._load_from_bytes", (storage_blob([3, 0, 11]),))
        hooks = symbol_call("collections.OrderedDict", ())
        tensor = symbol_call("torch._utils._rebuild_tensor_v2", (storage, 0, (3,), (1,), False, hooks))
        np.testing.assert_array_equal(tensor_array(tensor), [3, 0, 11])
        for shape, stride in (((4,), (1,)), ((3,), (2,))):
            tensor.args = (storage, 0, shape, stride, False, hooks)
            with self.assertRaises(DataError):
                tensor_array(tensor)

    def test_split_manifest_ast_does_not_execute_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "parser.py"
            path.write_text("raise RuntimeError('must not execute')\nmetadata = {'cadets': {'train': ['a'], 'test': ['b']}}\n", encoding="utf-8")
            self.assertEqual(source_split_manifest(path)["cadets"]["test"], ["b"])


if __name__ == "__main__":
    unittest.main()
