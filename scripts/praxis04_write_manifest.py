from __future__ import annotations

import argparse

from praxis.praxis04.data_loader import write_csv_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Write SHA-256 manifest for CIC-IDS2018 CSVs.")
    parser.add_argument("--data-dir", default="data/cic-ids-2018")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    output = write_csv_manifest(args.data_dir, args.output)
    print(f"Wrote manifest: {output}")


if __name__ == "__main__":
    main()

