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

## Run locally

```bash
# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # add ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --port 8000
# no key yet? DEMO_MODE=1 uvicorn app.main:app --port 8000   (canned receipts, no API calls)

# Web (second terminal)
cd web
npm install
npm run dev                     # http://localhost:3000, proxies /api to :8000
```

Tests: `cd api && pytest` (11 tests) and `cd web && npm test` (4 tests). CI runs both plus a production build.

## Deploy (about 15 minutes)

1. **Push to GitHub.**
2. **API on Render**: New → Blueprint → pick the repo. Render reads `render.yaml`. Set `ANTHROPIC_API_KEY`, and set `ALLOWED_ORIGINS` to your Vercel URL once you have it. Copy the generated `ADMIN_TOKEN`. Check `https://<service>.onrender.com/health`.
3. **Web on Vercel**: New Project → import the repo → Root Directory `web` → add env var `API_URL=https://<service>.onrender.com` → Deploy.
4. **Smoke test** on your phone with a real receipt, then:
   ```bash
   curl -H "Authorization: Bearer $ADMIN_TOKEN" https://<service>.onrender.com/api/stats
   ```

Free-tier notes: Render's free web service sleeps after inactivity (first request takes ~30–60 s) and its disk is wiped on redeploy. Before you share the link widely, either upgrade to the starter plan and attach a persistent disk at `api/data`, or export your stats before each redeploy. The stats are your resume numbers, so don't lose them.

## Launch plan: getting 10–20 real users

The goal is 10–20 people who upload at least one real receipt. Target people who actually have a pile of receipts:

1. **Warm list (aim for 8–10).** Friends and family who freelance, drive rideshare, run an Etsy shop, do contract work, or have a side business. Send a personal text, not a broadcast: "I built a tool that turns receipt photos into a categorized expense list for taxes. Would you try it with 5 receipts and tell me what it got wrong?"
2. **Communities (aim for 5–10).** Post where self-employed people talk about bookkeeping: r/freelance, r/smallbusiness, r/Etsy, r/doordash_drivers, local small-business Facebook groups, a university entrepreneurship club. Lead with the problem and ask for feedback; read each community's self-promotion rules first.
3. **Watch two people use it live.** Screen-share or sit next to them. You'll find the confusing parts in 10 minutes.
4. **Ship one improvement from feedback within 48 hours** and tell the people who asked for it. That turns testers into returning users and gives you a story for interviews.

Check `/api/stats` daily. The numbers worth tracking:

| Metric | Field | Why it matters |
|---|---|---|
| Users | `users` | People who parsed ≥1 receipt (not just visitors) |
| Receipts processed | `receipts_parsed` | Depth of use |
| AI accuracy proxy | `category_acceptance_rate` | Share of receipts whose category nobody changed |
| Returning users | `returning_users` | Came back on a different day |
| Feedback | `feedback` | Quotes for your write-up |

## Resume bullet

Fill in the brackets with real numbers from `/api/stats`:

> Built and launched Shoebox, an AI receipt categorizer for freelancers, in [N] days with Claude Code (TypeScript/Next.js, Python/FastAPI, Claude vision API; Vercel + Render), reaching [N] users who processed [N] receipts with [N]% of AI categories accepted without edits.

Shorter: *Built and launched an AI expense categorizer in [N] days with Claude Code, reaching [N] users and [N]% categorization accuracy.*

## Ideas for v2

- Remember a user's corrections per merchant ("Target → Office expense") and apply them next time.
- Mileage log, since car expenses are many freelancers' largest deduction.
- Email-in receipts (forward to a unique address).
- QuickBooks Online API sync instead of CSV.

---

Deductible estimates and Schedule C mappings are a starting point, not tax advice. Not affiliated with Intuit or QuickBooks.
