import assert from "node:assert/strict";
import { test } from "node:test";
import { fullCsv, quickbooksCsv, usDate } from "./csv.ts";
import { deductible } from "./tax.ts";
import type { DoneItem } from "./types.ts";

const item = (over: Partial<DoneItem["receipt"]> = {}, category: DoneItem["category"] = "Meals"): DoneItem => ({
  id: "1",
  fileName: "a.jpg",
  addedAt: 0,
  status: "done",
  edited: false,
  category,
  receipt: {
    is_receipt: true, merchant: 'Joe\'s "Diner", LLC', date: "2026-10-02", currency: "USD",
    subtotal: 20, tax: 1.8, tip: 4, total: 25.8, payment_method: null, line_items: [],
    category: "Meals", category_reason: "", confidence: 0.9, ...over,
  },
});

test("usDate", () => {
  assert.equal(usDate("2026-10-02"), "10/02/2026");
  assert.equal(usDate(null), "");
});

test("meals are 50% deductible", () => {
  assert.equal(deductible(25.8, "Meals"), 12.9);
  assert.equal(deductible(25.8, "Travel"), 25.8);
});

test("full CSV escapes quotes and commas", () => {
  const csv = fullCsv([item()]);
  assert.match(csv, /"Joe's ""Diner"", LLC"/);
  assert.match(csv, /Line 24b/);
});

test("QuickBooks CSV uses negative amounts and skips undated rows", () => {
  const csv = quickbooksCsv([item(), item({ date: null })]);
  const lines = csv.trim().split("\r\n");
  assert.equal(lines.length, 2);
  assert.equal(lines[1], '10/02/2026,"Joe\'s ""Diner"", LLC (Meals)",-25.80');
});
