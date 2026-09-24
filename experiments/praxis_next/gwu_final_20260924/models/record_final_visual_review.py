"""Bind final polish review to direct inspections and identical prior page PNGs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PDF = REPO / 'output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf'
PAGE_ROOT = Path('C:/w/gwu_final_document_qa_20260924')
FINAL_SHA = '0d05651384cf81300b7b13eb8a47cde8c93cf5ed1aac005a1f1660b8c9a0c7bd'
BASE_SHA = '84a8f9b7de30c9a815154439e4f7b0272ec7625e7842aa8124e4a142cc62b941'
DIRECT = {30, 31, 38, 39, 40, 41, 49, 50, 51, 57, 58, 59}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sha(PDF) != FINAL_SHA:
        raise AssertionError('Final PDF changed since direct visual inspection')
    archive = HERE / 'VISUAL_REVIEW_PRE_POLISH_84a8.json'
    current = HERE / 'VISUAL_REVIEW.json'
    previous_path = archive if archive.exists() else current
    previous_bytes = previous_path.read_bytes()
    previous = json.loads(previous_bytes.decode('utf-8'))
    if previous['pdf_sha256'] != BASE_SHA:
        raise AssertionError('Wrong baseline review')
    old_pages = {r['pdf_page_one_based']: r for r in previous['reviewed_pages']}
    map_path = HERE.parent / 'reference/POLISH_PAGE_MAP.json'
    mapping = json.loads(map_path.read_text(encoding='utf-8'))
    if mapping['baseline_pdf_sha256'] != BASE_SHA or mapping['final_pdf_sha256'] != FINAL_SHA:
        raise AssertionError('Renderer page map binds different PDFs')
    mapped = {r['final_page']: r for r in mapping['mapping']}
    pages = []
    for number in range(30, 62):
        path = PAGE_ROOT / f'page_{number:03d}.png'
        image_sha = sha(path)
        if number in DIRECT:
            inspection = 'Direct full-page view_image at original resolution after final hash confirmation.'
            prior_page = None
        else:
            prior_page = mapped[number]['baseline_exact_pixel_page']
            if prior_page not in old_pages:
                raise AssertionError('Uninspected mapped page')
            if old_pages[prior_page]['image_sha256'] != image_sha:
                raise AssertionError('PNG bytes differ from previously fully inspected page: ' + str(number))
            inspection = 'PNG byte-identical to the prior fully inspected page; SHA verified independently of renderer map.'
        pages.append({'pdf_page_one_based': number, 'printed_page_number': number - 10,
                      'image': str(path), 'image_sha256': image_sha,
                      'inspection': inspection, 'prior_pdf_page_if_identical': prior_page})
    if not archive.exists():
        archive.write_bytes(previous_bytes)
    receipt = {
        'status': 'PASS', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'reviewer': '/root/px080_context_selector',
        'pdf_path': str(PDF), 'pdf_sha256': FINAL_SHA, 'pdf_page_count': 120,
        'scope': 'Final model/data/math segment pages30–61; twelve changed pages directly re-inspected, twenty unchanged page PNGs independently SHA-matched to fully inspected baseline.',
        'reviewed_page_count': 32, 'direct_final_page_inspections': sorted(DIRECT),
        'unchanged_pages_bound_by_PNG_byte_identity': [r['pdf_page_one_based'] for r in pages if r['prior_pdf_page_if_identical'] is not None],
        'reviewed_pages': pages,
        'prior_review': {'file': archive.name, 'sha256': sha(archive), 'pdf_sha256': BASE_SHA},
        'renderer_mapping': {'file': str(map_path), 'sha256': sha(map_path)},
        'findings': [],
        'resolved_findings': [
            {'id': 'V01', 'final_page': 40, 'resolution': 'Multiclass introduction, loss and argmax decision are now together and legible.'},
            {'id': 'V02', 'final_page': 50, 'resolution': 'Ridge introduction and full objective are now together and legible.'}
        ],
        'confirmed': [
            'All changed model and result tables are centered, fully legible, have complete rows and headers, and carry descriptive captions.',
            'No clipped or missing mathematical symbol, text, table entry or graphic label is visible.',
            'No model equation block is split across pages.',
            'Prior figure pages remain byte-identical to the already inspected full-size landscape pages.',
            'All32 pages in the assigned final range are covered by direct inspection or independently verified PNG byte identity.'
        ],
        'limits': 'Review covers this assigned segment only; separate reviewers cover the remaining final PDF pages.'
    }
    current.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'final_pdf_sha256': FINAL_SHA, 'direct_pages': len(DIRECT), 'byte_identical_pages': 32 - len(DIRECT)}))


if __name__ == '__main__':
    main()
