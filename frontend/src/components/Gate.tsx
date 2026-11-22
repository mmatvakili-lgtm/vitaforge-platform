"use client";
import { useEffect, useRef, type ReactNode } from "react";

/** A barbell that gets loaded as the person moves through the form: each finished step slides a plate onto both sides. Decorative; the real progress is also in text. */
export function Barbell({ loaded, max = 3 }: { loaded: number; max?: number }) {
  return (
    <svg className="barbell" viewBox="0 0 240 44" aria-hidden="true" focusable="false" data-loaded={loaded}>
      <rect x="14" y="20" width="212" height="4" rx="2" className="bar" />
      <rect x="104" y="17" width="32" height="10" rx="2" className="grip" />
      {Array.from({ length: max }, (_, i) => (
        <g key={i} className={i < loaded ? "plate on" : "plate"} style={{ "--i": i } as React.CSSProperties}>
          <rect x={92 - i * 12} y={8 - i * 2} width="9" height={28 + i * 4} rx="2" className="pl pl-l" />
          <rect x={139 + i * 12} y={8 - i * 2} width="9" height={28 + i * 4} rx="2" className="pl pl-r" />
        </g>
      ))}
    </svg>
  );
}

/** Wraps the auth card: it leans toward the pointer with a moving glare (like a physical tag). Off for touch, reduced motion and keyboard-only use. */
export function Tilt({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof matchMedia !== "function" || matchMedia("(prefers-reduced-motion: reduce)").matches || !matchMedia("(pointer: fine)").matches) return;
    let raf = 0, x = 0, y = 0;
    const move = (e: PointerEvent) => {
      x = (e.clientX / innerWidth) * 2 - 1; y = (e.clientY / innerHeight) * 2 - 1;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const r = el.getBoundingClientRect();
        el.style.setProperty("--tx", x.toFixed(3)); el.style.setProperty("--ty", y.toFixed(3));
        el.style.setProperty("--gx", `${(((x + 1) / 2) * innerWidth - r.left).toFixed(0)}px`); el.style.setProperty("--gy", `${(((y + 1) / 2) * innerHeight - r.top).toFixed(0)}px`);
      });
    };
    addEventListener("pointermove", move, { passive: true });
    return () => { removeEventListener("pointermove", move); if (raf) cancelAnimationFrame(raf); };
  }, []);
  return <div className="gate-tilt" ref={ref}>{children}</div>;
}

export function greetingKey(hour: number): "morning" | "day" | "evening" | "night" {
  return hour >= 5 && hour < 12 ? "morning" : hour < 17 ? "day" : hour < 22 ? "evening" : "night";
}
