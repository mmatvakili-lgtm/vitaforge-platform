import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { dirOf, isLocale, LOCALES, t } from "../../lib/i18n.ts";
import { LocaleProvider } from "../../lib/react/context.tsx";
import { Header, Notice } from "../../components/Header.tsx";
import { RegisterSW } from "../../components/RegisterSW.tsx";
import "../globals.css";

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return isLocale(locale) ? { title: t(locale, "app.name"), description: t(locale, "app.tagline"), manifest: "/manifest.webmanifest", icons: { icon: "/icon.svg" }, themeColor: "#0f766e" } : {};
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <html lang={locale} dir={dirOf(locale)}>
      <body>
        <RegisterSW />
        <LocaleProvider locale={locale}>
          <Header />
          <main className="container">{children}</main>
          <footer className="container"><Notice /></footer>
        </LocaleProvider>
      </body>
    </html>
  );
}
