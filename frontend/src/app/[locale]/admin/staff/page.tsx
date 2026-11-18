"use client";
import { useCallback, useEffect, useState } from "react";
import { adminCall } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { Alert, Button, Card, Field, Loading } from "../../../../components/ui.tsx";

type Staff = { id: string; email: string; role: string };
type Entry = { at: number; actor: string; action: string; target: string; before: unknown; after: unknown };

export default function StaffPage() {
  const { t } = useT();
  const [staff, setStaff] = useState<Staff[] | null>(null);
  const [audit, setAudit] = useState<Entry[]>([]);
  const [forbidden, setForbidden] = useState(false);
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const load = useCallback(async () => {
    const s = await adminCall<{ staff: Staff[] }>("GET", "/admin/staff");
    if (!s.ok) { setForbidden(true); setStaff([]); return; }
    setStaff(s.data.staff);
    const a = await adminCall<{ entries: Entry[] }>("GET", "/admin/audit");
    if (a.ok) setAudit(a.data.entries);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function add() {
    setMsg(null);
    const r = await adminCall("POST", "/admin/staff", { email });
    if (r.ok) { setEmail(""); setMsg({ kind: "success", text: t("admin.staff.added") }); await load(); return; }
    setMsg({ kind: "error", text: r.status === 404 ? t("admin.staff.notFound") : r.status === 409 ? t("admin.staff.conflict") : t("admin.error") });
  }
  async function remove(id: string) {
    setMsg(null);
    const r = await adminCall("DELETE", `/admin/staff/${encodeURIComponent(id)}`);
    setMsg(r.ok ? { kind: "success", text: t("admin.staff.removed") } : { kind: "error", text: t("admin.error") });
    await load();
  }
  if (staff === null) return <Card title={t("admin.staff.title")}><Loading /></Card>;
  if (forbidden) return <Card title={t("admin.staff.title")}><Alert kind="warning">{t("admin.forbidden")}</Alert></Card>;
  return (
    <Card title={t("admin.staff.title")}>
      <p>{t("admin.staff.intro")}</p>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <div className="row">
        <Field id="adm-email" label={t("admin.staff.email")} hint={t("admin.staff.emailHint")}>
          <input id="adm-email" type="email" dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
        </Field>
      </div>
      <Button type="button" disabled={!email.includes("@")} onClick={add}>{t("admin.staff.add")}</Button>
      <ul className="plain">
        {staff.map((s) => (
          <li key={s.id} className="card-lite">
            <bdi dir="ltr">{s.email}</bdi> <span className="tag">{t(`admin.role.${s.role}`)}</span>
            {s.role === "admin" && <> <Button type="button" onClick={() => remove(s.id)}>{t("admin.staff.remove")}</Button></>}
          </li>))}
      </ul>
      <h2>{t("admin.audit.title")}</h2>
      {audit.length === 0 ? <p className="muted">{t("admin.audit.empty")}</p> : (
        <ul className="plain">
          {audit.map((a, i) => (
            <li key={i} className="card-lite">
              <bdi dir="ltr"><strong>{a.action}</strong> · {a.target} · {new Date(a.at * 1000).toLocaleString()}</bdi>
              <p className="muted"><bdi dir="ltr">{JSON.stringify(a.before)} → {JSON.stringify(a.after)}</bdi></p>
            </li>))}
        </ul>)}
    </Card>
  );
}
