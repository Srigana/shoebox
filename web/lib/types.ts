import type { Category } from "./tax.ts";

export interface LineItem {
  description: string;
  amount: number | null;
}

export interface Receipt {
  is_receipt: boolean;
  merchant: string | null;
  date: string | null;
  currency: string;
  subtotal: number | null;
  tax: number | null;
  tip: number | null;
  total: number | null;
  payment_method: string | null;
  line_items: LineItem[];
  category: Category;
  category_reason: string;
  confidence: number;
}

export interface ParseResponse {
  receipt: Receipt;
  schedule_c_line: string;
  deductible_estimate: number | null;
  latency_ms: number;
}

/** Set when the row came from one of the built-in sample receipts. */
export interface SampleRef {
  id: string;
  url: string;
}

interface Base {
  id: string;
  fileName: string;
  addedAt: number;
  sample?: SampleRef;
}

export type Item =
  | (Base & { status: "reading" })
  | (Base & { status: "error"; error: string })
  | (Base & {
      status: "done";
      receipt: Receipt;
      category: Category; // current (possibly user-edited) category
      edited: boolean;
    });

export type DoneItem = Extract<Item, { status: "done" }>;
