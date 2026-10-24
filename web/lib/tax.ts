// Mirrors api/app/schemas.py so edited categories update instantly on the client.

export const CATEGORIES = [
  "Advertising",
  "Car and truck expenses",
  "Contract labor",
  "Insurance",
  "Legal and professional services",
  "Office expense",
  "Rent or lease",
  "Repairs and maintenance",
  "Supplies",
  "Taxes and licenses",
  "Travel",
  "Meals",
  "Utilities",
  "Software and subscriptions",
  "Bank and merchant fees",
  "Education and training",
  "Other expenses",
] as const;

export type Category = (typeof CATEGORIES)[number];

export const SCHEDULE_C_LINE: Record<Category, string> = {
  Advertising: "Line 8",
  "Car and truck expenses": "Line 9",
  "Contract labor": "Line 11",
  Insurance: "Line 15",
  "Legal and professional services": "Line 17",
  "Office expense": "Line 18",
  "Rent or lease": "Line 20a/20b",
  "Repairs and maintenance": "Line 21",
  Supplies: "Line 22",
  "Taxes and licenses": "Line 23",
  Travel: "Line 24a",
  Meals: "Line 24b",
  Utilities: "Line 25",
  "Software and subscriptions": "Line 27b",
  "Bank and merchant fees": "Line 27b",
  "Education and training": "Line 27b",
  "Other expenses": "Line 27b",
};

export function deductible(total: number | null | undefined, category: Category): number | null {
  if (total == null) return null;
  const rate = category === "Meals" ? 0.5 : 1;
  return Math.round(total * rate * 100) / 100;
}

export function isCategory(v: string): v is Category {
  return (CATEGORIES as readonly string[]).includes(v);
}
