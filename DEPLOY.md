# Deploying Shoebox for free

Neon (database) → Render (API) → Vercel (website). About 30 minutes. Do the parts in order: each one produces a value the next one needs.

Keep a notes file open and paste these into it as you go:

```
DATABASE_URL   =
ANTHROPIC_KEY  =
RENDER_URL     =
ADMIN_TOKEN    =
VERCEL_URL     =
```

## Part 1 — Put the code on GitHub (5 min)

1. Unzip `shoebox.zip`. You get a `shoebox` folder that is already a git repo with one commit.
2. Go to https://github.com/new. Name it `shoebox`, choose **Public** (it's a portfolio piece), and leave every "Initialize" box **unchecked**. Click **Create repository**.
3. In a terminal, from inside the `shoebox` folder (replace `YOUR-USERNAME`):
   ```bash
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/shoebox.git
   git push -u origin main
   ```
   If it asks for a password, use a GitHub personal access token, or install GitHub Desktop and publish from there.
4. Refresh the GitHub page. You should see `api/`, `web/`, `render.yaml` and `README.md`.

## Part 2 — Database on Neon (5 min)

1. Go to https://neon.com and sign up (GitHub sign-in is fastest). No card needed.
2. Create a project: name `shoebox`, Postgres version default, region **AWS US East** (closest to Render's default Virginia region).
3. On the project dashboard, click **Connect**. Copy the connection string. It looks like
   `postgresql://neondb_owner:xxxx@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require`
4. Paste it into your notes as `DATABASE_URL`. You don't need to create tables; the app does that on first start.

## Part 3 — Claude API key (5 min, the only part that costs money)

1. Go to https://platform.claude.com and sign in or sign up.
2. Open **Settings → Billing** and add a payment method or a small amount of credit. Budget: about $0.01 per receipt, so 20 users × 10 receipts ≈ $2.
3. Still in Settings, set a **spend limit** (for example $10/month) so a surprise can't cost more than that. The app also caps itself at 300 receipts per day.
4. Open **Settings → API keys** (https://platform.claude.com/settings/keys) → **Create key**. Name it `shoebox`, choose a **workspace** (the default one is fine; a key without a workspace needs an extra header this app doesn't send), then create.
5. Copy the key (starts with `sk-ant-`). It's shown only once. Paste it into your notes as `ANTHROPIC_KEY`.

## Part 4 — API on Render (10 min)

1. Go to https://render.com and sign up with GitHub.
2. Click **New +** → **Blueprint**. Connect your GitHub account if asked and pick the `shoebox` repo.
3. Render reads `render.yaml` and shows a service named `shoebox-api` on the **Free** plan. It asks for three values:
   - `ANTHROPIC_API_KEY` → your `ANTHROPIC_KEY`
   - `DATABASE_URL` → your `DATABASE_URL`
   - `ALLOWED_ORIGINS` → type `http://localhost:3000` for now (you'll update it in Part 6)
4. Click **Apply** / **Deploy Blueprint**. The first build takes 3–5 minutes. Wait for **Live**.
5. Open the service. Copy the URL at the top (like `https://shoebox-api-xxxx.onrender.com`) into your notes as `RENDER_URL`.
6. Go to the service's **Environment** tab, reveal `ADMIN_TOKEN` (Render generated it), and copy it into your notes.
7. Check it works: open `RENDER_URL/health` in a browser. You should see `{"status":"ok"}`.

If the build fails, open **Logs**; the last red lines say why. The most common cause is a pasted value with a stray space.

## Part 5 — Website on Vercel (5 min)

1. Go to https://vercel.com and sign up with GitHub (Hobby plan, free).
2. **Add New… → Project** → import the `shoebox` repo.
3. Before deploying:
   - **Root Directory**: click **Edit** and choose `web`. This matters; without it the build fails.
   - Framework should auto-detect as **Next.js**.
   - **Environment Variables**: add `API_URL` = your `RENDER_URL` (no trailing slash, no `/api`).
4. Click **Deploy**. About 1–2 minutes.
5. Copy your site URL (like `https://shoebox-xxxx.vercel.app`) into your notes as `VERCEL_URL`.

## Part 6 — Connect them and test (5 min)

1. In Render → `shoebox-api` → **Environment**, edit `ALLOWED_ORIGINS` to:
   `http://localhost:3000,https://shoebox-xxxx.vercel.app` (your `VERCEL_URL`). Save; Render redeploys automatically.
   The site routes API calls through Vercel, so this is a backup, but set it anyway.
2. Open `VERCEL_URL` on your phone. Upload one real receipt. The first one can take up to a minute while the API wakes up.
3. Check your stats (replace both values):
   ```bash
   curl -H "Authorization: Bearer ADMIN_TOKEN" RENDER_URL/api/stats
   ```
   You should see `"users": 1` and `"receipts_parsed": 1`. No terminal? Use https://reqbin.com with a GET request and the `Authorization` header.

## Optional — rename the URL

Vercel → Project → **Settings → Domains** lets you change the subdomain to something like `shoebox-receipts.vercel.app`, which looks better on a resume. Remember to update `ALLOWED_ORIGINS` on Render if you do.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Upload says "Couldn't read that receipt" every time | Render → Logs. `ANTHROPIC_API_KEY` missing or wrong, or no billing set up on the Claude Console. |
| Upload fails with 404 or "Upload failed (500)" | Vercel `API_URL` is wrong. It must be exactly the Render URL, no trailing slash. Redeploy Vercel after changing it (Deployments → ⋯ → Redeploy). |
| Vercel build fails | Root Directory isn't set to `web`. |
| `/api/stats` says Unauthorized | Copy `ADMIN_TOKEN` again from Render's Environment tab; check for spaces. |
| Stats reset to zero | `DATABASE_URL` isn't set on Render, so it fell back to SQLite, which Render wipes. |
| First upload is slow | Normal on the free tier: the API sleeps after 15 min idle and takes about a minute to wake. |

## Updating later

Push to `main`. Render and Vercel both redeploy automatically, and your stats stay in Neon.
