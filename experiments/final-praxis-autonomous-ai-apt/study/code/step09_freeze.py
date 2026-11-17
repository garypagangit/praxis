"""Step 9: Freeze 1 (design section 10). NOT part of the preprocessing run:
it is written only on the user's word, after the review before the freeze.

Freeze 1 = hashes of the code, the verification report, the step reports,
the ledgers, the cleaned and windowed outputs, the command list, the labels
and the split file. Set-aside files are listed with their hashes as well.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_config as C
import s3_io as IO


def main():
    if "--confirm" not in sys.argv:
        raise SystemExit("Freeze 1 is written only after the pre-freeze review: run with --confirm")
    root = C.out_root()
    path = os.path.join(root, "reports", "FREEZE_1.json")
    if os.path.exists(path):
        raise SystemExit("FREEZE_1.json exists; it is never overwritten")
    summary = IO.read_json(os.path.join(root, "reports", "08_summary.json"))
    if not summary or summary["result"] != "PASS":
        raise SystemExit("chain check has not passed")
    files = {}
    for sub in ("code", "reports", "data", "set_aside"):
        for dirpath, dirs, names in os.walk(os.path.join(root, sub)):
            dirs.sort()
            dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
            for name in sorted(names):
                if name.endswith(".tmp") or name.endswith(".pyc") or name == ".DS_Store":
                    continue
                p = os.path.join(dirpath, name)
                sha, size = IO.sha256_file(p)
                files[os.path.relpath(p, root)] = dict(sha256=sha, bytes=size)
    IO.write_json(path, dict(freeze="Freeze 1", code_version=C.CODE_VERSION, design=C.DESIGN_DOC,
                             files=files, n_files=len(files)))
    print("Freeze 1 written:", len(files), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
