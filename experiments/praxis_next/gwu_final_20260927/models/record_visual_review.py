"""Bind the completed visual inspection; this script does not perform visual QA."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PDF = REPO / 'output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf'
PAGES = Path('C:/w/gwu_final_document_qa_20260924')
EXPECTED_PDF = '84a8f9b7de30c9a815154439e4f7b0272ec7625e7842aa8124e4a142cc62b941'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sha(PDF) != EXPECTED_PDF:
        raise AssertionError('PDF differs from visually inspected version')
    pages = []
    for number in range(31, 63):
        path = PAGES / f'page_{number:03d}.png'
        pages.append({'pdf_page_one_based': number, 'printed_page_number': number - 11,
                      'image': str(path), 'image_sha256': sha(path),
                      'inspection': 'Full-page image inspected at original resolution with view_image; no clipped text, missing math symbols, broken table header, overlap, or illegible content.'})
    receipt = {
        'status': 'PASS_LEGIBILITY_WITH_MINOR_PAGINATION_NOTES',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'reviewer': '/root/px080_context_selector',
        'pdf_path': str(PDF), 'pdf_sha256': EXPECTED_PDF, 'pdf_page_count': 121,
        'scope': 'Full-page visual inspection of every assigned PDF page31 through62 inclusive, with contact sheets used only for navigation.',
        'reviewed_page_count': 32, 'reviewed_pages': pages,
        'method': 'Read PDF skill; inspected original-resolution PNGs using view_image in batches. Re-inspected all32 pages after root confirmed final stable PDF hash. PDF hash checked again at end.',
        'findings': [
            {'id': 'V01', 'severity': 'minor_pagination', 'pages': [40, 41],
             'observation': 'The sentence introducing multiclass data-fit loss and its decision rule is at the end of page40; the complete, legible two-line equation is at the top of page41.',
             'suggestion': 'Keep the colon-ended introduction with the first equation image if another pagination pass is made.',
             'content_missing': False, 'blocking_legibility': False},
            {'id': 'V02', 'severity': 'minor_pagination', 'pages': [50, 51],
             'observation': 'The sentence introducing the Ridge estimate is at the end of page50; the complete, legible Ridge objective begins page51.',
             'suggestion': 'Keep the introduction with the objective if another pagination pass is made.',
             'content_missing': False, 'blocking_legibility': False}
        ],
        'confirmed': [
            'Prepared feature, example, model-count, hyperparameter, comparator and early-results tables fit their pages with readable headers and complete rows.',
            'LightGBM additive/softmax, multiclass loss/argmax, weighted-error/gate, acquisition-gain, gain-per-cost/eligibility, logistic and Ridge expressions render legibly.',
            'All actual equation blocks stay together in this final set; the preliminary split loss/argmax block was corrected.',
            'Metric formulas and temporal-support condition are complete; the longer code-style support condition wraps without losing text.',
            'Landscape figures61–62 preserve all labels, axes, legends, values and captions.',
            'The preliminary isolated Chapter4 numeral is fixed on final page32.',
            'No blank page exists within the inspected range.'
        ],
        'limits': 'This receipt certifies the assigned32 pages only. Other agents inspect remaining pages. Minor introduction/equation separation is disclosed rather than described as corrected.'
    }
    (HERE / 'VISUAL_REVIEW.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'reviewed_page_count': len(pages), 'pdf_sha256': EXPECTED_PDF}))


if __name__ == '__main__':
    main()
