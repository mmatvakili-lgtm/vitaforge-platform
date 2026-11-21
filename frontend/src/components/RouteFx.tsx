"use client";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

/** Navigation feedback that never blocks navigation: on a plain internal link click we only (a) remember which side the destination sits on in the
 *  menu so the new page can slide in from it, and (b) show a thin progress bar until the route commits. The old page stays interactive meanwhile. */
const ORDER = ["dashboard", "plan", "nutrition", "analytics", "exercises", "history", "body", "assessment", "health", "foods", "profile", "onboarding"];
const seg = (p: string) => p.split("/")[2] ?? "";

export function RouteFx() {
  const path = usePathname();
  useEffect(() => {
    const root = document.documentElement;
    const click = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download") || a.origin !== location.origin || a.pathname === location.pathname || a.hash) return;
      const from = ORDER.indexOf(seg(location.pathname)), to = ORDER.indexOf(seg(a.pathname));
      const rtl = getComputedStyle(root).direction === "rtl";
      root.dataset.side = (from < 0 || to < 0 || to >= from) !== rtl ? "r" : "l";
      root.dataset.nav = "loading";
      setTimeout(() => { if (root.dataset.nav === "loading") delete root.dataset.nav; }, 8000);   // never leave the bar running
    };
    document.addEventListener("click", click, true);
    return () => document.removeEventListener("click", click, true);
  }, []);
  useEffect(() => { delete document.documentElement.dataset.nav; }, [path]);
  return null;
}
