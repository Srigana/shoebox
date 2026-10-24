"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getClientId, logEvent, parseReceipt } from "@/lib/api";
import { fullCsv, quickbooksCsv } from "@/lib/csv";
import { prepareFile } from "@/lib/image";
import { CATEGORIES, deductible, isCategory, SCHEDULE_C_LINE, type Category } from "@/lib/tax";
import type { DoneItem, Item } from "@/lib/types";

const STORAGE_KEY = "shoebox.items.v1";
const LOW_CONFIDENCE = 0.7;
const CONCURRENCY = 3;

const money = (n: number | null | undefined, currency = "USD") =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency });

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [over, setOver] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [sent, setSent] = useState(false);
  const queue = useRef<{ id: string; file: File }[]>([]);
  const active = useRef(0);

  // Restore the ledger from this browser, and count the visit (once per day).
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as Item[];
      setItems(saved.filter((i) => i.status === "done"));
    } catch {
      /* fresh start */
    }
    setLoaded(true);
    getClientId();
    try {
      const today = new Date().toISOString().slice(0, 10);
      if (localStorage.getItem("shoebox.visit") !== today) {
        localStorage.setItem("shoebox.visit", today);
        logEvent("visit", { ref: document.referrer.slice(0, 120) });
      }
    } catch {
      logEvent("visit");
    }
  }, []);

  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items.filter((i) => i.status === "done")));
    } catch {
      /* storage full or blocked: ledger still works for this session */
    }
  }, [items, loaded]);

  const update = (id: string, next: Item) => setItems((prev) => prev.map((i) => (i.id === id ? next : i)));

  const pump = useCallback(() => {
    while (active.current < CONCURRENCY && queue.current.length) {
      const job = queue.current.shift()!;
      active.current++;
      (async () => {
        const base = { id: job.id, fileName: job.file.name, addedAt: Date.now() };
        try {
          const { blob, name } = await prepareFile(job.file);
          const { receipt } = await parseReceipt(blob, name);
          if (!receipt.is_receipt) throw new Error("This doesn't look like a receipt or invoice.");
          const category: Category = isCategory(receipt.category) ? receipt.category : "Other expenses";
          update(job.id, { ...base, status: "done", receipt: { ...receipt, category }, category, edited: false });
        } catch (e) {
          update(job.id, { ...base, status: "error", error: e instanceof Error ? e.message : "Something went wrong." });
        } finally {
          active.current--;
          pump();
        }
      })();
    }
  }, []);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const list = Array.from(files).slice(0, 25);
      if (!list.length) return;
      const jobs = list.map((file) => ({ id: crypto.randomUUID(), file }));
      setItems((prev) => [
        ...jobs.map((j) => ({ id: j.id, fileName: j.file.name, addedAt: Date.now(), status: "reading" as const })),
        ...prev,
      ]);
      queue.current.push(...jobs);
      pump();
    },
    [pump],
  );

  const setCategory = (item: DoneItem, category: Category) => {
    const edited = category !== item.receipt.category;
    update(item.id, { ...item, category, edited });
    if (edited) logEvent("correction", { item: item.id, from: item.receipt.category, to: category });
  };

  const done = useMemo(
    () =>
      items
        .filter((i): i is DoneItem => i.status === "done")
        .sort((a, b) => (b.receipt.date ?? "").localeCompare(a.receipt.date ?? "")),
    [items],
  );
  const pending = items.filter((i) => i.status !== "done");

  const tally = useMemo(() => {
    const by = new Map<Category, { total: number; ded: number; n: number }>();
    for (const i of done) {
      const t = i.receipt.total ?? 0;
      const row = by.get(i.category) ?? { total: 0, ded: 0, n: 0 };
      row.total += t;
      row.ded += deductible(t, i.category) ?? 0;
      row.n++;
      by.set(i.category, row);
    }
    const rows = [...by.entries()].sort((a, b) => b[1].total - a[1].total);
    const sum = rows.reduce((s, [, r]) => ({ total: s.total + r.total, ded: s.ded + r.ded }), { total: 0, ded: 0 });
    return { rows, sum };
  }, [done]);

  const needsLook = done.filter((i) => i.receipt.confidence < LOW_CONFIDENCE && !i.edited).length;

  return (
    <main className="wrap">
      <header className="masthead">
        <h1 className="wordmark">Shoebox</h1>
        <p className="lede">
          Drop in the receipts you&rsquo;ve been saving. Each one gets read, sorted into a Schedule C expense
          category, and added to your ledger, ready to export to QuickBooks or your accountant.
        </p>
      </header>

      <label
        className="drop"
        data-over={over}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          addFiles(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          multiple
          accept="image/*,.heic,.heif,application/pdf"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <strong>Add receipts</strong>
        <span>Drag photos or PDFs here, or tap to choose. Up to 25 at a time.</span>
      </label>

      <section aria-labelledby="ledger-title">
        <div className="ledger-head">
          <h2 id="ledger-title">Ledger</h2>
          {done.length > 0 && (
            <span className="count">
              {done.length} {done.length === 1 ? "receipt" : "receipts"}
              {needsLook > 0 && ` · ${needsLook} to check`}
            </span>
          )}
        </div>

        {items.length === 0 ? (
          <div className="empty">
            Your ledger is empty. Add a receipt above. A coffee receipt or a software invoice is a good first test.
          </div>
        ) : (
          <>
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Merchant</th>
                  <th scope="col">Category</th>
                  <th scope="col" className="num">Total</th>
                  <th scope="col" className="num">Deductible</th>
                  <th scope="col"><span className="sr-only">Remove</span></th>
                </tr>
              </thead>
              <tbody>
                {pending.map((i) => (
                  <tr key={i.id} className={i.status === "error" ? "err" : undefined}>
                    <td colSpan={5}>
                      {i.status === "reading" ? (
                        <span className="reading">Reading {i.fileName}…</span>
                      ) : (
                        <>
                          <strong>{i.fileName}</strong>: {i.error}
                        </>
                      )}
                    </td>
                    <td className="x">
                      {i.status === "error" && (
                        <button className="remove" aria-label={`Dismiss ${i.fileName}`} onClick={() => setItems((p) => p.filter((x) => x.id !== i.id))}>
                          ×
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {done.map((i) => {
                  const r = i.receipt;
                  const flag = r.confidence < LOW_CONFIDENCE && !i.edited;
                  return (
                    <tr key={i.id} className={flag ? "flag" : undefined}>
                      <td data-label="Date">{r.date ?? "No date"}</td>
                      <td>
                        <span className="merchant">{r.merchant ?? "Unknown merchant"}</span>
                        <span className="sub" title={r.category_reason}>{r.category_reason}</span>
                      </td>
                      <td>
                        <select
                          className={`cat${i.edited ? " edited" : ""}`}
                          value={i.category}
                          aria-label={`Category for ${r.merchant ?? i.fileName}`}
                          onChange={(e) => isCategory(e.target.value) && setCategory(i, e.target.value)}
                        >
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </td>
                      <td className="num" data-label="Total">{money(r.total, r.currency)}</td>
                      <td className="num" data-label="Deductible">{money(deductible(r.total, i.category), r.currency)}</td>
                      <td className="x">
                        <button className="remove" aria-label={`Remove ${r.merchant ?? i.fileName}`} onClick={() => setItems((p) => p.filter((x) => x.id !== i.id))}>
                          ×
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="legend">
              <mark>Highlighted</mark> rows are ones Shoebox was unsure about. Categories you change turn{" "}
              <span className="pencil">red</span>.
            </p>
          </>
        )}
      </section>

      <div className="below">
        <section className="tally" aria-labelledby="tally-title">
          <h2 id="tally-title">By category</h2>
          {tally.rows.length === 0 ? (
            <p className="note">Totals by Schedule C line appear here as receipts come in.</p>
          ) : (
            <table>
              <tbody>
                {tally.rows.map(([cat, r]) => (
                  <tr key={cat}>
                    <td>{cat} <span className="sub">{r.n} {r.n === 1 ? "receipt" : "receipts"}</span></td>
                    <td className="line">{SCHEDULE_C_LINE[cat]}</td>
                    <td className="num">{money(r.total)}</td>
                    <td className="num ded">{money(r.ded)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={2}>Total</td>
                  <td className="num">{money(tally.sum.total)}</td>
                  <td className="num ded">{money(tally.sum.ded)}</td>
                </tr>
              </tfoot>
            </table>
          )}
          <p className="note">
            Red figures are deductible estimates (business meals at 50%). They&rsquo;re a starting point for you
            or your accountant, not tax advice.
          </p>
        </section>

        <section className="actions" aria-labelledby="export-title">
          <h2 id="export-title">Export</h2>
          <p>QuickBooks format imports as bank transactions. The full CSV has every field for your accountant.</p>
          <button
            className="btn"
            disabled={!done.length}
            onClick={() => {
              download("shoebox-quickbooks.csv", quickbooksCsv(done));
              logEvent("export_qbo", { n: done.length });
            }}
          >
            Download QuickBooks CSV
          </button>
          <button
            className="btn ghost"
            disabled={!done.length}
            onClick={() => {
              download("shoebox-ledger.csv", fullCsv(done));
              logEvent("export_csv", { n: done.length });
            }}
          >
            Download full CSV
          </button>

          <form
            className="feedback"
            onSubmit={(e) => {
              e.preventDefault();
              if (!feedback.trim()) return;
              logEvent("feedback", { text: feedback.trim().slice(0, 1000), receipts: done.length });
              setFeedback("");
              setSent(true);
            }}
          >
            {sent ? (
              <p className="thanks">Feedback sent. Thank you, it goes straight to the person building this.</p>
            ) : (
              <>
                <label htmlFor="fb">What would make this useful for your business?</label>
                <textarea id="fb" value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="A category it got wrong, a feature you'd want, anything." />
                <button className="btn ghost" type="submit" disabled={!feedback.trim()}>Send feedback</button>
              </>
            )}
          </form>
        </section>
      </div>

      <footer className="foot">
        <p>
          Your ledger is saved in this browser only. Receipt images are sent to the server to be read and are not
          stored.
        </p>
        <p>
          Built with Claude. Not affiliated with Intuit or QuickBooks.{" "}
          {done.length > 0 && (
            <button
              className="remove"
              style={{ fontSize: "inherit", textDecoration: "underline" }}
              onClick={() => confirm("Clear every receipt from this ledger?") && setItems([])}
            >
              Clear ledger
            </button>
          )}
        </p>
      </footer>
    </main>
  );
}
