"""Synthetic bundle/extraction qualification; never contacts AWS or loads models."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from experiments.cert_gate.auto_review import prepare
from experiments.cert_gate import auto_review_cloud as cloud


def tar_fixture(path, members):
    with tarfile.open(path, 'w:gz') as archive:
        for name, content, kind in members:
            member = tarfile.TarInfo(name)
            member.type = kind
            if kind == tarfile.REGTYPE:
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            else:
                member.linkname = '../escape'
                archive.addfile(member)


class CloudReviewTests(unittest.TestCase):
    def test_frozen_model_contract_rejects_unpinned_or_changed_caps(self):
        cloud.validate_model_contract({'automated_review': dict(cloud.MODEL)})
        for key, value in [('revision', 'main'), ('model_id', 'another/model'),
                           ('max_input_tokens', 8192), ('max_new_tokens', 768)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                cloud.validate_model_contract({'automated_review': {**cloud.MODEL, key: value}})

    def test_blinded_bundle_ignores_extra_answer_key(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            cases = root / 'cases.json'
            cases.write_text(json.dumps([{'case_id': f'{i:064x}', 'alert': {'req_body': 'fixture'}}
                                         for i in range(50)]), encoding='utf-8')
            prepared = root / 'prepared'
            prepare(cases, prepared)
            (prepared / 'ANSWER_KEY.json').write_text('DO NOT UPLOAD', encoding='utf-8')
            protocol, freeze = root / 'protocol.json', root / 'freeze.json'
            protocol.write_text('{}'); freeze.write_text('{}')
            destination = root / 'bundle.tar.gz'
            with patch.object(cloud, 'verify_runtime', return_value={'synthetic': True}):
                checksum, record = cloud.build_bundle(prepared, protocol, freeze, destination)
            self.assertEqual(checksum, cloud.digest(destination))
            self.assertFalse(record['answer_key_uploaded'])
            with tarfile.open(destination) as archive:
                self.assertEqual(set(archive.getnames()), cloud.INPUT_NAMES)
                self.assertNotIn('ANSWER_KEY.json', '\n'.join(archive.getnames()))
            metadata = json.loads((prepared / 'PREPARED.json').read_text())
            metadata['code_sha256'] = '0' * 64
            (prepared / 'PREPARED.json').write_text(json.dumps(metadata))
            with patch.object(cloud, 'verify_runtime', return_value={}), self.assertRaises(ValueError):
                cloud.build_bundle(prepared, protocol, freeze, root / 'stale.tar.gz')

    def test_safe_extract_accepts_regular_files_without_overwriting(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); archive = root / 'result.tar.gz'; output = root / 'out'
            tar_fixture(archive, [('outputs/log.txt', b'fixture', tarfile.REGTYPE)])
            cloud.safe_extract(archive, output)
            self.assertEqual((output / 'outputs/log.txt').read_bytes(), b'fixture')
            with self.assertRaises(FileExistsError):
                cloud.safe_extract(archive, output)

    def test_safe_extract_rejects_escape_link_collision_and_oversize(self):
        fixtures = [
            [('../escape.txt', b'bad', tarfile.REGTYPE)],
            [('outputs/link', b'', tarfile.SYMTYPE)],
            [('outputs/a', b'x', tarfile.REGTYPE), ('outputs/A', b'y', tarfile.REGTYPE)],
        ]
        for index, members in enumerate(fixtures):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as name:
                root = Path(name); archive = root / 'bad.tar.gz'
                tar_fixture(archive, members)
                with self.assertRaises(ValueError):
                    cloud.safe_extract(archive, root / 'out')
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); archive = root / 'large.tar.gz'
            tar_fixture(archive, [('outputs/file', b'123', tarfile.REGTYPE)])
            with patch.object(cloud, 'MAX_ARCHIVE_BYTES', 2), self.assertRaises(ValueError):
                cloud.safe_extract(archive, root / 'out')


if __name__ == '__main__':
    unittest.main()
