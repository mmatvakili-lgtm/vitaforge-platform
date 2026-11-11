"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field } from "../../../components/ui.tsx";

export default function ForgotPage() {
  const { locale, t } = useT();
  const api = useApi();
  const [identifier, setIdentifier] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    const r = await api.call("API-AUTH-005", { body: { identifier: identifier.trim() } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setDone(true);                                    // identical for known and unknown addresses
  }

  return (
    <Card title={t("auth.forgot.title")}>
      {done ? <Alert kind="success">{t("auth.forgot.done")}</Alert> : (
        <form onSubmit={submit} noValidate>
          <Field id="identifier" label={t("auth.email")}><input id="identifier" type="email" inputMode="email" autoComplete="username" dir="ltr" required value={identifier} onChange={(e) => setIdentifier(e.target.value)} /></Field>
          <ApiErrorView error={error} />
          <Button type="submit" busy={busy}>{t("auth.forgot.submit")}</Button>
        </form>
      )}
      <p><Link href={`/${locale}/login`}>{t("auth.forgot.back")}</Link></p>
    </Card>
  );
}
