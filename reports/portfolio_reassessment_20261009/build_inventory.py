"""Build a retrospective overlay; never rewrite original experimental decisions."""
from pathlib import Path
from html.parser import HTMLParser
import csv, json, re, hashlib, shutil, subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag in ('td','th'): self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row: self.rows.append(self.row)

records={}
tracker='reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html'
p=Tables(); p.feed((ROOT/tracker).read_text(encoding='utf-8-sig'))
for row in p.rows:
    for i,cell in enumerate(row[:2]):
        m=re.fullmatch(r'PX[- ]?(\d{3})',cell)
        if m:
            key='PX-'+m[1]
            records[key]={'id':key,'title':row[i+1] if len(row)>i+1 else key,'historical_record':row,'source':tracker}
for rel in ['configs/new_praxis_experiment_registry_20260723.json','reports/PRAXIS_CURRENT_STATUS.json']:
    for r in json.loads((ROOT/rel).read_text(encoding='utf-8-sig'))['experiments']:
        key=r.get('id',r.get('px_id'))
        records.setdefault(key,{'id':key}).update(title=r['title'],historical_record=r,source=rel)

# Each line is an evidence-specific reassessment, not a replacement preregistered result.
notes='''001|bounded_positive|Original TTA gain survives only in-source; independent UNSW macro-F1 delta -0.017344 and protected-class decline. Study safe adaptation boundaries, not universal transfer.
002|bounded_positive|TTP overlap retrieval works with shared profiles; leave-query-out overlap zero. Retrieval utility does not establish actor attribution.
003|bounded_positive|CTI evidence improves original tasks; external 1247-case evidence-only accuracy declines 2.33/1.84 pp. Plausible source-compatibility evaluation, no universal RAG or checker win.
004|bounded_positive|Registry verifier rejects fabricated code references on a reused small panel. Independent references and simple lookup controls remain necessary.
005|measurement|Observable expert routing and repeated overlap support characterization, not causal expert specialization or SOC benefit.
006|data_blocked|OpTC window/host/day label readiness insufficient; not a negative model experiment.
007|no_advantage|Tested STGCN/GML remediation did not establish superiority or protected exfiltration benefit.
008|no_advantage|DAPT transfer negatives limit tested adaptation; distinct target domains remain untested.
009|no_advantage|Poisoning-trace AUC 0.5266 and zero trigger delta offer little tested effect; lower target does not create a defense.
010|measurement|Tiny circuit controls work; mini-transformer patch precision 0.7 and seed stability 0.4 limit recovery claim.
011|bounded_positive|Source-locked verifier macro-F1 0.9031 on constrained paired claims. Independent paraphrases, stronger controls and scope beyond structured pairs remain.
012|no_advantage|SSL positive/negative ordering 0.5227 is weak; no strong learned-representation result.
013|untested_extension|Temporal/hash proxy 0.5972 loses previous-event 0.6044. Full temporal graph network was not tested.
014|data_blocked|Provenance drift data span only 245 seconds and one source; cannot establish temporal generalization.
015|no_advantage|Strict TTC transfer 0.225 versus in-domain 0.725; distinct verifier-guided methods not tested.
016|conditional|Recall 0.8684 with safe blocking 0.0909 is a tradeoff, not a universally useful guardrail. A task-specific utility study could be valid.
017|data_blocked|VLA language/simulator prerequisites missing; no efficacy conclusion.
018|no_advantage|Evidence-plus-numeric hallucination F1 0.7215 loses response-only 0.7835.
019|untested_extension|Checksum/policy smoke test is not a learned world-model evaluation.
020|no_advantage|Stage router 0.5981 loses comparator 0.6313; stage prediction is bottleneck.
021|no_advantage|Rare-class gain 0.0049 accompanied by benign collapse; no useful joint gain shown.
022|measurement|Recovery diagnostic does not establish clean intervention benefit.
023|measurement|SAE reconstruction possible, but feature stability remains low and real-runtime interpretation unproven.
024|no_advantage|Broad-seed CTI training worsened; retain as negative antecedent to evidence routing.
025|no_advantage|Watermark detection 0.5217 does not support ownership detection.
026|measurement|Membership AUC 0.5599 confounded by time shift; privacy claim unresolved.
027|no_advantage|GraphSAGE loses cheap baseline in tested setting; does not refute every graph attribution application.
028|data_blocked|CTI fusion lacks dated outcomes; no efficacy test.
029|data_blocked|Graph-stage routing depends on qualified stage predictor.
030|data_blocked|Cross-detector robustness lacks stable detector families.
031|untested_extension|Causal GNN is a broad proposal without a qualified test.
032|data_blocked|Reverse TTP work lacks data/simulator.
033|no_advantage|SWE-EVO primary 1/5 versus metadata 0.8 with infrastructure failure; current implementation not competitive.
034|duplicate|Merged with PX-003; not independent corroboration.
035|conditional|Equal strict accuracy 0.0906 with 3.45% token saving is a modest bounded result; very low accuracy and stronger cheap comparator remain concerns.
036|untested_extension|World-model proposal deferred; no scientific negative.
037|untested_extension|Latent-loop gating deferred for architecture and measurement costs.
038|untested_extension|Circuit reward training lacks causal bridge.
039|untested_extension|FLAME-MoE extension not tested; do not count PX-005 routing as efficacy.
040|untested_extension|DP federated LoRA chain-of-thought proposal requires privacy and utility study.
041|data_blocked|Robotics quantization lacks qualified simulator/data.
042|data_blocked|Hospital ternary CLIP lacks qualified domain and privacy evaluation.
043|untested_extension|Multi-agent RL deferred; no measured effect.
044|roadmap|Survey/roadmap is not an experimental result.
045|untested_extension|Speech multimodal extension untested and outside current SOC focus.
046|data_blocked|Video proposal requires substantial dataset qualification.
047|untested_extension|3D proposal deferred for scope/compute, not refuted.
048|untested_extension|3D proposal deferred for scope/compute, not refuted.
049|invalid_measurement|No install actions and no baseline failure headroom; original harness could not test package defense.
050|measurement|Grammar-fixture gate positives do not establish agent safety; label qualification PX-069 and task controls PX-116 supersede broad claims.
051|conditional|Policy tradeoff on 288 tool rows depends on PX-050 label validity; not independent proof.
052|measurement|Perfect lineage recovery on explicitly constructed lineage is a prototype, not natural provenance validation.
053|untested_extension|Approval simulation lacks actual human completion/compromise outcomes.
054|measurement|Recurrent-depth geometry characterized; later PX-066 hazard discrimination fails.
055|bounded_positive|Latest R3 complete 9/9 cells, integrity pass: refusal geometry precision-invariant within registered scope; minimum directional ratio 0.975. Behavior relation descriptive across three models; restoration proxy not positive. Plausible characterization, not safety-restoration claim.
056|conditional|Model-registry nonexistent-identifier pilot and verifier feasible. Ambiguous identifiers, task completion and held-out simple registry controls remain.
057|no_advantage|Corrected 1119-case audit: adaptive 81.77% vs fixed-two 82.66%; adaptive saves fewer tokens (66.66% vs 76.58%). Not rescued by lower benefit target.
058|measurement|Explanation stability observed; drift-warning hypothesis failed. Bounded reliability evaluation remains possible.
059|untested_extension|Novelty-only closure too broad under applied standard. Speculative decoding application may be legitimate, but no measured target-workload advantage.
060|bounded_positive|Clean MSE improves 41.40%; edge direction unstable and 10% deletion increases MSE 143.44%. Prediction/interpretation boundary is a plausible empirical study.
061|conditional|Private adaptive noise 14.31% vs equal 12.89%: +1.42 pp, 4/5 seeds, below original 2 pp target. Reopen modest effect; low utility, uncertainty and stronger DP controls remain.
062|conditional|Authentic signed poisoning bypasses provenance. Later 1800-row existence/recovery study positive for Qwen, fails Mistral. Model-specific application possible, cross-model claim remains false.
063|invalid_measurement|Protocol 1.5: 517 rows, zero blocks, precision undefined; hacked recall genuinely 0/241. Reporting corrected to not evaluable, not a precision failure.
064|data_blocked|Environment/registry RL artifact not qualified for efficacy.
065|untested_extension|Memory provenance simulation readiness does not establish actual agent benefit.
066|no_advantage|Recurrent hazard classifier fails AUROC, worst balanced accuracy and safe FPR; geometry characterization does not rescue classifier.
067|no_advantage|No-op package repair works narrowly; PX-116 finds impossible versions accepted and unchanged 30/40 task completion.
068|bounded_positive|Source-compatibility CTI proposal must use later external/revised checker evidence; no general checker advantage. Related to PX-003, not independent success.
069|invalid_measurement|Parser repair reduces affected cases 147/4500 to 16/4500, but labels remain unqualified for broad gate claims.
070|verification_pending|Recurrent-depth router materials located; final outcome not reconciled. Do not infer efficacy from PX-054 or failure solely from PX-066.
071|verification_pending|Parser-free CTI materials include environmental blockage; use later CTI external evidence for related claims, not a fabricated completed run.
072|untested_extension|Abliteration-forensics source gate rescope; cross-format checkpoint evaluation untested. Prior art prevents generic first-detector claim, not applied robustness study.
080|no_advantage|Context selector improves movement recall but worsens FPR and weighted error in all five conditions.
081|conditional|Simulated acquisition cost reduced, but higher F1 can erase warnings; preserve stage/episode outcomes in any follow-up.
082|measurement|Time-mixed training improves F1 on identical anchors; diagnostic, not independent chronological generalization.
083|no_advantage|Context policy identical to cost-sensitive baseline on all 42 views.
084|data_blocked|No qualified all-class chronological cutoff; synthetic/clock-unqualified substitutes do not establish temporal APT validation.
085|no_advantage|Recalibration leaves exfiltration recall 67.33%; missing-class fallback warns on all 192193 cases.
086|measurement|Union improves flow recall at false-alarm cost, but PX-094 finds no extra proxy episodes; no demonstrated SOC case benefit.
087|bounded_positive|Same warning totals with modeled cost 1.0 to 0.9291 (7.09% reduction), almost unchanged macro-F1. Reopen applied efficiency; actual latency and independent incidents unmeasured.
088|conditional|Review-capacity tradeoffs simulated; no analyst performance study.
089|no_advantage|Warning recovery has substantial false-alert cost; no clear practical improvement shown.
090|measurement|Monotonic fitting alone does not prevent demotion; union veto does with more review burden.
091|data_blocked|Independent four-class/two-evidence data qualification failed, not model efficacy.
092|no_advantage|Union fails strict per-execution improvement; smaller flow benefit is different endpoint.
093|no_advantage|Heterogeneous extension does not rescue PX-092 with fixed workload denominator.
094|no_advantage|Union adds zero proxy episodes despite 1550/151 extra cases across sources.
095|measurement|Missed singleton episodes largely sparse endpoint/two-packet proxies without training support.
096|conditional|Post-hoc TCP22 overlay recovers source proxy episodes at 460-case cost; independent AIT does not transfer.
097|no_advantage|Independent AIT exfiltration uses UDP53; source TCP22 rule adds no coverage.
098|no_advantage|VLM images and text detect 0/8 diagnostic exfiltration windows; image arm adds false alert.
099|invalid_measurement|VLM smoke schema/context failure is not a valid efficacy comparison.
100|measurement|Verifiable warning-loss explanations support auditability; analyst benefit unmeasured.
101|measurement|Explanation stability characterization, not improved detection.
102|untested_extension|Human-review materials exist but no human study; may support SOC assistance proposal.
103|no_advantage|XAI restoration matches confidence cases; no extra AIT episodes. Simple baseline eliminates claimed added value.
104|no_advantage|Verifier/abstention controls work but ordinary calculator already correct; no added accuracy or human benefit.
105|no_advantage|Intervention replay ties full trace on 170 and 510 comparisons.
106|bounded_positive|Exact-class negative flips miss already-wrong-stage warnings erased by updates; meaningful evaluation-metric contribution, not improved detector.
107|data_blocked|All AIT episodes already warned; no XAI recovery headroom. Not a universal negative for XAI.
108|measurement|PCAP join qualification exposes ambiguity; not detector efficacy.
109|measurement|Most attack non-port53 UDP cannot be relabeled DNS; data correction preserved.
110|bounded_positive|Controlled DNS baseline detects 10/24 at 26 reviews, beats tested alternatives. Synthetic controlled transfer, not external APT efficacy.
111|no_advantage|Six XAI methods add 0-2 cases vs non-XAI 3 at same review budget.
112|conditional|Deferred explanation costs depend strongly on request volume; one timing measurement supports engineering follow-up, not general speedup.
113|no_advantage|Release gate rejects beneficial updates and passes declining one; no harmful-update test headroom.
114|conditional|Receipt verification ties self-judge 49 accepted/zero unsupported. Potential cost/latency benefit unmeasured.
115|invalid_measurement|Correct SHAP sidecars coexist with contradictory accepted prose; sidecar correctness is not semantic explanation correctness.
116|no_advantage|Package gates all 30/40 qualified completions; requirements-file coverage and impossible versions unresolved. Engineering repair possible, no added efficacy yet.
117|conditional|Cross-source binary AI signal confounded by source; later matched tests supersede optimistic operating point.
118|conditional|Masked-command signal promising only on exposed cross-source data; matched transfer remains weak.
119|measurement|Count normalization raises human errors 0/61 to 30/61; shortcut dependence demonstrated.
120|data_blocked|Ten-command allowlist leaves zero matched tasks; coverage failure, not evidence AI attribution impossible.
121|no_advantage|Short matched prefixes: agreement 19/24 AI with 3/11 human false flags; unreliable low-FPR claim.
122|measurement|Terminal replay improves extraction; fixture/audit validation does not create more independent experts.
123|conditional|Replayed matched InterCode development expands coverage; still small/calibration-sensitive and superseded by transfer evidence.
124|no_advantage|Longer transfer: ordinary classifiers false-flag 7-11/18 humans; agreement 13/51 AI, 1/18 human, 45/69 abstentions. No reliable detector demonstrated.
125|no_advantage|Response-conditioned features do not improve held-family behavior comparison; human error/action coverage sparse. Analyst assistance remains untested.'''
for line in notes.splitlines():
    num,category,note=line.split('|',2); key='PX-'+num
    records.setdefault(key,{'id':key,'title':key,'source':'cross-branch evidence index'})
    records[key].update(reassessment=category,decision=note)
