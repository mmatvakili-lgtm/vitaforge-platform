"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field } from "../../../components/ui.tsx";

export default function ResetPage() {
  const { locale, t } = useT();
  const api = useApi();
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => { setToken(new URLSearchParams(window.location.search).get("token") ?? ""); }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== again) return setMismatch(true);
    setMismatch(false); setBusy(true);
    const r = await api.call("API-AUTH-006", { body: { token: token ?? "", new_password: password } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setDone(true);
  }

  if (token === null) return <Card title={t("auth.reset.title")}><p className="muted">{t("common.loading")}</p></Card>;
  if (done) return (<Card title={t("auth.reset.title")}><Alert kind="success">{t("auth.reset.done")}</Alert><ButtonLink href={`/${locale}/login`}>{t("nav.login")}</ButtonLink></Card>);
  if (!token) return (<Card title={t("auth.reset.title")}><Alert>{t("auth.reset.missing")}</Alert><ButtonLink href={`/${locale}/forgot`}>{t("auth.reset.requestNew")}</ButtonLink></Card>);
  return (
    <Card title={t("auth.reset.title")}>
      <form onSubmit={submit} noValidate>
        <Field id="password" label={t("auth.reset.newPassword")} hint={t("auth.passwordHint")}><input id="password" type="password" autoComplete="new-password" dir="ltr" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <Field id="again" label={t("auth.reset.confirm")} error={mismatch ? t("auth.reset.mismatch") : undefined}><input id="again" type="password" autoComplete="new-password" dir="ltr" required value={again} onChange={(e) => setAgain(e.target.value)} /></Field>
        <ApiErrorView error={error} />
        <Button type="submit" busy={busy}>{t("auth.reset.submit")}</Button>
      </form>
      {error && <p><Link href={`/${locale}/forgot`}>{t("auth.reset.requestNew")}</Link></p>}
    </Card>
  );
}
