"""Reuse the inspected GWU template and its approved content-frame mapping."""
import json, shutil, tempfile
from pathlib import Path

OLD=Path(tempfile.gettempdir())/'codex-presentations/gwu-defense-20260927/tmp'
TMP=Path(tempfile.gettempdir())/'codex-presentations/campaign-validation-20260928/tmp'
TMP.mkdir(parents=True,exist_ok=True)
old=json.loads((OLD/'template-frame-map.json').read_text())
base=old['outputSlides'][1]
slides=[]
roles=['external-source scope','frozen method','pooled result','held-out execution sensitivity','claim boundary']
for i,role in enumerate(roles,1):
    s=json.loads(json.dumps(base));s['outputSlide']=i;s['narrativeRole']=role;slides.append(s)
plan={'outputSlides':slides,'omittedSourceSlides':[{'sourceSlide':i,'reason':'Focused campaign-validation addendum uses the methodology content frame.'} for i in range(1,17) if i!=9]}
(TMP/'template-frame-map.json').write_text(json.dumps(plan,indent=2))
(TMP/'template-audit.txt').write_text('Reuse the complete sixteen-slide source inventory and prior inspection from '+str(OLD)+'. Re-reviewed the full contact sheet on September 28. Source remains Final_Defense_Template.pptx. Duplicate source slide 9 five times; preserve its GWU brand, geometry, typography, content frame and inherited shapes. Edit the two explicitly mapped title/body slots. Add only the bounded source footer authorized in the reused frame map. No title slide is needed for a defense appendix.\n')
(TMP/'deviation-log.txt').write_text('Only new text and one bounded citation/footer per cloned content slide. No template geometry changes or external visuals.\n')
(TMP/'source-notes.txt').write_text('Audience: GWU praxis defense committee. Communication job: understand what a frozen external-execution test adds and how its observed results limit the claim. Narrative: source/scope -> fixed design -> pooled outcomes -> execution sensitivity -> defensible claim. Data: reports/campaign_validation_20260928 final audited results; AIT Zenodo 13168643; Landauer et al., TDSC 2023. No result-dependent design change.\n')
shutil.copytree(OLD/'template-inspect',TMP/'template-inspect',dirs_exist_ok=True)
print(TMP)
