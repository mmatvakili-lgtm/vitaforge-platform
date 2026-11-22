"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, Button, ButtonLink, AuthCard as Card, Field, PasswordInput } from "../../../components/ui.tsx";
import { Barbell, greetingKey } from "../../../components/Gate.tsx";
import { TelegramVerify } from "../../../components/TelegramVerify.tsx";

/** Login as a short conversation: one question at a time, a barbell that gets loaded, a body that wakes up as you type and ignites when you're in.
 *  Both inputs stay in the DOM (password managers can fill them); the inactive one is collapsed and inert. */
export default function LoginPage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<"email" | "pass">("email");
  const [busy, setBusy] = useState(false);
  const [forged, setForged] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [mailErr, setMailErr] = useState("");
  const [tg, setTg] = useState(false);
  const [greet, setGreet] = useState("day");
  const mailRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLDivElement>(null);
  useEffect(() => { setGreet(greetingKey(new Date().getHours())); }, []);
  useEffect(() => { if (step === "pass") passRef.current?.querySelector("input")?.focus(); }, [step]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (forged || busy) return;
    if (step === "email") {
      if (!/^\S+@\S+\.\S+$/.test(identifier.trim())) { setMailErr(t("g.mail.invalid")); mailRef.current?.focus(); return; }
      setMailErr(""); setError(null);
      // browser autofill may already have filled the password: go straight on
      if (password) return login();
      return setStep("pass");
    }
    return login();
  }

  async function login() {
    setBusy(true); setError(null);
    const r = await api.call("API-AUTH-003", { body: { identifier: identifier.trim(), password } });
    setBusy(false);
    if (!r.ok) { setStep("pass"); return setError(r.error); }
    setForged(true);
    window.dispatchEvent(new Event("vf-ignite"));
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(() => router.push(`/${locale}/${r.data.onboarding_status === "completed" ? "dashboard" : "onboarding"}`), reduce ? 0 : 900);
  }

  const loaded = forged ? 3 : step === "pass" ? 2 : identifier.trim() ? 1 : 0;
  return (
    <Card>
      <div className={`gate ${forged ? "forged" : ""}`} data-step={step}>
        <Barbell loaded={loaded} />
        <p className="gate-hello" aria-live="polite">{forged ? t("g.ready") : t(`g.hello.${greet}`)}</p>
        <h1 className="gate-q">{forged ? t("g.ready.sub") : step === "email" ? t("g.q.email") : t("g.q.pass")}</h1>
        <form onSubmit={submit} noValidate>
          <div className="gate-pane" data-on={step === "email"} aria-hidden={step !== "email"} inert={step !== "email"}>
            <div>
              <Field id="identifier" label={t("auth.email")} error={mailErr || undefined}>
                <input ref={mailRef} id="identifier" type="email" inputMode="email" autoComplete="username" dir="ltr" required autoFocus value={identifier} onChange={(e) => { setIdentifier(e.target.value); setMailErr(""); }} />
              </Field>
            </div>
          </div>
          <div className="gate-pane" data-on={step === "pass"} aria-hidden={step !== "pass"} inert={step !== "pass"} ref={passRef}>
            <div>
              <button type="button" className="gate-who" onClick={() => setStep("email")} aria-label={t("g.back")}><span dir="ltr">{identifier.trim()}</span><i aria-hidden="true">✎</i></button>
              <Field id="password" label={t("auth.password")}>
                <PasswordInput id="password" autoComplete="current-password" dir="ltr" required value={password} onChange={(e) => setPassword(e.target.value)} />
              </Field>
              <p className="auth-aux"><Link href={`/${locale}/forgot`}>{t("auth.login.forgot")}</Link></p>
            </div>
          </div>
          <ApiErrorView error={error} />
          <Button type="submit" busy={busy} disabled={forged}>{step === "email" ? t("g.next") : t("auth.login.submit")}</Button>
          <p className="gate-step" aria-hidden="true">{t("g.step", { a: step === "email" ? 1 : 2, b: 2 })}</p>
        </form>
      </div>
      {error?.status === 401 && (
        <aside className="auth-help" aria-live="polite">
          <p>{t("auth.login.unverifiedHelp")}</p>
          <div className="row">
            <ButtonLink href={`/${locale}/verify${identifier.trim() ? `?email=${encodeURIComponent(identifier.trim())}` : ""}`} secondary>{t("auth.login.verifyNow")}</ButtonLink>
            {identifier.trim() && password && !tg && <button type="button" className="btn btn-secondary" onClick={() => setTg(true)}>{t("telegram.loginHint")}</button>}
          </div>
        </aside>
      )}
      {tg && <TelegramVerify email={identifier} password={password} />}
      <p className="auth-alt"><Link href={`/${locale}/register`}>{t("auth.login.noAccount")}</Link></p>
    </Card>
  );
}
