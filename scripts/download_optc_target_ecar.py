from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
URL_MAP_PATH = REPO_ROOT / "external" / "PIDSMaker" / "dataset_preprocessing" / "optc" / "google_drive_urls.py"

DAY_TO_RELATIVE_DIR = {
    "1": "evaluation/23Sep19-red/",
    "2": "evaluation/24Sep19/",
    "3": "evaluation/25Sept/",
}


def load_url_map() -> dict[str, list[tuple[str, str]]]:
    spec = importlib.util.spec_from_file_location("optc_google_drive_urls", URL_MAP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {URL_MAP_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.url_map


def host_to_pidmaker_key(host: str) -> str:
    match = re.search(r"(\d+)$", host.lower())
    if not match:
        raise ValueError(f"Expected host like sysclient0501, got {host!r}")
    numeric = int(match.group(1))
    return f"optc_h{numeric:03d}"


def resolve_target(
    host: str,
    output_root: Path,
    day: str | None = None,
    relative_dir: str | None = None,
) -> dict[str, Any]:
    url_map = load_url_map()
    key = host_to_pidmaker_key(host)
    if relative_dir is None:
        if day is None:
            raise ValueError("Either day or relative_dir must be provided.")
        relative_dir = DAY_TO_RELATIVE_DIR[str(day)]
    if not relative_dir.endswith("/"):
        relative_dir += "/"
    if key not in url_map:
        raise KeyError(f"No OpTC URL map entry for {host!r} ({key}).")
    for item_relative_dir, url in url_map[key]:
        if item_relative_dir == relative_dir:
            return {
                "host": host.lower(),
                "day": str(day) if day is not None else "",
                "pidmaker_key": key,
                "relative_dir": relative_dir,
                "url": url,
                "output_dir": str(output_root / relative_dir),
            }
    raise KeyError(f"No OpTC URL for {host!r} day {day} ({relative_dir}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one targeted OpTC eCAR host/day or benign folder.")
    parser.add_argument("--host", required=True, help="Target OpTC host, e.g. sysclient0501.")
    parser.add_argument("--day", choices=sorted(DAY_TO_RELATIVE_DIR), help="OpTC red-team day: 1, 2, or 3.")
    parser.add_argument(
        "--relative-dir",
        help="Exact PIDSMaker OpTC relative folder, e.g. benign/20-23Sep19/. Overrides --day.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("external/datasets/optc/ecar"),
        help="Output root that will receive the evaluation/<day> folder.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved URL and output path without downloading.")
    args = parser.parse_args()

    target = resolve_target(args.host, args.output_root, args.day, args.relative_dir)
    print(json.dumps(target, indent=2, sort_keys=True))
    if args.dry_run:
        return

    try:
        import gdown
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency `gdown`. Install it with:\n"
            ".\\.venv-diag\\Scripts\\python.exe -m pip install gdown"
        ) from exc

    out_dir = Path(target["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    gdown.download_folder(url=target["url"], output=str(out_dir), quiet=False, resume=True)
    print(json.dumps({"downloaded_to": str(out_dir)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
