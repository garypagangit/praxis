"""Read-only, independent structural/geometry audit of the final publication files.

Run after the renderer has finished. This script never changes the PDF, DOCX,
manuscript, or experiment evidence. Visual review is recorded separately.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def norm(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip()


def number_only(text):
    return re.fullmatch(r'(?:\d+|[ivxlcdm]+)', text.strip(), re.I) is not None


def audit(pdf_path, docx_path, source_path):
    failures, warnings = [], []
    bindings = {key: {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}
                for key, path in [('pdf', pdf_path), ('docx', docx_path), ('manuscript', source_path)]}
    doc = fitz.open(pdf_path)
    pages, all_text, all_fonts = [], [], set()
    for i, page in enumerate(doc):
        width, height = page.rect.width, page.rect.height
        spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
                 for line in b['lines'] for s in line['spans'] if s['text'].strip()]
        for span in spans:
            all_fonts.add(span['font'])
        images = page.get_image_info()
        outside = []
        margin = []
        substantive = []
        for span in spans:
            rect = fitz.Rect(span['bbox'])
            footer = number_only(span['text']) and rect.y0 > height - 58
            if not footer:
                substantive.append(span)
            if rect.x0 < -1 or rect.y0 < -1 or rect.x1 > width + 1 or rect.y1 > height + 1:
                outside.append({'kind': 'text', 'text': span['text'], 'bbox': list(rect)})
            # Body pages use 1.25-inch side margins and 1-inch top/bottom margins.
            # A 6-point glyph tolerance avoids treating font descenders as clipping.
            if not footer and (rect.x0 < 84 or rect.x1 > width - 84 or
                               rect.y0 < 66 or rect.y1 > height - 66):
                margin.append({'text': span['text'], 'bbox': list(rect)})
        for info in images:
            rect = fitz.Rect(info['bbox'])
            if rect.x0 < -1 or rect.y0 < -1 or rect.x1 > width + 1 or rect.y1 > height + 1:
                outside.append({'kind': 'image', 'bbox': list(rect)})
        blank = not substantive and not images
        if outside:
            failures.append({'page': i + 1, 'issue': 'outside_physical_page', 'objects': outside})
        if blank:
            failures.append({'page': i + 1, 'issue': 'blank_except_page_number'})
        if margin:
            warnings.append({'page': i + 1, 'issue': 'body_margin_review', 'objects': margin})
        text = page.get_text()
        all_text.append(text)
        pages.append({'page': i + 1, 'width_pt': width, 'height_pt': height,
                      'orientation': 'landscape' if width > height else 'portrait',
                      'extracted_characters': len(text), 'displayed_images': len(images),
                      'blank_except_page_number': blank, 'outside_page': outside,
                      'body_margin_flags': margin,
                      'minimum_extracted_text_font_pt': min((s['size'] for s in spans), default=None)})
    pdf_text = norm('\n'.join(all_text))
    forbidden = ['\ufffd', '\u25a1', '@@TOC@@', '@@FIGURES@@', '@@TABLES@@',
                 'Error! Reference source not found', 'Error! Bookmark not defined']
    substitutions = {token: pdf_text.count(token) for token in forbidden if token in pdf_text}
    if substitutions:
        failures.append({'issue': 'unresolved_marker_or_replacement_glyph', 'found': substitutions})
    checkpoints = ['0.7148', '0.7379', '85.18%', '76.25%', '0.0632', '0.7365',
                   '0.7582', '1,722', '3,442', '192,193', '208,094', '259,120',
                   '86,691', '65,000', '2022a', '2022b', '19/27', '17/24',
                   'Chapter 1', 'Chapter 2', 'Chapter 3', 'Chapter 4', 'Chapter 5']
    checkpoint_result = {text: norm(text) in pdf_text for text in checkpoints}
    missing = [text for text, present in checkpoint_result.items() if not present]
    if missing:
        failures.append({'issue': 'missing_semantic_checkpoint', 'values': missing})

    with zipfile.ZipFile(docx_path) as z:
        corrupt = z.testzip()
        if corrupt:
            failures.append({'issue': 'docx_zip_corruption', 'entry': corrupt})
        names = set(z.namelist())
        main = ET.fromstring(z.read('word/document.xml'))
        styles = ET.fromstring(z.read('word/styles.xml'))
        paragraphs = main.findall('.//w:p', NS)
        text = norm(' '.join(e.text or '' for e in main.findall('.//w:t', NS)))
        missing_docx = [s for s in checkpoints if norm(s) not in text]
        if missing_docx:
            failures.append({'issue': 'docx_missing_semantic_checkpoint', 'values': missing_docx})
        docx_markers = {t: text.count(t) for t in forbidden if t in text}
        if docx_markers:
            failures.append({'issue': 'docx_marker_or_replacement', 'found': docx_markers})
        headings = Counter()
        for p in paragraphs:
            style = p.find('w:pPr/w:pStyle', NS)
            if style is not None:
                val = style.get(f"{{{NS['w']}}}val", '')
                if val.lower().startswith('heading'):
                    headings[val] += 1
        tables = main.findall('.//w:tbl', NS)
        header_repeat = []
        for index, table in enumerate(tables, 1):
            rows = table.findall('w:tr', NS)
            repeated = bool(rows and rows[0].find('w:trPr/w:tblHeader', NS) is not None)
            header_repeat.append({'table': index, 'rows': len(rows), 'first_row_repeats': repeated})
            if not repeated:
                warnings.append({'issue': 'table_without_repeating_header', 'table': index})
        sections = []
        for section in main.findall('.//w:sectPr', NS):
            size = section.find('w:pgSz', NS)
            margin = section.find('w:pgMar', NS)
            def attrs(element):
                return {k.rsplit('}', 1)[-1]: v for k, v in element.attrib.items()} if element is not None else {}
            sections.append({'size_twips': attrs(size), 'margins_twips': attrs(margin)})
        broken_internal = []
        external_count = 0
        for name in sorted(n for n in names if n.endswith('.rels')):
            rels = ET.fromstring(z.read(name))
            base = posixpath.dirname(posixpath.dirname(name)) if name != '_rels/.rels' else ''
            for rel in rels:
                if rel.get('TargetMode') == 'External':
                    external_count += 1
                    continue
                target = rel.get('Target', '').split('#')[0]
                resolved = posixpath.normpath(posixpath.join(base, target)).lstrip('/')
                if resolved not in names:
                    broken_internal.append({'part': name, 'target': target, 'resolved': resolved})
        if broken_internal:
            failures.append({'issue': 'docx_broken_internal_relationships', 'values': broken_internal})
        normal = next((e for e in styles.findall('w:style', NS)
                       if e.get(f"{{{NS['w']}}}styleId") == 'Normal'), None)
        normal_xml = ET.tostring(normal, encoding='unicode') if normal is not None else None
        fields = [e.text for e in main.findall('.//w:instrText', NS) if e.text]
        docx_result = {'zip_integrity': corrupt is None, 'paragraphs': len(paragraphs),
                       'tables': len(tables), 'table_headers': header_repeat,
                       'heading_styles': dict(headings), 'sections': sections,
                       'media_parts': sum(n.startswith('word/media/') for n in names),
                       'external_relationships': external_count,
                       'broken_internal_relationships': broken_internal,
                       'normal_style_xml': normal_xml,
                       'native_index_fields': [f for f in fields if 'TOC ' in f],
                       'missing_semantic_checkpoints': missing_docx}
    # Prevent a review receipt from binding a mixture of concurrent builds.
    for key, path in [('pdf', pdf_path), ('docx', docx_path), ('manuscript', source_path)]:
        if sha(path) != bindings[key]['sha256']:
            failures.append({'issue': 'input_changed_during_audit', 'input': key})
    return {'status': 'FAIL' if failures else ('PASS_WITH_MARGIN_REVIEW_FLAGS' if warnings else 'PASS'),
            'utc': datetime.now(timezone.utc).isoformat(), 'script_sha256': sha(__file__),
            'scope': 'Independent read-only PDF geometry, blank-page, marker, selected semantic-checkpoint and DOCX-structure audit. No model fitting or evidence changes.',
            'inputs': bindings, 'pdf_pages': len(doc), 'pdf_fonts': sorted(all_fonts),
            'semantic_checkpoints': checkpoint_result, 'pages': pages, 'docx': docx_result,
            'failures': failures, 'warnings': warnings,
            'visual_review': 'Recorded separately in VISUAL_REVIEW.json; text extraction is not visual verification.',
            'limits': 'Margin flags require visual adjudication; extracted text cannot detect every graphical overlap or validate equation images. Semantic checkpoints are selected, not a claim of exhaustive source-to-PDF textual equivalence. External hyperlinks were not fetched. This does not guarantee institutional approval or publication acceptance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=ROOT/'output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf')
    parser.add_argument('--docx', type=Path, default=ROOT/'output/doc/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.docx')
    parser.add_argument('--source', type=Path, default=HERE.parent/'manuscript.md')
    parser.add_argument('--output', type=Path, default=HERE/'PUBLICATION_DOCUMENT_AUDIT.json')
    args = parser.parse_args()
    result = audit(args.pdf, args.docx, args.source)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'pages': result['pdf_pages'],
                      'failures': result['failures'], 'warning_count': len(result['warnings'])}, indent=2))
