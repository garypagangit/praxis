import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/garyp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const root='C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_final_20260927';
const scratch='C:/Users/garyp/AppData/Local/Temp/codex-presentations/gwu-defense-20260927/tmp';
const out='C:/Users/garyp/OneDrive/Documents/codex/output/praxis_final_20260927';
const source='C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260927';
const data=JSON.parse(await fs.readFile(root+'/FULL_RELEASE_RESULTS.json','utf8'));
const sum=JSON.parse(await fs.readFile(root+'/SUMMARY.json','utf8'));
const fmt=n=>n.toLocaleString('en-US');
const slides=[];
function add(title,body,notes,citation='Praxis manuscript and evidence, September 27, 2026',image=null){slides.push({title,body,notes,citation,image});}
add('When Better APT Scores Hide Missed Attack Warnings',[],
'Opening: This praxis studies how to evaluate an APT stage classifier before accepting a higher headline score. The contribution is controlled measurement and an executable review procedure. It does not claim a new detector architecture. Today I will connect the research problem, experimental controls, observed tradeoffs, full-release extension and limits of the resulting claim. This is the completed computational manuscript and defense review edition; committee approval, defense scheduling and degree certification are not asserted.');
add('A better score can hide a lost warning',[
'A wrong attack stage can still trigger review.',
'A benign prediction can suppress that warning.',
'Macro-F1 alone does not describe this difference.',
'Warning recall must be read with benign false alerts.'
],'Illustration, not an experimental result: among 100 exfiltration-labeled flows, 60 correct stage predictions plus 20 predictions of another attack stage give 60% exact-stage recall and 80% warning recall. Calling all flows attacks would preserve every warning but create excessive workload. Therefore neither stage recognition nor warning retention alone is enough. The measured outcome is a non-benign model label, not a real analyst response. Uddin and colleagues already distinguish attacks called normal from wrong attack types.','Chapter 1; Uddin et al. (2025)');
add('Problem, purpose and thesis',[
'Problem: score improvements can conceal missed stage warnings.',
'Purpose: expose the tradeoff on the same evaluation records.',
'Thesis: review score, warning loss and false alerts together.',
'A valid comparison also needs credible labels and chronology.'
],'The engineering decision is whether to accept a proposed model or evidence change. This study makes the consequences visible rather than optimizing an isolated score. The thesis is empirical: it is supported by saved paired predictions, fixed evaluation populations and transparent sensitivity checks. Dataset qualification matters because a chronological experiment is not meaningful if the source clock or class coverage cannot support it. The contribution is deliberately bounded to the inspected author labels and completed network flows.','Chapter 1, Sections 1.3–1.4');
add('Three research questions',[
'RQ1: When score improves, what happens to warnings and false alerts?',
'RQ2: How much does later-period training access change a fixed-anchor score?',
'RQ3: Which proposed releases support the unchanged chronological task?',
'Warning-loss analysis is retrospective; it is not preregistered.'
],'RQ1 is the primary question. RQ2 holds the evaluation anchor, architecture and per-class fitting counts fixed while changing training composition. RQ3 tests necessary conditions for the declared all-native-class chronological comparison. Fitted historical experiments had frozen protocols, but the warning-loss interpretation was inspected afterward. I therefore call these analytical propositions, not retrospectively preregistered hypotheses. The new full-release role-feature protocol was frozen before its own fitting jobs.','Chapter 1, Section 1.6; FULL_RELEASE_PROTOCOL.json');
add('The applied contribution',[
'Paired evidence of higher F1 with fewer exfiltration warnings.',
'A fixed-anchor training-composition contrast.',
'An executable dataset-qualification and model-review record.',
'Full-release coverage with uncapped training for a new role-feature contrast.'
],'Novelty is the specific assembled controlled evidence and reproducible applied procedure. Temporal validation, wrong-stage versus benign errors, contextual features and gradient boosting all have substantial prior art. The contribution does not depend on inventing a new metric or architecture. The full-release extension directly addresses two practical review questions: whether every upstream flow file was accounted for, and whether the new comparison trains on all eligible observations. It does not replace the population of the historical acquisition experiment.','Chapters 2 and 5; Section 4.10');
add('What the closest work already establishes',[
'TESSERACT: temporal and distribution constraints.',
'Bilot / Guerra: practical and benchmark validity in APT evaluation.',
'Uddin: wrong attack type versus attack called normal.',
'This study: a controlled flow-stage tradeoff and traceable audit.'
],'Pendlebury et al. (2019), TESSERACT, USENIX Security: https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury. Bilot et al. (2025), Sometimes Simpler Is Better: https://www.usenix.org/conference/usenixsecurity25/presentation/bilot. Guerra et al. (2026), preprint version 3: https://arxiv.org/abs/2608.01454v3. The manuscript references and literature audit distinguish the accessible Uddin author manuscript from its 2025 journal record. This is a targeted review, not an exhaustive priority search. Do not state that no one previously considered warning retention.','Chapter 2; complete primary-source references in paper');
add('The evidence has three different scopes',[
'Original controlled study: 11 complete sensor files; 382,229 source rows.',
'Full-release extension: 173 files; 6,877,157 rows; six sensor views.',
'External source qualification: eligibility findings, not fitted replications.',
'All UNRAVELED sensor views still describe one exposed campaign.'
],'These denominators must remain distinct. Original training, calibration and testing derive from the prepared eleven-file artifact. The new extension audits all released files and fits a current versus current-plus-roles comparison separately by sensor. More sensor observations are not more independent campaigns. The separately inspected SCVIC, DAPT, DSRL and S-DAPT sources do not qualify automatically as replications. The Casino/CAM technique supplement addresses a different target and different negatives.','Sections 1.7, 3.11 and 4.10; source inventory');
add('Graphical model of the research',[],
'Walk from the applied evaluation problem through three evidence branches: contextual evidence decisions, fixed-anchor training composition, and source qualification. The outputs join in a report of exact-stage recognition, warning retention and benign workload. The historical GMR is retained in the appendix for provenance. The September 27 full-release extension belongs to the coverage and model-review branch: it broadens row coverage and removes fitting caps for its declared role comparison. It does not alter the original research questions or introduce a forecasting claim.','Chapter 3, GMR; extension in Section 3.11',source+'/figures/gmr_current.png');
add('Controls that make the comparisons useful',[
'Compare the same evaluation rows within each paired contrast.',
'Keep architecture and class budgets fixed in the temporal contrast.',
'Freeze decisions before evaluating later test observations.',
'Retain adverse conditions, seed variation and source limitations.'
],'Fixed rows prevent a score change from being explained merely by a different evaluation population. The fixed-anchor experiment still changes composition and diversity when it permits later observations, so time is not isolated from all other distributional effects. The original history/acquisition interventions include synthetic missing, delayed and wrong-host evidence; these are stress conditions, not estimated production incident rates. The new extension freezes calibration choices before their test evaluation.','Chapter 3; historical protocols; FULL_RELEASE_PROTOCOL.json');
add('Models are tools for the measurement',[
'Historical core: 141 LightGBM fitting jobs.',
'Policy-transfer supplement: two Ridge selector fits.',
'New extension: 12 deterministic sensor/arm fitting jobs.',
'One-class jobs are constant controls, not learned multiclass detectors.'
],'The total recorded fitting-job inventory is 155, but this is not a count of independent attacks or successful multiclass detectors. Historical boosting models include classifiers and selection regressors; Chapter 3 and the model inventory specify their different objectives. The two-fit supplement uses Ridge selectors over previously fitted logistic-regression experts. No large language model, graph neural network or new deep architecture was fitted for this measurement contribution. The extension uses 300 LightGBM boosting iterations, 15 leaves, learning rate .05 and all eligible training rows.','Model inventory; Sections 3.7–3.11');
add('Read the score and the error destination',[
'Macro-F1: average of declared class F1 scores.',
'Exact-stage recall: correct stage / true stage records.',
'Warning recall: any attack prediction / true stage records.',
'False-alert rate: benign records called attack / benign records.'
],'Warning recall for stage k is one minus the benign-prediction fraction among true stage-k observations. Its denominator differs from false-alert rate. Per-class precision, ROC AUC, average precision and complete confusion matrices are also retained. The extension fixes macro-F1 to four labels with zero for absent labels; a perfect benign-only control therefore scores .25. Cross-sensor headline comparisons are not equivalent tasks when stage support differs. Unsupported recall is unavailable, not zero or perfect.','Chapter 3 metrics; Appendix D');
add('Higher F1, fewer exfiltration warnings',[],
'This is the main clean acquisition comparison at the largest registered budget, using identical test rows. Across three fits, macro-F1 rises from .7148 to .7379 while exfiltration warning recall falls from 85.18% to 76.25%, a decline of 8.93 percentage points. The warning denominator is 3,442 exfiltration-labeled rows. These are means across fits, not pooled independent observations. Read the complete benign-workload and adverse-condition results in Table 3 and the machine-readable supplement before choosing a policy. The next slide shows why the magnitude must be qualified.','Chapter 4, acquisition results; Table 3',source+'/figures/defense_main_result.png');
add('The warning-loss size is seed-sensitive',[],
'The specified mean warning-loss direction survives every single-seed and single-capture omission in the retrospective analysis, but its size is highly sensitive. Omitting seed 8101 reduces the clean largest-budget loss from about 8.93 to about .36 percentage point. This is evidence against presenting 8.93 points as a stable deployment effect. Capture fragments share a workflow; resampling them does not estimate uncertainty across independent campaigns. The defense claim is that the observed tradeoff can occur and should be made visible, not that a universal effect size has been estimated.','Chapter 4 seed/capture sensitivity; original sensitivity evidence',source+'/figures/defense_seed.png');
add('Training composition changes the score',[
'The evaluation anchor stays fixed at 104,051 rows.',
'Architecture and per-class fitting counts stay fixed.',
'Allowing later observations increases mean macro-F1 by 0.0632.',
'The contrast measures composition/access sensitivity, not pure time causality.'
],'The same-anchor design is a control against evaluation-population shifts. The anchor includes 96,098 benign rows and only 18 movement-author-label rows. Permitting later observations changes composition and diversity even with equal class-specific counts. Random-row evaluations have a different denominator and are therefore reported separately rather than subtracted as a clean paired temporal effect. This result supports temporal hygiene but does not quantify an isolated causal effect of chronology.','Chapter 4, temporal results; Table 2');
add('History can help and still lose warnings',[
'Chronological macro-F1: 0.7365 → 0.7582.',
'Mean benign false alerts: 24.0 → 14.3.',
'A smaller stage-warning loss remains visible.',
'The joint report exposes benefits and costs together.'
],'This example prevents an oversimplified conclusion that context is bad. History improved the aggregate score and reduced benign workload in the chronological comparison, while a smaller warning loss remained. False-alert counts use the same benign denominator within this comparison. The complete stage metrics and three-fit means are in the paper. A practitioner must judge whether the warning change is acceptable in the intended use; these experiments do not estimate analyst response or actual incident outcomes.','Chapter 4 chronological-history results');
add('Full release: frozen before new fitting',[
'All 173 files verified against source hashes and native counts.',
'Train: before June 27; calibrate: June 27; test: June 28 onward, UTC.',
'Every eligible training row; current versus current + roles.',
'Duplicates, label conflicts and cutoff-crossing flows accounted for.'
],'The exact date logic uses flow start and completion: training completion precedes June 27; calibration starts June 27 or later and completes before June 28; testing starts June 28 or later. Boundary-crossing flows are excluded. Observable identity includes endpoints, timestamps and current numeric measurements; exact consistent copies are deduplicated and conflicting labels quarantined. Numeric fields come from the stable prefix and annotation fields from the right edge because unquoted commas can shift application fields. The correction for one-class probability alignment changes implementation, not the protocol.','Section 3.11; FULL_RELEASE_PROTOCOL.json');
add('Every released flow row is accounted for',[],
`There are ${fmt(sum.raw_rows)} source rows across six sensor views. After declared handling, the extension has ${fmt(sum.train)} training, ${fmt(sum.calibration)} calibration and ${fmt(sum.test)} test rows. It removes ${fmt(sum.duplicate)} exact duplicates, quarantines ${fmt(sum.conflict)} conflicting-label rows and excludes ${fmt(sum.boundary)} cutoff-crossing rows. Training is uncapped for each declared arm. These are sensor observation counts, not deduplicated cross-network events or independent incidents. The evidence includes all 173 source-file hashes and row counts.`,'Section 4.10; per-sensor PREPARATION.json',source+'/figures/defense_coverage.png');
add('Full-release results retain support limits',[],
`Roles increase test macro-F1 in ${sum.improved_sensor_count} of six sensor views. Views with an F1 increase and a warning-recall decline for at least one supported attack stage: ${sum.warning_reversal_sensors.join(', ')||'none'}. Single-class training sensors: ${sum.single_class_sensors.join(', ')||'none'}. Sensors with all four classes in both train and test: ${sum.all_four_train_test_sensors.join(', ')||'none'}. The fixed four-class macro-F1 denominator gives absent classes zero; read class support before interpreting a bar. This new role-feature comparison does not rerun historical acquisition interventions.`,'Section 4.10; FULL_RELEASE_RESULTS.json; Appendix D',source+'/figures/defense_full_results.png');
add('An executable calibration review',[
'Score-only choice: select higher calibration macro-F1.',
'Review choice: also constrain stage-warning loss and benign FPR.',
'Freeze the choice, then evaluate the same later test rows.',
'All six views lack at least one attack stage in calibration.'
],'The example allows roles only when calibration macro-F1 increases, each supported attack-stage warning recall loses no more than one percentage point and benign false-positive rate rises no more than 0.1 percentage point. Ties favor current flow. These thresholds were frozen for this computational illustration; they are not learned operational preferences. Missing classes make review provisional. A calibration constraint cannot guarantee test behavior. The evidence stores both selected test outcomes, with no retuning on test. Read the per-sensor choices in Table 10.','Sections 3.11 and 4.10; calibration_selection records');
add('Why another dataset name is not enough',[
'SCVIC: inspected clock fields did not qualify.',
'DAPT: only 15 exfiltration rows and stage/time support constraints.',
'DSRL: DAPT-derived synthetic construction limits independence.',
'S-DAPT: withdrawn record; no qualified acquired replacement.'
],'These are eligibility conclusions for the unchanged all-native-class chronological classifier comparison. They do not declare the datasets useless for every task. The support interval tests whether a single cutoff can put the required native classes in both earlier training and later testing. DAPT can support different session timing or survival questions. CAM-LDS and Casino supply technique contexts but do not provide the same native benign-versus-exfiltration flow target. A full-release expansion of UNRAVELED addresses coverage, while independent-campaign replication remains unmeasured.','Chapter 4 qualification results; Table 5');
add('Limits that bound the claim',[
'One exposed campaign; sensors and capture fragments are dependent.',
'Author-stage labels do not verify compromise or stolen-file receipt.',
'Completed-flow features do not establish early forecasting.',
'No analyst trial, production benefit or independent-campaign replication.'
],'The original movement target is author-annotated remote discovery on a narrow host pair, with only 35 evaluation rows. In the full release, retain the native movement label without claiming every sensor means the same operational action. The warning analysis is retrospective. Simulated evidence failures are controlled conditions rather than estimated real failure distributions. Prior exposure prevents presenting the expanded source as a fresh external benchmark. These limitations are part of the defended claim, not hidden in an appendix.','Chapter 5 validity; Appendix D support tables');
add('The deliverable is reviewable evidence',[
'Final manuscript, references, equations and full result appendices.',
'Frozen full-release protocol and per-sensor source accounting.',
'Saved models and every new calibration/test prediction.',
'Independent count checks, hashes and reproduction instructions.'
],'The original paper verification rechecked 120 pages, 30 references, 588 configuration records and 308 printed group means before extension. The new audit independently recomputes confusion counts, warning outcomes and macro-F1 from prediction files, and verifies population alignment and temporal separation. The local evidence bundle includes prepared arrays and source bindings; raw flow CSVs remain in the pinned local source directory. Hash identity establishes bytes, not label truth. Same-team computational verification is not external peer review or committee approval.','Evidence package README, manifests and FULL_RELEASE_AUDIT.json');
add('The next study has a specific purpose',[
'Independent execution with legitimate background traffic.',
'Reliable event clocks and native stage labels.',
'Freeze the joint report and selection rule before evaluation.',
'Then test whether the report improves real review decisions.'
],'Independent execution would test recurrence and magnitude of the warning tradeoff beyond this campaign. A meaningful external test needs a different workflow, sufficient native class support and legitimate background traffic for false-alert measurement. An analyst study is a separate next step with real users, an explicit decision task and a comparison design. Neither is necessary to report the completed bounded computational observation, but both are necessary for stronger generalization and operational-benefit claims. Committee expectations about scope remain an academic decision.','Chapter 5, Section 5.5');
add('Defensible conclusion',[
'Higher macro-F1 did not ensure preserved exfiltration warnings.',
'The effect size is sensitive to fitting seed and shared workflow.',
'Full-release coverage strengthens the declared role comparison.',
'Accept a model change only with a joint, source-qualified report.'
],'Close with the precise claim. On these inspected records, a higher score coexisted with fewer non-benign predictions for exfiltration-labeled flows. The work supplies paired evidence, a fixed-anchor sensitivity contrast, qualification logic and an executable review record. It does not claim universal warning loss, a production detector or a population effect across APT campaigns. The full-release extension resolves source coverage and fitting caps for its declared comparison while retaining support limitations. Invite questions. Slides 25–32 are technical backups.','Chapter 5 conclusions; technical backups follow');
add('Backup: original denominators',[
'Training: 147,087 benign; 12,362 other; 27 movement; 1,740 exfil.',
'Calibration: 8,929 benign; 2,659 other; 0 movement; 1,331 exfil.',
'Test: 192,193 benign; 12,424 other; 35 movement; 3,442 exfil.',
'Temporal anchor: 104,051 rows; 18 movement-author-label rows.'
],'These are original prepared-artifact split populations, before the historical per-class fitting caps. They sum to 382,229 rows across the eleven complete sensor files. Do not substitute the full-release counts into historical metric denominators. The absence of movement in calibration is a practical support limitation. The expanded extension has its own deduplication, chronology and class support recorded in Appendix D.','Original data inventory; Chapters 3–4');
add('Backup: warning accounting',[
'For true stage k: count benign, wrong-stage and correct-stage predictions.',
'Warning recall = 1 − benign predictions / stage-k support.',
'Exact recall = correct-stage predictions / stage-k support.',
'No support means unavailable recall; include the confusion matrix.'
],'This formula is stage-conditioned binary attack recall and is not proposed as a novel metric. Warning recall equals exact-stage recall plus the fraction sent to another attack stage. It says nothing about alert deduplication, analyst attention, response time or successful remediation. Benign workload is a separate conditional rate and must be shown alongside it. Saved full confusion matrices allow a reviewer to recompute every count and understand which error destination changed.','Chapter 3; metric definitions and audit script');
add('Backup: full-release class support',data.sensors.map(s=>`${s.sensor}: train [${s.preparation.split_counts.train.join(', ')}]`),
'Vectors follow the fixed order benign, other attack stage, movement author label, exfiltration author label. These are complete eligible training counts after duplicate and boundary handling. Full calibration and test vectors appear in Appendix D. All-zero attack support means a sensor cannot learn those classes under the frozen cutoff; changing the cutoff after results would change the question. The machine-readable preparation records preserve every file and every native-stage source count.','Appendix D; PREPARATION.json');
add('Backup: roles and prediction inputs',[
'Stable numeric current-flow fields; no absolute timestamps or raw endpoint IDs.',
'Three destination-service indicators in both arms.',
'Roles arm adds eight coarse endpoint-topology indicators.',
'No future history or sensor ID enters either arm.'
],'The role function maps selected topology subnets into four categories per endpoint; unknown/other is not synonymous with Internet. Ports inform three coarse service flags but raw numeric ports are excluded. Timestamps and endpoints participate in the duplicate identity and split verification but are not direct predictor columns. The source feature list is in each PREPARATION.json. This is an explicit contextual-feature ablation under one campaign topology, so transfer across networks is not established.','Section 3.11; full_release.py; feature lists');
add('Backup: fitting and uncertainty',[
'Extension: 300 boosting iterations; 15 leaves; learning rate 0.05; L2 = 1.',
'Minimum child support 10; deterministic seed 20260927.',
'One fit per sensor/arm; no new campaign confidence interval.',
'Historical seed and capture omissions describe conditional sensitivity.'
],'Every eligible training row enters each extension arm; there is no class cap or sampling weight. A single deterministic fit cannot estimate seed variability. The historical study has its own multiple-fit sensitivity and correlated capture resampling. It is misleading to treat millions of dependent flow records as millions of independent campaign trials. The number of jobs counts executed fits, with one-class jobs marked degenerate rather than credited as successful multiclass learning.','FULL_RELEASE_PROTOCOL.json; historical sensitivity audit');
add('Backup: calibration choices',data.sensors.map(s=>`${s.sensor}: score → ${s.calibration_selection.f1_choice==='current_roles'?'roles':'current'}; review → ${s.calibration_selection.review_choice==='current_roles'?'roles':'current'}`),
'Each choice is made using calibration only and tested on the corresponding fixed later population. Read missing-stage flags alongside the choices. A score tie favors current flow. A review tie or constraint failure also favors current flow. Equal choices do not prove the review procedure adds operational benefit; they may show that the observed candidates do not trigger its veto. The evidence records both selected test metrics so this result remains inspectable, including a failure to produce a different decision.','Table 10; calibration_selection records');
add('Backup: closest primary sources',[
'Pendlebury et al. (2019), TESSERACT, USENIX Security.',
'Bilot et al. (2025), Sometimes Simpler Is Better, USENIX Security.',
'Guerra et al. (2026), benchmark/protocol study, preprint v3.',
'Myneni et al. (2023), UNRAVELED source release.'
],'Primary URLs: https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury ; https://www.usenix.org/conference/usenixsecurity25/presentation/bilot ; https://arxiv.org/abs/2608.01454v3 ; https://gitlab.com/asu22/unraveled . The full manuscript contains 30 references with the retrieved version and scope audit. Guerra is cited as an available preprint, not as a future conference proceeding already published. Scores from unrelated papers are not presented as reproduced baselines.','Complete APA references and reference audit in paper');
add('Backup: likely committee questions',[
'Novelty? The controlled applied evidence and reproducible review procedure.',
'Full dataset? Every released flow file; uncapped fitting for the new contrast.',
'Independent validation? No; the claim remains one-campaign measurement.',
'Ready to defend? Computational artifacts complete; academic approval remains.'
],'If asked whether another dataset is mandatory, explain the scope tradeoff rather than guarantee a committee decision. The bounded observation and its audit can be defended on these data; a claim of generalizable operational improvement would require evidence not provided here. If asked why not a new architecture, explain that model novelty does not solve the measurement problem. If asked whether all historical models were retrained on the expanded release, answer no: historical controlled findings retain their original population, and the full-release role-feature contrast is separately declared.');
if(slides.length!==32)throw Error('slide count');
const tableNumbers={'2':'4-5','3':'4-1','5':'4-8','10':'4-14'};
slides[8].title='Controls for a valid comparison';
slides[11].notes+=' The policies are entropy acquisition and error-focused acquisition, both at budget three. Mean benign false alerts increase from 111.3 to 122.3 on the same 192,193 benign records.';
slides[26].citation='Order: benign, other, movement, exfiltration | Appendix D';
slides[17].citation='Unequal class support across sensors | Section 4.10 and Appendix D';
slides[17].notes+=' At the gateway, F1 changes only from 0.49909446 to 0.49911102, with one fewer benign false alert and one more OtherAttackStage warning missed: 25,429 to 25,430 out of 26,712. This tiny change does not establish practical significance or a stable replicated effect. The principal sensor slightly improves both F1 and exfiltration warnings.';
for(const s of slides)for(const key of ['notes','citation'])s[key]=s[key].replace(/\bTable (10|2|3|5)\b(?![-.][0-9])/g,(_,n)=>'Table '+tableNumbers[n]);
await fs.mkdir(out,{recursive:true});await fs.mkdir(scratch+'/final-render',{recursive:true});
await fs.writeFile(root+'/DEFENSE_CONTENT.json',JSON.stringify(slides,null,2));
const pres=await PresentationFile.importPptx(await FileBlob.load(scratch+'/starter.pptx'));
const inspected=await pres.inspect({kind:'slide,textbox,shape',maxChars:500000});
await fs.writeFile(scratch+'/before.ndjson',inspected.ndjson);
const objects=inspected.ndjson.split(/\r?\n/).filter(Boolean).map(x=>JSON.parse(x));
for(let i=0;i<32;i++){
 const slide=pres.slides.items[i],c=slides[i];
 const shapes=objects.filter(o=>o.slide===i+1&&o.kind==='textbox');
 const title=shapes.find(o=>o.placeholder==='title'||o.name?.toLowerCase().includes('title')&&!o.name?.toLowerCase().includes('subtitle'));
 if(!title)throw Error('title '+i);
 const t=slide.shapes.getById(i===0?'2':'3');t.text=c.title;t.text.style={typeface:'Arial',fontSize:i===0?42:40,bold:true,color:i===0?'#FFFFFF':'#033c5a'};
 if(i===0){
  for(const o of shapes.filter(o=>o.id!==title.id)){
   const sh=slide.shapes.getById(o.bbox[0]<500?'3':'4');sh.text=o.bbox[0]<500?'Gary Pagan\nDoctor of Engineering\nPraxis Defense':'Computational review edition\nSeptember 27, 2026';sh.text.style={typeface:'Arial',fontSize:25.33,color:'#FFFFFF'};
  }
 }else{
  const b=slide.shapes.getById('2');
  b.text=c.image?'':c.body.map(line=>({runs:[line],bulletCharacter:'•',marginLeft:22,indent:-17,spaceAfter:18}));
  b.text.style={typeface:'Arial',fontSize:29.33,color:'#727272',verticalAlignment:'top'};
  if(c.image)b.delete();
  if(i===7){
   const steps=[['1. Qualify\nsources',65,155],['2. Prepare\nchronological data',350,155],['3. Fit controlled\ncomparisons',635,155],['4. Record error\ndestinations',635,355],['5. Check sensitivity\nand scope',350,355],['6. Deliver\nreviewable evidence',65,355]];
   for(const [txt,left,top] of steps){const sh=slide.shapes.add({geometry:'textbox',name:'Research workflow step',position:{left,top,width:245,height:100},fill:'none',line:{fill:'none',width:0}});sh.text=txt;sh.text.style={typeface:'Arial',fontSize:29.33,bold:true,color:'#007cab',alignment:'center'};}
   for(const [txt,left,top] of [['→',307,185],['→',592,185],['↓',745,280],['←',592,385],['←',307,385]]){const sh=slide.shapes.add({geometry:'textbox',name:'Workflow direction',position:{left,top,width:42,height:50},fill:'none',line:{fill:'none',width:0}});sh.text=txt;sh.text.style={typeface:'Arial',fontSize:32,color:'#727272'};}
  }else if(c.image)slide.images.add({blob:new Uint8Array(await fs.readFile(c.image)),contentType:'image/png',alt:c.title,fit:'contain',position:{left:49,top:115,width:862,height:430}});
  const footer=slide.shapes.add({geometry:'textbox',name:'Evidence source',position:{left:49,top:548,width:850,height:27},fill:'none',line:{fill:'none',width:0}});footer.text=`${String(i+1).padStart(2,'0')}  |  ${c.citation}`;footer.text.style={typeface:'Arial',fontSize:15,color:'#5a6873'};
 }
 slide.speakerNotes.clear();slide.speakerNotes.textFrame.setText(c.notes+'\n\nEvidence: '+c.citation+'\nAuthoring support: AI-assisted artifact preparation and computational checks; author review is required under applicable GWU policy.');
 const stem=`slide-${String(i+1).padStart(2,'0')}`;
 const png=await pres.export({slide,format:'png',scale:1.3});await fs.writeFile(scratch+'/final-render/'+stem+'.png',new Uint8Array(await png.arrayBuffer()));
 const layout=await slide.export({format:'layout'});await fs.writeFile(scratch+'/final-render/'+stem+'.json',await layout.text());
}
const pptx=await PresentationFile.exportPptx(pres);await pptx.save(out+'/Gary_Pagan_GWU_Praxis_Defense.pptx');
await fs.writeFile(out+'/Defense_Speaker_Notes.txt',slides.map((s,i)=>`SLIDE ${i+1}: ${s.title}\n\n${s.notes}\n\nSOURCE: ${s.citation}`).join('\n\n'+'='.repeat(60)+'\n\n'));
console.log(JSON.stringify({slides:32,mainSlides:24,backups:8,path:out+'/Gary_Pagan_GWU_Praxis_Defense.pptx'}));
