"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import type { ApiError } from "../lib/api/client.ts";
import { invalidFields } from "../lib/api/client.ts";
import { useT } from "../lib/react/context.tsx";

export function Alert({ kind = "error", children }: { kind?: "error" | "info" | "success" | "warning"; children: ReactNode }) {
  return <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}

export function ApiErrorView({ error }: { error: ApiError | null }) {
  const { t, err } = useT();
  if (!error) return null;
  const fields = invalidFields(error);
  return (
    <Alert>
      <p>{err(error)}</p>
      {fields.length > 0 && <p>{t("error.invalidFields", { fields: fields.join(", ") })}</p>}
      {error.requestId && <p className="muted">{t("common.requestId")}: <bdi dir="ltr">{error.requestId}</bdi></p>}
    </Alert>
  );
}

export function Field({ id, label, hint, error, children }: { id: string; label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <p className="hint" id={`${id}-hint`}>{hint}</p>}
      {error && <p className="field-error" id={`${id}-err`} role="alert">{error}</p>}
    </div>
  );
}

export function Button({ busy, children, ...rest }: { busy?: boolean; children: ReactNode } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { t } = useT();
  return <button {...rest} disabled={busy || rest.disabled} aria-busy={busy}>{busy ? t("common.submitting") : children}</button>;
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return <section className="card">{title && <h1>{title}</h1>}{children}</section>;
}

export function Loading() {
  const { t } = useT();
  return <p role="status" className="muted">{t("common.loading")}</p>;
}

export function ButtonLink({ href, children, secondary }: { href: string; children: ReactNode; secondary?: boolean }) {
  return <Link href={href} className={secondary ? "btn btn-secondary" : "btn"}>{children}</Link>;
}
