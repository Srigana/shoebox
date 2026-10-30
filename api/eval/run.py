"""Measure field-level extraction accuracy on a labeled set of receipts.

    python -m eval.run eval/data/sroie/labels.csv
    python -m eval.run eval/sets/samples/labels.csv --model claude-haiku-5-5

labels.csv columns: file, merchant, date, total, category, notes.
Blank cells are not scored, so a set can label only some fields.

Writes:
  eval/reports/<name>.md          human-readable report (commit this)
  eval/summary.json               latest numbers per set (commit this)
  eval/data/results/<name>/       per-receipt CSV and the prediction cache (ignored by git)

Predictions are cached by file content, model and prompt version, so re-running
after fixing a label costs nothing; changing the prompt re-runs everything.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from app.extract import MODEL, PROMPT_VERSION, SUPPORTED_TYPES, ExtractionError, extract_receipt_detailed
from app.schemas import Receipt

from .score import FIELDS, MATCHERS, MERCHANT_SIMILARITY, wilson

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent.parent

# USD per million tokens (input, output), from platform.claude.com/docs/en/about-claude/pricing.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

MAX_SIDE = 1600  # same downscale the web app applies before upload
EXT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
             ".gif": "image/gif", ".heic": "image/heic", ".pdf": "application/pdf"}

Extractor = Callable[[bytes, str, str], tuple[Receipt, dict[str, int]]]


def prepare(path: Path) -> tuple[bytes, str]:
    """Return (bytes, media_type) exactly as production would send them."""
    media_type = EXT_TYPES.get(path.suffix.lower())
    raw = path.read_bytes()
    if media_type == "application/pdf":
        return raw, media_type
    if media_type is None:
        raise ExtractionError(f"Unsupported file type: {path.suffix}")
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        scale = min(1.0, MAX_SIDE / max(im.size))
        if scale < 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85)
    return out.getvalue(), "image/jpeg"


def _api_extractor(data: bytes, media_type: str, model: str) -> tuple[Receipt, dict[str, int]]:
    return extract_receipt_detailed(data, media_type, model=model)


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = [{k.strip().lower(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]
    if not rows or "file" not in rows[0]:
        raise SystemExit(f"{path} needs a 'file' column (see eval/README.md).")
    return [r for r in rows if r.get("file")]


class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.items: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    if rec.get("error") is None:  # always retry failures
                        self.items[rec["key"]] = rec
                except (json.JSONDecodeError, KeyError):
                    continue

    def get(self, key: str) -> Optional[dict[str, Any]]:
        return self.items.get(key)

    def put(self, rec: dict[str, Any]) -> None:
        with self.lock:
            self.items[rec["key"]] = rec
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")


def run_eval(
    labels_path: Path,
    *,
    name: Optional[str] = None,
    model: Optional[str] = None,
    extractor: Optional[Extractor] = None,
    concurrency: int = 4,
    limit: Optional[int] = None,
    results_dir: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
    summary_path: Optional[Path] = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    labels_path = labels_path.resolve()
    name = name or labels_path.parent.name
    model = model or MODEL
    extractor = extractor or _api_extractor
    rows = read_labels(labels_path)[: limit or None]
    results_dir = results_dir or EVAL_DIR / "data" / "results" / name
    reports_dir = reports_dir or EVAL_DIR / "reports"
    summary_path = summary_path or EVAL_DIR / "summary.json"
    results_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    cache = Cache(results_dir / "predictions.jsonl")

    jobs = []
    for r in rows:
        path = (labels_path.parent / r["file"]).resolve()
        if not path.exists():
            raise SystemExit(f"Missing file listed in labels.csv: {r['file']}")
        jobs.append((r, path))

    def key_for(data: bytes) -> str:
        return f"{hashlib.sha256(data).hexdigest()[:20]}:{model}:{PROMPT_VERSION}"

    prepared = []
    for r, path in jobs:
        try:
            data, mt = prepare(path)
        except Exception as e:  # unreadable image counts as a failed extraction
            data, mt = b"", f"error:{type(e).__name__}"
        prepared.append((r, path, data, mt))

    uncached = [p for p in prepared if p[2] and not cache.get(key_for(p[2]))]
    if uncached and extractor is _api_extractor and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first (export ANTHROPIC_API_KEY=sk-ant-...).")
    log(f"{name}: {len(prepared)} receipts, {len(prepared) - len(uncached)} cached, model {model}")

    done = [0]
    done_lock = threading.Lock()

    def work(item: tuple[dict[str, str], Path, bytes, str]) -> dict[str, Any]:
        r, path, data, mt = item
        if not data:
            return {"key": None, "file": r["file"], "error": f"Could not open file ({mt[6:]})"}
        key = key_for(data)
        hit = cache.get(key)
        if hit:
            return hit
        started = time.perf_counter()
        rec: dict[str, Any] = {"key": key, "file": r["file"], "model": model, "prompt_version": PROMPT_VERSION}
        for attempt in range(3):
            try:
                if mt not in SUPPORTED_TYPES:
                    raise ExtractionError(f"Unsupported type {mt}")
                receipt, usage = extractor(data, mt, model)
                rec.update(receipt=receipt.model_dump(), usage=usage, error=None)
                break
            except Exception as e:  # API errors, or output that fails validation
                rec.update(receipt=None, usage={}, error=str(e)[:200] or type(e).__name__)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        rec["latency_ms"] = int((time.perf_counter() - started) * 1000)
        cache.put(rec)
        with done_lock:
            done[0] += 1
            status = "error: " + rec["error"] if rec["error"] else f"{rec['latency_ms'] / 1000:.1f}s"
            log(f"  [{done[0]}/{len(uncached)}] {r['file']}  {status}")
        return rec

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        records = list(pool.map(work, prepared))

    return _score_and_report(name, model, labels_path, rows, records, results_dir, reports_dir, summary_path, log)


def _fmt(v: Any) -> str:
    if v is None or v == "":
        return "(blank)"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v).replace("|", "/").replace("\n", " ")


def _score_and_report(
    name: str, model: str, labels_path: Path, rows: list[dict[str, str]], records: list[dict[str, Any]],
    results_dir: Path, reports_dir: Path, summary_path: Path, log: Callable[[str], None],
) -> dict[str, Any]:
    per_field = {f: {"correct": 0, "labeled": 0, "misses": []} for f in FIELDS}
    all_correct = receipts_scored = errors = 0
    latencies, in_tok, out_tok = [], [], []
    out_rows = []

    for r, rec in zip(rows, records):
        pred = rec.get("receipt") or {}
        if rec.get("error"):
            errors += 1
        else:
            latencies.append(rec.get("latency_ms", 0))
            in_tok.append(rec.get("usage", {}).get("input_tokens", 0))
            out_tok.append(rec.get("usage", {}).get("output_tokens", 0))
        row_out: dict[str, Any] = {"file": r["file"], "error": rec.get("error") or ""}
        scored_any, all_ok = False, True
        for f in FIELDS:
            gold = r.get(f, "")
            got = pred.get(f)
            row_out[f"{f}_expected"], row_out[f"{f}_got"] = gold, "" if got is None else got
            if not gold:
                row_out[f"{f}_ok"] = ""
                continue
            ok = (not rec.get("error")) and MATCHERS[f](got, gold)
            scored_any = True
            all_ok = all_ok and ok
            per_field[f]["labeled"] += 1
            per_field[f]["correct"] += int(ok)
            row_out[f"{f}_ok"] = "yes" if ok else "no"
            if not ok:
                per_field[f]["misses"].append((r["file"], gold, "extraction failed" if rec.get("error") else got))
        if scored_any:
            receipts_scored += 1
            all_correct += int(all_ok)
        out_rows.append(row_out)

    with (results_dir / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else ["file"])
        w.writeheader()
        w.writerows(out_rows)

    fields_correct = sum(v["correct"] for v in per_field.values())
    fields_labeled = sum(v["labeled"] for v in per_field.values())
    price = PRICES.get(model)
    cost = None
    if price and in_tok:
        cost = (statistics.mean(in_tok) * price[0] + statistics.mean(out_tok) * price[1]) / 1_000_000

    def pct(k: int, n: int) -> Optional[float]:
        return round(100 * k / n, 1) if n else None

    summary = {
        "name": name,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "run_date": date.today().isoformat(),
        "receipts": len(rows),
        "field_accuracy": pct(fields_correct, fields_labeled),
        "fields_correct": fields_correct,
        "fields_labeled": fields_labeled,
        "field_ci": [round(100 * x, 1) for x in wilson(fields_correct, fields_labeled)],
        "receipts_all_correct": all_correct,
        "receipts_scored": receipts_scored,
        "errors": errors,
        "per_field": {
            f: {"correct": v["correct"], "labeled": v["labeled"], "accuracy": pct(v["correct"], v["labeled"])}
            for f, v in per_field.items()
        },
        "median_latency_s": round(statistics.median(latencies) / 1000, 1) if latencies else None,
        "p95_latency_s": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] / 1000, 1) if latencies else None,
        "cost_per_receipt_usd": round(cost, 4) if cost is not None else None,
    }

    # ---- report ----
    rel_labels = os.path.relpath(labels_path, REPO_ROOT)
    lines = [
        f"# Extraction accuracy: {name}",
        "",
        f"{len(rows)} receipts from `{rel_labels}`, model `{model}`, prompt version `{PROMPT_VERSION}`, "
        f"run {summary['run_date']}.",
        "",
        "| Field | Correct | Accuracy | 95% interval |",
        "|---|---|---|---|",
    ]
    for f in FIELDS:
        v = per_field[f]
        if not v["labeled"]:
            lines.append(f"| {f.capitalize()} | not labeled | | |")
            continue
        lo, hi = wilson(v["correct"], v["labeled"])
        lines.append(f"| {f.capitalize()} | {v['correct']}/{v['labeled']} | {pct(v['correct'], v['labeled'])}% "
                     f"| {100 * lo:.1f}% to {100 * hi:.1f}% |")
    lo, hi = wilson(fields_correct, fields_labeled)
    lines.append(f"| **All labeled fields** | **{fields_correct}/{fields_labeled}** | "
                 f"**{summary['field_accuracy']}%** | {100 * lo:.1f}% to {100 * hi:.1f}% |")
    lines += [
        "",
        f"- Receipts with every labeled field correct: {all_correct}/{receipts_scored}"
        + (f" ({pct(all_correct, receipts_scored)}%)" if receipts_scored else ""),
        f"- Extraction failures (no result after 3 tries): {errors}",
    ]
    if latencies:
        lines.append(f"- Latency per receipt: median {summary['median_latency_s']} s, "
                     f"95th percentile {summary['p95_latency_s']} s")
    if cost is not None:
        lines.append(f"- Model cost: about ${cost:.4f} per receipt "
                     f"({statistics.mean(in_tok):.0f} input and {statistics.mean(out_tok):.0f} output tokens on average)")
    lines += ["", "## Misses by field", ""]
    ranked = sorted(FIELDS, key=lambda f: -len(per_field[f]["misses"]))
    if not any(per_field[f]["misses"] for f in FIELDS):
        lines.append("None.")
    for f in ranked:
        misses = per_field[f]["misses"]
        if not misses:
            continue
        lines += [f"### {f.capitalize()}: {len(misses)} missed", "", "| File | Expected | Got |", "|---|---|---|"]
        lines += [f"| {_fmt(fn)} | {_fmt(exp)} | {_fmt(got)} |" for fn, exp, got in misses[:25]]
        if len(misses) > 25:
            lines.append(f"| ... | {len(misses) - 25} more in results.csv | |")
        lines.append("")
    lines += [
        "## How fields are scored",
        "",
        "- Total: within one cent of the label.",
        "- Date: same calendar day.",
        f"- Merchant: equal after ignoring case, punctuation and suffixes such as Inc or Sdn Bhd, "
        f"or at least {MERCHANT_SIMILARITY:.0%} similar character by character.",
        "- Category: exact match with the labeled Schedule C category.",
        "- Blank labels are not scored. A failed extraction counts as wrong for every labeled field.",
        "- Images are downscaled to 1600 px JPEG first, the same as the web app does before upload.",
        "",
    ]
    report = reports_dir / f"{name}.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    all_summaries: dict[str, Any] = {}
    if summary_path.exists():
        try:
            all_summaries = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            all_summaries = {}
    all_summaries[name] = summary
    summary_path.write_text(json.dumps(all_summaries, indent=2) + "\n", encoding="utf-8")

    log("")
    log("\n".join(lines[4: 6 + len(FIELDS) + 1]))  # the results table
    log(f"\nReport: {os.path.relpath(report)}")
    log(f"Per-receipt detail: {os.path.relpath(results_dir / 'results.csv')}")
    return summary


START, END = "<!-- accuracy:start -->", "<!-- accuracy:end -->"
MIN_README_SET = 10


def readme_section(summaries: dict[str, Any], reports_rel: str) -> str:
    rows = ["| Test set | Receipts | Total | Date | Merchant | Category | All fields |", "|---|---|---|---|---|---|---|"]
    # Tiny sets such as the three built-in samples are smoke tests, not evidence.
    summaries = {k: v for k, v in summaries.items() if v["receipts"] >= MIN_README_SET}
    if not summaries:
        return "No test set with at least 10 receipts has been run yet. See [api/eval](api/eval/README.md)."
    for name, s in sorted(summaries.items()):
        cell = lambda f: (f"{s['per_field'][f]['accuracy']}%" if s["per_field"][f]["labeled"] else "not labeled")  # noqa: E731
        rows.append(
            f"| [{name}]({reports_rel}/{name}.md) | {s['receipts']} | {cell('total')} | {cell('date')} | "
            f"{cell('merchant')} | {cell('category')} | **{s['field_accuracy']}%** |"
        )
    models = sorted({s["model"] for s in summaries.values()})
    return "\n".join(rows) + f"\n\nModel: {', '.join(f'`{m}`' for m in models)}. Each report lists every miss."


def update_readme(readme: Path, summary_path: Path | None = None) -> bool:
    summary_path = summary_path or EVAL_DIR / "summary.json"
    if not summary_path.exists():
        return False
    summaries = json.loads(summary_path.read_text(encoding="utf-8"))
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        return False
    reports_rel = os.path.relpath(EVAL_DIR / "reports", readme.parent)
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    readme.write_text(f"{head}{START}\n{readme_section(summaries, reports_rel)}\n{END}{tail}", encoding="utf-8")
    return True


def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("labels", type=Path, help="path to labels.csv")
    ap.add_argument("--name", help="name for this test set (default: the labels folder name)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--limit", type=int, help="only the first N receipts")
    ap.add_argument("--no-readme", action="store_true", help="don't update the accuracy table in README.md")
    args = ap.parse_args(argv)
    if not args.labels.exists():
        sys.exit(f"Not found: {args.labels}")
    run_eval(args.labels, name=args.name, model=args.model, concurrency=args.concurrency, limit=args.limit)
    if not args.no_readme and update_readme(REPO_ROOT / "README.md"):
        print("Updated the accuracy table in README.md")


if __name__ == "__main__":
    main()
