"""Plain-language manuscript additions, diagrams and dataset examples."""
import json, textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from docx.shared import Inches

HERE=Path(__file__).resolve().parent
FIG=HERE/'figures'

def figures():
    """Draw original engineering diagrams; no generated empirical observations."""
    FIG.mkdir(exist_ok=True)
    def boxes(name,items,cols=2):
        fig,ax=plt.subplots(figsize=(7.2,7.4 if len(items)>4 else 5.2))
        ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        rows=(len(items)+cols-1)//cols
        for i,(title,body) in enumerate(items):
            x=.02+(i%cols)*.5;y=.97-(i//cols+1)*(.94/rows);w=.46;ht=.94/rows-.035
            ax.add_patch(FancyBboxPatch((x,y),w,ht,boxstyle='round,pad=.01',facecolor='#edf5f6',edgecolor='#176575',linewidth=1.4))
            ax.text(x+.025,y+ht-.035,title,va='top',fontsize=9.5,weight='bold',color='#144657')
            ax.text(x+.025,y+ht-.09,'\n'.join(textwrap.fill(line,30) for line in body.split('\n')),va='top',fontsize=9.5,linespacing=1.4)
        fig.savefig(FIG/(name+'.png'),dpi=200,bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    boxes('gmr',[
      ('1. Establish the problem','What: separate operator from source.\nWhy: dataset clues can mislead.\nHow: explicit provenance audit.'),
      ('2. Qualify the data','What: ten-command windows.\nWhy: compare shared observations.\nHow: common parser and exclusions.'),
      ('3. Separate observations','What: fit, calibration, evaluation.\nWhy: prevent related-row leakage.\nHow: group and duplicate checks.'),
      ('4. Compare representations','What: words, verbs, counts.\nWhy: identify what the model uses.\nHow: fixed linear baselines.'),
      ('5. Explain and challenge','What: exact feature contributions.\nWhy: inspect dependence on clues.\nHow: masking and count tests.'),
      ('6. Validate transfer','What: fresh operators (pending).\nWhy: resolve source confounding.\nHow: same tasks and recorder.')])
    boxes('methodology',[
      ('Current development data','GAMBiT human + Honey AI\nDifferent tasks and environments\nCommon command processing\nSource and class remain aligned.'),
      ('Required matched study','Human + autonomous AI\nSame tasks, images and recorder\nNew operators and held-out tasks\nOperator assignment gives label.'),
      ('Shared evaluation pipeline','Split groups before fitting\nFit model on training data\nSet threshold on calibration\nFreeze before test evaluation.'),
      ('Decision and explanation','Ten qualifying commands\nLinear score + contributions\nAI or human attribution label\nRecall, human errors, coverage.')])
    r=json.loads((HERE/'RESULTS.json').read_text())
    labels=['Masked\noriginal','Frozen masked\ncounts equalized','Retrained\none marker','Counts only']
    points=[r['frozen_masked_original'],r['frozen_masked_equalized'],r['results'][2]['test'],r['results'][0]['test']]
    fig,ax=plt.subplots(figsize=(7.2,3.8));x=list(range(4))
    ax.bar([v-.18 for v in x],[v['agent_recall']*100 for v in points],.36,label='AI recall',color='#176575')
    ax.bar([v+.18 for v in x],[v['human_group_mean_fpr']*100 for v in points],.36,label='Mean human-group FPR',color='#b7652c')
    ax.set_xticks(x,labels);ax.set_ylabel('Percent');ax.set_ylim(0,110);ax.legend(fontsize=9)
    ax.spines[['top','right']].set_visible(False);fig.tight_layout()
    fig.savefig(FIG/'argument_test.png',dpi=200);fig.savefig(FIG/'argument_test.svg');plt.close(fig)

def add(g,section):
    """Use the existing manuscript helpers to preserve GWU document styles."""
    p,h,table,doc=g['p'],g['h'],g['table'],g['doc']
    def image(name,caption):
        doc.add_paragraph(caption,'GWU Figure Caption');doc.add_picture(str(FIG/(name+'.png')),width=Inches(5.0 if name=='gmr' else 5.8))
    if section=='objectives':
        h('1.7 Objectives and organization')
        p('The objectives are to qualify operator labels, measure attribution errors at a fixed operating rule, identify which command details drive those errors, and test the resulting procedure on fresh matched conditions. Chapter 2 establishes the prior work. Chapter 3 defines the data and tests. Chapter 4 reports completed results, including unfavorable outcomes. Chapter 5 states the contribution and what remains unproved.')
    elif section=='methods':
        image('methodology','Figure 1. Current development data and required matched evaluation')
        p('The left-hand data sources support development. They cannot separate operator effects from source effects. The matched collection on the right is still pending. Both paths use the same evaluation steps. All figures were prepared for this study.')
    elif section=='qualification':
        h('3.2.1 Dataset evaluation')
        table('Table 3A. What each dataset can support',['Source','Qualified material','Important limitation'],[
          ['GAMBiT (human)','244 windows; 42 conservative groups','Human red-team provenance; tasks differ from Honey.'],
          ['Honey (AI)','7,659 eligible sessions','Autonomous SSH activity; not all sessions are multi-stage attacks.'],
          ['KYPO (human)','180 external windows after duplicate exclusion','Training-task check; groups are not verified independent people.'],
          ['Rouxii archive (AI)','2 eligible runs from 1,544 reports','Too small for a reliable external AI estimate.']])
        p('These counts have different units and should not be added into a participant total. Eligibility is part of the result: short or structurally incompatible sessions receive no prediction. Honey qualification excluded 2,744 files without the required parsed-command fields and 5,796 with too few eligible commands. Source-level coverage must accompany accuracy; the present classifier does not apply to every session.')
        table('Table 3B. Command representation example (constructed illustration)',['Input','Representation','Information retained'],[
          ['ls -la /tmp','ls ARG ARG','Verb and two argument positions'],
          ['ls -la /tmp','ls ARG','One-marker control removes argument count'],
          ['ls -la /tmp','ls','Verb frequency or sequence'],
          ['whoami','whoami ARG','One-marker control adds a marker even with zero arguments']])
        p('Table 3B is an illustration, not a collected participant record. The evidence package also includes short normalized excerpts selected by a fixed record-ID rule from actual correct and missed AI examples. No command in these files is executed.')
        examples=json.loads((HERE/'DATA_EXAMPLES.json').read_text())
        table('Table 3C. Actual normalized excerpts from development records',['Source / outcome','First three commands','AI score'],[[e['source']+' / '+e['outcome'],'; '.join(e['first_three_normalized_commands']),f"{e['score']:.3f}"] for e in examples])
        p('Each excerpt is the first three commands from a ten-command window, selected as the lowest record ID in its outcome category. The model scores the full window. The frozen masked threshold is 0.717. Scores are model outputs and have not been validated as calibrated deployment probabilities. In the missed AI example, grep-related contributions lower the AI score; in the human example, repeated ls strongly lowers it. These explain the fitted decision, not the operator\'s intent.')
        h('3.2.2 Observation point and practical meaning')
        p('The present inputs are recorded operator-side shell commands. A defender could potentially obtain comparable commands from an instrumented shell, session recorder or endpoint process telemetry, but this mapping has not been tested. The study does not infer commands from NetFlow or encrypted packets. The model identifies an operator class within eligible records; it is not an attack detector. No timing feature or attack-stage label is needed for these tests.')
    elif section=='gmr':
        h('3.9 Graphical methodology representation (GMR)')
        image('gmr','Figure 2. GMR: what is tested, why it matters and how it is evaluated')
        h('3.10 Additional development test: PX-119')
        p('PX-119 was specified before fitting at commit e1f40ed. It reuses examined partitions, weights and calibration rules. Three controls compare positional counts, count summaries and one ARG token per verb. A separate stress test equalizes counts in the frozen masked model. Meaning preservation is not assumed. The three local fits took less than one second.')
    elif section=='results':
        h('4.6 Argument-count dependence: PX-119')
        r=json.loads((HERE/'RESULTS.json').read_text())
        table('Table 10. Argument-count diagnostic on the same development test',['Representation','AI recall','Human errors','Group FPR'],[[x['model'],f"{x['test']['agent_recall']:.2%}",f"{x['test']['fp']}/61",f"{x['test']['human_group_mean_fpr']:.2%}"] for x in r['results']])
        p('Counts alone recover 11.46% of AI windows. The order-free count summaries recover none at their calibration threshold, despite test AUROC of 0.894. A ranking score alone therefore does not demonstrate usefulness at the chosen operating point. The retrained one-marker model reaches 79.77% recall and 4.32% mean human-group FPR, narrowly missing the 80% recall target. Its KYPO false labels are 2/180; positional counts produce 36/180. These external checks remain conditional on eligible training-task records.')
        image('argument_test','Figure 3. Argument-count intervention and retrained controls')
        p('When the frozen masked model receives equalized argument counts, its recall changes from 92.85% to 90.92%, but human false labels rise from 0/61 to 30/61. Mean human-group FPR rises to 50.93%, and 9.92% of all decisions change. This demonstrates sensitivity to count-related representation changes. It does not establish that count alone explains the original result, nor that argument count is inherently an invalid feature. The intervention changes the input distribution; the matched study must determine whether the dependence transfers.')
        p('Of the original masked model\'s 93 AI misses, 74 are Alibaba, 14 Meta and 5 Google. The corresponding main-test denominators are 705, 240 and 351; DeepSeek has only four main-test records and no misses. These are the main-test slices, not the larger family-exclusion tests. Concentration of errors is useful for diagnosis but does not justify family-specific threshold tuning on this test.')
        h('4.7 Hypothesis status and practical interpretation')
        table('Table 11. Status of proposed confirmatory hypotheses',['Hypothesis','Current status'],[['H1: fresh matched transfer','Not tested: matched evaluation not collected.'],['H2: masking improves transfer at a human-error limit','Not tested on fresh data; PX-118/119 are diagnostics.'],['H3: validated irrelevant renaming preserves explanations','Not tested: broad argument/count changes do not meet that definition.']])
        p('No completed test establishes population-level operator attribution. With only nine conservative human groups, zero observed errors gives weak evidence about a low future error rate. The existing group bootstrap is conditional and degenerates at zero observed errors. A confirmatory analysis needs adequate independent operators, group-resampled intervals and an explicit decision rule agreed before evaluation.')
    elif section=='remaining':
        h('5.5 Work remaining before a defense claim')
        table('Table 12. Remaining work and completion evidence',['Work item','Required evidence'],[
          ['Matched collection','Institutional determination; recruited humans; autonomous runs on identical tasks and recorder.'],
          ['Collection implementation','Task images, autonomous adapter and container integration tests; prototype is not a validated collection system.'],
          ['Fresh evaluation','Frozen selection, sample size, holdouts and thresholds; independent operators and unseen conditions.'],
          ['Explanation validity','Validated irrelevant-identifier interventions; errors and stability measured on fresh records.'],
          ['Novelty and review','Full closest papers, updated comparison and committee agreement on the narrow contribution.'],
          ['Final manuscript','Author verification, AI-use disclosure, committee metadata and approved submission format.']])
        p('The next decision is whether to invest in a matched pilot. More tuning on the present sources cannot remove their class/source confounding. The pilot should estimate eligible-window yield, variability between operators and task effects before fixing the final sample size. The 80% recall and 5% human-error limits are proposed engineering targets, not universal SOC standards. They require stakeholder justification before confirmation.')
        p('For a hypothetical deployment with 1% AI windows, 80% sensitivity and 5% human FPR, only about 13.9% of AI labels would be correct. The formula is sensitivity times prevalence divided by that quantity plus FPR times one minus prevalence. This example uses assumed inputs; it is not an observed precision estimate. It explains why a useful triage label may require much lower human error than a balanced benchmark suggests.')
    elif section=='appendix':
        g['chapter']('Appendix C: Package Guide and Research Disclosure')
        p('The code package contains annotated PX-119 code, frozen PX-118 training code and its dependencies, a portable reproduction launcher, pinned numerical requirements, artifact verification and a code-section guide. Prepared source inputs are kept in a separate local private-input package. The evidence package contains protocols, predictions, result tables, qualification records, figures, audits and file hashes. Prediction files support independent metric checking without redistributing full source logs.')
        p('The packages distinguish completed tests from pending collection. They do not claim a public release of participant-level data or permission to redistribute original datasets. The local prepared-input bundle is for the author\'s reproduction workflow and must be reviewed against source terms before sharing. Serialized model files should only be loaded from the trusted package.')
        p('AI tools supported literature retrieval, code drafting, execution and manuscript revision. The author remains responsible for verifying claims, sources, analysis and institutional disclosure requirements. No AI-writing detector outcome or defense approval is guaranteed. Draft disclosure wording must be reviewed by the author and committee.')

if __name__=='__main__':figures()
