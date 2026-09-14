"""Package read-only audit source separately from frozen experimental code."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
FILES=("audit_results.py","extension_checks.py","statistical_checks.py",
       "test_audit_results.py","test_extension_checks.py","test_statistical_checks.py","README.md")


def main():
    captured={name:(HERE/name).read_bytes() for name in FILES}
    target=HERE/"AUDIT_SOURCE_BUNDLE.tar.gz"
    with tarfile.open(target,"w:gz") as archive:
        for name,payload in captured.items():
            info=tarfile.TarInfo(name)
            info.size=len(payload);info.mtime=0;info.mode=0o644
            archive.addfile(info,io.BytesIO(payload))
    report=dict(scope="Read-only artifact audit source, no experimental data or model execution",
                archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),archive_bytes=target.stat().st_size,
                files_sha256={name:hashlib.sha256(payload).hexdigest() for name,payload in captured.items()},
                original_protocol_sha256="11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a",
                extension_protocol_sha256="9e6ba43fd988b47273c13ae4a5dc569640d210d2178103afaab964ed2bf236c3")
    (HERE/"AUDIT_SOURCE_BUNDLE.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
