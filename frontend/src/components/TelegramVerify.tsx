"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useApi, useT } from "../lib/react/context.tsx";
import { POLL_MS, clock, linkErrorKey, pollOutcome, safeDeepLink, secondsLeft, type TgPhase } from "../lib/telegram.ts";
import { Alert, Button } from "./ui.tsx";

/** Primary account verification. The password is only held in memory (props) to prove ownership and to detect completion via the normal login. */
export function TelegramVerify({ email, password }: { email: string; password: string }) {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [phase, setPhase] = useState<TgPhase>("idle");
  const [msg, setMsg] = useState<string>("");
  const [link, setLink] = useState<string | null>(null);
  const [expires, setExpires] = useState("");
  const [left, setLeft] = useState(0);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const request = useCallback(async () => {
    setPhase("requesting"); setMsg("");
    const r = await api.call("API-AUTH-010", { body: { identifier: email.trim(), password } });
    if (!alive.current) return;
    if (!r.ok) { const e = linkErrorKey(r.status); setPhase(e.phase); setMsg(e.key); return; }
    const url = safeDeepLink(r.data.deep_link);
    if (!url) { setPhase("error"); setMsg("telegram.linkFailed"); return; }
    setLink(url); setExpires(r.data.expires_at); setLeft(secondsLeft(r.data.expires_at, Date.now())); setPhase("pending");
  }, [api, email, password]);

  useEffect(() => {                                   // countdown + completion detection (a normal login succeeds only once the bot verified the account)
    if (phase !== "pending") return;
    const tick = setInterval(() => {
      const s = secondsLeft(expires, Date.now());
      setLeft(s);
      if (s <= 0) setPhase("expired");
    }, 1000);
    let stop = false;
    const poll = async () => {
      if (stop) return;
      const r = await api.call("API-AUTH-003", { body: { identifier: email.trim(), password } });
      if (stop || !alive.current) return;
      const o = pollOutcome(r.status);
      if (o === "verified" && r.ok) { setPhase("verified"); router.push(`/${locale}/${r.data.onboarding_status === "completed" ? "plan" : "onboarding"}`); return; }
      if (o === "locked" || o === "error") { setPhase("error"); setMsg(o === "locked" ? "error.account_locked" : "telegram.linkFailed"); return; }
      timer = setTimeout(poll, POLL_MS);
    };
    let timer = setTimeout(poll, POLL_MS);
    return () => { stop = true; clearInterval(tick); clearTimeout(timer); };
  }, [phase, expires, api, email, password, router, locale]);

  return (
    <div aria-live="polite">
      <p className="muted">{t("telegram.intro")}</p>
      {(phase === "idle" || phase === "requesting" || phase === "error" || phase === "expired") && (
        <>
          {phase === "expired" && <Alert kind="warning">{t("telegram.expired")}</Alert>}
          {phase === "error" && <Alert kind="error">{t(msg)}</Alert>}
          <Button type="button" busy={phase === "requesting"} onClick={request}>{phase === "expired" || phase === "error" ? t("telegram.again") : t("telegram.button")}</Button>
        </>
      )}
      {phase === "pending" && link && (
        <>
          <Alert kind="info">{t("telegram.pending")}</Alert>
          <p><a className="btn" href={link} target="_blank" rel="noopener noreferrer">{t("telegram.open")}</a></p>
          <p className="muted">{t("telegram.steps")}</p>
          <p className="muted">{t("telegram.expiresIn")} <bdi dir="ltr">{clock(left)}</bdi></p>
        </>
      )}
      {phase === "verified" && <Alert kind="success">{t(msg || "telegram.verified")}</Alert>}
      {phase === "unavailable" && <Alert kind="warning">{t("telegram.unavailable")}</Alert>}
      <p className="muted">{t("telegram.privacy")}</p>
    </div>
  );
}
