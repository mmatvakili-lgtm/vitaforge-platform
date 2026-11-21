"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

/** Page transitions with depth (View Transitions API): the old page recedes (scale + blur + fade) while the new one slides in from the side the
 *  destination sits on in the menu. Header and embers stay put. Works for plain internal link clicks only; unsupported browsers, modified clicks,
 *  new tabs and reduced-motion users get ordinary navigation. Total ≤ 450 ms, One UI curve. */
const ORDER = ["dashboard", "plan", "nutrition", "analytics", "exercises", "history", "body", "assessment", "health", "foods", "profile", "onboarding"];
const seg = (p: string) => p.split("/")[2] ?? "";

type VTDoc = Document & { startViewTransition?: (cb: () => Promise<void> | void) => { finished: Promise<void> } };

export function RouteFx() {
  const router = useRouter();
  const path = usePathname();
  const done = useRef<(() => void) | null>(null);

  useEffect(() => {
    const doc = document as VTDoc;
    if (!doc.startViewTransition || (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches)) return;
    const click = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download") || a.origin !== location.origin) return;
      if (a.pathname === location.pathname || a.hash || /^\/(api|vendor|exercise-media)\b/.test(a.pathname)) return;
      const from = ORDER.indexOf(seg(location.pathname)), to = ORDER.indexOf(seg(a.pathname));
      const rtl = getComputedStyle(document.documentElement).direction === "rtl";
      const forward = from < 0 || to < 0 ? true : to >= from;
      document.documentElement.dataset.vt = forward !== rtl ? "r" : "l";     // side the new page enters from
      e.preventDefault(); e.stopPropagation();
      const next = a.pathname + a.search;
      const vt = doc.startViewTransition!(() => new Promise<void>((resolve) => {
        done.current = resolve;
        router.push(next);
        setTimeout(resolve, 1500);                                         // never hang the screen if navigation stalls
      }));
      vt.finished.finally(() => { delete document.documentElement.dataset.vt; });
    };
    document.addEventListener("click", click, true);
    return () => document.removeEventListener("click", click, true);
  }, [router]);

  useEffect(() => {          // route committed: let the browser snapshot the new page one frame later
    if (!done.current) return;
    const d = done.current; done.current = null;
    requestAnimationFrame(() => requestAnimationFrame(d));
  }, [path]);

  return null;
}
