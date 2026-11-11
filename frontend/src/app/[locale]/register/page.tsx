"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field } from "../../../components/ui.tsx";

const PW = /^(?=.*[A-Z])(?=.*\d).{10,}$/;

export default function RegisterPage() {
  const { locale, t } = useT();
  const api = useApi();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [dob, setDob] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);
  const [local, setLocal] = useState<Record<string, string>>({});

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) errs.email = t("error.validation_failed");
    if (!PW.test(password)) errs.password = t("auth.passwordHint");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dob)) errs.dob = t("error.validation_failed");
    setLocal(errs);
    if (Object.keys(errs).length) return;
    setBusy(true); setError(null);
    const r = await api.call("API-AUTH-001", { body: { email: email.trim(), password, date_of_birth: dob, language: locale } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setDone(true);
  }

  if (done) {
    return (
      <Card title={t("auth.register.title")}>
        <Alert kind="success">{t("auth.register.done")}</Alert>
        <div className="row"><ButtonLink href={`/${locale}/verify?email=${encodeURIComponent(email.trim())}`}>{t("auth.verify.title")}</ButtonLink><ButtonLink href={`/${locale}/login`} secondary>{t("nav.login")}</ButtonLink></div>
      </Card>
    );
  }
  return (
    <Card title={t("auth.register.title")}>
      <form onSubmit={submit} noValidate>
        <Field id="email" label={t("auth.email")} error={local.email}><input id="email" type="email" inputMode="email" autoComplete="email" dir="ltr" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field id="password" label={t("auth.password")} hint={t("auth.passwordHint")} error={local.password}><input id="password" type="password" autoComplete="new-password" dir="ltr" required value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="password-hint" /></Field>
        <Field id="dob" label={t("auth.dob")} hint={t("auth.adultsOnly")} error={local.dob}><input id="dob" type="date" dir="ltr" required value={dob} onChange={(e) => setDob(e.target.value)} /></Field>
        <ApiErrorView error={error} />
        <Button type="submit" busy={busy}>{t("auth.register.submit")}</Button>
      </form>
      <p><Link href={`/${locale}/login`}>{t("auth.register.have")}</Link></p>
    </Card>
  );
}
