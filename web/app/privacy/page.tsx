import type { Metadata } from "next";
import Link from "next/link";
import Contact from "@/components/Contact";
import DeleteData from "@/components/DeleteData";
import { gaEnabled } from "@/components/GoogleAnalytics";
import { POLICY_DATE } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy policy" };

export default function Privacy() {
  return (
    <main className="wrap legal">
      <p className="back"><Link href="/">Back to the ledger</Link></p>
      <h1>Privacy policy</h1>
      <p className="effective">Effective {POLICY_DATE}</p>

      <p>
        Shoebox turns photos and PDFs of receipts into an expense list. This page explains what happens to
        the files you add and what we keep.{" "}
        {gaEnabled
          ? "We don\u2019t use ads and we don\u2019t sell data. We use Google Analytics, which sets cookies; see the Google Analytics section below."
          : "We don\u2019t use cookies, ads or third-party analytics, and we don\u2019t sell data."}
      </p>

      <h2>Receipt files</h2>
      <p>
        When you add a receipt, your browser shrinks photos to a smaller size and sends the file to our server.
        Our server passes it to Anthropic&rsquo;s API, which reads the receipt and returns the merchant, date,
        amounts and a suggested category. The result goes back to your browser. We don&rsquo;t save the file, and
        we don&rsquo;t save the merchant, amounts or date read from it.
      </p>
      <p>
        Anthropic handles that request under its{" "}
        <a href="https://www.anthropic.com/legal/commercial-terms">Commercial Terms</a>, which do not allow it to
        train models on content sent through its API.
      </p>

      <h2>Your ledger</h2>
      <p>
        The ledger is saved in your browser&rsquo;s local storage, on your device. We can&rsquo;t see it. Clearing
        your browser data or using &ldquo;Clear ledger&rdquo; removes it.
      </p>

      <h2>What we record</h2>
      <p>
        Your browser creates a random ID the first time you visit. It isn&rsquo;t tied to your name, email or
        account. With that ID we record:
      </p>
      <ul>
        <li>
          a visit each time you open Shoebox, with the website that linked you here (only its domain, such as
          google.com) and any campaign tags in the link (utm_source, utm_medium and utm_campaign)
        </li>
        <li>
          each receipt read: its category, file type, how long it took and whether it was one of the built-in sample
          receipts, but not the merchant, amounts or date
        </li>
        <li>when a receipt can&rsquo;t be read: a short technical error message</li>
        <li>when you change a category: the old and new category</li>
        <li>
          when you download a CSV: which format, how many rows it had and how many of them came from your own receipts
          rather than the samples
        </li>
        <li>feedback you choose to send, exactly as you typed it, and how many receipts were in your ledger</li>
      </ul>
      <p>
        We use these records to count how many people use Shoebox, which websites bring people who find it useful,
        and how often its categories need fixing. If a request arrives without an ID, we use a one-way hash of your
        IP address in its place. If your browser blocks local storage, a new random ID is used for each page load
        instead.
      </p>
      <p>
        The records are stored in our databases, and a copy is kept in Google BigQuery so we can analyze them.
      </p>
      <p>
        To stop abuse, the server also counts requests per ID in memory for up to an hour. Our hosting providers,
        Vercel for the website, Render for the servers and Neon for the databases, may keep standard technical logs
        such as IP addresses. Google Cloud hosts the BigQuery copy.
      </p>

      {gaEnabled && (
        <>
          <h2>Google Analytics</h2>
          <p>
            We also use Google Analytics to count visits and compare its numbers with our own. It sets cookies on
            your device, records pages viewed, the website that sent you here, your approximate location and device
            type, and the same upload and export events listed above. Google processes this data under its{" "}
            <a href="https://policies.google.com/privacy">privacy policy</a>. You can block it with the{" "}
            <a href="https://tools.google.com/dlpage/gaoptout">Google Analytics opt-out add-on</a> or a content
            blocker; Shoebox works the same without it. The delete button below does not remove data held by
            Google.
          </p>
        </>
      )}

      <h2>How long we keep it</h2>
      <p>
        Usage records stay until you delete them or Shoebox shuts down. You can delete yours at any time below.
      </p>

      <h2>Delete your data</h2>
      <p>
        This removes every record tied to this browser&rsquo;s ID and clears the ledger saved here. The copy in
        BigQuery is removed within a few hours.
      </p>
      <DeleteData />

      <h2>Children</h2>
      <p>Shoebox is meant for adults keeping business records and is not directed at children under 13.</p>

      <h2>Changes</h2>
      <p>If this policy changes, we&rsquo;ll update this page and the date at the top.</p>

      <h2>Contact</h2>
      <Contact />
    </main>
  );
}