names={66:'Recurrent-depth safety geometry hazard detection',68:'CTI source compatibility routing',70:'Recurrent-depth safety router',71:'Parser-free CTI evaluation',72:'Cross-format abliteration forensics',120:'Lyptus matched data coverage',121:'Short-prefix human/AI comparison',122:'Human terminal replay qualification',123:'Replayed matched InterCode comparison',124:'Longer-benchmark human/AI transfer',125:'Response-conditioned AI attribution'}
for n,title in names.items(): records[f'PX-{n:03}']['title']=title

extra='''FINAL-001|Outcome-state verification|conditional|Judge false accepts 7/200 vs verifier 0, but 205/400 schema failures. Qualified utility and matched controls remain.
FINAL-002|Cascade containment|bounded_positive|Compromise 10/60 to 0/60; clean task completion unchanged 51/60. Original 90% absolute floor failed. Reopen narrow containment with ordinary validation controls and held-out tasks.
FINAL-003|Adaptive investigation stopping|no_advantage|Accuracy 34.5% vs fixed-long 54.25%; premature stopping harms observed.
FINAL-004|Specialist revision|invalid_measurement|No valid correct revised candidates; preservation question not evaluable with this scaffold.
FINAL-005|Defense distillation|no_advantage|Tested erasure/replay arms over-refuse safe tasks; no useful defense advantage over parent established.
FINAL-006|Cognitive expert containment|invalid_measurement|Capability/format qualification fails; containment efficacy remains untested.
FINAL-007|Overthinking revision|no_advantage|Later closure supersedes positive pilot; both models fail registered recovery comparison.
FINAL-008|Selective executed-test evidence in code review|bounded_positive|Qwen harmful-patch acceptance 12/101 selected vs 4/101 uniform (+7.92 pp); second-model replication absent and defense no better. Plausible vulnerability/evaluation Praxis.
FINAL-009|SOUP streaming and prefetch|conditional|16/16 numerical trajectories match; prefetch 6.32% slower in tiny warm-cache test. Real I/O-bound memory-constrained application untested.
FINAL-010|Cross-channel forecasting attack/mitigation|no_advantage|Raw joint perturbations do not increase mean error in six tested settings; no attack harm to mitigate.
SUITE-APT-FINAL|Normal-only MAGIC and evidence joins|no_advantage|MAGIC 0/6 cases pass; ordinary exact join already correct or correctly abstains on all 60 questions. No selector headroom.
SUITE-CERT|Certificate alert checker|no_advantage|Checker decisions identical to score-only baseline. Original practical criterion unattainable from observed baseline: correct that judgment, but tie still gives no added benefit.
SUITE-APT-BENIGN|Normal-label allocation and lateral protection|bounded_positive|Normal FPR 10.04% to 0.40%, macro-F1 0.4421 to 0.6543; lateral any-attack recall 94.24% to 83.06%. Useful controlled tradeoff, no no-loss claim.
SUITE-APT-FUSION|APT stage-specialist fusion|bounded_positive|General+specialist average macro-F1 0.68407 vs general average 0.67487 (+0.92 pp) across three fits. Exposed flows; independent runs and stronger tuning remain.
SUITE-AI-FAMILY|AI-family fingerprints and logging fidelity|bounded_positive|AI-only held-environment lexical mean 89.82%, worst81.51; truncated32 retrained mean86.31%, worst80.49. Logging tradeoff plausible; not human/AI or real APT detection.
SUITE-PLANB|Attack evidence, log origin and temporal dependencies|verification_pending|Archived planning/qualification paths found; no reconciled completed efficacy result added to shortlist.'''
for line in extra.splitlines():
    key,title,category,note=line.split('|',3)
    records[key]={'id':key,'title':title,'reassessment':category,'decision':note,'source':'cross-branch evidence index'}

