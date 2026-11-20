"use client";
import { useCallback, useEffect, useState } from "react";
import { adminCall } from "../../../../lib/admin.ts";
import { groupAuditByDay, type AuditEntry } from "../../../../lib/adminStats.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { useStaffRole } from "../../../../components/admin/AdminShell.tsx";

type Staff = { id: string; email: string; role: string };
const short = (v: unknown) => { const s = JSON.stringify(v) ?? "—"; return s.length > 90 ? s.slice(0, 87) + "…" : s; };

export default function StaffPage() {
  const { locale, t } = useT();
  const role = useStaffRole();
  const [staff, setStaff] = useState<Staff[] | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [failed, setFailed] = useState(false);
  const [email, setEmail] = useState("");
  const [confirm, setConfirm] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const load = useCallback(async () => {
    const s = await adminCall<{ staff: Staff[] }>("GET", "/admin/staff");
    if (!s.ok) { setFailed(true); setStaff([]); return; }
    setStaff(s.data.staff);
    const a = await adminCall<{ entries: AuditEntry[] }>("GET", "/admin/audit");
    if (a.ok) setAudit(a.data.entries);
  }, []);
  useEffect(() => { if (role === "super_admin") load(); else { setFailed(true); setStaff([]); } }, [load, role]);

  async function add() {
    setMsg(null);
    const r = await adminCall("POST", "/admin/staff", { email });
    if (r.ok) { setEmail(""); setMsg({ kind: "success", text: t("admin.staff.added") }); await load(); return; }
    setMsg({ kind: "error", text: r.status === 404 ? t("admin.staff.notFound") : r.status === 409 ? t("admin.staff.conflict") : t("admin.error") });
  }
  async function remove(id: string) {
    setMsg(null); setConfirm(null);
    const r = await adminCall("DELETE", `/admin/staff/${encodeURIComponent(id)}`);
    setMsg(r.ok ? { kind: "success", text: t("admin.staff.removed") } : { kind: "error", text: t("admin.error") });
    await load();
  }
  if (staff === null) return <div className="adm-skel" aria-busy="true"><span /><span /></div>;
  if (failed) return <p className="alert alert-warning" role="status">{t("admin.forbidden")}</p>;
  const fmtDay = new Intl.DateTimeFormat(locale, { dateStyle: "full", timeZone: "UTC" });
  const fmtTime = new Intl.DateTimeFormat(locale, { timeStyle: "short" });
  return (
    <div className="adm-split">
      <section className="adm-panel">
        <header><h2>{t("admin.staff.title")}</h2><span className="adm-pill">{staff.length}</span></header>
        <p className="adm-lead">{t("admin.staff.intro")}</p>
        <div className="adm-inline">
          <input type="email" dir="ltr" value={email} placeholder={t("admin.staff.email")} aria-label={t("admin.staff.email")} autoComplete="off" onChange={(e) => setEmail(e.target.value)} />
          <button type="button" className="adm-primary" disabled={!email.includes("@")} onClick={add}>{t("admin.staff.add")}</button>
        </div>
        <p className="adm-foot">{t("admin.staff.emailHint")}</p>
        {msg && <p className={`adm-msg ${msg.kind}`} role={msg.kind === "error" ? "alert" : "status"}>{msg.text}</p>}
        <ul className="adm-people">
          {staff.map((s) => (
            <li key={s.id}>
              <span className="adm-avatar" aria-hidden="true">{s.email.slice(0, 1).toUpperCase()}</span>
              <bdi dir="ltr" className="adm-people-mail">{s.email}</bdi>
              <span className={s.role === "super_admin" ? "adm-role owner" : "adm-role"}>{t(`admin.role.${s.role}`)}</span>
              {s.role === "admin" && (confirm === s.id
                ? <span className="adm-confirm"><button type="button" className="danger" onClick={() => remove(s.id)}>{t("admin.staff.confirmRemove")}</button><button type="button" className="adm-ghost" onClick={() => setConfirm(null)}>{t("admin.media.clear")}</button></span>
                : <button type="button" className="adm-ghost" onClick={() => setConfirm(s.id)}>{t("admin.staff.remove")}</button>)}
            </li>))}
        </ul>
      </section>
      <section className="adm-panel">
        <header><h2>{t("admin.audit.title")}</h2><span className="adm-pill">{audit.length}</span></header>
        {audit.length === 0 ? <p className="adm-empty">{t("admin.audit.empty")}</p> : (
          <div className="adm-timeline">
            {groupAuditByDay(audit).map((g) => (
              <div key={g.day}>
                <h3>{fmtDay.format(new Date(g.day * 1000))}</h3>
                <ul>
                  {g.items.map((a, i) => (
                    <li key={i}>
                      <time dateTime={new Date(a.at * 1000).toISOString()}>{fmtTime.format(new Date(a.at * 1000))}</time>
                      <div><bdi dir="ltr"><b>{a.action}</b> <code>{a.target}</code></bdi>
                        <p><bdi dir="ltr">{short(a.before)} → {short(a.after)}</bdi></p></div>
                    </li>))}
                </ul>
              </div>))}
          </div>)}
      </section>
    </div>
  );
}
