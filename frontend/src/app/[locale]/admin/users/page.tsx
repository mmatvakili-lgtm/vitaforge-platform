"use client";
import { useEffect, useState } from "react";
import { adminCall } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { Alert, Card, Loading } from "../../../../components/ui.tsx";

type U = { id: string; email: string; role: string; verified: boolean };
export default function UsersAdmin() {
  const { t } = useT();
  const [rows, setRows] = useState<U[] | null>(null);
  const [forbidden, setForbidden] = useState(false);
  useEffect(() => { adminCall<{ users: U[] }>("GET", "/admin/accounts").then((r) => (r.ok ? setRows(r.data.users) : setForbidden(true))); }, []);
  if (forbidden) return <Card title={t("admin.users.title")}><Alert kind="warning">{t("admin.forbidden")}</Alert></Card>;
  if (!rows) return <Card title={t("admin.users.title")}><Loading /></Card>;
  return (
    <Card title={t("admin.users.title")}>
      <p>{t("admin.users.intro", { n: rows.length })}</p>
      <ul className="plain">
        {rows.map((u) => <li key={u.id} className="card-lite"><bdi dir="ltr">{u.email}</bdi> <span className="tag">{u.role}</span> {!u.verified && <span className="tag">{t("admin.users.unverified")}</span>}</li>)}
      </ul>
    </Card>
  );
}
