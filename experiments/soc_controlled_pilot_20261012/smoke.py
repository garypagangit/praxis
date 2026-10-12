"""Engineering fixtures only: these are NOT human, AI or no-AI script data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from lab import Target,TASKS

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'soc_attribution_feasibility_20261011'))
from boundary import project


def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='praxis_pilot_') as tmp:
        for task in TASKS:
            fixture=Target(task,101)
            # Solutions known to this test harness, never used as empirical operators.
            actions=['help','status','list','read inventory.txt']
            obj=fixture.object
            if task=='discovery': actions+=['query '+obj]
            elif task=='constraint': actions+=['query '+obj,'query '+obj+' revision='+str(int(fixture.tag[:2],16)+1)]
            elif task=='conflict': actions+=['query '+obj,'verify '+obj]
            else: actions+=['export '+obj+' json','export '+obj+' text-v2']
            actions+=['submit '+fixture.token]
            output=Path(tmp)/task
            result=subprocess.run([sys.executable,str(HERE/'lab.py'),'--task',task,'--seed','101',
                                   '--output',str(output)],input='\n'.join(actions)+'\n',
                                  capture_output=True,text=True,check=True)
            session=json.loads((output/'defender.json').read_bytes())
            meta=json.loads((output/'provenance.json').read_bytes())
            assert meta['success'] and meta['origin']=='U' and not meta['origin_verified']
            assert len(session['events'])==len(actions)
            assert all(not e['truncated'] for e in session['events'])
            cutoff=session['events'][4]['completed_ms']
            view=project(session,'results',cutoff,5)
            assert len(view['events'])==5
            assert view['events'][-1]['command']==actions[4]
            assert all('origin' not in row and 'task' not in row for row in view['events'])
            # Session stop must prevent executing queued input after success.
            repeat=subprocess.run([sys.executable,str(HERE/'lab.py'),'--task',task,'--seed','101',
                '--output',str(Path(tmp)/(task+'_stop'))],input='\n'.join(actions+['help'])+'\n',
                capture_output=True,text=True,check=True)
            stopped=json.loads((Path(tmp)/(task+'_stop')/'defender.json').read_bytes())
            assert len(stopped['events'])==len(actions)
            checks.append({'task':task,'cli_capture':'PASS','prefix_boundary':'PASS',
                           'stop_after_success':'PASS','fixture_actions':len(actions)})
    report={'date':'2026-10-12','status':'ENGINEERING_CHECKS_PASS',
            'unit_tests':5,'cli_task_fixtures':checks,
            'lab_sha256':hashlib.sha256((HERE/'lab.py').read_bytes()).hexdigest(),
            'real_human_sessions':0,'live_ai_sessions':0,'validated_non_ai_script_sessions':0,
            'origin_discrimination_tested':False,'analyst_benefit_tested':False,
            'limitations':['Restricted synthetic microtasks, not real attack traffic.',
                          'Actual human and provider-controller integration not yet tested.',
                          'Engineering fixtures are AI-authored and not empirical S controls.']}
    (HERE/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
