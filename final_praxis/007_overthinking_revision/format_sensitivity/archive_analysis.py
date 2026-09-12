"""Archive the completed offline analysis, excluding already-archived source responses."""
import hashlib,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    target=HERE/'outputs'/'analysis_archive.zip'
    files=sorted(p for p in (HERE/'outputs').glob('*.json'))
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.name)
        archive.write(HERE/'PROTOCOL.md','PROTOCOL.md')
        archive.writestr('archive_manifest.json',json.dumps(manifest,indent=2))
    print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
