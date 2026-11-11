"use client";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { normalizeDigits } from "../../../lib/i18n.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field } from "../../../components/ui.tsx";

export default function VerifyPage() {
  const { locale, t } = useT();
  const api = useApi();
  const [identifier, setIdentifier] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);
  const [sent, setSent] = useState(false);
  const [wait, setWait] = useState(0);

  useEffect(() => {                                   // prefill from ?email= (set by the register step); read client-side to stay static-export safe
    const e = new URLSearchParams(window.location.search).get("email");
    if (e) setIdentifier(e);
  }, []);
  useEffect(() => {
    if (wait <= 0) return;
    const id = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(id);
  }, [wait]);

  async function resend() {
    setBusy(true); setError(null); setSent(false);
    const r = await api.call("API-AUTH-009", { body: { identifier: identifier.trim() } });
    setBusy(false);
    if (!r.ok) { if (r.error.status === 429) setWait(60); return setError(r.error); }
    setSent(true); setWait(60);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const r = await api.call("API-AUTH-002", { body: { identifier: identifier.trim(), code: normalizeDigits(code.trim()) } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setDone(true);
  }

  if (done) return (<Card title={t("auth.verify.title")}><Alert kind="success">{t("auth.verify.done")}</Alert><ButtonLink href={`/${locale}/login`}>{t("nav.login")}</ButtonLink></Card>);
  return (
    <Card title={t("auth.verify.title")}>
      <form onSubmit={submit} noValidate>
        <Field id="identifier" label={t("auth.email")}><input id="identifier" type="email" inputMode="email" dir="ltr" required value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></Field>
        <Field id="code" label={t("auth.verify.code")}><input id="code" inputMode="numeric" autoComplete="one-time-code" dir="ltr" required value={code} onChange={(e) => setCode(e.target.value)} /></Field>
        <ApiErrorView error={error} />
        {error && (error.status === 410 || error.code === "bad_request") && <p className="muted">{t("auth.verify.expiredHint")}</p>}
        {sent && <Alert kind="success">{t("auth.verify.sent")}</Alert>}
        <p className="muted">{t("auth.verify.checkInbox")}</p>
        <div className="row">
          <Button type="submit" busy={busy}>{t("auth.verify.submit")}</Button>
          <Button type="button" busy={busy} disabled={wait > 0 || !identifier.trim()} onClick={resend}>{t("auth.verify.resend")}</Button>
        </div>
        {wait > 0 && <p className="muted" aria-live="polite">{t("auth.verify.resendWait", { seconds: wait })}</p>}
      </form>
    </Card>
  );
}
