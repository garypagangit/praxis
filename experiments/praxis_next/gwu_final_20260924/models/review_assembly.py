"""Record the bounded, read-only methods review of the assembled manuscript."""
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    paths = [ROOT / 'manuscript.md', ROOT / 'abstract.md', ROOT / 'references.json',
             HERE / 'MODEL_INVENTORY.json', HERE / 'MODEL_EXPLANATION.md',
             ROOT / 'results/tables/all_class_group_means.csv']
    raw = {p: p.read_bytes() for p in paths}
    manuscript = raw[paths[0]].decode('utf-8').replace('\r\n', '\n')
    abstract = raw[paths[1]].decode('utf-8').replace('\r\n', '\n')
    refs = json.loads(raw[paths[2]].decode('utf-8'))
    model_text = raw[paths[4]].decode('utf-8').replace('\r\n', '\n')
    equations = re.findall(r'\$\$(.*?)\$\$', manuscript, re.S)
    verified_equations = re.findall(r'\$\$(.*?)\$\$', model_text, re.S)
    positions = [equations.index(block) if block in equations else -1 for block in verified_equations]
    copied_math = all(p >= 0 for p in positions) and positions == sorted(set(positions))
    if not copied_math:
        raise AssertionError('Model equations changed; independent rereview required')
    ref_by_id = {r['id']: r for r in refs}
    source_rows = list(csv.DictReader(io.StringIO(raw[paths[5]].decode('utf-8'))))
    stage_rows = [r for r in source_rows if r['study'] == 'PX082' and r['arm'] == 'past_only_anchor']
    if len(stage_rows) != 8:
        raise AssertionError('Expected eight chronological stage-metric rows')
    class_names = {'Benign': 'Benign', 'OtherAttackStage': 'Other attack',
                   'LateralMovement': 'Movement', 'DataExfiltration': 'Exfiltration'}
    view_names = {'current': 'Current', 'current_history': 'History'}
    fields = ('precision', 'exact_recall', 'f1', 'roc_auc', 'average_precision')
    supports = {'Benign': 96098, 'OtherAttackStage': 6213, 'LateralMovement': 18, 'DataExfiltration': 1722}
    stage_section = manuscript.split('## 4.8 Ranking Metrics and Operating Decisions', 1)[1].split('## 4.9', 1)[0]
    table_rows = []
    for row in stage_rows:
        if row['n_views'] != '3' or int(row['support']) != supports[row['class']]:
            raise AssertionError('Table support or fitting-seed count differs from source')
        if any(row[f + '_available_views'] != '3' for f in fields):
            raise AssertionError('Table source metric missing from a fitting seed')
        label = view_names[row['view']] + ' / ' + class_names[row['class']]
        expected = '| ' + label + ' | ' + ' | '.join(f'{float(row[f]):.4f}' for f in fields) + ' |'
        if stage_section.count(expected) != 1:
            raise AssertionError('Stage table differs from published CSV: ' + label)
        table_rows.append({'label': label, 'source_support': int(row['support']),
                           'source_n_views': 3, 'displayed_metrics': {f: f'{float(row[f]):.4f}' for f in fields}})
    if len(re.findall(r'^\| (?:Current|History) / ', stage_section, re.M)) != 8:
        raise AssertionError('Unexpected additional table row')
    findings = [
        {
            'id': 'R01', 'severity': 'publication_presentation',
            'location': 'Methodology model section: Corrections and qualifications for the final manuscript',
            'observation': 'Internal editing instructions are copied into the publication body.',
            'required_change': 'Remove the internal instruction subsection, or replace it with declarative methodological qualifications. Move duplicated full bibliographic entries and locators out of methods if appropriate.',
            'open': 'Replace “classifier trees”' in manuscript
        },
        {
            'id': 'R02', 'severity': 'citation_consistency',
            'location': 'Sections 2.5 and 3.3.7; References; references.json liu2022 and liu2022dataset',
            'observation': 'The text cites Liu 2022a/2022b, but both bibliography entries initially retained unsuffixed 2022; the benchmark paragraph used unsuffixed Liu et al. (2022).',
            'required_change': 'Use journal article 2022a and dataset 2022b consistently in APA strings and in-text references; this follows alphabetical title order for identical authors and year.',
            'open': any('(2022)' in ref_by_id[k]['apa'] for k in ('liu2022', 'liu2022dataset')) or 'Liu et al. (2022)' in manuscript
        },
        {
            'id': 'R03', 'severity': 'method_terminology',
            'location': 'Section 3.4, temporal classifier settings',
            'observation': 'The summary says 200 estimators, 15 leaves, whereas detailed methods correctly distinguish boosting iterations and class-specific trees.',
            'required_change': 'Use 200 boosting iterations and at most 15 leaves per tree.',
            'open': '200 estimators, 15 leaves' in manuscript
        },
        {
            'id': 'R04', 'severity': 'method_terminology',
            'location': 'Section 3.8, paired identity/schema validation',
            'observation': 'The main task uses a grouped four-class schema, while this sentence calls its class meanings native.',
            'required_change': 'Replace native class meanings with declared evaluation-class meanings in this sentence. Preserve native terminology for the separate D1 source-qualification task.',
            'open': 'native class meanings must match' in manuscript
        },
        {
            'id': 'R05', 'severity': 'bibliographic_completeness',
            'location': 'End References, eight model/software entries',
            'observation': 'Model reference records retain APA strings and URLs separately, so a renderer that emits only apa omits the primary source URL.',
            'required_change': 'Append the record URL when rendering an APA entry that does not already contain it. Keep the machine-readable url field.',
            'open': any(r['url'] not in manuscript.split('# References', 1)[-1] for r in refs if r.get('id') in {
                'ke2017lightgbm', 'lightgbm_features_460', 'lightgbm_classifier_460', 'lightgbm_regressor_460',
                'lightgbm_parameters_460', 'pedregosa2011sklearn', 'sklearn_logistic_19', 'sklearn_ridge_17'})
        },
        {
            'id': 'R06', 'severity': 'APA_style_recommendation',
            'location': 'Model-source attributions in Methodology',
            'observation': 'Direct primary-source hyperlinks identify the relevant documentation; author-date citations make matching to the end bibliography clearer, particularly after removing the duplicated in-method reference list.',
            'required_change': 'Use LightGBM developers n.d.-a/b/c/d for features/classifier/regressor/parameters respectively; Scikit-learn developers n.d.-a/b for LogisticRegression/Ridge; cite Pedregosa et al. (2011) for software. Documentation suffix ordering is already correct.',
            'open': not all(text in manuscript.split('# References', 1)[0] for text in (
                'LightGBM developers (n.d.-a)', 'LightGBM developers (n.d.-b)',
                'LightGBM developers (n.d.-c)', 'LightGBM developers (n.d.-d)',
                'Scikit-learn developers (n.d.-a)', 'Scikit-learn developers (n.d.-b)',
                'Pedregosa et al. (2011)'))
        }
    ]
    for f in findings:
        if f['open'] is not None:
            f['status'] = 'OPEN' if f['open'] else 'RESOLVED_BY_CURRENT_ASSEMBLY'
        else:
            f['status'] = 'STYLE_RECOMMENDATION_REQUIRES_EDITORIAL_CHECK'
    receipt = {
        'status': 'METHODS_AND_MATHEMATICS_PASS_WITH_PRESENTATION_CORRECTIONS' if any(f['open'] for f in findings) else 'METHODS_AND_MATHEMATICS_PASS',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Independent read-only audit of assembled model methods, equations, abstract qualifications and citation consistency; no new fitting or manuscript modification.',
        'input_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(value).hexdigest() for p, value in raw.items()},
        'stage_ranking_table': {
            'status': 'PASS', 'source': paths[5].relative_to(ROOT).as_posix(),
            'filter': {'study': 'PX082', 'arm': 'past_only_anchor'},
            'rows_checked': 8, 'rounded_numeric_cells_checked': 40,
            'checks': 'Every displayed cell equals the corresponding source mean rounded to four decimals; every metric is available for all three views; class supports sum to the 104051-row common anchor in each feature view.',
            'rows': table_rows,
            'ranking_explanation_review': 'ROC-AUC summarizes class-versus-rest ranking, whereas average precision is the recall-increment-weighted precision summary, not trapezoidal PR area. Neither is determined by one confusion matrix or guarantees the multiclass argmax operating decision. The informal rank interpretation includes half credit for tied scores.',
            'primary_checks': [
                {'url': 'https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html',
                 'verified_on': '2026-09-24', 'locator': 'Definition preceding Parameters; weighted precision by recall increments and explicit non-trapezoidal distinction.'},
                {'url': 'https://scikit-learn.org/1.7/modules/model_evaluation.html#roc-metrics',
                 'verified_on': '2026-09-24', 'locator': 'Section 3.4.4.15, Receiver operating characteristic and score-based evaluation.'}
            ]
        },
        'equations': {'assembled_blocks': len(equations), 'audited_model_blocks': len(verified_equations),
                      'model_blocks_preserved_in_order_after_line_ending_normalization': copied_math,
                      'additional_logistic_equation_review': 'Binary sigmoid of intercept plus the inner product of coefficients and hashed-text/metadata features matches the saved binary LogisticRegression model; class-balanced logistic loss and inverse regularization C descriptions are correct. A sigmoid score is not claimed calibrated.',
                      'metric_blocks_review': 'Precision, recall, F1, macro-F1, exact-stage recall, warning recall and benign false-alert equations are ordinary confusion-matrix definitions. Unsupported true-class handling is explicitly described.'},
        'passed_method_checks': [
            '141 main LightGBM fits: 111 classifiers and 30 regressors; supplementary two Ridge fits; reused native classifiers excluded from new-fit total.',
            'Stage costs modify selector regression responses, not class/sample weights of main base classifiers.',
            'PX080 target is context-minus-current loss and selects context for negative score; PX081 target is before-minus-after loss and requests positive gain.',
            'Forward-held-out expert predictions train selectors; source exposure and retrospective warning analysis remain explicit.',
            'Acquisition is greedy gain-per-cost with regime-supplied availability priors and simulated costs/delays, not globally optimized planning or guaranteed deadline success.',
            'History augmentation is identified as data augmentation; GOSS, DART, TabM, GNNs and LLMs are not claimed as fitted models.',
            'Ridge alpha 10, SVD solver, intercept and no scaling match source; decision score is not represented as a probability.',
            'T1105 transfer is a different target with native per-source experts; only two deterministic selectors transfer, with other-technique negatives rather than verified benign traffic.',
            'Main CPU execution and software-version differences are stated accurately.',
            'Abstract keeps one exposed campaign, retrospective sensitivity and unmeasured operational/forecasting benefits explicit; numerical headline effects agree with the previously independently checked result reports.'
        ],
        'recommended_general_prose': 'Stage costs changed the numerical targets learned by the selectors; the base stage classifiers used ordinary multiclass training. The cost penalized every wrong destination equally within a true class, so it did not specifically protect attack-to-benign warnings.',
        'findings': findings,
        'limits': 'This pass checks assembled methods against the already verified source/model inventory and prior primary-reference audit, plus all 40 displayed stage-ranking cells against the published class-mean CSV. It does not refit models, recompute ranking areas from raw probabilities, conduct an exhaustive literature search, or perform visual document QA.'
    }
    (HERE / 'MANUSCRIPT_REVIEW.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'model_equations_identical': copied_math,
                      'open_findings': [f['id'] for f in findings if f['open']],
                      'style_recommendations': [f['id'] for f in findings if f['open'] is None]}))


if __name__ == '__main__':
    main()
