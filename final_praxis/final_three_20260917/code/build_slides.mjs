import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation, PresentationFile, layers, text, shape} from '@oai/artifact-tool';

// Codex Grid adaptations: 64 chart/evidence, 72 metric columns, 34 result table.
// CSS pixels at 96 dpi. All titles 48px (36pt), body >=22px (16.5pt).
const root=process.argv[2];
if (!root) throw new Error('Usage: node build_slides.mjs ABSOLUTE_CLOSURE_DIRECTORY');
const here=path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/,'$1'));
const summaries=await Promise.all(['01_cti','02_008','03_010'].map(d=>fs.readFile(`${root}/${d}/slide_summary.json`,'utf8').then(JSON.parse)));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const frames=[];
const T=(name,s,x,y,w,h,size=24,bold=false,color='#222222')=>{frames.push({slide:p.slides.items.length,name,left:x,top:y,width:w,height:h,fontSize:size});return text([s],{name,position:{left:x,top:y},width:w,height:h,style:{fontFamily:'Arial',fontSize:size,color,bold,verticalAlignment:'middle'}})};
const rule=(y)=>shape({name:'Divider',geometry:'rect',position:{left:56,top:y},width:1168,height:1,fill:'#C9C9C9'});
function compose(s,children){s.background.fill='#FFFFFF';s.compose(layers({width:'fill',height:'fill'},children),{frame:{left:0,top:0,width:1280,height:720},baseUnit:1});}
const foot=(source,n)=>[rule(658),T('Sources',source,56,672,1100,28,22,false,'#555555'),T('Page',String(n),1192,672,32,28,22,false,'#555555')];
const git='https://github.com/garypagangit/praxis/tree/Final-Praxis-Three-Closure-20260917/final_praxis/final_three_20260917/';

