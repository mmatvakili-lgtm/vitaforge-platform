import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { dirOf, isLocale, LOCALES, t } from "../../lib/i18n.ts";
import { LocaleProvider } from "../../lib/react/context.tsx";
import { ContentModeBanner } from "../../components/ContentModeBanner.tsx";
import { Header, Notice } from "../../components/Header.tsx";
import { RegisterSW } from "../../components/RegisterSW.tsx";
import { Barlow_Condensed, IBM_Plex_Mono, Vazirmatn } from "next/font/google";
import "../globals.css";

// Self-hosted at build time by next/font (no runtime request to Google; satisfies the font-src 'self' CSP).
const fa = Vazirmatn({ subsets: ["arabic", "latin"], variable: "--font-fa", display: "swap" });
const display = Barlow_Condensed({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-display", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });
const THEME_INIT = `(function(){try{var t=localStorage.getItem("vf_theme");if(t==="forge"||t==="lab"||t==="track")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export const viewport = { themeColor: "#0f766e" };

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
