import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { dirOf, isLocale, LOCALES, t } from "../../lib/i18n.ts";
import { LocaleProvider } from "../../lib/react/context.tsx";
import { ContentModeBanner } from "../../components/ContentModeBanner.tsx";
import { Header, Notice } from "../../components/Header.tsx";
import { RegisterSW } from "../../components/RegisterSW.tsx";
import localFont from "next/font/local";
import "../globals.css";

// Fonts are vendored in src/fonts (OFL) and self-hosted by next/font/local: no request to Google at build, dev or runtime (works offline / where Google is blocked).
const fa = localFont({ src: "../../fonts/Vazirmatn.ttf", weight: "100 900", variable: "--font-fa", display: "swap" });
const display = localFont({ src: [{ path: "../../fonts/BarlowCondensed-SemiBold.ttf", weight: "600" }, { path: "../../fonts/BarlowCondensed-Bold.ttf", weight: "700" }], variable: "--font-display", display: "swap" });
const mono = localFont({ src: [{ path: "../../fonts/IBMPlexMono-Regular.woff2", weight: "400" }, { path: "../../fonts/IBMPlexMono-Medium.woff2", weight: "500" }], variable: "--font-mono", display: "swap" });
const THEME_INIT = `(function(){try{var t=localStorage.getItem("vf_theme");if(t==="forge"||t==="lab"||t==="track")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export const viewport = { themeColor: "#0f0e0d" };

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return isLocale(locale) ? { title: t(locale, "app.name"), description: t(locale, "app.tagline"), manifest: "/manifest.webmanifest", icons: { icon: "/icon.svg" } } : {};
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <html lang={locale} dir={dirOf(locale)} className={`${fa.variable} ${display.variable} ${mono.variable}`} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_INIT }} /></head>
      <body>
        <RegisterSW />
        <LocaleProvider locale={locale}>
          <Header />
          <ContentModeBanner />
          <main className="container">{children}</main>
          <footer className="container"><Notice /></footer>
        </LocaleProvider>
      </body>
    </html>
  );
}
