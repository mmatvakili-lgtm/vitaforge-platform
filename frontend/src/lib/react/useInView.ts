"use client";
import { useEffect, useRef, useState } from "react";

/** True once the element has entered the viewport (stays true). Without IntersectionObserver (old browsers, tests) it is true at once. */
export function useInViewOnce<T extends Element>(rootMargin = "0px 0px -10% 0px") {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); } }, { rootMargin });
    io.observe(el);
    return () => io.disconnect();
  }, [seen, rootMargin]);
  return [ref, seen] as const;
}

/** Eased count-up from 0 to `target` once `run` is true. Respects prefers-reduced-motion (jumps to the final value). */
export function useCountUp(target: number, run: boolean, ms = 1400): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!run) return;
    if (typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches) { setV(target); return; }
    let raf = 0; const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [run, target, ms]);
  return v;
}
