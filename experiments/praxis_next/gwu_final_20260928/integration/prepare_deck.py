"""Integrate AIT slides into the complete GWU defense and revise stale claims."""
import json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TMP=Path(tempfile.gettempdir())/'codex-presentations/praxis-integrated-20260928/tmp'
old=json.loads((ROOT.parent/'praxis_final_20260927/DEFENSE_CONTENT.json').read_text(encoding='utf-8'))
ait=json.loads((Path(tempfile.gettempdir())/'codex-presentations/campaign-validation-20260928/tmp/slide-content.json').read_text(encoding='utf-8'))
inspect=[json.loads(x) for x in (TMP/'template-inspect/template-inspect.ndjson').read_text(encoding='utf-8').splitlines() if x]
updates={
5:{'body':['Paired evidence of score gains with lost exfiltration warnings.','A fixed-anchor training-composition contrast.','An executable source-qualification and model-review record.','Uncapped coverage and a separate AIT execution test.']},
7:{'title':'The evidence has four distinct scopes','body':['Original controlled study: 382,229 source rows.','UNRAVELED full release: 6,877,157 rows; same campaign.','AIT: eight executions; two later runs held out.','Source qualification retains other releases\' eligibility limits.'],
   'notes':'Keep the populations distinct. The original controlled and full-release UNRAVELED results remain the same campaign. AIT adds a different public source with six development and two later held-out laboratory executions. Its native three classes and one optional history group differ from the original four-class/two-group contract. The original policy direction is unreplicated; a small opposite-order warning tradeoff appears on Wilson. SCVIC, DAPT, DSRL and S-DAPT qualification findings remain source-specific.', 'citation':'Sections 1.7, 3.11-3.12 and 4.10-4.11'},
10:{'title':'Backup: complete fitting inventory','body':['Historical core: 141 LightGBM fitting jobs.','Technique-policy supplement: two Ridge selector fits.','Full-release extension: 12 sensor/arm fitting jobs.','AIT extension: 36 classifier and six selector fits.'],
    'notes':'The complete recorded inventory is 197 fitting jobs: 143 historical/supplementary, 12 full-release and 42 AIT. The count includes regressors and constant-class controls, and is not a count of independent attacks. AIT fits use every eligible training row and three seeds under its own frozen protocol. Model inventories and code/data hashes retain separate experimental provenance.','citation':'Sections 3.6, 3.10-3.12; fitting inventories'},
19:{'title':'Backup: executable calibration review'},
20:{'notes':old[19]['notes'].replace('A full-release expansion of UNRAVELED addresses coverage, while independent-campaign replication remains unmeasured.','The UNRAVELED expansion addresses coverage. The following AIT slides report a separately qualified three-class history test with two later executions held out; an exact four-class/two-group replication remains unresolved.')},
21:{'body':['UNRAVELED is one campaign; AIT runs share a lab generator.','Author labels do not independently verify stolen-file receipt.','Completed-flow features do not establish early forecasting.','Exact four-class replication and operational benefit remain open.'],
    'notes':old[20]['notes']+' AIT adds genuine execution-disjoint, calendar-separated testing for an adapted task. It does not reproduce the original policy direction. Its movement class is absent, history is the sole optional group, and its exfiltration labels follow publisher rules. The small Wilson tradeoff cannot establish a practically large or universal effect.','citation':'Sections 3.12, 4.11 and 5.4; Appendices D-E'},
22:{'body':['Integrated manuscript with complete result appendices.','Frozen protocols and complete source accounting.','Saved models, per-row predictions and source archives.','622 full-release and 1,245 AIT audit checks passed.'],
    'notes':'The integrated edition retains the original arithmetic and source evidence, the full UNRAVELED role-feature extension, and the separately frozen AIT test. The full-release audit passes 622 checks and the AIT audit passes 1,245. The AIT archive includes all eight publisher archives, prepared arrays, 42 models and every saved prediction. The original evidence bundles remain alongside the integrated delivery. Hash identity and computational consistency do not verify label truth or constitute external peer review.','citation':'Integrated delivery manifest; full-release and AIT audits'},
23:{'title':'The next test must retain the full task','body':['New workflow with all four native stage classes.','Original role/history groups and collection constraints.','Measure policy recurrence and label validity.','Then test whether joint reports improve real review decisions.'],
    'notes':'The adapted AIT execution test is complete. Its negative primary result and small secondary tradeoff narrow the claim. The next exact replication must retain the original four-class and two-evidence-group contract with reliable chronology and legitimate background. Unrelated real campaigns would test broader generalization. Analyst or deployment trials require measured operational outcomes and an explicit comparison design.','citation':'Section 5.5; completed AIT test in Section 4.11'},
24:{'body':['Higher F1 can coexist with fewer exfiltration warnings.','The original policy direction did not recur on AIT.','Wilson shows a small tradeoff in the opposite policy order.','Review scores, warnings and false alerts together.'],
    'notes':'The conclusion integrates favorable and adverse evidence. The original UNRAVELED policy result is sensitive in magnitude. The complete AIT release supplies two later held-out executions, but the original error-focused score-up/warnings-down direction is unreplicated. Wilson shows a much smaller tradeoff under entropy relative to error-focused selection: one, three and eight extra missed warnings; Harrison improves both. The thesis supports joint, source-qualified reporting, not universal warning loss or a universally superior acquisition policy. Technical backups begin at slide 26.','citation':'Chapter 5 synthesis; Section 4.11; Appendix E'},
29:{'title':'Backup: full-release fit uncertainty','body':old[28]['body']},
32:{'body':['Novelty: controlled evidence and reproducible review.','Full data: both source releases audited; new fits uncapped.','External test: adapted AIT; original direction unreplicated.','Exact replication and operational benefit remain future work.'],
    'notes':'Answer the validation question with the actual result, not a blanket yes or no. AIT provides eight laboratory executions, with two later executions held out after a pre-fit freeze. It uses three classes and one history group. The original named-policy direction does not recur; Wilson has a small opposite-order tradeoff while Harrison improves both metrics under entropy. The original four-class/two-group configuration remains distinct. All historical interventions were not retrained on both full releases: each extension has its declared task and population.','citation':'Integrated praxis, September 28, 2026; Section 4.11'}
}
for n,u in updates.items():old[n-1].update(u)
old[0]['notes']+=' This integrated edition includes the completed AIT validation in the main presentation, with updated limitations and conclusions.'
old[0]['citation']='Integrated praxis and evidence, September 28, 2026'
old[7]['notes']+=' The source-qualification branch now includes the separate AIT execution test described in Sections 3.12 and 4.11.'
for i,a in enumerate(ait):
    a['citation']=a.pop('cite')
    a['image']=None
