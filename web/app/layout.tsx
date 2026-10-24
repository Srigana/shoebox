import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Shoebox — receipts to a categorized ledger",
  description:
    "Drop in receipt photos. Shoebox reads them, sorts each into a Schedule C expense category, and exports a QuickBooks-ready CSV.",
};

export const viewport: Viewport = { themeColor: "#EEF3EA" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,400;0,500;0,600;0,800;1,400&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
