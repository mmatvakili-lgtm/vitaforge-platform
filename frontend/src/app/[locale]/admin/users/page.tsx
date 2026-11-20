"use client";
import { useEffect, useMemo, useState } from "react";
import { adminCall } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { useStaffRole } from "../../../../components/admin/AdminShell.tsx";

type U = { id: string; email: string; role: string; verified: boolean };
export default function UsersAdmin() {
  const { t, n } = useT();
  const role = useStaffRole();
  const [rows, setRows] = useState<U[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [q, setQ] = useState("");
  const [only, setOnly] = useState<"all" | "unverified" | "staff">("all");
  useEffect(() => { if (role !== "super_admin") { setFailed(true); return; } adminCall<{ users: U[] }>("GET", "/admin/accounts").then((r) => (r.ok ? setRows(r.data.users) : setFailed(true))); }, [role]);
  const shown = useMemo(() => (rows ?? []).filter((u) => u.email.toLowerCase().includes(q.trim().toLowerCase())
    && (only === "all" || (only === "unverified" ? !u.verified : u.role === "admin" || u.role === "super_admin"))), [rows, q, only]);
  if (failed) return <p className="alert alert-warning" role="status">{t("admin.forbidden")}</p>;
  if (!rows) return <div className="adm-skel" aria-busy="true"><span /><span /></div>;
  return (
    <>
      <p className="adm-lead">{t("admin.users.intro", { n: rows.length })}</p>
      <div className="adm-toolbar">
        <input type="search" dir="ltr" placeholder={t("admin.users.search")} aria-label={t("admin.users.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="adm-chips" role="group" aria-label={t("admin.media.filter")}>
          {(["all", "unverified", "staff"] as const).map((f) => <button key={f} type="button" aria-pressed={only === f} onClick={() => setOnly(f)}>{t(`admin.users.f.${f}`)}</button>)}
        </div>
      </div>
      <p className="adm-foot">{t("admin.media.count", { n: shown.length })}</p>
      {shown.length === 0 ? <p className="adm-empty">{t("admin.users.empty")}</p> : (
        <div className="adm-table-wrap">
          <table className="adm-table">
            <thead><tr><th scope="col">{t("admin.users.col.email")}</th><th scope="col">{t("admin.users.col.role")}</th><th scope="col">{t("admin.users.col.status")}</th></tr></thead>
            <tbody>
              {shown.map((u) => (
                <tr key={u.id}>
                  <td><bdi dir="ltr">{u.email}</bdi></td>
                  <td><span className={u.role === "super_admin" ? "adm-role owner" : "adm-role"}>{["admin", "super_admin"].includes(u.role) ? t(`admin.role.${u.role}`) : u.role}</span></td>
                  <td><span className={u.verified ? "adm-dot on" : "adm-dot"} />{u.verified ? t("admin.users.verified") : t("admin.users.unverified")}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
      <p className="adm-foot">{n(shown.length)} / {n(rows.length)}</p>
    </>
  );
}