ait[0]['body']=['AIT release: eight testbeds; 3,465,342 source rows.','Six executions train; two later executions evaluate.','2,397,158 training rows; 1,067,211 held-out rows.','Three native classes; history is the optional evidence.']
ait[1]['title']='Backup: the adapted AIT method'
ait[4]['title']='Backup: AIT interpretation limits'
# Twenty-five main slides; preserve displaced material and detailed AIT slides as backups.
order=[('old',i) for i in range(1,10)]+[('old',i) for i in range(11,19)]+[('old',20)]+[('ait',i) for i in [0,2,3]]+[('old',i) for i in range(21,25)]+[('old',i) for i in range(25,33)]+[('old',10),('old',19),('ait',1),('ait',4)]
assert len(order)==37
content=[];mapping=[]
for output,(kind,n) in enumerate(order,1):
    source=n if kind=='old' else 9
    c=dict(old[n-1] if kind=='old' else ait[n]);c.update(sourceSlide=source,sourceKind=kind,sourceIndex=n,outputSlide=output)
    content.append(c)
    targets=[{'shapeId':x['id'],'action':'rewrite'} for x in inspect if x.get('slide')==source and x['kind']=='textbox']
    mapping.append({'outputSlide':output,'sourceSlide':source,'narrativeRole':c['title'],'reuseMode':'duplicate-slide','editTargets':targets})
(TMP/'template-frame-map.json').write_text(json.dumps({'outputSlides':mapping,'omittedSourceSlides':[]},indent=2))
(TMP/'integrated-content.json').write_text(json.dumps(content,indent=2),encoding='utf-8')
(ROOT/'DEFENSE_CONTENT.json').write_text(json.dumps(content,indent=2),encoding='utf-8')
(TMP/'template-audit.txt').write_text('Source: completed September 27 GWU defense, all 32 slides preserved in content. Native artifact-tool inspection of all slides and prior visual review retained. Insert three AIT evidence slides into the main results sequence. Move two existing detail slides to backups and retain two AIT method/limitation backups. Main slide count 25; total 37. Edit existing title/body/footer slots only; preserve images, brand geometry and source typography.\n')
(TMP/'deviation-log.txt').write_text('Authorized incorporation: revised scope, model inventory, external-validation claims, limitations, future work, conclusion and committee answers. Reordered two detail slides into backups to preserve a 25-slide main defense. Five AIT slides duplicate the inherited source slide 9 content layout. No added visual primitives.\n')
(TMP/'source-notes.txt').write_text('Communication job: explain the complete praxis and how audited AIT evidence changes its generalization claim. Narrative: problem, method, original results, full release, source qualification, AIT results, limitations, conclusion, backups. All AIT values come from the audited September 28 evidence.\n')
print(json.dumps({'main':25,'backup':12,'total':len(content)}))
