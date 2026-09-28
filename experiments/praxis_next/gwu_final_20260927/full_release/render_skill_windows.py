"""Use the document skill renderer with a Windows-correct profile URI."""
from pathlib import Path
import importlib.util,subprocess
SKILL=Path('C:/Users/garyp/.codex/plugins/cache/openai-primary-runtime/documents/26.630.12135/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('docskill',SKILL);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def run(cmd,env,verbose):
 fixed=[]
 for arg in cmd:
  prefix='-env:UserInstallation=file://'
  fixed.append('-env:UserInstallation='+Path(arg[len(prefix):]).resolve().as_uri() if arg.startswith(prefix) else arg)
 fixed[0]='C:/Program Files/LibreOffice/program/soffice.com'
 result=subprocess.run(fixed,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
 if verbose:print(result.stdout,result.stderr)
 return result
m._run_cmd=run
def convert(pdf_path,dpi=96,output_folder=None,**kwargs):
 import pymupdf
 doc=pymupdf.open(pdf_path);paths=[]
 for i,page in enumerate(doc):
  p=Path(output_folder)/f'skill-render-{i+1:03d}.png';page.get_pixmap(dpi=dpi).save(p);paths.append(str(p))
 return paths
m.convert_from_path=convert
m.rasterize('C:/Users/garyp/OneDrive/Documents/codex/output/praxis_final_20260927/Gary_Pagan_Final_Praxis.docx','C:/w/gwu_final_document_skill_qa_20260927',96,verbose=True,emit_pdf=True)
