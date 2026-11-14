"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { otherLocale } from "../lib/i18n.ts";
import { useApi, useT } from "../lib/react/context.tsx";

export function Header() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const pathname = usePathname() ?? `/${locale}`;
  const other = otherLocale(locale);
  const switched = pathname.replace(new RegExp(`^/${locale}`), `/${other}`);

  async function logout() {
    await api.call("API-AUTH-004");            // clears cookies server-side; ignore result: user lands on login either way
    router.push(`/${locale}/login`);
  }

  return (
    <header className="site-header">
      <Link href={`/${locale}`} className="brand">{t("app.name")}</Link>
      <nav aria-label="main">
        <Link href={`/${locale}/onboarding`}>{t("nav.onboarding")}</Link>
        <Link href={`/${locale}/dashboard`}>{t("nav.dashboard")}</Link>
        <Link href={`/${locale}/plan`}>{t("nav.plan")}</Link>
        <Link href={`/${locale}/exercises`}>{t("nav.exercises")}</Link>
        <Link href={`/${locale}/history`}>{t("nav.history")}</Link>
        <Link href={`/${locale}/body`}>{t("nav.body")}</Link>
        <Link href={`/${locale}/health`}>{t("nav.health")}</Link>
        <Link href={`/${locale}/nutrition`}>{t("nav.nutrition")}</Link>
        <Link href={`/${locale}/foods`}>{t("nav.foods")}</Link>
        <Link href={`/${locale}/profile`}>{t("nav.profile")}</Link>
        <Link href={`/${locale}/login`}>{t("nav.login")}</Link>
        <button type="button" className="linklike" onClick={logout}>{t("nav.logout")}</button>
        <a href={switched} hrefLang={other} lang={other} onClick={() => { document.cookie = `vf_locale=${other}; Path=/; Max-Age=31536000; SameSite=Lax`; }}>{t("nav.language")}</a>
      </nav>
    </header>
  );
}

export function Notice() {
  const { t } = useT();
  return <p className="notice" role="note">{t("notice.notMedical")}</p>;
}