# Preserve the decision sources on this branch; leave bulky data/model archives in their original locations.
sources=[
('C:/Users/garyp/OneDrive/Documents/codex','reports/refusal_direction_quantization/e1_e4_20260831/closeout_r3/PX055_R3_INDEPENDENT_ADJUDICATION.json','quantization_r3.json'),
('C:/w/ai_operator_20261007','experiments/praxis_next/aivh_lyptus_20261007/FINDINGS.txt','ai_matched.txt'),
('C:/w/ai_operator_20261007','experiments/praxis_next/aivh_replay_20261007/FINDINGS.txt','ai_replay_transfer.txt'),
('C:/w/ai_operator_20261007','experiments/praxis_next/aivh_response_20261007/PRAXIS_DECISION.txt','ai_response.txt'),
('C:/w/px_final_20260917','final_praxis/002_cascade_containment/FINAL_DETERMINATION.md','cascade.txt'),
('C:/w/px_final_20260917','final_praxis/008_independent_evidence_audit/code_study/paper_package/FINAL_RESULTS_SUMMARY.md','selective_evidence.txt'),
('C:/w/cti_external_20260918','reports/cti_external_validation_20260918/RESULTS.json','cti_external.json'),
('C:/w/cti_external_20260918','reports/cti_checker_revision_20260918/RESULTS.json','cti_checker.json'),
('C:/w/p62g2','reports/coding_agent_skill_provenance/PX062_FINAL_DETERMINATION_20260727.md','skill_provenance.txt'),
('C:/w/p63rh','reports/reward_hack_trace/PX063_PROTOCOL_1_5_RESULT_AUDIT_20260726.md','reward_hack_audit.txt'),
('C:/w/px009','final_praxis/009_soup_streaming/RESULTS.md','soup.txt'),
('C:/Users/garyp/OneDrive/Documents/codex','reports/px057_novelty_review_20260918/EXPERIMENT_AUDIT.md','adaptive_stopping_audit.txt'),
(str(ROOT),'reports/wavelet_dp_federated_learning/PX061_FINAL_DETERMINATION_20260724.md','private_fl.txt'),
(str(ROOT),'experiments/praxis_next/warning_control_20260930/INTERPRETATION.md','warning_cost.txt'),
(str(ROOT),'experiments/apt_benchmark/results/exfil_stage_v1/REPORT.md','stage_fusion.txt'),
(str(ROOT),'experiments/apt_benchmark/results/strong_benign_controls_v1/REPORT.md','benign_support.txt'),
(str(ROOT),'experiments/apt_benchmark/results/lateral_protection_v1/REPORT.md','lateral_protection.txt'),
(str(ROOT),'experiments/apt_benchmark/lateral_protection_experiment/paper/FINDINGS_PRAXIS.md','lateral_synthesis.txt'),
(str(ROOT),'experiments/cert_gate/STATUS.json','certificate_status.json'),
(str(ROOT),'experiments/apt_final/CURRENT_RESEARCH_STATUS.json','apt_final_status.json'),
(str(ROOT),'experiments/praxis_next/defense_opportunities_20261007/FINDINGS.md','ai_logging.txt'),
]
evidence=[]; (OUT/'evidence').mkdir(exist_ok=True)
for work,rel,name in sources:
    source=Path(work)/rel
    if not source.is_file(): raise FileNotFoundError(source)
    data=source.read_bytes(); (OUT/'evidence'/name).write_bytes(data)
    commit=subprocess.check_output(['git','-C',work,'rev-parse','HEAD'],text=True).strip()
    tracked=subprocess.run(['git','-C',work,'ls-files','--error-unmatch',rel],capture_output=True).returncode==0
    dirty=subprocess.check_output(['git','-C',work,'status','--porcelain','--',rel],text=True).strip()
    evidence.append({'snapshot':'evidence/'+name,'original_path':rel,'source_checkout_head':commit,'source_tracked':tracked,'source_dirty':bool(dirty),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'original_url':f'https://github.com/garypagangit/praxis/blob/{commit}/{rel}' if tracked and not dirty else None})

