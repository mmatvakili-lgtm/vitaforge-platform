"use client";
import Link from "next/link";
import { cloneElement, isValidElement, useState, type ReactElement, type ReactNode } from "react";
import type { ApiError } from "../lib/api/client.ts";
import { invalidFields } from "../lib/api/client.ts";
import { passwordChecks } from "../lib/password.ts";
import { useT } from "../lib/react/context.tsx";
import { useCountUp, useInViewOnce } from "../lib/react/useInView.ts";
import { AuthStage } from "./AuthStage.tsx";

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
  // Link the hint and the error to the control so screen readers announce them (explicit aria-describedby on the child is kept and extended).
  const ids = [hint ? `${id}-hint` : "", error ? `${id}-err` : ""].filter(Boolean);
  let control = children;
  if (isValidElement(children) && (ids.length > 0 || error)) {
    const el = children as ReactElement<Record<string, unknown>>;
    const own = typeof el.props["aria-describedby"] === "string" ? (el.props["aria-describedby"] as string).split(" ") : [];
    const all = [...new Set([...own, ...ids])].join(" ");
    control = cloneElement(el, { ...(all ? { "aria-describedby": all } : {}), ...(error ? { "aria-invalid": true } : {}) });
  }
  return (
    <div className="field">
      <label htmlFor={id} id={`${id}-lbl`}>{label}</label>
      {control}
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

/** Skeleton instead of a bare "loading" line: a heated bar sweeps over placeholder blocks; the text stays for screen readers. */
export function Loading() {
  const { t } = useT();
  return (
    <div role="status" className="sk" aria-live="polite">
      <span className="sr-only">{t("common.loading")}</span>
      <span className="sk-bar sk-w60" /><span className="sk-bar" /><span className="sk-bar sk-w80" /><span className="sk-heat" aria-hidden="true" />
    </div>
  );
}

/** Number that counts up from 0 when it scrolls into view (jumps straight to the value for reduced motion). */
export function CountUp({ value }: { value: number }) {
  const { n } = useT();
  const [ref, seen] = useInViewOnce<HTMLSpanElement>();
  const v = useCountUp(value, seen);
  return <span ref={ref}>{n(seen ? v : 0)}</span>;
}

/** Password field with a show/hide toggle and (optionally) the policy as live checks; it never reads the value anywhere else. */
export function PasswordInput({ meter, ...rest }: { meter?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  const { t } = useT();
  const [show, setShow] = useState(false);
  const c = passwordChecks(String(rest.value ?? ""));
  return (
    <div className="pw">
      <div className="pw-row">
        <input {...rest} type={show ? "text" : "password"} />
        <button type="button" className="pw-toggle" aria-pressed={show} onClick={() => setShow(!show)}>{show ? t("auth.hide") : t("auth.show")}</button>
      </div>
      {meter && (
        <div className="pw-meter" data-score={c.score} aria-live="polite">
          <span className="pw-bar" aria-hidden="true"><i /><i /><i /></span>
          <ul>
            <li className={c.len ? "ok" : ""}>{t("auth.rule.len")}</li>
            <li className={c.upper ? "ok" : ""}>{t("auth.rule.upper")}</li>
            <li className={c.digit ? "ok" : ""}>{t("auth.rule.digit")}</li>
          </ul>
        </div>)}
    </div>
  );
}

export function ButtonLink({ href, children, secondary }: { href: string; children: ReactNode; secondary?: boolean }) {
  return <Link href={href} className={secondary ? "btn btn-secondary" : "btn"}>{children}</Link>;
}

/** Auth screens: the form card beside a forge panel (brand line + heated anvil edge). Decorative panel hides on phones. */
export function AuthCard({ title, children }: { title?: string; children: ReactNode }) {
  const { t } = useT();
  return (
    <div className="auth">
      <aside className="auth-art" aria-hidden="true">
        <p className="auth-line"><span>{t("landing.h1a")}</span><span>{t("landing.h1b")}</span></p>
        <div className="auth-glow" /><AuthStage /><div className="lp-anvil" />
      </aside>
      <Card title={title}>{children}</Card>
    </div>
  );
}
