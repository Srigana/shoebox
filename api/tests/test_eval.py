import csv
import json
from datetime import date

import pytest
from PIL import Image

from app.schemas import Receipt
from eval.run import END, START, run_eval, update_readme
from eval.score import date_match, merchant_match, parse_amount, parse_date, total_match, wilson


# --- scoring rules ---------------------------------------------------------

@pytest.mark.parametrize("pred,gold,ok", [
    ("Book Ta.K (Taman Daya) Sdn. Bhd.", "BOOK TA .K (TAMAN DAYA) SDN BHD", True),
    ("Fieldnote Software", "Fieldnote Software, Inc.", True),
    ("Corner Grind Cofee", "Corner Grind Coffee", True),   # one OCR slip is tolerated
    ("Starbucks", "Corner Grind Coffee", False),
    ("Gardenia", "GARDENIA BAKERIES (KL) SDN BHD", False),  # too much missing
    (None, "Corner Grind Coffee", False),
])
def test_merchant_match(pred, gold, ok):
    assert merchant_match(pred, gold) is ok


@pytest.mark.parametrize("raw,dayfirst,expected", [
    ("25/12/2018", True, date(2018, 12, 25)),
    ("12-01-19", True, date(2019, 1, 12)),
    ("12-01-19", False, date(2019, 12, 1)),
    ("16.03.2018 8:13 PM", True, date(2018, 3, 16)),
    ("13/05/2018", False, date(2018, 5, 13)),   # month can't be 13, so it must be day-first
    ("02 JAN 2018", True, date(2018, 1, 2)),
    ("02/JAN/2017", True, date(2017, 1, 2)),
    ("15 JUN 18", True, date(2018, 6, 15)),
    ("Oct 1, 2026", False, date(2026, 10, 1)),
    ("2026-10-14", False, date(2026, 10, 14)),
    ("31/02/2018", True, None),
    ("", True, None),
])
def test_parse_date(raw, dayfirst, expected):
    assert parse_date(raw, dayfirst=dayfirst) == expected


def test_date_and_total_match():
    assert date_match("2026-10-14", "2026-10-14")
    assert not date_match(None, "2026-10-14")
    assert not date_match("2026-10-14", "")
    assert parse_amount("RM 1,234.50") == 1234.5
    assert total_match(9.0, "9.00") and total_match(20.16, "$20.17")
    assert not total_match(20.16, "20.18") and not total_match(None, "9.00")


def test_wilson_interval():
    lo, hi = wilson(76, 80)
    assert 0.87 < lo < 0.88 and 0.98 < hi < 0.99
    assert wilson(0, 0) == (0.0, 0.0)


# --- end to end with a fake model ------------------------------------------

def _receipt(**kw):
    base = {"merchant": "Shop", "date": "2026-01-01", "total": 10.0, "category": "Supplies",
            "category_reason": "", "confidence": 0.9}
    return Receipt.model_validate({**base, **kw})


