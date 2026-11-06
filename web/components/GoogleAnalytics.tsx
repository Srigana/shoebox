import Script from "next/script";

// Off unless NEXT_PUBLIC_GA_MEASUREMENT_ID is set. Before turning it on, read the Google Analytics
// section of the privacy policy (app/privacy/page.tsx), which appears automatically when this is set,
// and check whether your visitors' countries require a consent banner for analytics cookies.
export const GA_ID = (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID ?? "").trim();
export const gaEnabled = /^G-[A-Z0-9]{4,20}$/.test(GA_ID);

export default function GoogleAnalytics() {
  if (!gaEnabled) return null;
  return (
    <>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
      <Script id="ga-init" strategy="afterInteractive">
        {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${GA_ID}');`}
      </Script>
    </>
  );
}
