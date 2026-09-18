"""Build readable artifacts from fixed pilot outputs; never fits or tunes a model."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
NAMES = {
    'always_vanilla': 'No extra evidence', 'always_evidence': 'Always use evidence',
    'relevance': 'Published relevance: question',
    'relevance_options': 'Published relevance: question + choices',
    'source_classifier': 'Question-only source selector',
    'question_utility': 'Question-only benefit selector',
    'evidence_utility': 'Proposed evidence-aware benefit selector',
}
MODELS = ('llama', 'qwen')


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def signed(x):
    return f'{x:+.2f}'


def interval(x):
    return f'[{signed(x[0])}, {signed(x[1])}]'


def make_report():
    r, fit, audit = read('RESULTS.json'), read('FIT_RECEIPT.json'), read('REVIEW.json')
    m = r['metrics']
    c = m['evidence_utility']
    if r['status'] == 'METHOD_SPECIFIC_PILOT_SIGNAL':
        verdict = ('The proposed checker met the exploratory usefulness and added-value criteria. '
                   'This supports a focused follow-up, while fresh data and stronger published checkers remain necessary.')
    elif r['status'] == 'USEFUL_SELECTION_SIGNAL_ADDED_VALUE_UNPROVEN':
        verdict = ('Selective evidence use met the practical pilot criteria, but this checker did not establish '
                   'an advantage over every simpler comparator. The application has a signal; the proposed '
                   'method is not yet a defensible improvement.')
    else:
        verdict = ('The proposed checker did not meet all practical pilot criteria. Its positive and negative '
                   'results must be considered together; this run does not validate it as the solution.')
    lines = ['# CTI checker pilot: completed experiment', '', 'September 18, 2026.', '',
             '## Decision', '', verdict, '', f'**Recorded status:** `{r["status"]}`.', '',
             'For this completed run, the practical recommendation is to carry the published relevance '
             'model with a locally calibrated cutoff and the frozen candidate into a fresh CTI test. '
             'The simpler relevance approach already preserves substantial benefit and limits mismatch '
             'loss to about one percentage point. Further complexity is not justified by a clear '
             'advantage in this pilot. See [NEXT_STEPS.md](NEXT_STEPS.md).', '',
             '## What was actually run', '',
             'The experiment used all 2,500 archived CTI questions and both fixed generators. '
             'New neural checker inference scored 15,000 retrieved facts twice: once with the question '
             'and once with the question plus all answer choices. New selectors were trained in five '
             'source-separated splits, with 1,500 training, 500 validation and 500 test questions per fit. '
             'Every question received exactly one held-out selector decision.', '',
             'The selector decides whether to use the existing with-evidence or without-evidence answer. '
             'It does not produce new generator answers, remove individual facts, refuse to answer, or '
             'verify every logical condition in a security recommendation. All policies answer every question.', '',
             'Correctness uses the released multiple-choice labels and the original frozen answer parser. '
             'Invalid outputs remain wrong in every denominator. These scores do not establish open-ended '
             'answer quality, analyst productivity or independently verified ground truth.', '',
             'The candidate predicts whether evidence will help from question text, all choices and '
             '38 numerical features of the actual retrieved evidence. It learns from correctness changes '
             'on training questions only. It never receives the test answer label, known source, '
             'source category, or inherited source-aware option scores.', '',
             '## Overall accuracy', '',
             '| Policy | Evidence used | Llama accuracy | Qwen accuracy |',
             '|---|---:|---:|---:|']
    for arm, name in NAMES.items():
        a = m[arm]['all']
        lines.append(f'| {name} | {a["evidence_use_pct"]:.2f}% | {a["llama"]["accuracy_pct"]:.2f}% | {a["qwen"]["accuracy_pct"]:.2f}% |')
    lines += ['', 'These percentages share a denominator of 2,500 questions per model. '
              'The two model outcomes are paired observations, not 5,000 independent questions.', '',
              '## Useful benefit and mismatch harm', '',
              'The eligible group contains 1,578 ATT&CK-technique questions; the mismatch group contains '
              '922 questions outside that source category. Category membership is an evaluation stratum, '
              'not a human judgment that every retrieved fact is applicable or inapplicable.', '',
              '| Model / group | Always-evidence change | Candidate change [95% interval] |',
              '|---|---:|---:|']
    for model in MODELS:
        for cohort in ('eligible', 'mismatch'):
            a, b = m['always_evidence'][cohort][model], c[cohort][model]
            lines.append(f'| {model.title()} / {cohort} | {signed(a["delta_vs_vanilla_pp"])} pp | {signed(b["delta_vs_vanilla_pp"])} pp {interval(b["delta_ci95_pp"])} |')
    lines += ['', 'Intervals use 5,000 paired resamples of source groups, holding fitted predictions fixed. '
              'They describe this retrospective result; they do not resolve cross-validation training '
              'dependence, project exposure or benchmark contamination.', '',
              '## Did the added evidence features earn their complexity?', '',
              f'Every comparison below uses evidence on exactly {c["all"]["evidence_used_n"]} questions '
              f'({c["all"]["evidence_use_pct"]:.2f}%), with counts matched separately in each test fold. '
              'Positive differences favor the proposed checker. Computational costs are not equalized.', '',
              '| Matched-use comparator | Llama difference | Qwen difference | Paired model-average difference [95% interval] |',
              '|---|---:|---:|---:|']
    for arm in ('relevance', 'relevance_options', 'source_classifier', 'question_utility'):
        a = r['candidate_vs_comparator'][arm+'_matched']
        avg = a['paired_model_average']
        lines.append(f'| {NAMES[arm]} | {signed(a["llama"]["difference_pp"])} pp | {signed(a["qwen"]["difference_pp"])} pp | {signed(avg["difference_pp"])} pp {interval(avg["ci95_pp"])} |')
    lines += ['', '## Prespecified checks', '', '| Check | Llama | Qwen |', '|---|---|---|']
    labels = {'overall_gain_at_least_3pp': 'Overall improvement at least 3 points',
              'retains_half_eligible_benefit': 'At least half the eligible benefit retained',
              'mismatch_loss_no_worse_than_2pp': 'Mismatch net loss no worse than 2 points',
              'mismatch_ci_lower_above_minus5pp': 'Mismatch interval lower bound above -5 points'}
    for key, title in labels.items():
        states = ['PASS' if r['core_checks'][model][key] else 'FAIL' for model in MODELS]
        lines.append(f'| {title} | {states[0]} | {states[1]} |')
    lines += ['', f'**Core criteria:** {"PASS" if r["core_signal_pass"] else "FAIL"}. '
              f'**Added value versus every matched comparator:** {"PASS" if r["added_value_pass"] else "FAIL"}.', '',
              'The added-value rule requires at least a one-point gain in each model against every comparator '
              'and a positive interval lower bound for the paired model average. These are exploratory '
              'decision rules, not multiplicity-adjusted confirmatory significance tests.', '',
              '## Remaining mistakes and lost improvements', '',
              '| Model | Evidence-induced mistakes retained | Such mistakes prevented | Helpful changes retained | Helpful changes lost |',
              '|---|---:|---:|---:|---:|']
    for model in MODELS:
        a = c['all'][model]
        lines.append(f'| {model.title()} | {a["induced_mistakes"]} | {a["prevented_mistakes"]} | {a["recovered_wrong_answers"]} | {a["lost_improvements"]} |')
    lines += ['', 'Preventing some mistakes is not enough: the same policy can discard helpful evidence. '
              'These counts are based on paired archived answers, not human judgments of evidence quality.', '',
              '## Exposure sensitivity', '',
              'Excluding the historical 500 development items leaves 2,000 questions. This is a sensitivity '
              'analysis without refitting. Those 2,000 questions were also later used by the project, '
              'so they are not a fresh confirmation sample.', '',
              '| Model | Candidate gain over vanilla on remaining 2,000 |', '|---|---:|']
    for model in MODELS:
        a = c['excluding_prior_500'][model]
        lines.append(f'| {model.title()} | {signed(a["delta_vs_vanilla_pp"])} pp {interval(a["delta_ci95_pp"])} |')
    metas = [read(n) for n in ('relevance_metadata.json', 'relevance_options_metadata.json')]
    lines += ['', '## Cost and verification', '',
              f'- Local CPU relevance inference: {metas[0]["this_run_inference_seconds"]:.1f} seconds '
              f'for question-only and {metas[1]["this_run_inference_seconds"]:.1f} seconds for question plus choices.',
              f'- All five selector fits and associated preprocessing/calibration: {fit["elapsed_seconds"]:.1f} seconds.',
              f'- Truncated pairs: {metas[0]["pairs_truncated"]} / 15,000 and {metas[1]["pairs_truncated"]} / 15,000.',
              '- No paid cloud jobs were launched. These are local batch timings, not production latency or dollar-savings estimates.',
              '- The candidate requires the neural relevance scores. Question-only selectors avoid that extra inference.',
              '- Learning benefit requires paired generator outcomes for training; this pilot reused archived outcomes.',
              f'- Independent automated audit status: `{audit["status"]}`. Details are in [REVIEW.json](REVIEW.json).', '',
              '## What this establishes and what it leaves open', '',
              'This is an executed test of a new selection policy over old model responses. '
              'The same corpus, generators and historical benchmark are reused. Source-separated splitting '
              'reduces direct source overlap but does not demonstrate transfer to a new benchmark or model.', '',
              'The published comparator is [MiniLM](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2), '
              'a general relevance model. Full CRAG and the released CoRM-RAG critic were not run here. '
              '[CoRM-RAG](https://arxiv.org/html/2605.01302v1) already learns evidence utility, so that '
              'general idea cannot be claimed as a new algorithm. See [BASELINES.md](BASELINES.md) for the '
              'available checkpoints and resource limitations.', '',
              'Academic originality, independent source/answer review and performance on new questions remain '
              'unresolved. Human review has not been performed. The diagnostic review packet provides a '
              'way to examine concrete failures; its examples are deliberately selected and cannot estimate '
              'population error rates.', '',
              '## Reproduction and artifacts', '',
              '[Protocol](PROTOCOL.md) · [frozen hashes](FREEZE.json) · [results](RESULTS.json) · '
              '[run instructions](README.md) · [human review packet](HUMAN_REVIEW.md)', '']
    (ROOT/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def human_packet():
    data = [json.loads(x) for x in (ROOT/'data.jsonl').read_text(encoding='utf-8').splitlines()]
    pred = {r['id']: r for r in (json.loads(x) for x in (ROOT/'predictions.jsonl').read_text().splitlines())}
    chosen, key = [], []
    categories = ('prevented_harm', 'retained_harm', 'retained_benefit', 'lost_benefit')
    for category in categories:
        subset = []
        for row in data:
            b, e = (row['outcomes']['qwen'][x] for x in ('vanilla', 'evidence'))
            use = pred[row['id']]['use_evidence']['evidence_utility']
            kind = ('retained_harm' if use else 'prevented_harm') if b and not e else (
                   ('retained_benefit' if use else 'lost_benefit') if e and not b else 'unchanged')
            if kind == category:
                subset.append(row)
        for row in sorted(subset, key=lambda r: int(r['id'].rsplit('_', 1)[1]))[:3]:
            chosen.append(row)
            key.append({'id': row['id'], 'selection_reason': category, 'model': 'qwen'})
    # Do not expose outcome-based sampling labels in the human packet.
    chosen.sort(key=lambda r: int(r['id'].rsplit('_', 1)[1]))
    lines = ['# Independent evidence review: pending', '',
             'No human review has been completed. This packet is a diagnostic aid, not a validation result.', '',
             'Twelve or fewer cases were selected deterministically from four kinds of Qwen policy outcomes. '
             'Outcome categories and released answer labels are withheld here. The separate sampling key '
             'must remain hidden from reviewers until they finish. These deliberately chosen cases cannot '
             'estimate general error rates.', '',
             'For each question, identify which option the supplied facts support, if any. Distinguish '
             'information that merely discusses the same topic from information that resolves the question. '
             'Record missing conditions, conflicting facts and questionable benchmark wording. A source-domain '
             'label is not an applicability judgment. Consult original authoritative sources if needed and '
             'record the URLs used.', '',
             '**Reviewer name:** __________  **Review date:** __________', '',
             '**Review status:** PENDING. Leave this unchanged until a person actually performs the review.', '']
    for row in chosen:
        lines += [f'## {row["id"]}', '', row['question'], '']
        lines += [f'- **{k}.** {v}' for k, v in sorted(row['options'].items())]
        lines += ['', '**Retrieved facts**', '']
        lines += [f'{i+1}. {e["text"]}' for i, e in enumerate(row['evidence'])]
        lines += ['', '**Supported option(s), or insufficient evidence:** __________',
                  '**Fact(s) that establish the answer and required conditions:** __________',
                  '**Irrelevant, conflicting or missing information:** __________',
                  '**Independent sources checked:** __________',
                  '**Reviewer confidence and explanation:** __________', '']
    (ROOT/'HUMAN_REVIEW.md').write_text('\n'.join(lines), encoding='utf-8')
    (ROOT/'REVIEW_SAMPLE_KEY.json').write_text(json.dumps({'status': 'NO_HUMAN_REVIEWS_COMPLETED',
                  'sampling': 'first three numeric IDs per specified outcome category', 'cases': key}, indent=2)+'\n', encoding='utf-8')


def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r = read('RESULTS.json')
    arms = ('always_evidence', 'relevance_options', 'source_classifier', 'question_utility', 'evidence_utility')
    labels = ['Always use evidence', 'Relevance + choices', 'Question-only source selector', 'Question-only benefit selector', 'Proposed checker']
    colors = ['#8a96a5', '#4d70a9', '#8268aa', '#b07931', '#008b8b']
    bound = max(abs(v) for arm in arms for cohort in ('eligible', 'mismatch') for model in MODELS
                for v in r['metrics'][arm][cohort][model]['delta_ci95_pp'])
    axis_limit = max(25, 5*int((bound+7)//5))
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 7.8), sharex=True)
    for row, cohort in enumerate(('eligible', 'mismatch')):
        for col, model in enumerate(MODELS):
            ax = axes[row, col]
            for i, (arm, color) in enumerate(zip(arms, colors)):
                a = r['metrics'][arm][cohort][model]
                point = a['delta_vs_vanilla_pp']
                low, high = a['delta_ci95_pp']
                ax.errorbar(point, i, xerr=[[max(0, point-low)], [max(0, high-point)]],
                            fmt='o', color=color, markersize=7, capsize=3, linewidth=1.6)
            ax.axvline(0, color='#333333', linewidth=.8)
            ax.set_yticks(range(len(arms)), labels if col == 0 else ['']*len(arms))
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=.2)
            ax.set_xlim(-axis_limit, axis_limit)
            ax.set_title(f'{model.title()}: {"eligible questions" if cohort == "eligible" else "source-mismatch questions"}', loc='left', fontsize=11)
            ax.spines[['top', 'right']].set_visible(False)
            if row == 1:
                ax.set_xlabel('Accuracy change versus no extra evidence (percentage points)')
    fig.suptitle('Does evidence selection keep the benefit and limit the harm?', fontsize=15, x=.04, ha='left')
    fig.text(.04, .025, 'Retrospective CTI pilot: 2,500 questions, five source-separated test folds. Bars: conditional 95% source-group bootstrap intervals.\nNew checker computation; archived generator answers. This figure does not establish fresh-data performance or algorithmic novelty.', fontsize=9, color='#444444')
    fig.subplots_adjust(left=.25, right=.98, top=.89, bottom=.16, hspace=.38, wspace=.16)
    fig.savefig(ROOT/'RESULTS_CHART.png', dpi=150)
    fig.savefig(ROOT/'RESULTS_CHART.svg')
    plt.close(fig)


if __name__ == '__main__':
    make_report()
    human_packet()
    plot()
    print('REPORT.md, human review packet and results charts created from fixed outputs.')
