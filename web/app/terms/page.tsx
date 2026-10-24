import type { Metadata } from "next";
import Link from "next/link";
import Contact from "@/components/Contact";
import { POLICY_DATE } from "@/lib/site";

export const metadata: Metadata = { title: "Terms of use" };

export default function Terms() {
  return (
    <main className="wrap legal">
      <p className="back"><Link href="/">Back to the ledger</Link></p>
      <h1>Terms of use</h1>
      <p className="effective">Effective {POLICY_DATE}</p>

      <p>
        By using Shoebox you agree to these terms. If you don&rsquo;t agree, please don&rsquo;t use it. How we
        handle your data is covered in the <Link href="/privacy">privacy policy</Link>.
      </p>

      <h2>What Shoebox is</h2>
      <p>
        Shoebox is a free tool that reads receipts and suggests an expense category for each one. It is an
        independent project, offered as is, and may change, have limits or stop running at any time.
      </p>

      <h2>Not tax or accounting advice</h2>
      <p>
        Categories, Schedule C line numbers and deductible estimates are suggestions and can be wrong. Check every
        amount and category before you file or share them, and ask a tax professional about your situation. You
        are responsible for your own tax returns and records.
      </p>

      <h2>What you can upload</h2>
      <p>
        Only upload receipts and invoices you have the right to use. Don&rsquo;t upload documents that aren&rsquo;t
        receipts, such as IDs, bank statements or medical records.
      </p>

      <h2>Fair use</h2>
      <p>Don&rsquo;t:</p>
      <ul>
        <li>use Shoebox for anything illegal</li>
        <li>try to get around its usage limits, or send automated or bulk traffic</li>
        <li>try to break, overload or gain unauthorized access to it</li>
      </ul>
      <p>We may block access that breaks these rules.</p>

      <h2>No warranty</h2>
      <p>
        Shoebox is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without warranties of any kind,
        including accuracy, availability or fitness for a particular purpose.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the extent the law allows, we are not liable for any loss or damage from using Shoebox or relying on its
        results, including tax penalties, lost data or lost profits.
      </p>

      <h2>Trademarks</h2>
      <p>
        QuickBooks is a trademark of Intuit Inc. Shoebox is not affiliated with or endorsed by Intuit. The
        QuickBooks export follows a common CSV layout and is provided for convenience.
      </p>

      <h2>Changes</h2>
      <p>
        We may update these terms. The date at the top shows the latest version. Using Shoebox after a change means
        you accept the new terms.
      </p>

      <h2>Contact</h2>
      <Contact />
    </main>
  );
}
