"use client";
import { useEffect, useState } from "react";
import { clock, restFraction, restRemaining } from "../lib/rest-timer.ts";
import { useT } from "../lib/react/context.tsx";

/** Rest countdown between sets. Optional convenience: logging never depends on it. */
export function RestTimer({ seconds, onDone }: { seconds: number; onDone: () => void }) {
  const { t, n } = useT();
  const [endsAt] = useState(() => Date.now() + seconds * 1000);
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    const id = window.setInterval(() => {
      const r = restRemaining(endsAt, Date.now());
      setLeft(r);
      if (r === 0) { window.clearInterval(id); try { navigator.vibrate?.(200); } catch { /* not supported */ } }
    }, 250);
    return () => window.clearInterval(id);
  }, [endsAt]);
  const f = restFraction(seconds, left), C = 2 * Math.PI * 44;
  return (
    <div className="rest" role="group" aria-label={t("wk.restTimer")}>
      <svg viewBox="0 0 100 100" width="96" height="96" aria-hidden="true">
        <circle cx="50" cy="50" r="44" fill="none" stroke="var(--line)" strokeWidth="6" />
        <circle cx="50" cy="50" r="44" fill="none" stroke="var(--accent)" strokeWidth="6" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - f)} transform="rotate(-90 50 50)" />
      </svg>
      <span className="num rest-clock" aria-hidden="true">{clock(left)}</span>
      <p role="status" className="muted">{left === 0 ? t("wk.restDone") : t("wk.restLeft", { n: n(left) })}</p>
      <button type="button" onClick={onDone}>{left === 0 ? t("wk.restNext") : t("wk.restSkip")}</button>
    </div>
  );
}