@pytest.fixture
def labeled_set(tmp_path):
    d = tmp_path / "mini"
    d.mkdir()
    for i, color in enumerate(["red", "green", "blue"]):
        Image.new("RGB", (3000, 1000), color).save(d / f"r{i}.png")  # big: should be downscaled
    with (d / "labels.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "merchant", "date", "total", "category", "notes"])
        w.writerow(["r0.png", "Shop", "2026-01-01", "10.00", "Supplies", ""])
        w.writerow(["r1.png", "Shop", "2026-01-01", "10.00", "", "category not labeled"])
        w.writerow(["r2.png", "Shop", "2026-01-01", "10.00", "Meals", ""])
    return d


def test_run_eval_scores_caches_and_reports(labeled_set, tmp_path):
    calls = []

    def fake(data, media_type, model):
        calls.append((len(data), media_type))
        with Image.open(__import__("io").BytesIO(data)) as im:
            assert max(im.size) == 1600 and media_type == "image/jpeg"
            color = im.getpixel((5, 5))
        if color[0] > 200:      # r0: all right
            return _receipt(), {"input_tokens": 1500, "output_tokens": 200}
        if color[1] > 100:      # r1: wrong total
            return _receipt(total=11.0), {"input_tokens": 1500, "output_tokens": 200}
        raise RuntimeError("model fell over")  # r2: extraction failure

    kw = dict(results_dir=tmp_path / "res", reports_dir=tmp_path / "rep", summary_path=tmp_path / "summary.json",
              extractor=fake, model="claude-sonnet-5-5", log=lambda m: None)
    s = run_eval(labeled_set / "labels.csv", **kw)

    # r0: 4/4, r1: 2/3 (total wrong), r2: 0/4 (failed) -> 6/11
    assert s["fields_labeled"] == 11 and s["fields_correct"] == 6
    assert s["per_field"]["total"] == {"correct": 1, "labeled": 3, "accuracy": 33.3}
    assert s["per_field"]["category"] == {"correct": 1, "labeled": 2, "accuracy": 50.0}
    assert s["receipts_all_correct"] == 1 and s["errors"] == 1
    assert s["cost_per_receipt_usd"] == round((1500 * 2 + 200 * 10) / 1e6, 4)
    assert len(calls) == 2 + 3  # r2 retried 3 times

    report = (tmp_path / "rep" / "mini.md").read_text()
    assert "| Total | 1/3 | 33.3% |" in report and "extraction failed" in report and "\u2014" not in report
    rows = list(csv.DictReader((tmp_path / "res" / "results.csv").open()))
    assert rows[1]["total_ok"] == "no" and rows[1]["category_ok"] == ""

    # Second run: successes come from the cache, the failure is retried.
    calls.clear()
    run_eval(labeled_set / "labels.csv", **kw)
    assert len(calls) == 3

    readme = tmp_path / "README.md"
    readme.write_text(f"# X\n\n{START}\nold\n{END}\n\nmore\n")
    assert update_readme(readme, tmp_path / "summary.json")
    assert "No test set with at least 10 receipts" in readme.read_text()  # 3 receipts is too few to show
    import eval.run as run_mod
    run_mod.MIN_README_SET = 1
    try:
        assert update_readme(readme, tmp_path / "summary.json")
    finally:
        run_mod.MIN_README_SET = 10
    text = readme.read_text()
    assert "| [mini](" in text and "**54.5%**" in text and "old" not in text and text.endswith("more\n")
    assert json.loads((tmp_path / "summary.json").read_text())["mini"]["field_ci"][0] < 54.5


def test_missing_file_is_a_clear_error(labeled_set, tmp_path):
    (labeled_set / "r1.png").unlink()
    with pytest.raises(SystemExit, match="r1.png"):
        run_eval(labeled_set / "labels.csv", extractor=lambda *a: None, results_dir=tmp_path / "x",
                 reports_dir=tmp_path / "y", summary_path=tmp_path / "s.json", log=lambda m: None)


def test_sample_set_labels_match_demo_fixtures():
    """The sample receipts' labels and the fixtures used by DEMO_MODE must agree."""
    from pathlib import Path

    from app.samples import EXPECTED
    from eval.score import MATCHERS

    labels = Path(__file__).resolve().parent.parent / "eval" / "sets" / "samples" / "labels.csv"
    rows = list(csv.DictReader(labels.open()))
    ids = {"corner-grind-coffee.jpg": "coffee", "lantern-office-supply.jpg": "office", "fieldnote-invoice.pdf": "invoice"}
    for r in rows:
        name = r["file"].rsplit("/", 1)[-1]
        assert (labels.parent / r["file"]).resolve().exists()
        exp = EXPECTED[ids[name]].model_dump()
        for f, match in MATCHERS.items():
            assert match(exp[f], r[f]), (name, f)
