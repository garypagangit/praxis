"""Render the findings revision with compact, readable paragraph spacing.

The original paper builder and its historical receipt are preserved unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
from docx.shared import Pt
from build_document import Renderer


def build(source, output, repo_url):
    renderer = Renderer(source, repo_url, None)
    normal = renderer.doc.styles['Normal'].paragraph_format
    normal.line_spacing = 1.05
    normal.space_after = Pt(4)
    document = renderer.render()
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'docx_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'headings': renderer.headings, 'tables': renderer.tables, 'images': renderer.images,
        'hyperlinks': renderer.links, 'local_only_links': renderer.local_only_links,
        'body_font_points': 11, 'body_line_spacing': 1.05, 'body_space_after_points': 4,
        'rendered_visual_qa': 'REQUIRED_SEPARATELY'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo-url', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.repo_url)))
