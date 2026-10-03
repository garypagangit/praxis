"""Build a local pilot form or score genuine exported responses. No simulated people."""
import json,sys,csv,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
if sys.argv[1]=='build':
    cases=(HERE/'PX102_CASES.json').read_text()
    html='''<!doctype html><meta charset="utf-8"><title>Warning review pilot</title>
<style>body{font:18px system-ui;max-width:950px;margin:40px auto}pre{font-size:14px;background:#eee;padding:16px;white-space:pre-wrap}button,input,select{font:inherit;margin:10px}#explanation{background:#e5f2ff;padding:16px}</style>
<h1>Warning review pilot</h1><p>Research materials only. Begin enrollment only after consent and applicable university review. Use an anonymous numeric participant ID.</p>
<div id="start"><input id="pid" type="number" min="1" placeholder="Participant number"><button onclick="begin()">Start</button></div>
<div id="task" hidden><h2 id="heading"></h2><p>Each member chooses its largest score; a non-benign choice is a warning. Mean averages each class score, then chooses the largest. OR warns if any member warns.</p><pre id="scores"></pre><p id="explanation"></p><p id="question"></p>
<select id="answer"><option value="">Choose answer</option><option value="true">Yes</option><option value="false">No</option></select><label>Confidence <select id="confidence"><option value="">Choose</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label><button onclick="next()">Save and next</button></div><div id="finish"></div>
<script>const cases=CASES;let order=[],rows=[],at=0,p=0,t=0;
function begin(){p=Number(document.getElementById('pid').value);if(!Number.isInteger(p)||p<1)return;order=[...cases];let seed=p>>>0;function rand(){seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296;}for(let j=order.length-1;j>0;j--){let k=Math.floor(rand()*(j+1));[order[j],order[k]]=[order[k],order[j]];}document.getElementById('start').hidden=true;document.getElementById('task').hidden=false;show();}
function show(){const c=order[at],arm=(p+c.case_id)%2===0;document.getElementById('heading').textContent=`Case ${at+1} of ${order.length}`;document.getElementById('scores').textContent=JSON.stringify({class_order:c.class_order,member_scores:c.member_probabilities},null,2);document.getElementById('explanation').textContent=arm?c.explanation:'';document.getElementById('explanation').hidden=!arm;document.getElementById('question').textContent=c.question;document.getElementById('answer').value='';document.getElementById('confidence').value='';t=performance.now();}
function next(){let a=document.getElementById('answer').value,q=document.getElementById('confidence').value;if(!a||!q)return;const c=order[at];rows.push({anonymous_participant_id:p,case_id:c.case_id,arm:(p+c.case_id)%2===0?'explanation':'scores',answer:a==='true',elapsed_seconds:(performance.now()-t)/1000,confidence_1_to_5:Number(q)});at++;if(at<order.length){show();return;}document.getElementById('task').hidden=true;let link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:'application/json'}));link.download=`review_${p}.json`;link.textContent='Download responses';document.getElementById('finish').append(link);}
</script>'''.replace('CASES',cases)
    (HERE/'PX102_REVIEW.html').write_text(html,encoding='utf-8')
elif sys.argv[1]=='score':
    key={r['case_id']:r['answer'] for r in json.loads(Path('C:/w/explanation_trials_20261003/PX102_ANSWER_KEY.json').read_text())}
    rows=[];seen=set()
    for f in sys.argv[2:]:
        for r in json.loads(Path(f).read_text()):
            pair=(r['anonymous_participant_id'],r['case_id']);assert pair not in seen;seen.add(pair)
            assert type(r['answer']) is bool and r['case_id'] in key
            assert r['arm']==('explanation' if sum(pair)%2==0 else 'scores')
            assert r['elapsed_seconds']>=0 and 1<=r['confidence_1_to_5']<=5
            rows.append({**r,'correct':r['answer']==key[r['case_id']]})
    assert rows,'Supply real participant response files'
    result={}
    for arm in ['scores','explanation']:
        a=[r for r in rows if r['arm']==arm]
        result[arm]={'responses':len(a),'accuracy':statistics.mean(r['correct'] for r in a) if a else None,'median_seconds':statistics.median(r['elapsed_seconds'] for r in a) if a else None}
    print(json.dumps({'descriptive_only':True,'participants':len(set(r['anonymous_participant_id'] for r in rows)),'arms':result},indent=2))
