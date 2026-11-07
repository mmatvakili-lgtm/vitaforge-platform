"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";

export default function Login() {
  const [msg, setMsg] = useState("");
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const r = await api<{ token: string }>("POST", "/auth/login", undefined, { email: f.get("email"), password: f.get("password") });
    setMsg(r.ok ? "OK" : String(r.status));
  }
  return (
    <main>
      <p role="note">{t("fa", "devNotice")}</p>
      <form onSubmit={submit}>
        <label>{t("fa", "email")} <input name="email" type="email" autoComplete="email" required /></label>
        <label>{t("fa", "password")} <input name="password" type="password" autoComplete="current-password" required /></label>
        <button type="submit">{t("fa", "submit")}</button>
      </form>
      <p aria-live="polite">{msg}</p>
    </main>
  );
}
