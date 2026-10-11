"""Portable contract tests and byte manifest; raw audit must be run separately."""
import hashlib, io, json, pathlib, unittest
import test_boundary

root=pathlib.Path(__file__).resolve().parent
suite=unittest.defaultTestLoader.loadTestsFromModule(test_boundary)
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
if not result.wasSuccessful():
    print(stream.getvalue());raise SystemExit(1)
for file in root.rglob('*.json'):
    json.loads(file.read_text(encoding='utf-8'))
audit=json.loads((root/'results/READINESS.json').read_text())
demo=json.loads((root/'results/BOUNDARY_DEMO.json').read_text())
assert audit['archive_count']==93 and not audit['integrity_errors']
assert audit['forbidden_collector_shortcut']['correct']==308
assert audit['forbidden_collector_shortcut']['total']==309
assert audit['matched_by_minimum_submissions']['3']['human']==25
assert audit['matched_by_minimum_submissions']['3']['ai']==42
assert not audit['four_arm_confirmation_gate']['engineering_ready']
assert not demo['fixture_training_gate']['engineering_ready']
assert demo['future_output_hidden'] and demo['identical_observation_hashes']
receipt={'date':'2026-10-11','tests_run':result.testsRun,'failures':len(result.failures),
 'errors':len(result.errors),'all_json_parsed':True,'expected_readiness_denominators_checked':True,
 'raw_hashes_freshly_reverified_by_this_script':False,
 'raw_audit_command':'python audit_readiness.py (executed separately; see READINESS.json)',
 'scope':'Software invariants and artifact consistency; not detector performance, field validity or novelty.'}
(root/'results/VALIDATION.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
files=[]
for path in sorted(root.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or 'private_collection' in path.parts or path.name=='PACKAGE_MANIFEST.json':continue
    data=path.read_bytes();files.append({'path':path.relative_to(root).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(root/'PACKAGE_MANIFEST.json').write_text(json.dumps({'date':'2026-10-11','files':files},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'tests':receipt,'manifest_files':len(files)},indent=2))
