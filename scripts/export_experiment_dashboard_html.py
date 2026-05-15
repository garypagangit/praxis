from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


CSS = """:root{--ink:#111827;--muted:#4b5563;--line:#d1d5db;--soft:#f8fafc;--blue:#1d4ed8;--blue-soft:#dbeafe}*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",Arial,sans-serif;color:var(--ink);background:#eef2f7;line-height:1.55}main{max-width:1220px;margin:28px auto;background:white;padding:42px 48px;border:1px solid #e5e7eb;box-shadow:0 18px 60px rgba(15,23,42,.10)}h1{font-size:34px;line-height:1.15;margin:0 0 18px;padding-bottom:14px;border-bottom:4px solid var(--blue)}h2{font-size:23px;margin-top:34px;padding-bottom:6px;border-bottom:1px solid var(--line)}p{margin:12px 0}li{margin:5px 0}code{background:#f3f4f6;border:1px solid #e5e7eb;padding:1px 5px;border-radius:4px;font-family:Consolas,"Liberation Mono",monospace;font-size:.93em}pre{background:#111827;color:#f9fafb;padding:16px;overflow:auto;border-radius:8px}pre code{background:transparent;border:0;color:inherit;padding:0}.table-wrap{overflow-x:auto;margin:16px 0 24px;border:1px solid var(--line);border-radius:8px}table{width:100%;border-collapse:collapse;min-width:820px}th{background:var(--blue-soft);color:#0f172a;font-weight:700;text-align:left}th,td{border-bottom:1px solid #e5e7eb;padding:9px 11px;vertical-align:top}tr:nth-child(even)td{background:var(--soft)}tr:last-child td{border-bottom:0}.meta{color:var(--muted);font-size:13px;margin-bottom:24px}.print-note{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}@media print{body{background:white}main{box-shadow:none;border:0;margin:0;max-width:none;padding:20px}.table-wrap{overflow:visible}}"""


def inline(text: str) -> str:
    out = html.escape(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def is_table_sep(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    in_ul = False
    in_ol = False
    i = 0

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            close_lists()
            if in_code:
                in_code = False
                out.append("</code></pre>")
            else:
                in_code = True
                lang = stripped[3:].strip()
                cls = f' class="language-{html.escape(lang)}"' if lang else ""
                out.append(f"<pre><code{cls}>")
            i += 1
            continue
        if in_code:
            out.append(html.escape(line))
            i += 1
            continue
        if not stripped:
            flush_paragraph()
            close_lists()
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            flush_paragraph()
            close_lists()
            header = split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append('<div class="table-wrap"><table>')
            out.append("<thead><tr>" + "".join(f"<th>{inline(cell)}</th>" for cell in header) + "</tr></thead>")
            out.append("<tbody>")
            for row in rows:
                cells = (row + [""] * (len(header) - len(row)))[: len(header)]
                out.append("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in cells) + "</tr>")
            out.append("</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            i += 1
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
            i += 1
            continue
        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline(ordered.group(1))}</li>")
            i += 1
            continue
        close_lists()
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    close_lists()
    return "\n".join(out)


def export_dashboard(source: Path, output: Path, date_label: str) -> None:
    body = markdown_to_html(source.read_text(encoding="utf-8"))
    document = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Experiment Current Dashboard</title><style>{CSS}</style></head>
<body><main><div class="meta">Exported from <code>{html.escape(str(source))}</code> on {html.escape(date_label)}.</div>
{body}
<div class="print-note">Open this file directly in a browser, or print to PDF for a shareable snapshot.</div></main></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(output)
    print(output.resolve())
    print(output.stat().st_size)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("reports/EXPERIMENT_CURRENT_DASHBOARD_20260513.md"))
    parser.add_argument("--output", type=Path, default=Path("reports/EXPERIMENT_CURRENT_DASHBOARD_20260514.html"))
    parser.add_argument("--date-label", default="2026-05-14")
    args = parser.parse_args()
    export_dashboard(args.source, args.output, args.date_label)


if __name__ == "__main__":
    main()
