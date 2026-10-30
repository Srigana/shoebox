"""Create (or extend) labels.csv for a folder of your own receipts.

    python -m eval.template eval/data/mine

Lists every image and PDF in the folder with blank label columns. Fill them in
by looking at each receipt, not at Shoebox's output, or the score will flatter
the model. Use YYYY-MM-DD dates, plain-number totals (12.50), and one of the
17 category names from app/schemas.py. Leave a cell blank to skip that field.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from app.schemas import CATEGORIES

FIELDS = ["file", "merchant", "date", "total", "category", "notes"]
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".pdf"}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        sys.exit("Usage: python -m eval.template FOLDER")
    folder = Path(args[0])
    if not folder.is_dir():
        sys.exit(f"Not a folder: {folder}")
    labels = folder / "labels.csv"
    rows: list[dict[str, str]] = []
    if labels.exists():
        with labels.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    known = {r["file"] for r in rows}
    new = [p.name for p in sorted(folder.iterdir()) if p.suffix.lower() in EXTS and p.name not in known]
    rows += [{k: (name if k == "file" else "") for k in FIELDS} for name in new]
    with labels.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{labels}: {len(rows)} receipts ({len(new)} new). Valid categories:")
    print("  " + "\n  ".join(CATEGORIES))


if __name__ == "__main__":
    main()