{
const s=p.slides.add();
compose(s,[
 T('Title','CTI: gains depend on source compatibility',56,36,1168,112,48,true),
 T('Setup','2,500 questions · two fixed models · paired accuracy changes',56,146,1168,48,32),
 T('Chart label','Change versus vanilla, percentage points',56,211,750,36,24),
 T('Chart legend','Llama (black) · Qwen (gray)',56,250,750,32,22),
 T('Category 1','Source-known\neligible',130,531,205,52,22),
 T('Category 2','Query-only\neligible',360,531,205,52,22),
 T('Category 3','Query-only\nmismatch',587,531,205,52,22),
 T('Router label','External router',850,230,374,46,32,true),
 T('Router precision','46.26%',850,281,374,84,68,true),
 T('Router explanation','precision on 2,997 questions\n52.53% false-positive rate',850,371,374,76,24),
 T('Router outcome','Confirmation failed',850,476,374,76,32,true),
 T('Limitations','Limits: source-known access advantage; 500 prior-exposed items; options visible.',56,603,1168,42,24),
 ...foot('CTI evidence C03–C07 · Intervals and sources in paper / speaker notes',1)
]);
s.charts.add('bar',{
 position:{left:56,top:286,width:750,height:235},
 categories:['Source-known\neligible','Query-only\neligible','Query-only\nmismatch'],
 series:summaries[0].chart.series.map((v,i)=>({name:v.name,values:v.values.map(x=>Number(x.toFixed(2))),valuesFormatCode:'0.00',fill:i?'#919191':'#111111',dataLabelOverrides:v.values.map((x,idx)=>({idx,text:x.toFixed(2),showValue:true,position:'outEnd',textStyle:{fontSize:22,fill:'#111111'}}))})),
 barOptions:{direction:'column',grouping:'clustered',gapWidth:125},
 hasLegend:false,
 xAxis:{visible:false,tickLabelPosition:'none'},
 yAxis:{min:-25,max:30,majorUnit:10,numberFormatCode:'0',textStyle:{fontSize:22,fill:'#444444'},majorGridlines:{fill:'#DDDDDD',width:1}},
 dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:22,fill:'#111111'}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'
});
s.speakerNotes.textFrame.setText(`CTI — completed bounded empirical study; human academic review pending.\nAll effects are paired parser-accuracy percentage-point differences versus matching vanilla. Eligible n=1578; mismatch n=922. Source-known Llama +23.06717, Qwen +19.58175; query-only eligible +18.18758/+13.87833; mismatch -14.96746/-17.46204. Question units=2500; 40000 records include repeated conditions and are not independent n. CIs and exact gates are in PAPER/EVIDENCE. External router precision904/1954; FPR1050/1999; confirmation failed. External format defects limit efficacy interpretation. Prior exposure of500items and answer-option access remain limitations.\nEvidence: ${git}01_cti/EVIDENCE.json\nPaper: ${git}01_cti/PAPER.md\nPrimary prior work:\n${summaries[0].primary_citations.map(x=>x.label+' '+x.url).join('\n')}\nPrepared17September2026 with AI assistance; no human approval inferred.`);
}
{
const s=p.slides.add();
compose(s,[
 T('Title','008: selected disclosure changed decisions',56,36,1168,112,48,true),
 T('Setup','101 paired harmful revisions · schema-constrained Qwen',56,146,1168,48,32),
 T('Uniform label','Uniform disclosure',56,233,363,45,32,true),
 T('Uniform metric','4 / 101',56,286,363,105,80,true),
 T('Uniform detail','harmful revisions accepted\n3.96% of paired tasks',56,396,363,76,24),
 T('Selected label','Selected disclosure',466,233,363,45,32,true),
 T('Selected metric','12 / 101',466,286,363,105,80,true),
 T('Selected detail','harmful revisions accepted\n11.88% of paired tasks',466,396,363,76,24),
 T('Change label','Paired increase',876,233,348,45,32,true),
 T('Change metric','+7.92 pp',876,286,348,105,64,true),
 T('Change detail','95% CI: 2.97–13.86 pp\nHolm-adjusted p = .015625',876,396,348,76,24),
 rule(501),
 T('Mechanism','8 selected-only acceptances: 7 omit failures; 2 of those disclose no tests.',56,520,1168,55,26),
 T('Limits','Compound intervention. Devstral effect unsupported; hybrid defense gates failed.',56,591,1168,53,24),
 ...foot('008 evidence E07–E09 · Paired task bootstrap; four-test Holm family',2)
]);
s.speakerNotes.textFrame.setText(`008 — completed bounded empirical study; human academic review pending.\nThe comparison is UNIFORM versus selected passing-only disclosure, not all acquired tests versus a subset. Both keep code pairs, acquisition and maximum display count fixed. Actual record count may differ. Qwen native harmful n=101, selected12 uniform4; both4, selected-only8, uniform-only0, neither89. Effect+7.920792pp; 95%paired task-bootstrap CI[2.970297,13.861386]; raw one-sided exact p=.00390625; Holm-four p=.015625. Seven of eight selected-only cases omit uniform-visible failures; two of these seven are empty disclosures. Do not add7+2. Devstral3versus1/101 is unsupported(adjustedp=.75); reused V1 observations are not an independent replication. Both primary hybrid-defense gates failed. Generated harmful cohort n34 has no disclosure discordances for either reviewer; finite-test labels are conditional.\nEvidence: ${git}02_008/EVIDENCE.json\nPaper: ${git}02_008/PAPER.md\nClosest prior work:\n${summaries[1].closest_prior_sources.map(x=>x.title+' '+x.url).join('\n')}\nPrepared17September2026 with AI assistance; no human approval inferred.`);
}
{
const s=p.slides.add();
compose(s,[
 T('Title','010: the harm criterion was not met',56,36,1168,112,48,true),
 T('Setup','1,024 evaluations completed · 32 overlapping development contexts',56,146,1168,48,32),
 T('Table label','Raw joint TimesFM 3 · unchanged channels',56,211,760,38,24),
 T('Qualifying metric','0 / 6',874,253,350,96,80,true),
 T('Qualifying label','variants qualified',874,354,350,44,32,true),
 T('Decision','Scale-up held',874,428,350,44,32,true),
 T('Interpretation','Individual harm occurred.\nMean harm did not meet\nthe frozen threshold.',874,489,350,105,24),
 T('Limits','Simple-control sufficiency: not reached. Technical audit passed; no defense validated.',56,604,1168,44,24),
 ...foot('010 evidence E1–E8 · Δerror < 0 means lower average error',3)
]);
const values=[['Variant','Mean Δerror','Displaced / 32'],['Step 1','−0.007942','6'],['Step 3','−0.006084','8'],['Step 6','−0.007084','11'],['Ramp 1','−0.017816','22'],['Ramp 3','−0.013414','23'],['Ramp 6','−0.008986','23']];
const t=s.tables.add({rows:7,columns:3,left:56,top:261,width:752,height:322,columnWidths:[202,275,275],values});
t.cells.block({row:0,column:0,rowCount:7,columnCount:3}).assign({fill:'#FFFFFF',textStyle:{fontFamily:'Arial',fontSize:24,color:'#222222'},margins:{left:12,right:12,top:6,bottom:6}});
t.cells.block({row:0,column:0,rowCount:1,columnCount:3}).assign({fill:'#EEEEEE',textStyle:{fontSize:24,bold:true,color:'#111111'}});
t.borders.assign({style:'solid',fill:'#BBBBBB',width:1});
for(let i=0;i<7;i++)t.rows[i].height=46;
s.speakerNotes.textFrame.setText(`010 D0 — technically complete; HOLD_CROSS_CHANNEL_HARM_SCALE_UP.\nSix raw-joint variants had mean protected-channel error changes[-.007942247884642175,-.006083820171482706,-.007083947727937341,-.017815747361900038,-.013413696269373214,-.008985887932459632]. Counts with displacement>=.05 standard units[6,8,11,22,23,23]of32. Positive-error origins[11,14,14,13,15,15]. Joint criterion required meanerrorinflation>=.02 AND displacementcount>=8, with at least2qualifying variants to proceed. Zero qualified. All six raw-joint means are negative; this does not imply absence of individual harm. Conditional simple-control adequacy gate NOT_REACHED, not failed. Fourpipelines×32origins×8conditions=1024evaluations;1536nativeforwards. Clean point/quantile repeats zero; independent-channel displacement zero. Three semisynthetic channels from one previously inspected public NABseries; origins overlap; no independent industrial/cyber replication. Cloud was stopped after run; no inference commissioned for this closure.\nEvidence: ${git}03_010/EVIDENCE.json\nPaper: ${git}03_010/PAPER.md\nPrimary sources:\nhttps://arxiv.org/html/2606.06347v1\nhttps://arxiv.org/html/2606.05332v1\nhttps://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py\nPrepared17September2026 with AI assistance; human approval pending.`);
}
await fs.mkdir(path.join(here,'slides'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 const blob=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(here,'slides',`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
 const layout=await p.export({slide:s,format:'layout'});await fs.writeFile(path.join(here,'slides',`slide-${i+1}.layout.json`),await layout.text());
}
await fs.writeFile(path.join(here,'frames.json'),JSON.stringify(frames,null,2));
await(await PresentationFile.exportPptx(p)).save(`${root}/deliverables/Praxis_Three_Experiments.pptx`);
console.log('Exported exactly '+p.slides.items.length+' slides');
