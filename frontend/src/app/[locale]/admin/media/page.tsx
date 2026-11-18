"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import codes from "../../../../lib/motion.codes.json";
import { adminCall, fileToBase64, loadOverrides, parseYouTubeId, shrinkImage, type MediaOverride, type View } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { ExerciseAnim } from "../../../../components/ExerciseAnim.tsx";
import { Alert, Button, Card, Loading } from "../../../../components/ui.tsx";

type Filter = "all" | "changed" | "no3d";
const ALL = (codes as [string, string][]).map(([c]) => c);
const KINDS: [keyof Pick<MediaOverride, "photo" | "video" | "anim3d">, string][] = [["photo", "admin.media.photo"], ["video", "admin.media.video"], ["anim3d", "admin.media.3d"]];

export default function MediaAdmin() {
  const { t } = useT();
  const [ov, setOv] = useState<Record<string, MediaOverride> | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [ver, setVer] = useState(0);
  const [video, setVideo] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const me = await adminCall<{ role: string }>("GET", "/admin/me");
    if (!me.ok || (me.data.role !== "admin" && me.data.role !== "super_admin")) { setForbidden(true); setOv({}); return; }
    setOv(await loadOverrides(true)); setVer((v) => v + 1);
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setVideo(open && ov?.[open]?.video_id ? `https://youtu.be/${ov[open].video_id}` : ""); setNote(open ? ov?.[open]?.note ?? "" : ""); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = useMemo(() => ALL.filter((c) => c.includes(q.trim().toLowerCase().replace(/\s+/g, "_"))
    && (filter === "all" || (filter === "changed" ? !!ov?.[c] : ov?.[c]?.anim3d === false))), [q, filter, ov]);

  async function save(code: string, patch: Record<string, unknown>) {
    setBusy(true); setMsg(null);
    const r = await adminCall("PUT", `/admin/media/${code}`, patch);
    setBusy(false);
    if (!r.ok) { setMsg({ kind: "error", text: r.status === 403 ? t("admin.forbidden") : t("admin.media.invalid") }); return false; }
    setMsg({ kind: "success", text: t("admin.saved") }); await load(); return true;
  }
  async function reset(code: string) {
    setBusy(true); const r = await adminCall("DELETE", `/admin/media/${code}`); setBusy(false);
    setMsg(r.ok || r.status === 404 ? { kind: "success", text: t("admin.media.resetDone") } : { kind: "error", text: t("admin.error") }); await load();
  }
  async function bulk(set: Record<string, unknown>) {
    setBusy(true); setMsg(null);
    const r = await adminCall("POST", "/admin/media-bulk", { codes: [...sel], set });
    setBusy(false);
    setMsg(r.ok ? { kind: "success", text: t("admin.saved") } : { kind: "error", text: t("admin.error") }); if (r.ok) { setSel(new Set()); await load(); }
  }
  async function saveVideo(code: string) {
    if (!video.trim()) { await save(code, { video_id: null, video_title: null }); return; }
    const id = parseYouTubeId(video);
    if (!id) { setMsg({ kind: "error", text: t("admin.media.videoBad") }); return; }
    await save(code, { video_id: id, video_title: note.trim() ? undefined : "YouTube" });
  }
  async function upload(code: string, f: File | undefined) {
    if (!f) return;
    setBusy(true); setMsg(null);
    try {
      const blob = await shrinkImage(f);
      const up = await adminCall<{ id: string }>("POST", "/admin/media-files", { data_base64: await fileToBase64(blob), name: f.name });
      if (!up.ok) { setMsg({ kind: "error", text: t("admin.media.uploadFail") }); setBusy(false); return; }
      setBusy(false); await save(code, { photo_file: up.data.id, photo: true });
    } catch { setBusy(false); setMsg({ kind: "error", text: t("admin.media.uploadFail") }); }
  }

  if (ov === null) return <Card title={t("admin.media.title")}><Loading /></Card>;
  if (forbidden) return <Card title={t("admin.media.title")}><Alert kind="warning">{t("admin.forbidden")}</Alert></Card>;
  const toggle = (k: string) => setSel((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  return (
    <Card title={t("admin.media.title")}>
      <p>{t("admin.media.intro")}</p>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <div className="row">
        <input type="search" dir="ltr" placeholder={t("admin.media.search")} aria-label={t("admin.media.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label={t("admin.media.filter")} value={filter} onChange={(e) => setFilter(e.target.value as Filter)}>
          <option value="all">{t("admin.media.filter.all")}</option><option value="changed">{t("admin.media.filter.changed")}</option><option value="no3d">{t("admin.media.filter.no3d")}</option>
        </select>
        <Button type="button" onClick={() => setSel(new Set(rows))}>{t("admin.media.selectShown", { n: rows.length })}</Button>
      </div>
      {sel.size > 0 && (
        <Alert kind="info">
          <p>{t("admin.media.selected", { n: sel.size })}</p>
          <div className="row">
            <Button type="button" busy={busy} onClick={() => bulk({ anim3d: false })}>{t("admin.media.bulk.hide3d")}</Button>
            <Button type="button" busy={busy} onClick={() => bulk({ anim3d: true })}>{t("admin.media.bulk.show3d")}</Button>
            <Button type="button" busy={busy} onClick={() => bulk({ photo: false })}>{t("admin.media.bulk.hidePhoto")}</Button>
            <Button type="button" busy={busy} onClick={() => bulk({ video: false })}>{t("admin.media.bulk.hideVideo")}</Button>
            <Button type="button" busy={busy} onClick={() => bulk({ photo: null, video: null, anim3d: null, default: null })}>{t("admin.media.bulk.auto")}</Button>
            <Button type="button" onClick={() => setSel(new Set())}>{t("admin.media.clear")}</Button>
          </div>
        </Alert>)}
      <p className="muted">{t("admin.media.count", { n: rows.length })}</p>
      <ul className="plain">
        {rows.map((c) => {
          const o = ov[c] ?? {};
          return (
            <li key={c} className="card-lite">
              <label className="check"><input type="checkbox" checked={sel.has(c)} onChange={() => toggle(c)} aria-label={c} /><bdi dir="ltr"><strong>{c}</strong></bdi></label>
              {ov[c] && <span className="tag">{t("admin.media.changed")}</span>} {o.reviewed && <span className="tag">{t("admin.media.reviewed")}</span>}
              <div className="row">
                {KINDS.map(([k, label]) => (
                  <label key={k} className="check"><input type="checkbox" disabled={busy} checked={o[k] !== false} onChange={(e) => save(c, { [k]: e.target.checked ? null : false })} />{t(label)}</label>))}
                <select aria-label={t("admin.media.default")} value={o.default ?? ""} disabled={busy} onChange={(e) => save(c, { default: e.target.value || null })}>
                  <option value="">{t("admin.media.auto")}</option>
                  {(["photo", "video", "3d"] as View[]).map((v) => <option key={v} value={v}>{t(v === "3d" ? "admin.media.3d" : `admin.media.${v}`)}</option>)}
                </select>
                <Button type="button" onClick={() => setOpen(open === c ? null : c)}>{open === c ? t("admin.media.close") : t("admin.media.edit")}</Button>
              </div>
              {open === c && (
                <div>
                  <ExerciseAnim key={`${c}-${ver}`} code={c} height={220} />
                  <label htmlFor={`v-${c}`}>{t("admin.media.videoLink")}</label>
                  <input id={`v-${c}`} dir="ltr" value={video} placeholder="https://youtu.be/…" onChange={(e) => setVideo(e.target.value)} />
                  <Button type="button" busy={busy} onClick={() => saveVideo(c)}>{t("admin.media.saveVideo")}</Button>
                  <label htmlFor={`u-${c}`}>{t("admin.media.upload")}</label>
                  <input id={`u-${c}`} type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={(e) => { upload(c, e.target.files?.[0]); e.currentTarget.value = ""; }} />
                  <p className="hint">{t("admin.media.uploadHint")}</p>
                  {o.photo_file && <Button type="button" busy={busy} onClick={() => save(c, { photo_file: null })}>{t("admin.media.removeUpload")}</Button>}
                  <label htmlFor={`n-${c}`}>{t("admin.media.note")}</label>
                  <input id={`n-${c}`} value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} />
                  <div className="row">
                    <Button type="button" busy={busy} onClick={() => save(c, { note: note.trim() || null })}>{t("admin.media.saveNote")}</Button>
                    <Button type="button" busy={busy} onClick={() => save(c, { reviewed: !o.reviewed })}>{o.reviewed ? t("admin.media.unreview") : t("admin.media.markReviewed")}</Button>
                    {ov[c] && <Button type="button" busy={busy} onClick={() => reset(c)}>{t("admin.media.reset")}</Button>}
                  </div>
                </div>)}
            </li>);
        })}
      </ul>
    </Card>
  );
}
