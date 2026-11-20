"use client";
import { useEffect, useState } from "react";
import { useT } from "../lib/react/context.tsx";
import { Body3D, type RegionStatus } from "./Body3D.tsx";

const UPPER = ["chest", "shoulders", "biceps", "triceps", "lats", "traps"];
const LOWER = ["quadriceps", "hamstrings", "glutes", "calves", "abdominals"];

/** The login scene: the 3D body reacts to the form next to it (idea from "reactive character" sign-in pages).
 *  - follows the pointer with a small turn; - turns its back while a password field is focused (looking away);
 *  - upper body lights when the email field has an address, lower body when the password has text; - shakes when an error appears.
 *  Purely decorative: it never reads or stores what is typed, only whether a field is empty. Skipped on phones. */
export function AuthStage() {
  const { t } = useT();
  const [wide, setWide] = useState(false);
  const [gaze, setGaze] = useState(0);
  const [away, setAway] = useState(false);
  const [mail, setMail] = useState(false);
  const [pass, setPass] = useState(false);
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
      const el = e.target as HTMLInputElement;
      if (!inAuth(e) || !el) return;
      if (el.type === "password") setPass(el.value.length > 0);
      else if (el.type === "email" || el.id === "identifier") setMail(el.value.includes("@"));
    };
    const mo = new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n instanceof Element && (n.matches('[role="alert"]') || n.querySelector('[role="alert"]'))) setShake((k) => k + 1); });
    const card = document.querySelector(".auth"); if (card) mo.observe(card, { childList: true, subtree: true });
    addEventListener("pointermove", move, { passive: true });
    document.addEventListener("focusin", fin); document.addEventListener("focusout", fout); document.addEventListener("input", inp);
    return () => { removeEventListener("pointermove", move); document.removeEventListener("focusin", fin); document.removeEventListener("focusout", fout); document.removeEventListener("input", inp); mo.disconnect(); };
  }, [wide]);

  if (!wide) return null;
  const status: Record<string, RegionStatus> = {};
  if (mail) for (const g of UPPER) status[g] = "focus";
  if (pass) for (const g of LOWER) status[g] = "focus";
  return (
    <div className="auth-stage">
      <Body3D height={520} status={status} faceFocus={false} controls={false} gaze={away ? 2 : gaze} shakeKey={shake} label={t("home.bodyAria")} />
    </div>
  );
}
