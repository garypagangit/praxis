"""Assemble the evidence-bound final review edition, retaining historical results."""
from pathlib import Path
import json, shutil, importlib.util, argparse, hashlib, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260924')
NEW=OLD.parent/'gwu_final_20260927'
OUT=Path('C:/Users/garyp/OneDrive/Documents/codex/output/praxis_final_20260927')
SCRATCH=Path('C:/Users/garyp/AppData/Local/Temp/codex-presentations/gwu-defense-20260927/tmp')
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,row))+'|' for row in rows])
def pct(x):return 'Unsupported' if x is None else f'{100*x:.2f}%'
def main():
 r=json.loads((ROOT/'FULL_RELEASE_RESULTS.json').read_text());audit=json.loads((ROOT/'FULL_RELEASE_AUDIT.json').read_text());assert audit['status']=='PASS'
 NEW.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True,parents=True)
 for d in ['figures','results','models','reference']:shutil.copytree(OLD/d,NEW/d,dirs_exist_ok=True)
 shutil.copy2(OLD/'references.json',NEW/'references.json')
 shutil.copytree(ROOT,NEW/'full_release',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 sensors=r['sensors'];train=sum(sum(s['preparation']['split_counts']['train']) for s in sensors);cal=sum(sum(s['preparation']['split_counts']['calibration']) for s in sensors);test=sum(sum(s['preparation']['split_counts']['test']) for s in sensors)
 dupe=sum(s['preparation']['exact_duplicate_rows_removed'] for s in sensors);conflict=sum(s['preparation']['conflicting_rows_quarantined'] for s in sensors);boundary=sum(s['preparation']['boundary_overlap_rows_excluded'] for s in sensors)
 qualified=[s for s in sensors if all(s['preparation']['split_counts']['train']) and all(s['preparation']['split_counts']['test'])]
 degenerate=[s['sensor'] for s in sensors if s['arms']['current']['test']['single_class_training']]
 improved=[s for s in sensors if s['arms']['current_roles']['test']['macro_f1']>s['arms']['current']['test']['macro_f1']]
 reversals=[s['sensor'] for s in improved if any(s['arms']['current']['test']['classes'][c]['support'] and s['arms']['current_roles']['test']['classes'][c]['warning_recall']<s['arms']['current']['test']['classes'][c]['warning_recall'] for c in ['OtherAttackStage','MovementAuthorLabel','ExfiltrationAuthorLabel'])]
 summary={'raw_rows':r['raw_rows'],'train':train,'calibration':cal,'test':test,'duplicate':dupe,'conflict':conflict,'boundary':boundary,'single_class_sensors':degenerate,'all_four_train_test_sensors':[s['sensor'] for s in qualified],'improved_sensor_count':len(improved),'warning_reversal_sensors':reversals}
 (ROOT/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
 scope=f'''The September 27 full-release extension additionally audits all 173 released flow files and all 6,877,157 source rows across six sensor views, fitting current-flow and current-flow-plus-role models on every eligible training row. Its 12 fitting jobs bring the combined recorded inventory to 155; single-class training jobs are explicitly identified as degenerate controls. The new extension extends population coverage and removes fitting caps for the role-feature comparison. It does not rerun every historical intervention on the expanded population and does not create a second campaign.'''
 method='''## 3.11 Full-Release, Uncapped Extension

The original controlled history and acquisition study used eleven complete net1013x files (382,229 source rows), with class-specific fitting caps. To address the distinction between a complete prepared artifact and the complete upstream release, the new extension binds the original source inventory by SHA-256 and checks every released flow file against its recorded byte hash, row count and right-anchored native-stage totals. The pinned author repository revision is d2ea90055d82fa448ab20588a13e3ec8bfd74816. All 173 files across 31 capture directories are included; six sensor views remain separate because simultaneous network observations are dependent. A source row is not an independent attack execution.

The extension protocol was written before its new fitting jobs. It fixes training to flows completed before June 27, 2021 UTC, calibration to flows starting on or after June 27 and completed before June 28, and testing to flows starting on or after June 28. Flows spanning a boundary are excluded and counted. Exact within-sensor observable identities combine endpoints, service ports, timestamps and numeric current-flow measurements. Identical copies with consistent labels are counted once; conflicting copies are quarantined. Near-duplicates and cross-sensor dependence remain limitations.

The parser takes stable numeric fields from the first 77 columns and native annotation fields from the final four columns; variable unquoted comma-containing application fields are not treated as additional numeric inputs. Benign remains benign; reconnaissance, foothold and cover-up map to OtherAttackStage; movement and exfiltration retain their author labels. Flow identifiers, absolute timestamps, endpoint addresses, MAC addresses, raw ports, VLAN and tunnel identifiers are excluded from predictors. Three coarse destination-service indicators are included. The roles arm adds eight coarse topology indicators from the two endpoints. An 'other' role is not an independently verified Internet or attacker designation.

Each sensor has a current-flow arm and a current-flow-plus-roles arm. Every eligible training row is used without a class cap, downsampling or class weighting. LightGBM 4.7.0 uses 300 boosting iterations, 15 leaves, learning rate 0.05, minimum child support 10, L2 regularization 1.0, deterministic mode and seed 20260927. The extension environment uses NumPy 2.4.6, scikit-learn 1.9.0 and joblib 1.5.3; the historical environment remains recorded separately. No new history, future-event feature, source-sensor identity or alternative architecture is introduced. Prediction is multiclass argmax. A sensor with only one training class receives the corresponding constant-class probability vector: that is a degenerate control, not evidence of attack-learning ability. A probability-column alignment failure first exposed this library edge case; the implementation was corrected without changing cutoffs, source rows, features or selection thresholds.

Metrics include the complete four-by-four confusion matrix, exact-stage precision and recall, per-class F1, stage-conditioned non-benign warning recall, benign false-alert counts and rates, one-versus-rest ROC AUC and average precision where supported. Macro-F1 always averages the four declared classes, assigning zero to unsupported classes. It is not comparable across different support patterns as if they were equivalent tasks; for example, perfect benign-only prediction yields 0.25 on that fixed four-class measure. Unsupported warning recall is reported as unavailable, not as zero or success. Per-capture tables and every calibration/test prediction are retained.

A small applied review example freezes two choices on calibration alone. The score-only choice selects the higher macro-F1 arm, with ties favoring current flow. The conservative choice allows roles only if macro-F1 increases, warning recall for every supported attack stage falls by at most one percentage point, and benign false-positive rate rises by at most 0.1 percentage point. A missing calibration attack class makes the decision provisional. These tolerances are illustrative engineering choices, not validated analyst preferences or a guarantee on later data. Both choices are evaluated on the unchanged test population without retuning.

The new source inventory, frozen protocol, per-sensor results, prediction files, model objects and independent count-based audit are retained in the accompanying evidence. One deterministic fit per arm estimates this declared contrast; it adds no campaign-level confidence interval. The original fitting-seed sensitivity remains the evidence about historical run variation.

'''
 counts=table(['Sensor','Files','Source rows','Train / cal / test'],[[s['sensor'],len(s['preparation']['files']),f"{s['preparation']['raw_rows']:,}",' / '.join(f'{sum(v):,}' for v in s['preparation']['split_counts'].values())] for s in sensors])
 performance=table(['Sensor','Macro-F1 current / roles','Exfil warnings current / roles','Benign alerts current / roles'],[[s['sensor'],f"{s['arms']['current']['test']['macro_f1']:.4f} / {s['arms']['current_roles']['test']['macro_f1']:.4f}",' / '.join(pct(s['arms'][a]['test']['classes']['ExfiltrationAuthorLabel']['warning_recall']) for a in ['current','current_roles']),' / '.join(str(s['arms'][a]['test']['benign_false_alerts']) for a in ['current','current_roles'])] for s in sensors])
 selection=table(['Sensor','Score choice','Review choice','Missing calibration stages'],[[s['sensor'],s['calibration_selection']['f1_choice'].replace('current_roles','roles'),s['calibration_selection']['review_choice'].replace('current_roles','roles'),', '.join(x.replace('AuthorLabel','').replace('OtherAttackStage','Other') for x in s['calibration_selection']['review_provisional_missing_classes']) or 'None'] for s in sensors])
 outcome=f'''## 4.10 Full-Release Results and Calibration Review

The source audit accounts for all **6,877,157 rows in 173 files**. Across the six sensor views, {dupe:,} exact duplicate rows were removed, {conflict:,} conflicting-label rows were quarantined and {boundary:,} retained rows crossed a temporal boundary. The resulting analysis contains {train:,} training rows, {cal:,} calibration rows and {test:,} test rows. These are sensor observations rather than independent-event totals. All eligible training rows were used in each arm. The independent computational audit passed {audit['check_count']} checks of source coverage, row conservation, temporal separation, unique identities, prediction populations, probability normalization, confusion matrices, macro-F1, class support and warning counts.

**Table 8. Complete release coverage and chronological allocation.** Source rows precede duplicate and boundary handling. Training, calibration and test counts are after handling. The three numbers in the final column follow that order.

{counts}

The single-class training sensors are {', '.join(degenerate) or 'none'}. Their constant-class outcomes document a support limit. Sensors with all four mapped classes represented in both training and testing are {', '.join(s['sensor'] for s in qualified) or 'none'}. Class support is detailed in Appendix D; more files do not automatically supply every attack stage at every cutoff.

**Table 9. Full-release paired test results.** Current and roles use identical evaluation rows within a sensor. Macro-F1 uses a fixed four-class denominator. Unsupported exfiltration recall is not estimable. False-alert counts must be read with the benign support in Appendix D.

{performance}

Roles improve test macro-F1 in {len(improved)} of the six views. Views with a macro-F1 increase and a decline in warning recall for at least one supported attack stage are {', '.join(reversals) or 'none'}. At netgw, macro-F1 changes from 0.49909446 to 0.49911102, benign false alerts decrease from 2,105 to 2,104, and OtherAttackStage warnings decrease by one: missed warnings increase from 25,429 to 25,430 among 26,712 such rows. This tiny one-event reversal is not evidence of a stable or practically large effect. At net1013x, both exfiltration warning recall and macro-F1 improve slightly; that arm does not reproduce the historical exfiltration-warning loss. This is the declared role-feature contrast under uncapped chronological fitting. It neither estimates the historical acquisition-budget effect on the expanded release nor converts sensor views into independent replications. The historical warning-loss finding retains its own population and sensitivity limits.

**Table 10. Calibration-only model choices.** A review with absent attack-stage support remains provisional. Test results for the selected arms are exactly the corresponding Table 9 arm outcomes; no second test optimization occurs.

{selection}

This applied example demonstrates an executable audit decision and reveals which stages its calibration data can assess. {sum(bool(s['calibration_selection']['review_provisional_missing_classes']) for s in sensors)} of the six views lack at least one attack stage in calibration. Their review decisions are therefore provisional; the extension does not demonstrate a fully supported all-stage calibration safeguard. A favorable calibration decision does not establish later warning preservation, an optimal tolerance, or actual analyst benefit. The complete per-capture confusion matrices and stage metrics accompany the table, including the unfavorable outcomes.

'''
 appendix='''# Appendix D: Full-Release Evidence and Reproduction

This appendix reports the new uncapped extension separately from Appendix A's historical experiment inventory. The fixed class order is Benign, OtherAttackStage, MovementAuthorLabel and ExfiltrationAuthorLabel. All counts below are after duplicate handling and temporal-boundary exclusions.

'''
 for s in sensors:
  appendix+=f"## D.{sensors.index(s)+1} {s['sensor']}\n\n"
  appendix+=f"**Table D. {s['sensor']} class support by split.**\n\n"+table(['Split','Benign','Other','Movement','Exfiltration'],[[k,*v] for k,v in s['preparation']['split_counts'].items()])+'\n\n'
  for arm in ['current','current_roles']:
   t=s['arms'][arm]['test'];appendix+=f"**{arm.replace('_',' ')} test results.** Benign false-alert rate: {pct(t['benign_fpr'])}.\n\n"
   appendix+=f"**Table D. {s['sensor']} {arm.replace('_',' ')} test outcomes.**\n\n"+table(['Author-stage group','Support','Exact recall','Warning recall','Missed warnings'],[[c.replace('AuthorLabel','').replace('OtherAttackStage','Other'),m['support'],pct(m['recall']),pct(m['warning_recall']),m['missed_warnings'] if m['missed_warnings'] is not None else 'N/A'] for c,m in t['classes'].items()])+'\n\n'
 appendix+='''## D.7 Artifact Layout and Execution

The evidence package contains FULL_RELEASE_PROTOCOL.json, FULL_RELEASE_RESULTS.json, FULL_RELEASE_AUDIT.json, per-sensor PREPARATION.json and RESULTS.json, full_release.py, audit_full_release.py, the revised manuscript source and figure assets, and the original evidence archive. The local reproducibility bundle additionally contains saved models and every new calibration/test probability vector, target and row key. The source inventory records the original released flow-file hashes and acquisition provenance. Raw flow CSVs remain in the pinned local source directory and are not duplicated into the manuscript bundle.

Run full_release.py with Python, NumPy, scikit-learn, LightGBM and joblib using the recorded environment. The script's ROOT and PRIVATE paths locate public outputs and local prepared arrays. It requires the inventory at the recorded path and the matching raw source directory. Run audit_full_release.py after fitting to recompute count-based metrics independently from saved predictions. Dependencies and environment versions are captured in the final manifest. Repointing paths for another machine does not change the frozen analytical choices; verify source hashes before fitting.

The original 143-fit inventory and the extension's 12 fitting jobs are kept separate. A one-class LightGBM fitting job is identified as such and supplies a constant-class control; it is not counted as a successfully learned multiclass detector. The evidence is computationally reviewable and remains subject to source-label, campaign-dependence and institutional-review limitations.
'''
 md=(OLD/'manuscript.md').read_text(encoding='utf-8')
 marker='These fitting counts are not counts of independent attacks.';md=md.replace(marker,marker+'\n\n'+scope,1)
 md=md.replace('# Chapter 4:',method+'# Chapter 4:',1).replace('# Chapter 5:',outcome+'# Chapter 5:',1)
 md=md.replace('this publication assembly performs no new source search or download.','these historical qualification outcomes are preserved. The full-release extension in Section 3.11 additionally verifies all UNRAVELED flow-file bytes and performs new fitting.')
 md=md.replace('This completion adds reanalysis, source checks, and document assembly, not new model fits.', 'The historical completion added reanalysis, source checks and document assembly without new model fits.')
 md=md.replace('The GWU edition assembles existing results and adds explanatory text, diagrams, mathematical summaries and complete publication tables. It performs no additional model fitting.','The September 24 GWU edition assembled existing results without additional model fitting. The September 27 edition retains that evidence and adds the 12 full-release fitting jobs described in Section 3.11.')
 md=md.replace('The completed experiments use a fixed subset of eleven','The historical controlled experiments use a fixed subset of eleven')
 md=md.replace('| UNRAVELED | Primary completed experiments |','| UNRAVELED | Historical controlled experiments |')
 md=md.replace('| Benchmark qualification | 4 requested sources; no new fits | Native support, timing and dependencies |','| Benchmark qualification | 4 requested sources; no new fits | Native support, timing and dependencies |\n| Full-release extension | 173 files; 6,877,157 rows; 12 fitting jobs | Uncapped current-flow versus role-feature comparison; same campaign |')
 md=md.replace('The completed contribution is the controlled evidence and reproducible procedure:',f'The full-release extension accounts for all 6,877,157 released rows and evaluates the declared role-feature comparison with uncapped training. It strengthens coverage while exposing sensor-specific support limits; it supplies no independent campaign or operational validation.\n\nThe completed contribution is the controlled evidence and reproducible procedure:')
 md=md.replace('### 5.4.5 Scope of the finished manuscript','The full-release extension removes the original file-coverage and class-cap restrictions for its own role-feature comparison. It retains one exposed campaign, sensor dependence and author-stage semantics. Its fixed four-class macro-F1 penalizes unsupported classes; comparisons across sensors with different class support are descriptive. Calibration-only review tolerances are illustrative, and a missing stage cannot be protected by an unobserved calibration measurement.\n\n### 5.4.5 Scope of the finished manuscript')
 md=md.replace('## 5.6 Conclusions','The September 26 follow-up acquired eight CRC-verified CAM-LDS archive members from two previously inspected executions and checked 3,332 flow records against four T1041 actions. Tool output reported successful downloads, but each action had multiple candidate C2 flows and the streams lacked verified legitimate-user labels. The complete publisher archive checksum was not verified. These additional bytes improve source inspection, yet do not create untouched executions or defensible benign/exfiltration flow labels. No unsupported replication model was fitted. The acquisition and qualification receipts accompany the final evidence.\n\n## 5.6 Conclusions')
 md+='\n\n'+appendix
 table_numbers={'1':'3-1','2':'4-5','3':'4-1','4':'4-7','5':'4-8','6':'5-1','7':'4-11','8':'4-12','9':'4-13','10':'4-14'}
 md=re.sub(r'\bTable (10|[1-9])\b(?![-.][0-9])',lambda m:'Table '+table_numbers[m[1]],md)
 (NEW/'manuscript.md').write_text(md,encoding='utf-8')
 abstract=f'''This praxis examines when improved advanced persistent threat (APT) classification scores accompany more missed attack warnings. The contribution is controlled empirical evidence and an executable evaluation procedure that reports exact attack stages, attacks classified as benign, and benign false alerts together. In a completed UNRAVELED evidence-acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379 while exfiltration warning recall decreased from 85.18% to 76.25%. A fixed-anchor temporal contrast increased macro-F1 by 0.0632 when later-period observations entered fitting. Chronological history improved macro-F1 from 0.7365 to 0.7582 and reduced mean benign false alerts from 24.0 to 14.3, alongside a smaller warning loss. Retrospective seed and capture omission analyses retained the specified mean warning-loss direction while showing substantial magnitude sensitivity. A new full-release extension verifies all 173 released flow files and 6,877,157 source rows, and compares current-flow and role-augmented models using every eligible training row in six separate sensor views. It allocates {train:,} training, {cal:,} calibration and {test:,} test observations after declared duplicate and boundary handling. Roles improve macro-F1 in {len(improved)} views; single-class training and absent calibration stages constrain interpretation. A frozen calibration review illustrates joint score, warning and workload criteria. An independent computational audit passed {audit['check_count']} checks of the new evidence. A separate source-qualification audit documents timing, class-support, dependency and access limits in proposed benchmark extensions. The full-release analysis expands coverage for its declared role-feature contrast; it does not rerun all historical interventions or supply independent campaigns. Claims remain specific to inspected author labels and completed-flow observations. Early forecasting, operational benefit and independent-campaign generalization were not measured.'''
 abstract=f'''This praxis examines when improved advanced persistent threat (APT) classification scores accompany more missed attack warnings. It contributes controlled empirical evidence and an executable evaluation procedure reporting exact attack stages, attacks classified as benign, and benign false alerts together. In a UNRAVELED evidence-acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379 while exfiltration warning recall decreased from 85.18% to 76.25%. A fixed-anchor temporal contrast increased macro-F1 by 0.0632 when later-period observations entered fitting. Retrospective seed and capture omissions retained the specified warning-loss direction while revealing substantial magnitude sensitivity. A full-release extension verifies all 173 flow files and 6,877,157 source rows and compares current-flow and role-augmented models using every eligible training row in six separate sensor views. After declared handling, it includes {train:,} training, {cal:,} calibration and {test:,} test observations. Roles improve macro-F1 in {len(improved)} views. Single-class training and missing calibration stages constrain interpretation; calibration-only choices illustrate joint score, warning and workload review. An independent computational audit passed {audit['check_count']} checks. Separate source qualification documents timing, support, dependency and access limits in proposed benchmark extensions. The extension expands population coverage for its declared role-feature contrast; it does not rerun every historical intervention or supply independent campaigns. Claims concern inspected author labels and completed-flow observations. Independent-campaign generalization, early forecasting and operational benefits remain unmeasured.'''
 (NEW/'abstract.md').write_text(abstract,encoding='utf-8')
 # Publication plots, derived directly from the evidence; never pooled as independent sensors.
 figdir=NEW/'figures';plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13})
 fig,axs=plt.subplots(1,3,figsize=(11.5,5),layout='constrained')
 for ax,values,title,ylim in [(axs[0],[.7148,.7379],'Macro-F1',(0,1)),(axs[1],[85.18,76.25],'Exfil. warnings (%)',(0,100)),(axs[2],[111.3,122.3],'Benign false alerts',(0,150))]:
  ax.bar(['Entropy','Error\nfocused'],values,color=['#36566f','#aa6e23']);ax.set_title(title);ax.set_ylim(*ylim)
  for i,v in enumerate(values):ax.text(i,v+ylim[1]*.025,f'{v:.4f}' if ylim[1]==1 else f'{v:.2f}%' if ylim[1]==100 else f'{v:.1f}',ha='center',fontsize=14)
  ax.spines[['right','top']].set_visible(False)
 fig.savefig(figdir/'defense_main_result.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11.5,5),layout='constrained');ax.barh(['All three seeds','Omit seed 8101'],[-8.93,-.36],color=['#aa6e23','#36566f']);ax.axvline(0,color='black',lw=.8);ax.set_xlim(-10,1);ax.set_xlabel('Change in exfiltration warning recall (percentage points)');ax.set_title('The direction survives; the size is seed-sensitive');ax.spines[['right','top']].set_visible(False)
 for i,v in enumerate([-8.93,-.36]):ax.text(v-.1,i,f'{v:.2f}',ha='right',va='center')
 fig.savefig(figdir/'defense_seed.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11.5,5),layout='constrained');x=np.arange(6);bottom=np.zeros(6)
 for split,color in [('train','#36566f'),('calibration','#aa6e23'),('test','#769da7')]:
  vals=np.array([sum(s['preparation']['split_counts'][split]) for s in sensors]);ax.bar(x,vals/1e6,bottom=bottom/1e6,label=split.title(),color=color);bottom+=vals
 ax.set_xticks(x,[s['sensor'] for s in sensors]);ax.set_ylabel('Sensor observations (millions)');ax.legend(frameon=False,ncol=3);ax.spines[['right','top']].set_visible(False);fig.savefig(figdir/'defense_coverage.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11.5,5),layout='constrained')
 for off,arm,label,color in [(-.18,'current','Current','#36566f'),(.18,'current_roles','Current + roles','#aa6e23')]:ax.bar(x+off,[s['arms'][arm]['test']['macro_f1'] for s in sensors],width=.36,label=label,color=color)
 ax.set_xticks(x,[s['sensor'] for s in sensors]);ax.set_ylim(0,1);ax.set_ylabel('Fixed four-class macro-F1');ax.legend(frameon=False);ax.spines[['right','top']].set_visible(False);fig.savefig(figdir/'defense_full_results.png',dpi=180);plt.close(fig)
 print(json.dumps(summary,indent=2))
 # Preserve the validated GWU renderer and modify only the edition preparation date.
 spec=importlib.util.spec_from_file_location('gwu_renderer',OLD/'render_gwu.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 base=mod.GWURenderer
 class UpdatedRenderer(base):
  def frontmatter(self):
   super().frontmatter()
   for p in self.doc.paragraphs:
    for run in p.runs:
     if 'Manuscript prepared September 24, 2026' in run.text:run.text=run.text.replace('September 24','September 27')
 mod.GWURenderer=UpdatedRenderer
 mod.build(argparse.Namespace(source=NEW/'manuscript.md',abstract=NEW/'abstract.md',title=mod.TITLE,docx=OUT/'Gary_Pagan_Final_Praxis.docx',pdf=OUT/'Gary_Pagan_Final_Praxis.pdf',qa_dir=Path('C:/w/gwu_final_document_qa_20260927'),receipt=ROOT/'RENDER_RECEIPT.json'))
if __name__=='__main__':main()
