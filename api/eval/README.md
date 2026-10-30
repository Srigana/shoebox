# Measuring extraction accuracy

The harness runs Shoebox's real extraction pipeline (same prompt, same schema, same 1600 px downscale as the web app) over labeled receipts. It reports accuracy per field, a 95% confidence interval, and every miss.

Setup, once, from the `api` folder:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## 1. Public benchmark: SROIE (merchant, date, total)

[SROIE](https://rrc.cvc.uab.es/?ch=13) is the ICDAR 2019 scanned-receipt benchmark: real, often faded receipts with labeled company, date and total.

```bash
python -m eval.fetch_sroie            # 80 random receipts (fixed seed) into eval/data/sroie/
python -m eval.run eval/data/sroie/labels.csv
```

This takes a few minutes and costs well under a dollar. The images are for research use, so they're downloaded rather than committed.

## 2. Your own receipts (adds category)

SROIE has no category labels, so category accuracy comes from receipts you label yourself.

```bash
mkdir -p eval/data/mine            # copy 20+ receipt photos or PDFs here
python -m eval.template eval/data/mine
# open eval/data/mine/labels.csv and fill in merchant, date (YYYY-MM-DD), total, category
python -m eval.run eval/data/mine/labels.csv
```

Label from the receipt itself, not from Shoebox's output, or the score will be biased toward the model.

## 3. Quick check: the three built-in samples

```bash
python -m eval.run eval/sets/samples/labels.csv
```

Sets under 10 receipts get a report but are left out of the main README table.

## Output

- `eval/reports/<set>.md`: the table, misses by field, cost and latency. Commit this.
- `eval/summary.json`: latest numbers per set. The accuracy table in the main README is regenerated from it.
- `eval/data/results/<set>/results.csv`: one row per receipt, expected vs. got.

Predictions are cached by file, model and prompt version. Re-running after fixing a label is free; changing the prompt re-runs everything. Compare models with `--model claude-haiku-5-5`.

## Reading the results honestly

- Look at every miss before quoting a number. Some will be label noise (SROIE has a few known label errors), and some totals are ambiguous, such as a total versus a rounded total.
- Quote the interval as well as the point estimate: 76/80 is 95%, but anywhere from about 88% to 98% is consistent with it.
- The date field is a known weak spot for non-US receipts: `05/06/2018` means June 5 in Malaysia and May 6 in the US. Check whether date misses are this kind before changing the prompt.
