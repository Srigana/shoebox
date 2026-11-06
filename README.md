# Shoebox

Receipt photos and PDFs in, a categorized expense ledger out. Shoebox reads each receipt, files it under an IRS Schedule C category with a one-line reason, highlights the ones it's unsure about, and exports a QuickBooks-ready CSV. Built for freelancers and sole proprietors who do their own books.

**[Try the live demo](https://shoebox-taupe.vercel.app)**. No sign-up: click "Try the sample receipts" to run three sample receipts through it.

![Running the three sample receipts, changing one category, and the totals by Schedule C line](docs/demo.gif)

## Accuracy

Measured with the harness in [`api/eval`](api/eval/README.md): the production pipeline run over the public [SROIE](https://rrc.cvc.uab.es/?ch=13) scanned-receipt benchmark and hand-labeled receipts, scored field by field, with every miss listed in the report.

<!-- accuracy:start -->
| Test set | Receipts | Total | Date | Merchant: exact name / business identified | Category | All fields: strict / merchant identified |
|---|---|---|---|---|---|---|
| [sroie](api/eval/reports/sroie.md) | 80 | 97.5% | 100.0% | 72.5% / 97.5% | not labeled | **90.0%** / **98.3%** |

Model: `claude-sonnet-5-5`. Each report lists every miss.
<!-- accuracy:end -->

## How it works

```
Browser (Next.js, TypeScript)                FastAPI (Python) on Render                 Claude
  downscale photo to 1600 px JPEG  --/api-->   validate type and size, rate limit  -->   vision + structured output
  ledger in localStorage            (Vercel    Pydantic normalizes the result     <--   JSON matching the schema
  CSV and QuickBooks export          proxy)    anonymous usage events in Postgres
```

- **Structured output by construction.** Each request carries a JSON schema (Claude's structured outputs) that lists the 17 allowed categories, so every reply is valid, typed JSON. Pydantic then normalizes dates, currency and confidence, and maps anything unexpected to "Other expenses" rather than failing.
- **Confidence drives review.** Low-confidence rows are highlighted, and a category change is one click. Every change is logged, so the share of categories nobody changed is a live accuracy signal alongside the offline eval.
- **Measured, not assumed.** The eval runs the exact production prompt and image preprocessing, caches predictions by prompt version so prompt changes can be compared cheaply, and reports 95% confidence intervals because 80 receipts is a small sample.
- **Honest usage numbers.** Sample-receipt tries are tagged and kept out of the user counts.
- **Cheap to run.** One origin for the browser (Vercel proxies `/api` to Render), per-client and daily caps on model calls, and nothing stored server-side except anonymous events.

## Acquisition analytics (optional)

`web/lib/track.ts` reports where visitors come from and whether they go on to upload and export, to a separately deployed Trailmark collector (its own project, not in this repo). It sends four events: `visit` (with the referring domain and any `utm_source`, `utm_medium` and `utm_campaign` tags), `upload`, `upload_failed` and `export` (format, rows, and how many rows were the user's own receipts rather than samples). It reuses the `shoebox.cid` ID, so "Delete my data" on the privacy page clears these records too.

It is off until these are set in Vercel:

| Variable | Purpose |
|---|---|
| `COLLECTOR_URL` | Base URL of the Trailmark server. `/collect/*` is proxied to it, so the browser still talks to one origin. |
| `NEXT_PUBLIC_COLLECTOR_WRITE_KEY` | One of the server's `WRITE_KEYS`. It only allows sending events, so it is safe in the browser. |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | Optional `G-` ID. Loads Google Analytics and sends it the same events, for the comparison page. The privacy policy adds a Google Analytics section automatically when this is set. Check whether your visitors' countries require a consent banner first. |
