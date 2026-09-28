"""Integrate audited AIT evidence into the complete five-chapter praxis."""
import argparse,importlib.util,json,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=Path('C:/w/apt_benchmark_20260920/experiments/praxis_next')
OLD=BASE/'gwu_final_20260927'; NEW=BASE/'gwu_final_20260928'
EVIDENCE=ROOT.parent/'campaign_validation_20260928'
OUT=ROOT.parents[1]/'output/praxis_integrated_20260928'
QA=Path('C:/w/praxis_integrated_20260928_qa/paper')
for p in [NEW,OUT,ROOT]:p.mkdir(parents=True,exist_ok=True)
for folder in ['figures','models','results','reference']:
    if (OLD/folder).exists():shutil.copytree(OLD/folder,NEW/folder,dirs_exist_ok=True)
rows=json.loads((EVIDENCE/'RESULTS.json').read_text())
summary=json.loads((EVIDENCE/'SUMMARY.json').read_text())
prep=json.loads((EVIDENCE/'PREPARATION.json').read_text())
freeze=json.loads((EVIDENCE/'FREEZE.json').read_text())
audit=json.loads((EVIDENCE/'AUDIT.json').read_text());assert audit['failed']==0
policies=['none','always_history','entropy','harm']
names={'none':'Current','always_history':'Always history','entropy':'Entropy','harm':'Error-focused'}
def avg(n,p,k):
    a=[r[k] for r in rows if r['execution']==n and r['policy']==p]
    return sum(a)/len(a)
def table(h,rs):return '\n'.join(['|'+'|'.join(h)+'|','|'+'|'.join(['---']*len(h))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rs])
def pct(x):return f'{100*x:.3f}%'
md=(OLD/'manuscript.md').read_text(encoding='utf-8')
def insert_before(anchor,text):
    global md
    assert md.count(anchor)==1,anchor
    md=md.replace(anchor,text+'\n\n'+anchor,1)
