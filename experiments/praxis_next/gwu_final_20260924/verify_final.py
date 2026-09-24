"""Bind completed scientific and full-page document checks to the delivered edition."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import argparse

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(finalize=False):
    build=read('BUILD_RECEIPT.json');render=read('RENDER_RECEIPT.json')
    assert sha(HERE/'manuscript.md')==build['manuscript_sha256']==render['source_sha256']
    assert sha(HERE/'abstract.md')==build['abstract_sha256']==render['abstract_sha256']
    assert sha(HERE/'assemble_manuscript.py')==build['source_sha256']
    assert sha(HERE/'render_gwu.py')==render['renderer_sha256']
    assert sha(HERE/'render_uno.py')==render['uno_helper_sha256']
    for path,expected in build['input_sha256'].items():
        assert sha(REPO/path)==expected, path
    pdf=REPO/'output/pdf/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.pdf'
    docx=REPO/'output/doc/gwu_praxis_20260924/Gary_Pagan_GWU_APT_Evaluation_Praxis.docx'
    assert sha(pdf)==render['pdf_sha256'] and sha(docx)==render['docx_sha256']
    assert render['pages']==120 and render['figures']==10 and render['tables']==31
    assert len(render['equations'])==25
    assert not render['marker_tokens_remaining']
    assert not any(x['outside_page'] for x in render['geometry'])
    assert read('models/MODEL_AUDIT.json')['status']=='PASS'
    assert read('models/MANUSCRIPT_REVIEW.json')['status']=='METHODS_AND_MATHEMATICS_PASS'
    assert read('results/MANUSCRIPT_REVIEW.json')['status']=='PASS_WITH_ALL_REQUESTED_CORRECTIONS_RESOLVED'
    audit=read('results/PUBLICATION_DOCUMENT_AUDIT.json')
    assert audit['status']=='PASS' and audit['inputs']['pdf']['sha256']==sha(pdf)
    assert audit['inputs']['docx']['sha256']==sha(docx)
    coverage=set();receipt_hashes={}
    for name in ['ROOT_VISUAL_REVIEW.json','models/VISUAL_REVIEW.json',
                 'results/VISUAL_REVIEW.json','reference/VISUAL_REVIEW.json']:
        review=read(name);assert review['status']=='PASS',name
        assert review['pdf_sha256']==sha(pdf),name
        receipt_hashes[name]=sha(HERE/name)
        if name.startswith('ROOT'):
            pages=review['physical_pages_covered']
        elif name.startswith('models'):
            pages=[x['pdf_page_one_based'] for x in review['reviewed_pages']]
        elif name.startswith('results'):
            pages=review['assigned_pages']
        else:
            pages=review['final_full_resolution_pages_viewed']+[x['final_page'] for x in review['final_exact_pixel_equivalent_pages']]
        coverage.update(pages)
    assert coverage==set(range(1,121)),sorted(set(range(1,121))-coverage)
    counts=read('results/COVERAGE.json')
    assert counts['total_configuration_records']==588 and counts['group_mean_rows']==308
    assert counts['class_metric_rows']==1764 and counts['confusion_count_rows']==5880
    assert len(read('references.json'))==30
    report={'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),
            'manuscript_sha256':sha(HERE/'manuscript.md'), 'pdf_sha256':sha(pdf),'docx_sha256':sha(docx),
            'pages':120,'full_visual_coverage':sorted(coverage),'visual_receipt_sha256':receipt_hashes,
            'figures':10,'tables':31,'display_equations':25,'references':30,
            'configuration_records':588,'printed_group_means':308,
            'input_bindings_verified':len(build['input_sha256']),
            'new_model_fits':0,'institutional_approval_asserted':False,
            'verification_source_sha256':sha(Path(__file__)),
            'scope':'Scientific source checks, document integrity and full visual coverage. Same-team computational/document review; author and institutional review are separate.'}
    if finalize:
        (HERE/'PUBLICATION_QA.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        render['status']='PASS';render['visual_review']='PASS'
        render['visual_review_receipt']='PUBLICATION_QA.json'
        (HERE/'RENDER_RECEIPT.json').write_text(json.dumps(render,indent=2)+'\n',encoding='utf-8')
        build['status']='ASSEMBLED_RENDERED_AND_REVIEWED'
        (HERE/'BUILD_RECEIPT.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['full_visual_coverage','visual_receipt_sha256']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finalize',action='store_true',help='Write assembly review receipts; default is read-only verification.')
    verify(parser.parse_args().finalize)
