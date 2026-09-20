"""Create an aggregate confusion table and private readable bot-review report.

This is post-freeze reporting only. It cannot modify decisions or send evidence.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(frozen, answer_key, graded, private_html, output):
    frozen, answer_key, graded, private_html, output = map(Path, (frozen, answer_key, graded, private_html, output))
    repo = Path(__file__).resolve().parents[2]
    if private_html.resolve().is_relative_to(repo):
        raise ValueError('Quoted evidence and source labels must remain outside Git')
    if private_html.exists() or output.exists():
        raise ValueError('Preserve previous report attempts')
    seal = json.loads((frozen / 'FROZEN.json').read_bytes())
    scored = json.loads(graded.read_bytes())
    if seal.get('human_review_performed') is not False or scored.get('human_requirement_satisfied') is not False:
        raise ValueError('Explicit automated-review scope required')
    if sha(frozen / 'ANSWERS.json') != seal['answers_sha256'] or sha(frozen / 'RAW_OUTPUTS.jsonl') != seal['raw_outputs_sha256']:
        raise ValueError('Frozen review was changed')
    if scored['answers_sha256'] != seal['answers_sha256'] or scored['answer_key_sha256'] != sha(answer_key):
        raise ValueError('Graded receipt does not bind this review/key')
    answers = json.loads((frozen / 'ANSWERS.json').read_bytes())
    key = json.loads(answer_key.read_bytes())
    if len(answers) != 50 or len({a['case_id'] for a in answers}) != 50 or set(key) != {a['case_id'] for a in answers}:
        raise ValueError('All 50 unique cases required')
    decisions = ('Attack', 'Non-Attack', 'Unable to verify')
    confusion = {label: {decision: 0 for decision in decisions} for label in ('Attack', 'Non-Attack')}
    for answer in answers:
        confusion[key[answer['case_id']]][answer['decision']] += 1
    agreed = sum(confusion[label][label] for label in confusion)
    if agreed != scored['agreement_count']:
        raise ValueError('Independent confusion recount disagrees with grader')
    report = {
        'status': 'POST_FREEZE_AUTOMATED_AUDIT_RECOUNT', 'case_count': 50,
        'confusion_rows_dataset_labels_columns_bot_decisions': confusion,
        'agreement_count': agreed, 'agreement_fraction_all_cases': agreed / 50,
        'automated_45_of_50_benchmark_met': agreed >= 45,
        'human_requirement_satisfied': False, 'independent_ground_truth_verified': False,
        'validation_status_counts': dict(Counter(a['validation_status'] for a in answers)),
        'quoted_citations': sum(len(a['citations']) for a in answers),
        'graded_sha256': sha(graded), 'answers_sha256': seal['answers_sha256'],
        'interpretation': 'Agreement is with existing dataset labels. Disagreement does not establish which judgment is correct. Exact quotations establish presence, not reasoning quality.'
    }
    escape = html.escape
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Automated 50-case review</title>',
             '<style>body{max-width:1050px;margin:40px auto;font:17px/1.5 system-ui;color:#182437;padding:0 20px}article{border:1px solid #ccd5de;border-radius:8px;padding:20px;margin:18px 0}code{overflow-wrap:anywhere}blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:12px}small{color:#526070}h2{font-size:20px}</style>',
             '<h1>Automated review of 50 security alerts</h1><p>This is a bot audit, not a human review or verification of ground truth. Decisions were frozen before the answer key was read.</p>',
             f'<p><strong>{agreed}/50 agree with the dataset labels.</strong> Unable cases remain in the denominator. The original human-review requirement remains unmet.</p>',
             '<p>Model: Qwen3-4B-Instruct-2507. Exact revision, prompt and runtime are preserved with the result artifacts.</p>']
    for ordinal, answer in enumerate(answers, 1):
        truth = key[answer['case_id']]
        match = 'Agreement' if answer['decision'] == truth else 'Unable' if answer['decision'] == 'Unable to verify' else 'Disagreement'
        parts += [f'<article><h2>Case {ordinal}: {match}</h2>',
                  f'<p>Bot: <strong>{escape(answer["decision"])}</strong> · Dataset label: <strong>{escape(truth)}</strong></p>',
                  f'<p>{escape(answer["reason"])}</p>',
                  f'<small>Validation: {escape(answer["validation_status"])}<br>Case ID: <code>{escape(answer["case_id"])}</code></small>']
        for citation in answer['citations']:
            parts += [f'<p><strong>{escape(citation["field"])}</strong></p><blockquote>{escape(citation["quote"])}</blockquote>']
        parts.append('</article>')
    parts.append('</html>')
    private_html.parent.mkdir(parents=True, exist_ok=True)
    private_html.write_text('\n'.join(parts), encoding='utf-8')
    report['private_html_sha256'] = sha(private_html)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frozen', 'answer-key', 'graded', 'private-html', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = build(args.frozen, args.answer_key, args.graded, args.private_html, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'case_count', 'agreement_count')}))
