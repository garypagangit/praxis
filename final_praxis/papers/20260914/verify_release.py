"""Offline publication checks; no inference, network access, or source mutations."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import urllib.parse
import zipfile

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE / 'RELEASE_VERIFICATION.json')
    args = parser.parse_args()
    errors, checks, documents = [], [], []

    def check(name, passed, detail=None):
        checks.append({'check': name, 'pass': bool(passed), 'detail': detail})
        if not passed:
            errors.append(name)

    for name in ('01_cti', '02_008', '03_px055'):
        folder = HERE / name
        required = ['PAPER.md', 'PAPER.docx', 'PAPER.pdf', 'README.md', 'BUILD_MANIFEST.json', 'VISUAL_QA.json']
        for filename in required:
            check(f'{name}/{filename} exists', (folder / filename).is_file())
        if not all((folder / f).is_file() for f in required):
            continue
        build = json.loads((folder / 'BUILD_MANIFEST.json').read_text(encoding='utf-8-sig'))
        visual = json.loads((folder / 'VISUAL_QA.json').read_text(encoding='utf-8-sig'))
        for field, filename in [('source_sha256', 'PAPER.md'), ('docx_sha256', 'PAPER.docx'), ('pdf_sha256', 'PAPER.pdf')]:
            digest = sha(folder / filename)
            check(f'{name} build {field}', digest == build.get(field))
            check(f'{name} visual {field}', digest == visual.get(field))
        check(f'{name} visual review passed', visual.get('status') == 'PASS')
        page_checks = visual.get('page_checks', [])
        complete_pages = {p['page'] for p in page_checks if p.get('status', p.get('visual_status')) == 'PASS'} == set(range(1, build['page_count'] + 1))
        original_resolution = visual.get('all_pages_inspected_original_resolution') is True or 'original' in visual.get('method', '').lower()
        check(f'{name} every page reviewed', complete_pages and original_resolution)
        check(f'{name} visual page count', visual.get('page_count') == build.get('page_count'))
        check(f'{name} no text beyond safe page bounds', all(not row['outside_safe_bounds'] for row in build['page_geometry']))
        text = (folder / 'PAPER.md').read_text(encoding='utf-8')
        lower = text.lower()
        check(f'{name} executive summary before abstract', 0 <= lower.find('## executive summary') < lower.find('## abstract'))
        check(f'{name} completed chapter structure', all(f'## chapter {i}.' in lower for i in range(1, 6)) and '## references' in lower)
        check(f'{name} complete manuscript length', len(text.split()) >= 4000, len(text.split()))
        with zipfile.ZipFile(folder / 'PAPER.docx') as docx:
            xml = docx.read('word/document.xml').decode('utf-8')
            check(f'{name} editable native math', '<m:oMath' in xml)
        figure_targets = re.findall(r'^!\[[^\]]*\]\(([^)]+)\)', text, re.MULTILINE)
        check(f'{name} figure count agrees', len(figure_targets) == len(build.get('figures', [])))
        for target, figure in zip(figure_targets, build.get('figures', [])):
            path = (folder / target).resolve()
            check(f'{name} figure hash: {path.name}', path.is_file() and sha(path) == figure['sha256'])
        documents.append({'package': name, 'pages': build['page_count'], 'words_approx': len(text.split()), 'source_sha256': sha(folder / 'PAPER.md'), 'pdf_sha256': sha(folder / 'PAPER.pdf')})

    # Reader-facing documents, not historical protocols whose original relative
    # links may intentionally describe the earlier repository layout.
    readable = [HERE / 'README.md'] + list((HERE / 'research_opportunities').glob('*.md'))
    readable += [HERE / name / filename for name in ('01_cti', '02_008', '03_px055') for filename in ('README.md', 'PAPER.md')]
    links_checked = 0
    for path in readable:
        if not path.exists():
            continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            clean = urllib.parse.unquote(target.split('#')[0])
            resolved = (path.parent / clean).resolve()
            check(f'local link {path.relative_to(HERE)} -> {target}', resolved.exists())
            links_checked += 1
    largest = []
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            size = path.stat().st_size
            if size > 10 * 1024 * 1024:
                largest.append({'path': str(path.relative_to(HERE)), 'bytes': size})
            check(f'GitHub file-size limit: {path.relative_to(HERE)}', size < 100 * 1024 * 1024)
    report = {'status': 'FAIL' if errors else 'PASS', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'documents': documents, 'checks_passed': sum(c['pass'] for c in checks), 'checks_total': len(checks), 'local_links_checked': links_checked, 'largest_files': largest, 'errors': errors, 'checks': checks, 'scope': 'Document/evidence-link integrity and recorded visual QA. Statistical reproduction is separately documented in each package. No scientific novelty, semantic validity, or external approval certification.', 'network_calls': 0, 'inference_calls': 0}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'checks_passed', 'checks_total', 'local_links_checked', 'errors')}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
