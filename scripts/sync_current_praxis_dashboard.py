"""Publish current evidence/status without replacing the historical portfolio."""
import argparse
import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_COMMIT = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
BASE = 'https://github.com/garypagangit/praxis/blob/'+EVIDENCE_COMMIT+'/experiments/praxis_next/'
PAPERS = {
    'pack': ('PackMonitor: Enabling Zero Package Hallucinations Through Decoding-Time Monitoring', 'https://arxiv.org/abs/2602.20717'),
    'agent': ('AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents', 'https://arxiv.org/abs/2503.18666'),
    'defense': ('Evaluating Inference-Time Defenses Against Package Hallucination in LLM-Generated Code', 'https://arxiv.org/abs/2608.22652'),
    'receipt': ('Tool Receipts, Not Zero-Knowledge Proofs: Practical Hallucination Detection for AI Agents', 'https://arxiv.org/abs/2603.10060'),
    'narrative': ('Reasoning Externalization for Faithful Large Language Model Narratives of Stock Return Predictions', 'https://arxiv.org/abs/2609.38869'),
    'fax': ('Towards Faithful Agentic XAI: A Verification Method and an Open-World Benchmark for Better Model Faithfulness', 'https://arxiv.org/abs/2605.27879'),
    'story': ('How good is my story? Towards quantitative metrics for evaluating LLM-generated XAI narratives', 'https://arxiv.org/abs/2412.10220'),
    'retrain': ('On Minimizing the Impact of Dataset Shifts on Actionable Explanations', 'https://proceedings.mlr.press/v216/meyer23a.html'),
}

def cited(reason, keys):
    refs = [{'title':PAPERS[k][0], 'url':PAPERS[k][1]} for k in keys]
    return {'reason':reason + ((' Prior work: ' + '; '.join(p['title']+' — '+p['url'] for p in refs)) if refs else ''),
            'reason_summary':reason, 'papers':refs}

