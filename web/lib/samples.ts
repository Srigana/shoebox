// Fictional receipts in public/samples, each printed "SAMPLE RECEIPT - NOT A REAL PURCHASE".
// The ids match api/app/samples.py so the server can tag these parses and keep
// them out of the real-usage numbers.

export interface Sample {
  id: "coffee" | "office" | "invoice";
  url: string;
  type: string;
}

export const SAMPLES: Sample[] = [
  { id: "coffee", url: "/samples/corner-grind-coffee.jpg", type: "image/jpeg" },
  { id: "office", url: "/samples/lantern-office-supply.jpg", type: "image/jpeg" },
  { id: "invoice", url: "/samples/fieldnote-invoice.pdf", type: "application/pdf" },
];

export async function loadSample(s: Sample): Promise<File> {
  const res = await fetch(s.url);
  if (!res.ok) throw new Error(`Couldn't load the sample (${res.status}).`);
  const name = s.url.split("/").pop() ?? `${s.id}`;
  return new File([await res.blob()], name, { type: s.type });
}
