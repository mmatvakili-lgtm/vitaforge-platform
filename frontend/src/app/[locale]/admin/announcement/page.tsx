"use client";
import { useEffect, useState } from "react";
import { adminCall } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { Alert, Button, Card, Loading } from "../../../../components/ui.tsx";

type Ann = { enabled: boolean; text_fa: string; text_en: string; level: "info" | "warning"; expires_at: number | null };

export default function AnnouncementAdmin() {
  const { t } = useT();
  const [a, setA] = useState<Ann | null>(null);
  const [days, setDays] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  useEffect(() => { adminCall<Ann>("GET", "/admin/announcement").then((r) => (r.ok ? setA(r.data) : setForbidden(true))); }, []);
  async function save() {
    if (!a) return;
    const d = Number(days);
    const expires_at = days.trim() && d > 0 ? Math.floor(Date.now() / 1000 + d * 86400) : null;
    const r = await adminCall<Ann>("PUT", "/admin/announcement", { enabled: a.enabled, text_fa: a.text_fa, text_en: a.text_en, level: a.level, expires_at });
    if (r.ok) { setA(r.data); setMsg({ kind: "success", text: t("admin.saved") }); } else setMsg({ kind: "error", text: t("admin.media.invalid") });
  }
  if (forbidden) return <Card title={t("admin.announce.title")}><Alert kind="warning">{t("admin.forbidden")}</Alert></Card>;
  if (!a) return <Card title={t("admin.announce.title")}><Loading /></Card>;
  return (
    <Card title={t("admin.announce.title")}>
      <p>{t("admin.announce.intro")}</p>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <label className="check"><input type="checkbox" checked={a.enabled} onChange={(e) => setA({ ...a, enabled: e.target.checked })} />{t("admin.announce.enabled")}</label>
      <label htmlFor="an-fa">{t("admin.announce.fa")}</label>
      <textarea id="an-fa" rows={3} maxLength={300} value={a.text_fa} onChange={(e) => setA({ ...a, text_fa: e.target.value })} />
      <label htmlFor="an-en">{t("admin.announce.en")}</label>
      <textarea id="an-en" dir="ltr" rows={3} maxLength={300} value={a.text_en} onChange={(e) => setA({ ...a, text_en: e.target.value })} />
      <label htmlFor="an-lv">{t("admin.announce.level")}</label>
      <select id="an-lv" value={a.level} onChange={(e) => setA({ ...a, level: e.target.value as Ann["level"] })}>
        <option value="info">{t("admin.announce.info")}</option><option value="warning">{t("admin.announce.warning")}</option>
      </select>
      <label htmlFor="an-d">{t("admin.announce.days")}</label>
      <input id="an-d" type="number" min={1} max={365} dir="ltr" value={days} onChange={(e) => setDays(e.target.value)} />
      <Button type="button" onClick={save}>{t("admin.announce.save")}</Button>
    </Card>
  );
}
