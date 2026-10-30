"""Download a random sample of the public SROIE receipt benchmark and its labels.

    python -m eval.fetch_sroie            # 80 receipts into eval/data/sroie/
    python -m eval.fetch_sroie --n 100

SROIE (ICDAR 2019, "Scanned Receipts OCR and Information Extraction") has 626
labeled training receipts: real, often faded, scans of Malaysian store
receipts. Labels cover company (merchant), date and total, not category. Files
come from the cleaned copy at github.com/zzzDavid/ICDAR-2019-SROIE and are for
research use, so they're downloaded here rather than committed.

Dates in SROIE are day-first (25/12/2018); they're converted to ISO here so the
scorer never has to guess.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
import urllib.request
from pathlib import Path

from .score import parse_date

BASE = "https://raw.githubusercontent.com/zzzDavid/ICDAR-2019-SROIE/master/data"
TOTAL_RECEIPTS = 626
OUT = Path(__file__).resolve().parent / "data" / "sroie"


def _get(url: str) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=80, help="how many receipts (default 80)")
    ap.add_argument("--seed", type=int, default=2026, help="random seed, so the sample is reproducible")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    ids = sorted(random.Random(args.seed).sample(range(TOTAL_RECEIPTS), min(args.n, TOTAL_RECEIPTS)))
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, n in enumerate(ids, 1):
        stem = f"{n:03d}"
        img = args.out / f"{stem}.jpg"
        if not img.exists():
            img.write_bytes(_get(f"{BASE}/img/{stem}.jpg"))
        key = json.loads(_get(f"{BASE}/key/{stem}.json").decode("utf-8"))
        raw_date = (key.get("date") or "").strip()
        iso = parse_date(raw_date, dayfirst=True)
        rows.append({
            "file": img.name,
            "merchant": (key.get("company") or "").strip(),
            "date": iso.isoformat() if iso else "",
            "total": (key.get("total") or "").strip(),
            "category": "",
            "notes": f"SROIE {stem}; printed date {raw_date!r}" + ("" if iso else " (unparsed, not scored)"),
        })
        print(f"  [{i}/{len(ids)}] {img.name}", end="\r")

    with (args.out / "labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "merchant", "date", "total", "category", "notes"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {len(rows)} receipts and labels.csv to {args.out}")
    print(f"Next: python -m eval.run {args.out.relative_to(Path.cwd()) if args.out.is_relative_to(Path.cwd()) else args.out}/labels.csv")


if __name__ == "__main__":
    main()
