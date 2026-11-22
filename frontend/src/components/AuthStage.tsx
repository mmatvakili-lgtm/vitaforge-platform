"use client";
import { useEffect, useState } from "react";
import { useT } from "../lib/react/context.tsx";
import { Body3D, type RegionStatus } from "./Body3D.tsx";

/** Order in which muscles "wake up" while you type (count only; the text itself is never read). */
const SWEEP = ["abdominals", "chest", "shoulders", "lats", "biceps", "triceps", "traps", "quadriceps", "hamstrings", "glutes", "calves"];

/** The login scene: the 3D body reacts to the form next to it (idea from "reactive character" sign-in pages).
 *  - follows the pointer with a small turn; - turns its back while a password field is focused (looking away);
 *  - upper body lights when the email field has an address, lower body when the password has text; - shakes when an error appears.
 *  Purely decorative: it never reads or stores what is typed, only whether a field is empty. Skipped on phones. */
export function AuthStage() {
  const { t } = useT();
  const [wide, setWide] = useState(false);
  const [gaze, setGaze] = useState(0);
  const [away, setAway] = useState(false);
  const [typed, setTyped] = useState(0);
  const [fire, setFire] = useState(false);
  const [shake, setShake] = useState(0);

  useEffect(() => {
    const mq = matchMedia("(min-width: 801px)");
    const on = () => setWide(mq.matches); on();
    mq.addEventListener("change", on); return () => mq.removeEventListener("change", on);
  }, []);
  useEffect(() => {
    if (!wide) return;
    const inAuth = (e: Event) => (e.target as Element | null)?.closest?.(".auth");
    const move = (e: PointerEvent) => setGaze((e.clientX / innerWidth) * 2 - 1);
    const fin = (e: FocusEvent) => { if (inAuth(e) && (e.target as HTMLInputElement).type === "password") setAway(true); };
    const fout = (e: FocusEvent) => { if (inAuth(e) && (e.target as HTMLInputElement).type === "password") setAway(false); };
    const inp = (e: Event) => {
      if (!inAuth(e)) return;
      let total = 0;
      document.querySelectorAll<HTMLInputElement>(".auth input").forEach((i) => { if (i.type !== "checkbox") total += i.value.length; });
      setTyped(total);
    };
    const ignite = () => setFire(true);
    addEventListener("vf-ignite", ignite);
    const mo = new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n instanceof Element && (n.matches('[role="alert"]') || n.querySelector('[role="alert"]'))) setShake((k) => k + 1); });
    const card = document.querySelector(".auth"); if (card) mo.observe(card, { childList: true, subtree: true });
    addEventListener("pointermove", move, { passive: true });
    document.addEventListener("focusin", fin); document.addEventListener("focusout", fout); document.addEventListener("input", inp);
    return () => { removeEventListener("pointermove", move); document.removeEventListener("focusin", fin); document.removeEventListener("focusout", fout); document.removeEventListener("input", inp); removeEventListener("vf-ignite", ignite); mo.disconnect(); };
  }, [wide]);

  if (!wide) return null;
  const status: Record<string, RegionStatus> = {};
  const lit = fire ? SWEEP.length : Math.min(SWEEP.length, Math.floor(typed / 2));
  for (const g of SWEEP.slice(0, lit)) status[g] = "focus";
  return (
    <div className={fire ? "auth-stage fire" : "auth-stage"}>
      <i className="scan" aria-hidden="true" />
      <Body3D height={520} status={status} faceFocus={false} controls={false} gaze={away ? 2 : gaze} shakeKey={shake} label={t("home.bodyAria")} />
    </div>
  );
}
