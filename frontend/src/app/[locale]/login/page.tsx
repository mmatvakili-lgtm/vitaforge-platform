"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, Button, Card, Field } from "../../../components/ui.tsx";
import { TelegramVerify } from "../../../components/TelegramVerify.tsx";

export default function LoginPage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [tg, setTg] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const r = await api.call("API-AUTH-003", { body: { identifier: identifier.trim(), password } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    router.push(`/${locale}/${r.data.onboarding_status === "completed" ? "plan" : "onboarding"}`);
  }

  return (
    <Card title={t("auth.login.title")}>
      <form onSubmit={submit} noValidate>
        <Field id="identifier" label={t("auth.email")}><input id="identifier" type="email" inputMode="email" autoComplete="username" dir="ltr" required value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></Field>
        <Field id="password" label={t("auth.password")}><input id="password" type="password" autoComplete="current-password" dir="ltr" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <ApiErrorView error={error} />
        <Button type="submit" busy={busy}>{t("auth.login.submit")}</Button>
      </form>
      {error?.status === 401 && identifier.trim() && password && !tg && <p><button type="button" className="btn btn-secondary" onClick={() => setTg(true)}>{t("telegram.loginHint")}</button></p>}
      {tg && <TelegramVerify email={identifier} password={password} />}
      <p><Link href={`/${locale}/register`}>{t("auth.login.noAccount")}</Link></p>
      <p><Link href={`/${locale}/forgot`}>{t("auth.login.forgot")}</Link></p>
      <p><Link href={`/${locale}/verify`}>{t("auth.login.haveCode")}</Link></p>
    </Card>
  );
}
