"""Read-only release verification for the internal guide (AI-assisted code)."""
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'MANIFEST.json').read_text())
    problems = []
    for item in manifest['files']:
        path = root / item['file']
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            problems.append('Manifest mismatch: ' + item['file'])
    for path in root.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not target.startswith(('https://', 'http://', '#')) and not (root / target.split('#')[0]).exists():
                problems.append('Missing local link: ' + target)
    qa = json.loads((root / 'VISUAL_QA.json').read_text())
    for key, name in [('source_sha256', 'INTERNAL_RESEARCH_GUIDE.md'),
                      ('docx_sha256', 'INTERNAL_RESEARCH_GUIDE.docx'),
                      ('pdf_sha256', 'INTERNAL_RESEARCH_GUIDE.pdf')]:
        if qa.get(key) != sha(root / name):
            problems.append('QA not bound to current ' + name)
    if not (qa['status'] == 'PASS' and qa['all_pages_inspected_original_resolution'] is True
            and len(qa['pages']) == 9 and all(r['visual_status'] == 'PASS' for r in qa['pages'])):
        problems.append('Visual review incomplete')
    receipt = json.loads((root / 'CONSISTENCY_CHECK.json').read_text())
    if not (receipt['status'] == 'PASS' and receipt['checks_failed'] == 0 and
            receipt['index_sha256'] == sha(root / 'EVIDENCE_INDEX.json') and
            receipt['checker_sha256'] == sha(root / 'check_consistency.py')):
        problems.append('Consistency receipt missing, stale or failed')
    print(json.dumps({'status': 'PASS' if not problems else 'FAIL', 'files': len(manifest['files']),
                      'problems': problems, 'academic_submission_ready': False,
                      'scope': 'Package integrity, local links and artifact-bound visual/consistency receipts only.'}, indent=2))
    raise SystemExit(bool(problems))


if __name__ == '__main__':
    main()