scope='''The September 28 external-source extension qualifies all eight AIT netflow testbeds and evaluates a separately frozen three-class, one-history-group configuration on two later, held-out executions. It inspects 3,465,342 source rows and uses every eligible row: 2,397,158 for final training and 1,067,211 for evaluation. Its 36 classifier and six selector fits bring the recorded project inventory to 197 fitting jobs, including earlier constant-class controls. Separate source executions broaden the empirical record; the repeated laboratory scenario, different class taxonomy and different evidence groups limit the test to an adapted validation. Sections 3.12 and 4.11 state those changes before interpreting its results.'''
insert_before('## 1.8 Research Limitations',scope)
insert_before('## 1.9 Praxis Organization','The added AIT evaluation uses two held-out executions from a common laboratory generator. It supplies an external-source test for the adapted configuration, while leaving the original four-class, two-group experiment and real-world generalization distinct. The frozen original-direction test is unreplicated; a much smaller warning tradeoff appears in one execution with the opposite policy ordering.')
insert_before('## 2.6 Literature Gap and Contribution Positioning','''The AIT netflow release (Soro et al., 2024) derives TCP and UDP flow records from eight executions of the AIT laboratory environment. Its simulated legitimate activity and attack scenarios are described by Landauer et al. (2023), building on the model-driven testbed approach of Landauer et al. (2021). The released flow labels support benign activity, other attacks and DNS exfiltration. They do not supply the same movement class or evidence channels as the original UNRAVELED experiment. This distinction motivates the explicitly adapted validation in Section 3.12, rather than treating a dataset name as proof of an unchanged replication.''')
md=md.replace('| Policy-transfer supplement | 2 fits; T1105 recognition | Separate task; not stage replication |','| Policy-transfer supplement | 2 fits; T1105 recognition | Separate task; not stage replication |\n| AIT external-source validation | 8 executions; 3,465,342 rows; 42 fits | Three-class history acquisition; 2 later executions held out |')
insert_before('## 3.11 Full-Release, Uncapped Extension','The fit counts above describe the historical batch. The full-release extension adds 12 fitting jobs and the AIT validation adds 42, yielding 197 recorded jobs across the distinct evidence branches. Job counts include regressors and constant-class controls and do not count independent campaigns.')
coverage=table(['Execution','Use','Raw rows','Eligible rows','Other attack','Exfiltration'],[[s['execution'],'Test' if s['execution'] in freeze['test_executions'] else 'Train',f"{s['raw_rows']:,}",f"{s['eligible_rows']:,}",f"{s['class_counts']['other_attack']:,}",f"{s['class_counts']['exfiltration']:,}"] for s in sorted(prep,key=lambda s:s['raw_min_start_ms'])])
method=f'''## 3.12 Adapted External-Execution Validation on AIT

### 3.12.1 Question, source and pre-fit freeze

The added experiment tests the score, warning and false-alert comparison on a different source with entire executions held out. The acquisition objective comparison is retained, but the native taxonomy and evidence contract require an adaptation: benign, other attack and exfiltration replace the original four classes, and prior history is the only optional group. No movement label is inferred. Publisher roles, networks, ports and identities participate in source labeling and are excluded from model inputs. Thus this is an external-source execution test of an adapted configuration, not an exact PX081 replication.

All eight archives of AIT Netflow Data Set version 2, DOI 10.5281/zenodo.13168643, were downloaded and checked against publisher MD5s, local SHA256 hashes and every ZIP member's CRC (Soro et al., 2024). The laboratory generator supplies simulated legitimate traffic and repeated attack scenarios (Landauer et al., 2021, 2023). Qualification counts and timestamps were examined before fitting. PROTOCOL.md fixes the comparisons; FREEZE.json, written before the first fit, binds code, prepared data, software, features, execution membership and seeds. No result-dependent tuning or source omission followed evaluation.

### 3.12.2 Complete population and execution split

The complete source contains 3,465,342 rows. Preparation excludes 942 empty/unknown labels, ten invalid numeric records and 21 exact duplicate records; no conflicting-identity group was found. All 3,464,369 eligible rows remain. Exact observable identity combines protocol, endpoints, ports, times, packet counts and byte counts. Zero identity-hash intersections occur between final training and evaluation. Probe identities are absent from the aggregated release, so near-duplicate observations of the same activity may remain within an execution.

Executions are ordered by earliest observed start, with alphabetical tie-breaking. Santos, Fox, Wardbeck, Russellmitchell, Shaw and Wheeler provide 2,397,158 training rows. Wilson and Harrison provide 1,067,211 held-out rows. The latest training completion is January 30, 2022 at 23:58 UTC, before the first held-out observation on February 3 at 00:00 UTC. Final evaluation is both execution-disjoint and calendar-separated. Development forward folds use preceding executions to predict the next one; overlapping development execution intervals mean those folds are not a strict calendar-forward stream simulation.

**Table 3-10. Complete AIT source coverage and final allocation.** Counts are source observations, not independent attack counts.

{coverage}

### 3.12.3 Features, fitted models and acquisition rule

Ten current-flow features encode TCP/UDP, log duration, directional packet and byte totals, directional fractions and mean bytes per packet. Eight optional history features summarize flows from the same initiating endpoint that ended strictly before the current start and within the preceding hour: count, byte and packet totals and means, mean log duration, UDP fraction and time since the latest eligible completion. Empty histories are zero. Labels never enter history. Raw endpoint identifiers only key grouping; identifiers, ports, absolute timestamps, FQDNs, publisher roles, network names and execution identifiers are not predictors. Decisions describe completed flows.

For each of seeds 8101, 8102 and 8103, two LightGBM classifiers use current features or current plus history. Each has 150 boosting iterations, 15 leaves, learning rate .05, minimum child support ten and L2 regularization one, with deterministic execution and four CPU threads. Every eligible fitting row is used without class caps, class weighting, tuning or early stopping. Five forward development folds supply out-of-fold probabilities. Two regressors, each with 100 boosting iterations and nine leaves, estimate entropy reduction or weighted hard-error reduction after obtaining history. The illustrative error weights are [1,1,4]. Selectors observe only current features and current probabilities; optional history and post-acquisition probabilities are excluded from their inputs. Final classifiers fit all six development executions. The inventory is 36 classifier fits and six selector fits.

Policies are current-only, always-history, acquire if predicted entropy reduction is positive, and acquire if predicted weighted-error reduction is positive. All receive the same per-row budget of two; history costs two and arrives after .75 time units before a deadline of one. These are clean-delivery offline simulations. Equal available budgets do not imply equal realized spending, so acquisition fractions are reported. The implementation uses Python 3.11.9, NumPy 2.4.6, pandas 2.3.3 and LightGBM 4.7.0; full dependency pins accompany the evidence.

### 3.12.4 Outcome definitions and label limits

The frozen primary direction is higher macro-F1 accompanied by lower exfiltration warning recall under error-focused versus entropy-focused selection. Every policy, seed and held-out execution is reported, along with pooled and equal-execution summaries. Three-class macro-F1 cannot be read as equivalent to the original four-class score. Warning recall counts any non-benign prediction on an exfiltration-labeled row. Exact-stage recall, complete confusion matrices, false alerts, errors and acquisition counts remain separately available. Fitting seeds do not multiply the number of independent executions; no campaign-population confidence interval is claimed.

Publisher labels use topology, service ports and attack timing. The released UDP notebook labels residual unmatched traffic as exfiltration. A descriptive audit confirms that all 183,121 native exfiltration rows use DNS port 53 and a publisher-identified attacker endpoint. This establishes consistency with the published scenario, not independent payload verification. Those fields remain excluded from predictors. The computational audit independently recomputes reported results and verifies frozen hashes, strict prior-history boundaries, fitting populations, OOF targets, acquisition actions, selected probabilities and budget constraints. It passes all 1,245 checks.
'''
insert_before('# Chapter 4: Results',method)
pooled=table(['Policy','Macro-F1','Exfil warnings','Missed warnings','Benign alerts','Acquire'],[[names[p],f"{avg('pooled',p,'macro_f1'):.6f}",pct(avg('pooled',p,'exfil_warning_recall')),f"{avg('pooled',p,'exfil_warning_missed'):.1f}",f"{avg('pooled',p,'benign_false_alerts'):.1f}",pct(avg('pooled',p,'acquired_fraction'))] for p in policies])
byrun=table(['Execution','Policy','Macro-F1','Exfil warnings','Benign alerts'],[[n,names[p],f"{avg(n,p,'macro_f1'):.6f}",pct(avg(n,p,'exfil_warning_recall')),f"{avg(n,p,'benign_false_alerts'):.1f}"] for n in freeze['test_executions'] for p in policies])
paired=table(['Execution','Seed','Delta F1','Warning pp','Missed exfil','Benign alerts'],[[d['execution'],d['seed'],f"{d['delta_macro_f1']:+.6f}",f"{d['delta_exfil_warning_pp']:+.4f}",f"{d['delta_exfil_warning_missed']:+d}",f"{d['delta_benign_false_alerts']:+d}"] for d in summary['deltas'] if d['execution']!='pooled'])
result=f'''## 4.11 Adapted AIT Validation Results

The frozen primary direction did not recur: error-focused acquisition had higher macro-F1 with lower exfiltration warning recall in zero of six execution-by-seed comparisons and zero of three pooled seed comparisons. This is an adverse generalization result for the original named-policy contrast under the adapted task. It is retained without modifying the learned policies or decision thresholds.

**Table 4-15. Pooled AIT held-out results.** Means over seeds 8101-8103 on the same 1,067,211 rows. Fractional counts average integer seed outcomes. These are three fits of the same evaluation population.

{pooled}

Entropy selection has mean macro-F1 0.993970 versus 0.946233 for error-focused selection, exfiltration warning recall 99.772% versus 99.727%, and 971.3 versus 14,443.3 benign false alerts. History acquisition differs substantially: 74.400% versus 2.450%. These results compare the frozen policies with equal available budgets; they do not establish superiority at matched spending. The always-history reference attains macro-F1 0.994053 and 913.7 benign false alerts while retrieving history for every row.

**Table 4-16. Separate AIT held-out executions.** Means across three fitting seeds, retaining distinct execution populations.

{byrun}

Wilson supplies a smaller score/warning tradeoff with the opposite policy ordering. Entropy has higher F1 than error-focused selection but misses one, three and eight additional exfiltration warnings for seeds 8101, 8102 and 8103. The mean difference is four of 21,219 exfiltration observations, or 0.018851 percentage points, with 34.7 additional benign false alerts. This is a secondary descriptive observation, not a replacement for the frozen primary direction. Its small absolute size limits practical significance. On Harrison, entropy improves both F1 and exfiltration warning recall; the two executions therefore do not support a uniform score/warning reversal.

**Table 4-17. AIT paired sensitivity by execution and seed.** All deltas are error-focused minus entropy-focused selection. Positive missed-exfiltration counts mean more true exfiltration rows classified as benign.

{paired}

Giving each execution equal weight yields mean macro-F1 0.993536 and warning recall 99.781% for entropy, compared with 0.951903 and 99.739% for error-focused selection. Complete per-class precision, recall and F1, confusion matrices, unweighted and weighted errors, acquisition fractions and per-seed baselines are retained in the evidence and Appendix E. The 1,245-check audit passed with no failures.

In relation to RQ1, the separate source shows a small score/warning divergence in one held-out execution under the opposite policy ordering, while failing to reproduce the original primary direction. For RQ3, AIT qualifies for this declared three-class history task, not the unchanged four-class, two-group contract. RQ2 remains the original fixed-anchor temporal-composition experiment; the AIT extension does not re-estimate that effect.
'''
insert_before('# Chapter 5: Discussion and Conclusions',result)
insert_before('## 5.2 Contributions to the Body of Knowledge','''The AIT validation provides an empirical boundary on the policy result. Error-focused selection does not reproduce the original higher-F1/lower-warning direction on either held-out execution. Wilson nevertheless shows a small divergence in the opposite policy order, while Harrison favors entropy on both outcomes. This supports reading score, warning counts and false alerts jointly, without promoting a particular acquisition objective as universally superior. The large difference in realized acquisition rates also prevents a matched-spending superiority interpretation.''')
insert_before('## 5.3 Applied Evaluation Procedure','The new contribution additionally includes a frozen, external-source execution test on the complete AIT release. The retained negative primary result and small secondary tradeoff show where the earlier observation fails to generalize and where a narrower descriptive relationship remains visible. Shared laboratory construction, native label rules and the adapted evidence contract remain part of that contribution.')
md=md.replace('New fitting adapters await qualified source contracts.','The AIT adapter now implements a separate qualified three-class history contract; the original four-source contracts remain limited as reported.')
md=md.replace('whose locations and hashes are recorded without redistributing raw traces.','whose locations and hashes are recorded. The AIT reproduction archive additionally includes all eight unchanged publisher archives under CC BY 4.0 with attribution, prepared arrays, 42 model objects and every saved prediction.')
md=md.replace('Additional independent execution evidence would broaden the claim; its absence is a limit on generalization, not a reason to relabel the completed numerical observations as nonexistent or as four model failures.','The AIT extension adds two held-out laboratory executions for an adapted configuration. Their mixed findings broaden the empirical record while leaving exact four-class replication, unrelated-campaign generalization and operational benefit unresolved.')
insert_before('## 5.5 Recommendations for Future Research','''### 5.4.6 Validity of the external-execution extension

Whole-execution separation, final calendar separation, all-row fitting and strict prior-history construction strengthen the AIT test. They do not make two generated scenarios representative of independent real APT families. Native exfiltration labels are verified against the publisher's port/topology rule, not payload contents. The release aggregates probes without retaining sensor identity, so repeated observations may persist. Source taxonomies and evidence groups differ from PX081. The original-direction outcome was frozen before fitting, whereas the opposite-order Wilson interpretation is explicitly secondary and descriptive. Three seeds assess fitting sensitivity; no flow-level significance test or universal effect claim is made.''')
md=md.replace('The first empirical extension is independent-execution replication with reliable event clocks, native stage labels and legitimate background activity. The relevant aim is to test whether the measured relationship and its magnitude recur under a different workflow.','The next empirical extension is an exact four-class, two-evidence-group replication on another qualified execution, followed by unrelated campaign families and measured collection constraints. The completed AIT test addresses disjoint laboratory executions for the adapted three-class history task. Its unreplicated primary direction and small secondary tradeoff make recurrence, effect size and source-label verification explicit research questions.')
insert_before('# References','''The AIT extension adds 3,465,342 inspected source rows, two later held-out executions and 42 fits under a separate frozen contract. The original named-policy direction does not replicate. A small opposite-order warning loss occurs on Wilson, and Harrison improves both outcomes. The defensible synthesis is therefore bounded: aggregate stage scores and warning retention can diverge on inspected records, but neither the sign nor the size of a particular policy contrast is universal. A joint report makes these outcomes visible and preserves the adverse evidence.''')
# Insert new sources into the existing bibliography without displacing appendices.
prefix,tail=md.split('# References\n',1);refs,appendices=tail.split('# Appendix A:',1)
newrefs=[
'Soro, F., Landauer, M., Skopik, F., Hotwagner, W., & Wurzenberger, M. (2024). *AIT Netflow Data Set* (Version 2) [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.13168643',
'Landauer, M., Skopik, F., Frank, M., Hotwagner, W., Wurzenberger, M., & Rauber, A. (2023). Maintainable log datasets for evaluation of intrusion detection systems. *IEEE Transactions on Dependable and Secure Computing, 20*(4), 3466-3482. https://arxiv.org/abs/2203.08580',
'Landauer, M., Skopik, F., Wurzenberger, M., Hotwagner, W., & Rauber, A. (2021). Have it your way: Generating customized log datasets with a model-driven simulation testbed. *IEEE Transactions on Reliability, 70*(1), 402-415. https://doi.org/10.1109/TR.2020.3031317']
allrefs=sorted([r.strip() for r in refs.strip().split('\n\n') if r.strip()]+newrefs)
md=prefix+'# References\n\n'+'\n\n'.join(allrefs)+'\n\n# Appendix A:'+appendices
appendix='''# Appendix E: Complete AIT Validation and Reproduction

## E.1 Population, contract and audit

This appendix preserves the separate AIT experiment described in Sections 3.12 and 4.11. All eight archives are included in the reproduction package, with publisher MD5 verification, local SHA256 hashes, ZIP CRC checks and CC BY 4.0 attribution. Every eligible row enters its assigned final partition. Class support is shown below; the complete source accounting is in Table 3-10. Seeds share these same populations.

**Table E-1. AIT eligible class support by execution.**

'''+table(['Execution','Use','Benign','Other attack','Exfiltration'],[[s['execution'],'Test' if s['execution'] in freeze['test_executions'] else 'Train',*[f"{s['class_counts'][c]:,}" for c in ['benign','other_attack','exfiltration']]] for s in sorted(prep,key=lambda s:s['raw_min_start_ms'])])+'\n\n'
for i,seed in enumerate(freeze['seeds'],2):
    appendix+=f'## E.{i} Seed {seed}: Every Policy and Execution\n\n**Table E-{i}. Complete AIT outcomes for seed {seed}.** Rows within each execution are paired across policies. Pooled rows combine Wilson and Harrison for the same seed.\n\n'
    appendix+=table(['Execution / policy','Macro-F1','Warnings','Missed exfil','Benign alerts','Acquire'],[[r['execution']+' / '+names[r['policy']],f"{r['macro_f1']:.6f}",pct(r['exfil_warning_recall']),r['exfil_warning_missed'],r['benign_false_alerts'],pct(r['acquired_fraction'])] for r in rows if r['seed']==seed])+'\n\n'
