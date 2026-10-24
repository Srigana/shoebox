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

export type Item =
  | { id: string; fileName: string; addedAt: number; status: "reading" }
  | { id: string; fileName: string; addedAt: number; status: "error"; error: string }
  | {
      id: string;
      fileName: string;
      addedAt: number;
      status: "done";
      receipt: Receipt;
      category: Category; // current (possibly user-edited) category
      edited: boolean;
    };

export type DoneItem = Extract<Item, { status: "done" }>;
