"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { MORE_NAV, PRIMARY_NAV } from "../lib/journey.ts";
import { otherLocale } from "../lib/i18n.ts";
import { useApi, useT } from "../lib/react/context.tsx";
import { adminCall } from "../lib/admin.ts";

const ICONS: Record<string, string> = {
  dashboard: "M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z",
  plan: "M5 4h14a1 1 0 011 1v15a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1zm1 5v10h12V9zm2 2h3v3H8z",
  exercises: "M3 9h2V7h2v10H5v-2H3zm18 0h-2V7h-2v10h2v-2h2zM8 11h8v2H8z",
  nutrition: "M7 2v8a3 3 0 002 2.8V22h2v-9.2A3 3 0 0013 10V2h-2v6h-1V2H8v6H7V2zm9 0c-1.7 1.2-3 3.600-3 7 0 2 .9 3.300 2 3.800V22h2z",
  analytics: "M4 20V10h3v10zm6 0V4h3v16zm6 0v-7h3v7z",
  more: "M5 10.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm7 0a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm7 0a1.5 1.5 0 110 3 1.5 1.5 0 010-3z",
};
function Icon({ name }: { name: string }) {
  return <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><path d={ICONS[name]} fill="currentColor" /></svg>;
}

export function Header() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const pathname = usePathname() ?? `/${locale}`;
  const other = otherLocale(locale);
  const switched = pathname.replace(new RegExp(`^/${locale}`), `/${other}`);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [staff, setStaff] = useState(false);

  // Asking the server is the only truthful way to know whether the session cookie is valid; re-check on navigation (login/logout change it).
  useEffect(() => {
    let live = true;
    api.call("API-PRO-001").then((r) => { if (live) setAuthed(r.ok); });
    return () => { live = false; };
  }, [api, pathname]);

  useEffect(() => {
    let live = true;
    if (!authed) { setStaff(false); return; }
    adminCall<{ role: string }>("GET", "/admin/me").then((r) => { if (live) setStaff(r.ok && (r.data.role === "admin" || r.data.role === "super_admin")); });
    return () => { live = false; };
  }, [authed, pathname]);

  // Sliding indicator: one pill that glides to the active tab (measured, so it works for any label length and in RTL).
  const nav = useRef<HTMLElement>(null);
  const [ind, setInd] = useState<{ x: number; y: number; w: number; h: number; ready: boolean } | null>(null);
  useLayoutEffect(() => {
    const measure = () => {
      const el = nav.current?.querySelector<HTMLElement>("a.tab.on");
      if (!el) return setInd(null);
      setInd((p) => ({ x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight, ready: p !== null }));
    };
    measure(); addEventListener("resize", measure);
    document.fonts?.ready.then(measure);
    return () => removeEventListener("resize", measure);
  }, [pathname, authed, locale]);

  // Dock magnification (Apple-style fisheye): icons near the pointer grow, neighbours ramp down smoothly. Mouse + wide screens only.
  function magnify(e: React.PointerEvent<HTMLElement>) {
    if (e.pointerType !== "mouse" || !nav.current) return;
    for (const tab of nav.current.querySelectorAll<HTMLElement>(".tab")) {
      const r = tab.getBoundingClientRect(), d = Math.abs(e.clientX - (r.left + r.width / 2));
      tab.style.setProperty("--m", (1 + 0.55 * Math.exp(-((d / 70) ** 2))).toFixed(3));
    }
  }
  function unmagnify() { nav.current?.querySelectorAll<HTMLElement>(".tab").forEach((t) => t.style.removeProperty("--m")); }

  if (/^\/[a-z]{2}\/admin(\/|$)/.test(pathname)) return null;   // the admin console has its own shell

  async function logout() {
    await api.call("API-AUTH-004");            // clears cookies server-side; ignore result: user lands on login either way
    setAuthed(false);
    router.push(`/${locale}/login`);
  }
  const href = (k: string) => `/${locale}/${k}`;
  const active = (k: string) => pathname === href(k) || pathname.startsWith(`${href(k)}/`);
  const tools = (
    <>
      <a href={switched} hrefLang={other} lang={other} onClick={() => { document.cookie = `vf_locale=${other}; Path=/; Max-Age=31536000; SameSite=Lax`; }}>{t("nav.language")}</a>
    </>
  );

  return (
    <header className="site-header">
      <Link href={authed ? href("dashboard") : `/${locale}`} className="brand">{t("app.name")}</Link>
      {authed ? (
        <>
          <nav aria-label="main" className="nav-main" ref={nav} onPointerMove={magnify} onPointerLeave={unmagnify}>
            <span className={ind?.ready ? "nav-ind ready" : "nav-ind"} aria-hidden="true" style={ind ? { transform: `translate(${ind.x}px, ${ind.y}px)`, width: ind.w, height: ind.h, opacity: 1 } : { opacity: 0 }} />
            {PRIMARY_NAV.map((k) => <Link key={k} href={href(k)} aria-current={active(k) ? "page" : undefined} className={active(k) ? "tab on" : "tab"}><Icon name={k} /><span>{t(`nav.${k}`)}</span></Link>)}
            <details className="more" key={pathname}>
              <summary className="tab"><Icon name="more" /><span>{t("nav.more")}</span></summary>
              <div className="more-panel">
                {MORE_NAV.map((k) => <Link key={k} href={href(k)} aria-current={active(k) ? "page" : undefined}>{t(`nav.${k}`)}</Link>)}
                {staff && <Link href={href("admin")} aria-current={active("admin") ? "page" : undefined}>{t("nav.admin")}</Link>}
                <div className="more-tools">{tools}</div>
                <button type="button" className="linklike" onClick={logout}>{t("nav.logout")}</button>
              </div>
            </details>
          </nav>
        </>
      ) : (
        <nav aria-label="main" className="nav-public">
          {authed === false && <><Link href={href("login")}>{t("nav.login")}</Link><Link href={href("register")} className="btn">{t("nav.register")}</Link></>}
          {tools}
        </nav>
      )}
    </header>
  );
}

export function Notice() {
  const { t } = useT();
  return <p className="notice" role="note">{t("notice.notMedical")}</p>;
}
