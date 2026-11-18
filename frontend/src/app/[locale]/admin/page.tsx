"use client";
import { useEffect, useState } from "react";
import { adminCall } from "../../../lib/admin.ts";
import { useT } from "../../../lib/react/context.tsx";
import { Alert, ButtonLink, Card, Loading } from "../../../components/ui.tsx";

export default function AdminHome() {
  const { locale, t } = useT();
  const [role, setRole] = useState<string | null>(null);
  useEffect(() => { adminCall<{ role: string }>("GET", "/admin/me").then((r) => setRole(r.ok ? r.data.role : "user")); }, []);
  if (role === null) return <Card title={t("admin.title")}><Loading /></Card>;
  if (role !== "admin" && role !== "super_admin") return <Card title={t("admin.title")}><Alert kind="warning">{t("admin.forbidden")}</Alert></Card>;
  return (
    <Card title={t("admin.title")}>
      <p className="muted">{t("admin.role")}: <strong>{t(`admin.role.${role}`)}</strong></p>
      <div className="row">
        <ButtonLink href={`/${locale}/admin/media`}>{t("admin.hub.media")}</ButtonLink>
        <ButtonLink href={`/${locale}/admin/review`} secondary>{t("admin.hub.review")}</ButtonLink>
        {role === "super_admin" && <ButtonLink href={`/${locale}/admin/staff`} secondary>{t("admin.hub.staff")}</ButtonLink>}
      </div>
    </Card>
  );
}
