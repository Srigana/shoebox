"use client";

import { useEffect, useState } from "react";

type State = "idle" | "working" | "done" | "error";

export default function DeleteData() {
  const [id, setId] = useState<string | null>(null);
  const [state, setState] = useState<State>("idle");

  useEffect(() => {
    try {
      setId(localStorage.getItem("shoebox.cid"));
    } catch {
      setId(null);
    }
  }, []);

  async function remove() {
    if (!id || !confirm("Delete your usage records and the ledger saved in this browser?")) return;
    setState("working");
    try {
      const res = await fetch("/api/delete-my-data", { method: "POST", headers: { "X-Client-Id": id } });
      if (!res.ok) throw new Error(String(res.status));
      ["shoebox.cid", "shoebox.items.v1", "shoebox.visit"].forEach((k) => localStorage.removeItem(k));
      setState("done");
    } catch {
      setState("error");
    }
  }

  if (state === "done") {
    return <p className="callout">Deleted. Your usage records and this browser&rsquo;s ledger are gone.</p>;
  }
  if (!id) {
    return <p className="callout">This browser has no Shoebox ID, so there is nothing stored about it.</p>;
  }
  return (
    <div className="callout">
      <p>
        This browser&rsquo;s ID is <code>{id}</code>.
      </p>
      <button className="btn" onClick={remove} disabled={state === "working"}>
        {state === "working" ? "Deleting…" : "Delete my data"}
      </button>
      {state === "error" && <p role="alert">The delete request failed. Check your connection and try again.</p>}
    </div>
  );
}
