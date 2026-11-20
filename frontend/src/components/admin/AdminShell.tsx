"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { adminCall } from "../../lib/admin.ts";
import { otherLocale } from "../../lib/i18n.ts";
import { useT } from "../../lib/react/context.tsx";

export type StaffRole = "admin" | "super_admin";
const Ctx = createContext<StaffRole>("admin");
export const useStaffRole = () => useContext(Ctx);

const P = {
  dash: "M4 13h7V4H4zm9 7h7V11h-7zM4 20h7v-5H4zm9-11h7V4h-7z",
  media: "M4 5h16v14H4zm2 2v7l3-3 3 4 2-2 4 5V7z",
  announce: "M4 10v4h3l5 4V6L7 10zm12-1.5a4.5 4.5 0 010 7",
  users: "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zm-7 9c0-3.3 3.1-5.5 7-5.5s7 2.2 7 5.5zm14-9a3 3 0 100-6M18 20h4c0-2.4-1.8-4-4-4.4",
  staff: "M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5zm-1 12l5-5-1.4-1.4L11 11.2 9.4 9.6 8 11z",
  review: "M5 3h14v18l-7-4-7 4zm4 7l2 2 4-4",
  back: "M10 6l-6 6 6 6M4 12h16",
};
function Ico({ d }: { d: keyof typeof P }) {
  return <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d={P[d]} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

const ITEMS: { key: string; path: string; icon: keyof typeof P; owner?: boolean }[] = [
  { key: "dash", path: "", icon: "dash" },
  { key: "media", path: "/media", icon: "media" },
  { key: "announce", path: "/announcement", icon: "announce" },
  { key: "review", path: "/review", icon: "review" },
  { key: "users", path: "/users", icon: "users", owner: true },
  { key: "staff", path: "/staff", icon: "staff", owner: true },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const { locale, t } = useT();
  const pathname = usePathname() ?? "";
  const base = `/${locale}/admin`;
  const [role, setRole] = useState<StaffRole | "none" | null>(null);
  useEffect(() => {
    adminCall<{ role: string }>("GET", "/admin/me").then((r) => setRole(r.ok && (r.data.role === "admin" || r.data.role === "super_admin") ? (r.data.role as StaffRole) : "none"));
  }, []);

  if (role === null) return <div className="adm adm-center"><p role="status" className="muted">{t("common.loading")}</p></div>;
  if (role === "none") {
    return (
      <div className="adm adm-center">
        <div className="adm-gate"><h1>{t("admin.title")}</h1><p>{t("admin.forbidden")}</p>
          <Link className="btn" href={`/${locale}/login`}>{t("nav.login")}</Link> <Link className="btn btn-secondary" href={`/${locale}`}>{t("admin.backToSite")}</Link></div>
      </div>);
  }
  const items = ITEMS.filter((i) => !i.owner || role === "super_admin");
  const on = (p: string) => (p === "" ? pathname === base : pathname.startsWith(base + p));
  const current = items.find((i) => on(i.path)) ?? items[0];
  const other = otherLocale(locale);
  return (
    <Ctx.Provider value={role}>
      <div className="adm">
        <aside className="adm-side" aria-label={t("admin.title")}>
          <Link href={base} className="adm-brand"><span className="adm-mark" aria-hidden="true" />{t("admin.brand")}</Link>
          <nav className="adm-nav">
            {items.map((i) => (
              <Link key={i.key} href={base + i.path} aria-current={on(i.path) ? "page" : undefined} className={on(i.path) ? "on" : undefined}>
                <Ico d={i.icon} /><span>{t(`admin.nav.${i.key}`)}</span>
              </Link>))}
          </nav>
          <div className="adm-side-foot">
            <Link href={`/${locale}/dashboard`}><Ico d="back" /><span>{t("admin.backToSite")}</span></Link>
          </div>
        </aside>
        <div className="adm-main">
          <header className="adm-top">
            <h1 className="adm-page">{t(`admin.nav.${current.key}`)}</h1>
            <div className="adm-top-r">
              <a href={pathname.replace(new RegExp(`^/${locale}`), `/${other}`)} hrefLang={other} lang={other}
                 onClick={() => { document.cookie = `vf_locale=${other}; Path=/; Max-Age=31536000; SameSite=Lax`; }}>{t("nav.language")}</a>
              <span className={role === "super_admin" ? "adm-role owner" : "adm-role"}>{t(`admin.role.${role}`)}</span>
            </div>
          </header>
          <div className="adm-body">{children}</div>
        </div>
      </div>
    </Ctx.Provider>
  );
}