def plain(value):
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish-root', type=Path, required=True)
    args = parser.parse_args()
    registry_path = ROOT/'experiments/praxis_next/REGISTRY.json'
    registry = json.loads(registry_path.read_text())
    updates = {
        'PX-114':dict(status='COMPLETE_GENERIC_NOVELTY_CLAIM_SUPERSEDED',
            dashboard_status='Closed as standalone idea — generic novelty claim superseded',
            **cited('Receipt-based verification already exists. The completed comparison tied the same-model judge at 49 accepted / zero unsupported claims. A distinct empirical extension remains unproven; this is not a novel generic gate.', ['receipt'])),
        'PX-115':dict(status='COMPLETE_GENERIC_NOVELTY_CLAIM_SUPERSEDED',
            dashboard_status='Closed as standalone idea — generic novelty claim superseded',
            **cited('The September 30, 2026 preprint overlaps deterministic evidence checking; earlier work already evaluates SHAP narrative errors and verification. Our structured checker accepted all 32 contradictory-prose fixtures when the sidecar was correct. A narrower new comparison remains unproven.', ['narrative','fax','story'])),
        'PX-113':dict(dashboard_status='Complete — no release benefit; prior-art overlap',
            **cited('Explanation stability under retraining is established. Our gate rejected both beneficial updates; no evaluated release crossed the frozen harm threshold. No evidence of better release decisions.', ['retrain'])),
        'PX-116':dict(dashboard_status='Hold — qualification complete; candidate not ready',
            **cited('Current gates preserve only 30/40 qualified task-form completions (75%); PX-067 admits an unresolvable-version control. Full PackMonitor/AgentSpec efficacy comparison is unrun. Prior work removes the broad gate/first-utility claims, but does not establish that the narrower equal-protection completion comparison is non-novel. That novelty remains unestablished.', ['pack','agent','defense'])),
    }
    for row in registry['experiments']:
        if row['id'] in updates:
            row.update(updates[row['id']])
    registry_path.write_text(json.dumps(registry,indent=2)+'\n')
    rows = []
    for row in registry['experiments']:
        rows.append({**row, 'dashboard_status':row.get('dashboard_status',row['status'].replace('_',' ').capitalize()),
            'reason':row.get('reason',row.get('finding','See the frozen protocol and evidence.')),
            'evidence_url':BASE+row.get('results',row.get('protocol',row['directory']))})
    for id_, title, status, finding, reason, keys in [
        ('PX-050','Deterministic package-install gate','Broad novelty claim superseded — historical pilot only',
         'Historical PX-050Y failed its composite gate: review 6.82% exceeded 5%. Later PX-069 label qualification failed. Earlier positive runs remain historical evidence.',
         'PackMonitor constrains package names and AgentSpec enforces runtime rules. A generic deterministic package gate is not a defensible first-use claim. The August study also evaluates defenses and utility. The revised completion question is tracked separately in PX-116.', ['pack','agent','defense']),
        ('PX-067','Empty-install-command repair','Historical repair — independent efficacy unqualified',
         'Blocks the 142 extracted empty-install forms. In PX-116 it completes 30/40 qualified task-form cases and admits the impossible-version control.',
         'Review-to-block repair does not demonstrate task completion. Name verification alone does not validate versions or requirement files. The broader gate mechanism already has precedents.', ['pack','agent']),
        ('PX-069','Gate-blind command audit','Original qualification failed — development parser repair only',
         'Original 147/4500 responses affected (3.27%); PX-116 comment-only repair reduces this to 16/4500 (0.36%) with all 3086 extracted candidates unchanged.',
         'Parser coverage is improved, but independent validity labels and remaining disagreements are not resolved. Preserve the original failure; no novelty-based closure is asserted.', []),
    ]:
        rows.append(dict(id=id_,title=title,status=status,dashboard_status=status,finding=finding,
                         evidence_url=BASE+'package_completion_20261005/FINDINGS.txt',**cited(reason,keys)))
    rows.sort(key=lambda r:int(r['id'].split('-')[1]),reverse=True)
    data = dict(updated_utc='2026-10-05', evidence_commit=EVIDENCE_COMMIT,
                scope=f"{len(registry['experiments'])} current experiment records plus three historical corrections; not a new literature sweep of the entire archived portfolio.",
                claim_rule='A completed run is not proof of novelty. Superseded status applies to the stated generic claim; untested narrower extensions remain unproven.',
                experiments=rows)
    encoded = json.dumps(data,indent=2)+'\n'
    (ROOT/'reports/PRAXIS_CURRENT_STATUS.json').write_text(encoded,encoding='utf-8')
    target = args.publish_root
    (target/'reports/PRAXIS_CURRENT_STATUS.json').write_text(encoded,encoding='utf-8')
    cells=[]
    for r in rows:
        refs=''.join('<li><a href="'+html.escape(p['url'],quote=True)+'">'+html.escape(p['title'])+'</a></li>' for p in r.get('papers',[]))
        reason=html.escape(plain(r.get('reason_summary',r['reason'])))+(('<ul>'+refs+'</ul>') if refs else '')
        cells.append('<tr id="current-'+r['id']+'"><td>'+html.escape(r['id'])+'</td><td>'+html.escape(r['title'])+'</td><td><strong>'+html.escape(r['dashboard_status'])+'</strong></td><td>'+html.escape(plain(r.get('finding','')))+'</td><td>'+reason+'</td><td><a href="'+html.escape(r['evidence_url'],quote=True)+'">Evidence</a></td></tr>')
    section='''<!-- CURRENT_STATUS_START -->
<section id="current-status"><h2>Current experiment status — 5 October 2026 UTC</h2>
<p>This section supersedes conflicting status claims in the archived dashboard below. Completed experiments, research novelty and defense readiness are separate judgments.</p>
<p><strong>Latest decisions:</strong> PX-117 has a working prototype; its false-alert target was missed and matched confirmation remains open. PX-116 is not ready for confirmation. PX-050, PX-114 and PX-115 cannot advance on their generic gate novelty claims. Paper titles and links appear in the Reason column.</p>
<p>Current experiment records and three historical corrections. Other legacy ideas have not received a fresh literature review in this update. <a href="PRAXIS_CURRENT_STATUS.json">Download status data</a>.</p>
<label for="current-filter">Find an experiment, status or paper</label>
<input id="current-filter" type="search" style="width:100%;padding:12px;margin:10px 0" placeholder="For example: PX-116, superseded, PackMonitor">
<div class="table-wrap"><table id="current-table"><thead><tr><th>Experiment</th><th>Title</th><th>Status</th><th>Results</th><th>Reason / prior paper</th><th>Evidence</th></tr></thead><tbody>'''+''.join(cells)+'''</tbody></table></div>
<script>document.getElementById('current-filter').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('#current-table tbody tr').forEach(r=>{r.hidden=!r.textContent.toLowerCase().includes(q);});});</script>
</section><!-- CURRENT_STATUS_END -->
'''
    path=target/'reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html'
    page=path.read_text(encoding='utf-8')
    page=re.sub(r'<p class="meta">Updated .*?</p>', '<p class="meta">Current status updated 5 October 2026 UTC. See the current table for results, status reasons and linked prior work. The older portfolio below is retained as an archive.</p>',page,count=1,flags=re.S)
    # Preserve the old portfolio while removing a contradicted lead recommendation.
    page=re.sub(r'<p class="small">This is the newly integrated candidate branch.*?</p>', '<p class="small">Historical agent-defense results. PX-050 is no longer classified as defense-ready: its broad novelty claim overlaps prior work, and later qualification failed. See <a href="#current-PX-050">the current PX-050 decision</a> and <a href="#current-PX-116">PX-116 follow-up</a>. Other dated results below are retained as historical records.</p>',page,flags=re.S)
    def correct_row(match):
        row=match[0]
        if re.search(r'<td class="num">PX-050</td>',row):
            row=re.sub(r'<span class="badge [^"]+">.*?</span>','<span class="badge negative">Broad novelty superseded; pilot only</span>',row,count=1,flags=re.S)
        return row
    page=re.sub(r'<tr>.*?</tr>',correct_row,page,flags=re.S)
    if '<!-- CURRENT_STATUS_START -->' in page:
        page=re.sub(r'<!-- CURRENT_STATUS_START -->.*?<!-- CURRENT_STATUS_END -->\s*',lambda _:section,page,flags=re.S)
    else:
        page=page.replace('</header>','</header>\n'+section+'<details><summary style="padding:24px;font-weight:bold">Archived portfolio — dated historical statuses</summary>',1)
        page=page.replace('</main>','</details>\n</main>',1)
    path.write_text(page,encoding='utf-8')
    if target.resolve()!=ROOT.resolve():
        (ROOT/'reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html').write_text(page,encoding='utf-8')
    print(json.dumps({'rows':len(rows),'updated':['PX-050','PX-067','PX-069','PX-113','PX-114','PX-115','PX-116'],'target':str(target)}))

if __name__=='__main__':
    main()
