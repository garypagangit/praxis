"""Import only experiment result artifacts; preserve any existing local evidence."""
import argparse
import hashlib
import zipfile
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    count = 0
    with zipfile.ZipFile(args.archive) as archive:
        if archive.testzip():
            raise ValueError("Archive CRC failure")
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            relative = Path(entry.filename)
            pilot_marker = len(relative.parts) == 3 and relative.parts[-1] == "PILOT_PASS.json"
            if relative.is_absolute() or ".." in relative.parts or (len(relative.parts) < 4 and not pilot_marker):
                raise ValueError("Invalid evidence path")
            if relative.parts[0] != "final_praxis" or (relative.parts[2] not in {"runs", "artifacts"} and not pilot_marker):
                raise ValueError("Archive contains a non-result path: " + str(relative))
            target = (root / relative).resolve()
            if root not in target.parents:
                raise ValueError("Path escapes workspace")
            data = archive.read(entry)
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError("Refusing to overwrite different existing evidence: " + str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(data)
            count += 1
    print(f"Imported {count} evidence files; archive SHA256 {hashlib.sha256(args.archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
