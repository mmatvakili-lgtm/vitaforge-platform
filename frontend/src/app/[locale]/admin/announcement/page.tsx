"use client";
import { useEffect, useState } from "react";
import { adminCall, announcementText } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";

type Ann = { enabled: boolean; text_fa: string; text_en: string; level: "info" | "warning"; expires_at: number | null };

export default function AnnouncementAdmin() {
  const { locale, t } = useT();
  const [a, setA] = useState<Ann | null>(null);
  const [days, setDays] = useState("");
  const [failed, setFailed] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  useEffect(() => { adminCall<Ann>("GET", "/admin/announcement").then((r) => (r.ok ? setA(r.data) : setFailed(true))); }, []);
  async function save() {
    if (!a) return;
    const d = Number(days);
    const expires_at = days.trim() && d > 0 ? Math.floor(Date.now() / 1000 + d * 86400) : null;
    const r = await adminCall<Ann>("PUT", "/admin/announcement", { enabled: a.enabled, text_fa: a.text_fa, text_en: a.text_en, level: a.level, expires_at });
    if (r.ok) { setA(r.data); setMsg({ kind: "success", text: t("admin.saved") }); } else setMsg({ kind: "error", text: t("admin.media.invalid") });
  }
  if (failed) return <p className="alert alert-error" role="alert">{t("admin.error")}</p>;
  if (!a) return <div className="adm-skel" aria-busy="true"><span /><span /></div>;
  const preview = announcementText(a, locale);
  return (
    <div className="adm-split">
      <section className="adm-panel">
        <p className="adm-lead">{t("admin.announce.intro")}</p>
        <label className="adm-switch big"><input type="checkbox" role="switch" checked={a.enabled} onChange={(e) => setA({ ...a, enabled: e.target.checked })} /><span>{t("admin.announce.enabled")}</span></label>
        <div className="adm-field"><label htmlFor="an-fa">{t("admin.announce.fa")}</label>
          <textarea id="an-fa" rows={3} maxLength={300} value={a.text_fa} onChange={(e) => setA({ ...a, text_fa: e.target.value })} /><small className="num">{a.text_fa.length}/300</small></div>
        <div className="adm-field"><label htmlFor="an-en">{t("admin.announce.en")}</label>
          <textarea id="an-en" dir="ltr" rows={3} maxLength={300} value={a.text_en} onChange={(e) => setA({ ...a, text_en: e.target.value })} /><small className="num">{a.text_en.length}/300</small></div>
        <div className="adm-field"><span id="an-lv">{t("admin.announce.level")}</span>
          <div className="adm-chips" role="group" aria-labelledby="an-lv">
            {(["info", "warning"] as const).map((l) => <button key={l} type="button" aria-pressed={a.level === l} onClick={() => setA({ ...a, level: l })}>{t(`admin.announce.${l}`)}</button>)}
          </div></div>
        <div className="adm-field"><label htmlFor="an-d">{t("admin.announce.days")}</label>
          <input id="an-d" type="number" min={1} max={365} dir="ltr" value={days} onChange={(e) => setDays(e.target.value)} /></div>
        <button type="button" className="adm-primary" onClick={save}>{t("admin.announce.save")}</button>
        {msg && <p className={`adm-msg ${msg.kind}`} role="status">{msg.text}</p>}
      </section>
      <section className="adm-panel adm-preview" aria-label={t("admin.announce.preview")}>
        <header><h2>{t("admin.announce.preview")}</h2><span className="adm-pill">{a.enabled ? t("admin.dash.on") : t("admin.dash.off")}</span></header>
        <div className="adm-preview-site">
          {preview && a.enabled ? <div className={`notice announcement${a.level === "warning" ? " warn" : ""}`}><p>{preview}</p></div> : <p className="adm-empty">{t("admin.announce.previewEmpty")}</p>}
          <div className="adm-preview-page" aria-hidden="true"><i /><i /><i /></div>
        </div>
      </section>
    </div>
  );
}