rows=sorted(records.values(),key=lambda r:r['id'])
assert all('reassessment' in r for r in rows), [r['id'] for r in rows if 'reassessment' not in r]
assert len({r['id'] for r in rows})==len(rows)
payload={'date':'2026-10-09','method':'Retrospective record-level review plus focused decision-source reconciliation; no model reruns or independent peer review. Not a systematic literature review.','missing_number_range':'PX-073 through PX-079 not identified in inspected registries; not counted as failed experiments.','uncertainties':'PX-070, PX-071 and Plan B retain verification_pending; exhaustive recovery of every historical untracked file is not claimed.','records':rows}
(OUT/'INVENTORY.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
with (OUT/'INVENTORY.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['id','title','reassessment','decision','source']);w.writeheader();w.writerows({k:r.get(k,'') for k in w.fieldnames} for r in rows)
(OUT/'EVIDENCE_INDEX.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
counts={c:sum(r['reassessment']==c for r in rows) for c in sorted({r['reassessment'] for r in rows})}
checks={'records':len(rows),'px_records':sum(r['id'].startswith('PX-') for r in rows),'categories':counts,'snapshots':len(evidence),'snapshot_hashes_valid':all(hashlib.sha256((OUT/e['snapshot']).read_bytes()).hexdigest()==e['sha256'] for e in evidence),'arithmetic':{'cascade_compromise_reduction_pp':100*10/60,'cascade_clean_completion_pct':100*51/60,'selective_evidence_delta_pp':100*(12-4)/101,'private_fl_delta_pp':14.31-12.89,'warning_modeled_cost_reduction_pct':100*(1-.9291),'fusion_macro_f1_delta_pp':100*(.68407161-.67486795)}}
(OUT/'REVIEW_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
print(json.dumps(checks,indent=2))
