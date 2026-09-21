"""Offline worker packaging checks; no AWS APIs, model fits, or instance starts."""
import contextlib
from datetime import datetime,timedelta,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from experiments.apt_benchmark.tabular_batch.build_cloud_bundle import MODULE,render_bootstrap


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


class CloudOfflineTests(unittest.TestCase):
    def test_bootstrap_reserves_publication_before_tighter_ssm_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';private=base/'private';private.mkdir()
            worker=repo/MODULE/'run_cloud.sh';worker.parent.mkdir(parents=True);worker.write_text('#!/usr/bin/env bash\nexit 0\n')
            bundle=private/'bundle.tar.gz';bundle.write_bytes(b'fixture')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            settings={'account':'000000000000','region':'us-east-1','instance':'fixture','bucket':'offline-fixture','prefix':'test/','stop_role_arn':'fixture'}
            deadline=datetime.now(timezone.utc)+timedelta(minutes=50)
            active={**settings,'stage':'started','gate_failed':False,'worker_deadline_utc':deadline.isoformat(),'run_id':'0123456789abcdef0123456789abcdef'}
            dump(private/'settings.json',settings);dump(private/'ACTIVE_RUN.json',active)
            freeze={'launch_eligible':True,'bundle_sha256':sha(bundle),'runtime_files':{MODULE+'/run_cloud.sh':{'sha256':sha(worker)}}}
            dump(private/'RUNTIME_FREEZE.json',freeze)
            before=int(datetime.now(timezone.utc).timestamp())
            result=render_bootstrap(repo,private)
            plan=json.loads((private/'SEND_PLAN.json').read_text())
            self.assertLess(plan['effective_worker_deadline_epoch'],plan['controller_worker_deadline_epoch'])
            self.assertLessEqual(plan['effective_worker_deadline_epoch'],before+result['timeout_seconds']-18)
            self.assertTrue(result['no_aws_calls_performed'])
            freeze['launch_eligible']=False;dump(private/'RUNTIME_FREEZE.json',freeze)
            with self.assertRaisesRegex(ValueError,'Provisional'):render_bootstrap(repo,private)

    def test_worker_embedded_extractor_rejects_traversal_and_symlinks(self):
        worker=Path(__file__).parents[1]/'tabular_batch'/'run_cloud.sh'
        source=worker.read_text().split("bounded 60 python3 - <<'PY'\n",1)[1].split('\nPY\n',1)[0]
        for name,link in [('../outside',False),('repo/link',True),('/absolute',False)]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                with tarfile.open(root/'bundle.tar.gz','w:gz') as archive:
                    info=tarfile.TarInfo(name)
                    if link:info.type=tarfile.SYMTYPE;info.linkname='/etc/passwd';archive.addfile(info)
                    else:info.size=1;archive.addfile(info,io.BytesIO(b'x'))
                old=Path.cwd()
                try:
                    os.chdir(root)
                    with self.assertRaisesRegex(ValueError,'Invalid runtime bundle'):exec(compile(source,'worker-extractor','exec'),{})
                finally:os.chdir(old)


if __name__=='__main__':unittest.main()