appendix+='''## E.5 Reproduction Materials

Campaign_Validation_Full_Evidence.zip contains the full eight-archive release, eight prepared arrays, 36 classifier objects, six selector objects, all development out-of-fold predictions and every held-out probability/action array. Reports include ACQUISITION.json, QUALIFICATION.json, PREPARATION.json, PROTOCOL.md, FREEZE.json, FIT_LOG.json, RESULTS.json, RESULTS.csv, SUMMARY.json, AUDIT.json, ARTIFACTS.json, NATIVE_LABEL_DIAGNOSTIC.json and SELECTOR_DIAGNOSTIC.json. The latter diagnostic is descriptive after fitting and does not alter the frozen policies. Code and pinned compute dependencies are included. The computational audit passes 1,245 checks.

The local data root is C:/w/campaign_validation_20260928. Run acquire_qualify.py, validate.py prepare, validate.py run, and audit.py with the recorded environment. Repoint documented absolute paths when moving machines and record the path amendment. The complete output bundle accompanies the integrated paper and defense. Historical and full-release UNRAVELED evidence retain their own source bindings and experimental contracts; their metrics are not pooled with this different task.
'''
md+='\n\n'+appendix
(NEW/'manuscript.md').write_text(md,encoding='utf-8')
abstract='''This praxis examines when improved advanced persistent threat classification scores accompany missed attack warnings. It contributes controlled evidence and an executable procedure reporting exact-stage recognition, attacks classified as benign, and benign false alerts together. In a UNRAVELED acquisition comparison, mean macro-F1 increased from 0.7148 to 0.7379 while exfiltration warning recall decreased from 85.18% to 76.25%; omission analyses revealed substantial effect-size sensitivity. A fixed-anchor temporal contrast increased macro-F1 by 0.0632 when later-period observations entered fitting. A full-release extension verifies 173 files and 6,877,157 rows and fits current-flow and role-augmented models without class caps in six sensor views. Roles improve macro-F1 in two views, while stage support constrains interpretation. An adapted external-source test additionally inspects all 3,465,342 AIT netflow rows, trains on six executions and evaluates two later executions containing 1,067,211 eligible rows. Its three-class, history-only contract differs from the original four-class, two-group task. The original error-focused-versus-entropy score-up/warnings-down direction recurs in none of six execution-by-seed comparisons. Wilson shows a small opposite-order tradeoff: higher F1 under entropy accompanies one to eight additional missed exfiltration warnings; Harrison improves both outcomes. The AIT computational audit passes 1,245 checks. These results support joint reporting while limiting claims about policy superiority and recurrence. Shared laboratory scenarios, publisher-defined labels and completed-flow features leave unrelated-campaign generalization, early forecasting and operational benefits unresolved.'''
(NEW/'abstract.md').write_text(abstract,encoding='utf-8')
shutil.copy2(NEW/'manuscript.md',OUT/'manuscript.md');shutil.copy2(NEW/'abstract.md',OUT/'abstract.md')
(ROOT/'INTEGRATION_MAP.json').write_text(json.dumps({'paper_sections':['Abstract','1.7','1.8','2.5','3.2','3.10','3.12','4.11','5.1','5.2','5.3','5.4','5.5','5.6','References','Appendix E'],'references':len(allrefs),'recorded_fitting_jobs':197,'sources':str(NEW),'evidence_audit_passed':audit['passed']},indent=2))
spec=importlib.util.spec_from_file_location('gwu_renderer',BASE/'gwu_final_20260924/render_gwu.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent=mod.GWURenderer
class IntegratedRenderer(parent):
    def frontmatter(self):
        super().frontmatter()
        for p in self.doc.paragraphs:
            for r in p.runs:
                r.text=r.text.replace('Manuscript prepared September 24, 2026','Manuscript prepared September 28, 2026')
mod.GWURenderer=IntegratedRenderer
mod.build(argparse.Namespace(source=NEW/'manuscript.md',abstract=NEW/'abstract.md',title=mod.TITLE,
                            docx=OUT/'Gary_Pagan_Final_Praxis.docx',pdf=OUT/'Gary_Pagan_Final_Praxis.pdf',
                            qa_dir=QA,receipt=ROOT/'RENDER_RECEIPT.json'))
