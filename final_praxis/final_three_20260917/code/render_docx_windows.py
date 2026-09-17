"""Use the canonical renderer with a Windows-correct LibreOffice profile URI.

The bundled renderer concatenates file:// with a Windows backslash path, which
leaves LibreOffice waiting at profile initialization. Only conversion dispatch
is adapted; page rendering, sizing, and output remain the canonical workflow.
"""
import importlib.util
import os
import subprocess
from pathlib import Path

SKILL = Path("C:/Users/garyp/.codex/plugins/cache/openai-primary-runtime/documents/26.630.12135/skills/documents/render_docx.py")
spec = importlib.util.spec_from_file_location("canonical_docx_renderer", SKILL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def convert(doc_path, user_profile, convert_tmp_dir, stem, verbose):
    command = ["C:/Program Files/LibreOffice/program/soffice.exe", "-env:UserInstallation=" + Path(user_profile).resolve().as_uri(), "--headless", "--norestore", "--nofirststartwizard", "--convert-to", "pdf", "--outdir", convert_tmp_dir, doc_path]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, env=os.environ.copy())
    output = Path(convert_tmp_dir) / (stem + ".pdf")
    return (str(output) if output.exists() and output.stat().st_size else "", result.stdout + result.stderr)

module.convert_to_pdf = convert
if __name__ == "__main__":
    module.main()
