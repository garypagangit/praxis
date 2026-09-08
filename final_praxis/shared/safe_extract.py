"""Merge a trusted task archive without replacing different existing bytes."""
import sys
import zipfile
from pathlib import Path

archive_path, destination = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive_path) as archive:
    if archive.testzip():
        raise ValueError("Archive CRC failure")
    for member in archive.infolist():
        if member.is_dir():
            continue
        relative = Path(member.filename)
        target = (destination / relative).resolve()
        if relative.is_absolute() or destination not in target.parents or ".." in relative.parts:
            raise ValueError("Unsafe archive member")
        data = archive.read(member)
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError("Refusing to overwrite different bytes: " + str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
print("Archive merged; existing matching evidence preserved.")
