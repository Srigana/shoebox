import { deductible, SCHEDULE_C_LINE } from "./tax.ts";
import type { DoneItem } from "./types.ts";

function cell(v: string | number | null | undefined): string {
  if (v == null) return "";
  const s = String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function rows(table: (string | number | null | undefined)[][]): string {
  return table.map((r) => r.map(cell).join(",")).join("\r\n") + "\r\n";
}

/** Everything we extracted, one row per receipt. */
export function fullCsv(items: DoneItem[]): string {
  const header = [
    "Date", "Merchant", "Category", "Schedule C line", "Subtotal", "Tax", "Tip", "Total",
    "Deductible estimate", "Currency", "Payment method", "AI category", "Edited", "Confidence", "File",
  ];
  return rows([
    header,
    ...items.map((i) => [
      i.receipt.date, i.receipt.merchant, i.category, SCHEDULE_C_LINE[i.category],
      i.receipt.subtotal, i.receipt.tax, i.receipt.tip, i.receipt.total,
      deductible(i.receipt.total, i.category), i.receipt.currency, i.receipt.payment_method,
      i.receipt.category, i.edited ? "yes" : "no", i.receipt.confidence.toFixed(2), i.fileName,
    ]),
  ]);
}

/** MM/DD/YYYY from YYYY-MM-DD. */
export function usDate(iso: string | null): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${m}/${d}/${y}`;
}

/**
 * QuickBooks Online bank-transaction import, 3-column layout:
 * Date, Description, Amount (expenses negative). Category goes in the description
 * so it's visible while matching in the For Review tab.
 */
export function quickbooksCsv(items: DoneItem[]): string {
  return rows([
    ["Date", "Description", "Amount"],
    ...items
      .filter((i) => i.receipt.total != null && i.receipt.date)
      .map((i) => [
        usDate(i.receipt.date),
        `${i.receipt.merchant ?? "Unknown merchant"} (${i.category})`,
        (-(i.receipt.total as number)).toFixed(2),
      ]),
  ]);
}
