# Shoebox

Turn a shoebox of receipts into a categorized expense ledger. Drop in receipt photos or PDFs; Shoebox reads each one with Claude, assigns an IRS Schedule C expense category with a one-line reason, flags the ones it's unsure about, and exports a QuickBooks-ready CSV.

Built for freelancers and sole proprietors who do their own books.

## What it does

- **Reads receipts**: merchant, date, subtotal, tax, tip, total, payment method, line items. Photos are downscaled in the browser (≈4 MB → ≈300 KB) before upload; PDFs go straight through.
- **Categorizes for taxes**: 17 categories mapped to Schedule C lines, with business meals estimated at 50% deductible.
- **Keeps a human in the loop**: low-confidence rows are highlighted; one click changes a category, and every change is logged as a correction.
- **Exports**: QuickBooks Online bank-transaction CSV (Date, Description, Amount) and a full CSV for an accountant.
- **Measures itself**: an anonymous event log answers "how many people used it, and how often was the AI right?" at `GET /api/stats`.

## Architecture

```
Browser (Next.js, TypeScript)  ──/api/*──▶  Vercel rewrite  ──▶  FastAPI (Python) on Render  ──▶  Claude (vision + forced tool use)
  - image downscale                                              - validation, rate limits         returns typed JSON
  - ledger in localStorage                                       - SQLite event log
  - CSV / QuickBooks export                                      - /api/stats
```

- **Structured output via tool use.** The model is forced to call a `record_receipt` tool whose JSON schema enumerates the categories, so responses are always typed; Pydantic then normalizes dates, currency, confidence and unknown categories.
- **One origin for the browser.** Vercel proxies `/api/*` to Render, so there's no CORS in production and the backend URL isn't exposed.
- **Spend guardrails.** Per-client hourly limit plus a global daily cap on parses.
- **Privacy.** Receipt images aren't stored server-side; the ledger lives in the user's browser.

