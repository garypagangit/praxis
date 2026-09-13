"""Offline launch-path regression tests. No AWS, installs, models, or real Git."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile

STUDY=Path(os.environ.get('PRAXIS_STUDY_UNDER_TEST',Path(__file__).resolve().parent)).resolve()


def function_from_source(name, namespace):
    tree=ast.parse((STUDY/'launch.py').read_text(encoding='utf-8'))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
    module=ast.Module(body=[function],type_ignores=[])
    exec(compile(module,'<offline-launch-function>','exec'),namespace)
    return namespace[name]


class LaunchPathTests(unittest.TestCase):
    def test_shell_study_directory_tracks_script_location_after_rename(self):
        bash=shutil.which('bash')
        if not bash and Path('C:/Program Files/Git/bin/bash.exe').exists():
            bash='C:/Program Files/Git/bin/bash.exe'
        for name in ('bootstrap.sh','cloud_entry.sh'):
            text=(STUDY/name).read_text(encoding='utf-8')
            assignments=[line for line in text.splitlines() if line.startswith('study=')]
            self.assertEqual(len(assignments),1)
            self.assertIn('BASH_SOURCE[0]',assignments[0],name+' must derive its own directory')
            self.assertNotIn('$runroot/code/',assignments[0])
            if not bash: continue  # Structural guard still runs; cloud Linux has bash.
            with tempfile.TemporaryDirectory() as directory:
                renamed=Path(directory)/'renamed study with spaces';renamed.mkdir()
                (renamed/'PREREGISTRATION.md').write_text('offline fixture')
                probe=renamed/'path_probe.sh'
                # Execute only the assignment, never the real cloud/bootstrap commands.
                probe.write_text('set -eu\n'+assignments[0]+'\ntest -f "$study/PREREGISTRATION.md"\nprintf "%s\\n" "${study##*/}"\n',encoding='utf-8',newline='\n')
                result=subprocess.run([bash,'--noprofile','--norc',str(probe)],check=True,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.stdout.strip(),renamed.name)

    def test_deploy_and_collector_prefix_match_the_archived_study(self):
        root=STUDY.parents[2]
        namespace={'json':json,'shlex':shlex,'HERE':STUDY,'ROOT':root,
                   'cloud':types.SimpleNamespace(BUCKET='offline-bucket')}
        deploy=function_from_source('deploy_script',namespace)
        plan={'run_id':'fp006-format-1234567890','prereg_sha256':'a'*64,'archive_sha256':'b'*64,'bundle_key':'offline.zip'}
        script=deploy(plan)
        command=shlex.split(next(line for line in script.splitlines() if line.startswith('systemd-run ')))
        entry=command[command.index('/bin/bash')+1]
        runroot='/mnt/praxis-20260912-005/'+plan['run_id']
        expected_prefix='code/'+STUDY.relative_to(root).as_posix()+'/'
        self.assertEqual(entry,runroot+'/'+expected_prefix+'cloud_entry.sh')
        tree=ast.parse((STUDY/'collect.py').read_text(encoding='utf-8'))
        expressions=[node.value for node in ast.walk(tree) if isinstance(node,ast.Assign)
                     and any(isinstance(target,ast.Name) and target.id=='study_prefix' for target in node.targets)]
        self.assertEqual(len(expressions),1)
        actual=eval(compile(ast.Expression(expressions[0]),'<collector-prefix>','eval'),{'HERE':STUDY,'root':root})
        self.assertEqual(actual,expected_prefix)

    def test_archive_manifest_includes_relocated_runtime_and_matches_all_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'repo';here=root/'final_praxis'/'option'/'completion_format_pilot';here.mkdir(parents=True)
            names=['cloud_entry.sh','bootstrap.sh','audit.py','protocol.json','data.json','PREREGISTRATION.md']
            tracked=[]
            for name in names:
                path=here/name;path.write_text('offline fixture '+name,encoding='utf-8');tracked.append(path.relative_to(root).as_posix())
            shared=root/'final_praxis/shared_20260912';shared.mkdir();(shared/'supervisor.py').write_text('offline supervisor')
            artifacts=base/'artifacts'
            for part in ('source','tokenizer'):
                (artifacts/part).mkdir(parents=True);(artifacts/part/'fixture.json').write_text('{}')
            commit='1234567890'+'a'*30
            def check_output(command,**kwargs):
                if command[1:]==['rev-parse','HEAD']: return commit+'\n'
                if command[1]=='status': return ''
                if command[1:]==['ls-files','-z']: return ('\0'.join(tracked)+'\0').encode()
                raise AssertionError('Unexpected mocked subprocess')
            fake_subprocess=types.SimpleNamespace(check_output=check_output,run=lambda *args,**kwargs:None)
            namespace={'HERE':here,'ROOT':root,'SHARED':shared,'sys':sys,'subprocess':fake_subprocess,
                'verify_bundle':lambda *args:None,'zipfile':zipfile,'json':json,
                'sha':lambda path:hashlib.sha256(path.read_bytes()).hexdigest(),
                'cloud':types.SimpleNamespace(PREFIX='offline/',HOSTS={'005':'offline-host'})}
            result=function_from_source('build',namespace)(artifacts,base/'execution')
            with zipfile.ZipFile(result['archive']) as archive:
                manifest=json.loads(archive.read('bundle_manifest.json'))
                self.assertEqual(manifest['commit'],commit)
                self.assertEqual(set(archive.namelist()),set(manifest['files'])|{'bundle_manifest.json'})
                for name,digest in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
                prefix='code/'+here.relative_to(root).as_posix()+'/'
                self.assertTrue({prefix+name for name in names}.issubset(manifest['files']))
                self.assertIn('code/final_praxis/shared_20260912/supervisor.py',manifest['files'])
                self.assertIn('artifacts/source/fixture.json',manifest['files'])
                self.assertIn('artifacts/tokenizer/fixture.json',manifest['files'])


if __name__=='__main__': unittest.main()
