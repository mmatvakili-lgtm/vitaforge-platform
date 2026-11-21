"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/** Iris transition between pages: a circle grows from the click point and covers the screen, the route changes underneath, then the circle
 *  shrinks back to the same point (spatial logic: the new page "comes from" what you touched; curve and 100–500 ms budget follow Samsung One UI's motion guidance).
 *  Plain internal link clicks only; modified clicks, new tabs, downloads, hashes, other origins and reduced-motion users get the normal behaviour. */
export function RouteWipe() {
  const router = useRouter();
  const path = usePathname();
  const el = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<"idle" | "cover" | "reveal">("idle");
  const pending = useRef<string | null>(null);
  const guard = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const click = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download") || a.origin !== location.origin) return;
      const next = a.pathname + a.search;
      if (a.pathname === location.pathname || a.hash || /^\/(api|vendor|exercise-media)\b/.test(a.pathname)) return;
      e.preventDefault(); e.stopPropagation();
      const d = Math.hypot(Math.max(e.clientX, innerWidth - e.clientX), Math.max(e.clientY, innerHeight - e.clientY)) * 2;
      const n = el.current; if (!n) { router.push(next); return; }
      n.style.setProperty("--x", `${e.clientX}px`); n.style.setProperty("--y", `${e.clientY}px`); n.style.setProperty("--d", `${d}px`);
      pending.current = next; setPhase("cover");
      guard.current = setTimeout(() => setPhase("reveal"), 2500);   // never leave the screen covered if navigation stalls
    };
    document.addEventListener("click", click, true);
    return () => { document.removeEventListener("click", click, true); if (guard.current) clearTimeout(guard.current); };
  }, [router]);

  // Covered: wait for the circle to finish growing, then navigate.
  useEffect(() => {
    if (phase !== "cover") return;
    const id = setTimeout(() => { if (pending.current) router.push(pending.current); pending.current = null; }, 330);
    return () => clearTimeout(id);
  }, [phase, router]);
  // Route changed while covered: shrink the circle away.
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    if (phase === "cover") { const id = setTimeout(() => setPhase("reveal"), 120); return () => clearTimeout(id); }
  }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (phase !== "reveal") return;
    if (guard.current) clearTimeout(guard.current);
    const id = setTimeout(() => setPhase("idle"), 480);
    return () => clearTimeout(id);
  }, [phase]);

  return <div ref={el} className={`wipe wipe-${phase}`} aria-hidden="true" />;
}
