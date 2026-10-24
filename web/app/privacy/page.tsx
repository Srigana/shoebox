import type { Metadata } from "next";
import Link from "next/link";
import Contact from "@/components/Contact";
import DeleteData from "@/components/DeleteData";
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
        the files you add and what we keep. We don&rsquo;t use cookies, ads or third-party analytics, and we
        don&rsquo;t sell data.
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
        <li>a visit, at most once a day, and the page that linked you here, if any</li>
        <li>each receipt read: its category, file type and how long it took, but not the merchant, amounts or date</li>
        <li>when a receipt can&rsquo;t be read: a short technical error message</li>
        <li>when you change a category: the old and new category</li>
        <li>when you download a CSV: how many rows it had</li>
        <li>feedback you choose to send, exactly as you typed it, and how many receipts were in your ledger</li>
      </ul>
      <p>
        We use these records to count how many people use Shoebox and how often its categories need fixing. If a
        request arrives without an ID, we use a one-way hash of your IP address in its place.
      </p>
      <p>
        To stop abuse, the server also counts requests per ID in memory for up to an hour. Our hosting providers,
        Vercel for the website, Render for the server and Neon for the database, may keep standard technical logs
        such as IP addresses.
      </p>

      <h2>How long we keep it</h2>
      <p>
        Usage records stay until you delete them or Shoebox shuts down. You can delete yours at any time below.
      </p>

      <h2>Delete your data</h2>
      <p>This removes every record tied to this browser&rsquo;s ID and clears the ledger saved here.</p>
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
