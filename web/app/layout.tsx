import "@fontsource-variable/public-sans/wght.css";
import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Shoebox: receipts to a Schedule C expense ledger", template: "%s | Shoebox" },
  description:
    "Add receipt photos or PDFs. Shoebox reads each one, sorts it into a Schedule C expense category, and exports a QuickBooks-ready CSV.",
};

export const viewport: Viewport = { themeColor: "#EEF3EA" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <footer className="wrap foot">
          <nav aria-label="Legal" className="foot-links">
            <Link href="/">Ledger</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
          </nav>
          <p>QuickBooks is a trademark of Intuit Inc. Shoebox is not affiliated with or endorsed by Intuit.</p>
        </footer>
      </body>
    </html>
  );
}
