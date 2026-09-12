"""One command: resume blinded review, audit it, then close citation exceptions."""
import argparse,subprocess,sys
from pathlib import Path

def main():
    here=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=here/'outputs')
    parser.add_argument('--completion',type=Path,default=here/'completion')
    args=parser.parse_args();source=args.source.resolve();out=args.out.resolve()
    steps=[['run_review.py','--source',str(source),'--out',str(out),'--execute'],
           ['report_review.py','--out',str(out)],
           ['complete_citations.py','--source',str(source),'--review',str(out),'--out',str(args.completion.resolve())]]
    for script,*arguments in steps:subprocess.run([sys.executable,str(here/script),*arguments],check=True)

if __name__=='__main__':main()
