"use client";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

/** Ambient life for the learner site: rising embers behind the page, a pointer spotlight on surfaces, and pointer-parallax variables.
 *  All of it is decorative: off for reduced motion and for the admin console, paused when the tab is hidden, never intercepts input. */
export function Life() {
  const path = usePathname() ?? "";
  const canvas = useRef<HTMLCanvasElement>(null);
  const off = /^\/[a-z]{2}\/admin(\/|$)/.test(path);

  useEffect(() => {
    if (off || typeof matchMedia !== "function" || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const fine = matchMedia("(pointer: fine)").matches;
    const root = document.documentElement;
    let raf = 0, px = 0, py = 0, pending = false, el: Element | null = null;

    // Pointer: spotlight position on the hovered surface + page-level parallax in [-1, 1].
    const SURF = ".ex-tile, .lp-cell, .stat, .today-list li";
    const move = (e: PointerEvent) => {
      px = e.clientX; py = e.clientY; el = (e.target as Element | null)?.closest?.(SURF) ?? null;
      if (pending) return; pending = true;
      requestAnimationFrame(() => {
        pending = false;
        root.style.setProperty("--px", ((px / innerWidth) * 2 - 1).toFixed(3));
        root.style.setProperty("--py", ((py / innerHeight) * 2 - 1).toFixed(3));
        if (el) { const r = el.getBoundingClientRect(); (el as HTMLElement).style.setProperty("--mx", `${px - r.left}px`); (el as HTMLElement).style.setProperty("--my", `${py - r.top}px`); }
      });
    };
    if (fine) addEventListener("pointermove", move, { passive: true });

    // Embers.
    const c = canvas.current; const ctx = c?.getContext("2d");
    const dpr = Math.min(devicePixelRatio || 1, 1.5);
    const N = innerWidth < 720 ? 18 : 34;
    const P = Array.from({ length: N }, () => ({ x: Math.random(), y: Math.random(), r: 0.6 + Math.random() * 1.8, v: 0.02 + Math.random() * 0.05, s: Math.random() * 6.28, a: 0.25 + Math.random() * 0.5 }));
    const size = () => { if (!c) return; c.width = innerWidth * dpr; c.height = innerHeight * dpr; };
    size(); addEventListener("resize", size);
    let last = performance.now();
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!ctx || !c || document.hidden) { last = now; return; }
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      ctx.clearRect(0, 0, c.width, c.height);
      for (const p of P) {
        p.y -= p.v * dt * 4; p.s += dt; p.x += Math.sin(p.s) * 0.0004;
        if (p.y < -0.05) { p.y = 1.05; p.x = Math.random(); }
        const fade = Math.min(1, p.y * 2.2, (1.05 - p.y) * 4);
        ctx.beginPath(); ctx.arc(p.x * c.width, p.y * c.height, p.r * dpr, 0, 6.283);
        ctx.fillStyle = `rgba(255,${120 + Math.round(p.a * 100)},40,${(p.a * fade * 0.55).toFixed(3)})`;
        ctx.shadowColor = "rgba(255,90,31,.8)"; ctx.shadowBlur = 8 * dpr; ctx.fill();
      }
    };
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); removeEventListener("pointermove", move); removeEventListener("resize", size); root.style.removeProperty("--px"); root.style.removeProperty("--py"); };
  }, [off]);

  if (off) return null;
  return <canvas ref={canvas} className="life-embers" aria-hidden="true" />;
}
