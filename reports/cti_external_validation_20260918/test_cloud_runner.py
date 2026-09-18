"""Pure filesystem/mocked checks: no AWS requests, inference or credential reads."""
from __future__ import annotations

import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cloud_runner as run


class LauncherTests(unittest.TestCase):
    def test_copied_controller_bytes(self):
        self.assertEqual(run.cloud.digest(run.cloud.__file__), run.CONTROLLER_SHA256)
        self.assertEqual(run.cloud.digest(Path(run.__file__).with_name('trusted_cloud_controller.py')),
                         run.PROVENANCE_CONTROLLER_SHA256)
        self.assertEqual((run.cloud.TOTAL_SECONDS, run.cloud.WATCHDOG_SECONDS,
                          run.cloud.WORKER_DEADLINE_SECONDS, run.cloud.MAX_COMMAND_SECONDS),
                         (3600, 3360, 3120, 3000))

    def test_adaptation_changes_only_reviewed_constants_and_labels(self):
        source=Path(run.__file__).with_name('trusted_cloud_controller.py').read_text()
        changes={
            'One-attempt D0 cloud control;':'One-attempt CTI cloud control;',
            'TOTAL_SECONDS = 1800':'TOTAL_SECONDS = 3600',
            'WATCHDOG_SECONDS = 1560':'WATCHDOG_SECONDS = 3360',
            'WORKER_DEADLINE_SECONDS = 1320':'WORKER_DEADLINE_SECONDS = 3120',
            'MAX_COMMAND_SECONDS = 1200':'MAX_COMMAND_SECONDS = 3000',
            '"praxis-d0-"':'"praxis-cti-"',
            'Single D0 qualification host stop; 30-minute total cap with stop margin':
                'Single CTI validation host stop; 60-minute total cap with stop margin',
            'Command timeout must be between 30 and 1200 seconds':
                'Command timeout must be between 30 and 3000 seconds',
            'all must end by minute 22.':'all must end by minute 52.',
            'absolute minute-22 deadline':'absolute minute-52 deadline',
            'Authorized D0 bounded worker: ':'Authorized CTI bounded worker: ',
        }
        for old,new in changes.items():
            self.assertEqual(source.count(old),1)
            source=source.replace(old,new)
        self.assertEqual(source,Path(run.cloud.__file__).read_text())

    def test_timeout_plan_counts_boot_and_delivery(self):
        start = dt.datetime(2026, 9, 18, tzinfo=dt.timezone.utc)
        active = {"worker_deadline_utc": run.cloud.stamp(start + dt.timedelta(seconds=3120))}
        now = start + dt.timedelta(seconds=110)
        plan = run.timeout_plan(active, now)
        self.assertLess(plan["send_seconds"] + 130, 3010)
        self.assertLessEqual(plan["outer_seconds"], plan["send_seconds"] - 30)
        self.assertEqual(plan["deadline_epoch"], plan["outer_stop_epoch"])
        self.assertLessEqual(plan["outer_stop_epoch"] + 160, start.timestamp() + 3120)
        self.assertEqual(plan['outer_stop_epoch']-160, start.timestamp()+2780)
        with self.assertRaises(ValueError):
            run.timeout_plan(active, start + dt.timedelta(seconds=2800))

    def test_archive_rejects_escape_links_and_duplicate_files(self):
        for names, link in [(["reports/../../escaped"], False), (["reports/a"], True),
                            (["reports/a", "reports/a"], False), (["assets/a"], False)]:
            with self.subTest(names=names, link=link), tempfile.TemporaryDirectory() as tmp:
                arc = Path(tmp) / "bad.tar.gz"
                with tarfile.open(arc, "w:gz") as tar:
                    for name in names:
                        member = tarfile.TarInfo(name)
                        if link:
                            member.type = tarfile.SYMTYPE
                            member.linkname = "/etc/passwd"
                            tar.addfile(member)
                        else:
                            member.size = 1
                            tar.addfile(member, io.BytesIO(b"x"))
                with self.assertRaises(ValueError):
                    run.safe_extract(arc, Path(tmp) / "out", allowed_roots=("reports",))

    def test_bootstrap_contains_bound_and_only_secret_name(self):
        settings = {"bucket": "example-bucket", "prefix": "final-praxis/cti-external-20260918/test/",
                    "region": "us-east-1", "hf_secret_id": "praxis/huggingface/token"}
        active = {"run_id": "a" * 32}
        timing = {"deadline_epoch": 1234567890, "outer_stop_epoch": 1234567890}
        script = run.build_bootstrap(settings, active, timing, "b" * 64,
                                     {"freeze_path": run.RUNTIME_ROOT + "/FREEZE.json", "required_files": {}})
        self.assertLess(len(script.encode()), 23000)
        self.assertIn("mountpoint -q /opt/dlami/nvme", script)
        self.assertIn("68719476736", script)
        self.assertIn("CTI_HF_SECRET_ID=praxis/huggingface/token", script)
        self.assertIn("allowed_roots=('reports',)", script)
        self.assertNotIn("HF_TOKEN=", script)
        self.assertNotIn("final_praxis/010", script)

    def test_closeout_never_calls_success_until_observed_stopped(self):
        start = dt.datetime(2026, 9, 18, tzinfo=dt.timezone.utc)
        elapsed = [0]
        class Fake:
            count = 0
            stops = 0
            def active(self): return {"total_deadline_utc": run.cloud.stamp(start + dt.timedelta(seconds=3600))}
            def stop(self): self.stops += 1; return {"status": "STOP_REQUESTED_WATCHDOG_RETAINED"}
            def finalize(self):
                self.count += 1
                return {"status": "CLOSED_VERIFIED_STOPPED" if self.count == 3 else "PENDING_HOST_NOT_STOPPED_WATCHDOG_RETAINED"}
        fake = Fake()
        result = run.close_host(fake, lambda: start + dt.timedelta(seconds=elapsed[0]),
                               lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds))
        self.assertEqual(result["status"], "CLOSED_VERIFIED_STOPPED")
        self.assertEqual(fake.count, 3)

    def test_missing_final_marker_routes_to_partial_collection(self):
        class Fake:
            settings = {"prefix": "run/"}
        with patch.object(run, "object_exists", return_value=False), \
             patch.object(run, "collect_partial_results", return_value={"status": "PARTIAL"}) as collect:
            self.assertEqual(run.collect_results(Fake())["status"], "PARTIAL")
            collect.assert_called_once()

    def test_ambiguous_start_enters_stop_finally_and_collects_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            class Fake:
                active_path = private / "ACTIVE_RUN.json"
                settings = {"prefix": "run/"}
                def verify_account(self): pass
                def instance(self): return {"State": {"Name": "stopped"}}
                def transfer(self, *args): return {"status": "COMPLETE"}
                def start(self, *args):
                    self.active_path.write_text('{}')
                    raise OSError("Ambiguous start response")
            fake = Fake()
            fake.private = private
            args = SimpleNamespace(settings=private/'settings.json', bundle=private/'bundle.tar.gz',
                bundle_sha256='a'*64, protocol=private/'PROTOCOL.md', freeze=private/'FREEZE.json',
                verify_stop_role=True)
            with patch.object(run.cloud, 'Controller', return_value=fake), \
                 patch.object(run, 'verify_stop_role', return_value={"status":"PASSED"}), \
                 patch.object(run, 'validate_bundle', return_value={"bundle_sha256":"a"*64}), \
                 patch.object(run, 'object_exists', return_value=False), \
                 patch.object(run, 'close_host', return_value={"status":"CLOSED_VERIFIED_STOPPED"}) as close, \
                 patch.object(run, 'collect_results', return_value={"status":"PARTIAL"}) as collect:
                self.assertEqual(run.launch(args), 1)
                close.assert_called_once_with(fake)
                collect.assert_called_once_with(fake)
            attempt = json.loads((private/'LAUNCH_ATTEMPT.json').read_text())
            self.assertFalse(attempt['overall_operational_pass'])
            self.assertEqual(attempt['failure_type'], 'OSError')

    def test_manifest_rejects_unfrozen_bundle_files_and_changed_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)/'repo'
            private = Path(tmp)/'private'
            private.mkdir()
            directory = repo/run.RUNTIME_ROOT
            directory.mkdir(parents=True)
            inputs = run.RUNTIME_ROOT+'/generator_inputs.jsonl'
            qualification = run.RUNTIME_ROOT+'/qualification_inputs.jsonl'
            contents = {
                run.RUNNER: b'#!/bin/bash\n', run.WORKER: b'# mock worker\n',
                run.RUNTIME_ROOT+'/cloud_runner.py': Path(run.__file__).read_bytes(),
                run.RUNTIME_ROOT+'/cti_cloud_controller.py': Path(run.cloud.__file__).read_bytes(),
                run.RUNTIME_ROOT+'/trusted_cloud_controller.py':
                    Path(run.__file__).with_name('trusted_cloud_controller.py').read_bytes(),
                inputs: b'{}\n', qualification: b'{}\n',
            }
            for name, data in contents.items(): (repo/name).write_bytes(data)
            protocol = directory/'PROTOCOL.md'
            protocol.write_text('Frozen protocol\n')
            freeze = directory/'FREEZE.json'
            hashes = {name:run.cloud.digest(repo/name) for name in contents}
            freeze.write_text(json.dumps({'files':hashes,
                'worker_args':['--inputs',inputs,'--qualification',qualification]}))
            archive = private/'runtime.tar.gz'
            def identity(path):
                return {'commit':'f'*40, 'path':Path(path).relative_to(repo).as_posix(),
                        'sha256':run.cloud.digest(path)}
            def bundle(extra=False):
                with tarfile.open(archive, 'w:gz') as tar:
                    for path in [*(repo/name for name in contents), protocol, freeze]:
                        tar.add(path, arcname=path.relative_to(repo).as_posix())
                    if extra:
                        item=tarfile.TarInfo('reports/unfrozen_settings.json')
                        item.size=2
                        tar.addfile(item,io.BytesIO(b'{}'))
            with patch.object(run.cloud, 'committed_identity', side_effect=identity):
                bundle()
                run.validate_bundle(archive,run.cloud.digest(archive),protocol,freeze,private)
                bundle(extra=True)
                with self.assertRaisesRegex(ValueError,'exactly equal'):
                    run.validate_bundle(archive,run.cloud.digest(archive),protocol,freeze,private)
                (repo/run.WORKER).write_bytes(b'# changed after freeze\n')
                with self.assertRaisesRegex(ValueError,'differs from committed freeze'):
                    run.validate_bundle(archive,run.cloud.digest(archive),protocol,freeze,private)


if __name__ == "__main__":
    unittest.main()
