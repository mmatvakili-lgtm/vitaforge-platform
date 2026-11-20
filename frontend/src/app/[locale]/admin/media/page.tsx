"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import codes from "../../../../lib/motion.codes.json";
import { adminCall, fileToBase64, fileUrl, loadOverrides, parseYouTubeId, shrinkImage, type MediaOverride, type View } from "../../../../lib/admin.ts";
import { useT } from "../../../../lib/react/context.tsx";
import { ExerciseAnim } from "../../../../components/ExerciseAnim.tsx";

type Filter = "all" | "changed" | "no3d" | "nophoto" | "unreviewed";
type Kind = "photo" | "video" | "anim3d";
const ALL = (codes as [string, string][]).map(([c]) => c);
const KINDS: [Kind, string][] = [["photo", "admin.media.photo"], ["video", "admin.media.video"], ["anim3d", "admin.media.3d"]];
const PAGE = 48;
const FILTERS: Filter[] = ["all", "changed", "no3d", "nophoto", "unreviewed"];

function Thumb({ code, o }: { code: string; o: MediaOverride | undefined }) {
  const [bad, setBad] = useState(false);
  const src = o?.photo_file ? fileUrl(o.photo_file) : `/exercise-media/${code}/0.webp`;
  return bad || o?.photo === false
    ? <span className="adm-thumb-none" aria-hidden="true" />
    : <img src={src} alt="" loading="lazy" decoding="async" onError={() => setBad(true)} />;
}

export default function MediaAdmin() {
  const { t, n } = useT();
  const [ov, setOv] = useState<Record<string, MediaOverride> | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [shown, setShown] = useState(PAGE);
  const [open, setOpen] = useState<string | null>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [ver, setVer] = useState(0);
  const [video, setVideo] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => { setOv(await loadOverrides(true)); setVer((v) => v + 1); }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setVideo(open && ov?.[open]?.video_id ? `https://youtu.be/${ov[open].video_id}` : ""); setNote(open ? ov?.[open]?.note ?? "" : ""); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setShown(PAGE); }, [q, filter]);
  useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(null), 4000); return () => clearTimeout(id); }, [toast]);
  useEffect(() => { if (!open) return; const h = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); }; window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, [open]);

  const rows = useMemo(() => {
    const s = q.trim().toLowerCase().replace(/\s+/g, "_");
    return ALL.filter((c) => c.includes(s) && (
      filter === "all" ? true : filter === "changed" ? !!ov?.[c] : filter === "no3d" ? ov?.[c]?.anim3d === false
        : filter === "nophoto" ? ov?.[c]?.photo === false : !ov?.[c]?.reviewed));
  }, [q, filter, ov]);

  async function save(code: string, patch: Record<string, unknown>) {
    setBusy(true);
    const r = await adminCall("PUT", `/admin/media/${code}`, patch);
    setBusy(false);
    if (!r.ok) { setToast({ kind: "error", text: r.status === 403 ? t("admin.forbidden") : t("admin.media.invalid") }); return false; }
    setToast({ kind: "success", text: t("admin.saved") }); await load(); return true;
  }
  async function reset(code: string) {
    setBusy(true); const r = await adminCall("DELETE", `/admin/media/${code}`); setBusy(false);
    setToast(r.ok || r.status === 404 ? { kind: "success", text: t("admin.media.resetDone") } : { kind: "error", text: t("admin.error") }); await load();
  }
  async function bulk(set: Record<string, unknown>) {
    setBusy(true);
    const r = await adminCall("POST", "/admin/media-bulk", { codes: [...sel], set });
    setBusy(false);
    setToast(r.ok ? { kind: "success", text: t("admin.saved") } : { kind: "error", text: t("admin.error") }); if (r.ok) { setSel(new Set()); await load(); }
  }
  async function saveVideo(code: string) {
    if (!video.trim()) { await save(code, { video_id: null, video_title: null }); return; }
    const id = parseYouTubeId(video);
    if (!id) { setToast({ kind: "error", text: t("admin.media.videoBad") }); return; }
    await save(code, { video_id: id, video_title: "YouTube" });
  }
  async function upload(code: string, f: File | undefined) {
    if (!f) return;
    setBusy(true);
    try {
      const blob = await shrinkImage(f);
      const up = await adminCall<{ id: string }>("POST", "/admin/media-files", { data_base64: await fileToBase64(blob), name: f.name });
      if (!up.ok) { setToast({ kind: "error", text: t("admin.media.uploadFail") }); setBusy(false); return; }
      setBusy(false); await save(code, { photo_file: up.data.id, photo: true });
    } catch { setBusy(false); setToast({ kind: "error", text: t("admin.media.uploadFail") }); }
  }

  if (ov === null) return <div className="adm-skel" aria-busy="true"><span /><span /><span /></div>;
  const toggle = (k: string) => setSel((s) => { const x = new Set(s); x.has(k) ? x.delete(k) : x.add(k); return x; });
  const o = open ? ov[open] ?? {} : null;
  return (
    <>
      <p className="adm-lead">{t("admin.media.intro")}</p>
      <div className="adm-toolbar">
        <input type="search" dir="ltr" placeholder={t("admin.media.search")} aria-label={t("admin.media.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="adm-chips" role="group" aria-label={t("admin.media.filter")}>
          {FILTERS.map((f) => <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>{t(`admin.media.filter.${f}`)}</button>)}
        </div>
        <button type="button" className="adm-ghost" onClick={() => setSel(new Set(rows))}>{t("admin.media.selectShown", { n: rows.length })}</button>
      </div>
      <p className="adm-foot">{t("admin.media.count", { n: rows.length })}</p>

      {rows.length === 0 ? <p className="adm-empty">{t("admin.media.empty")}</p> : (
        <ul className="adm-grid-tiles">
          {rows.slice(0, shown).map((c) => {
            const x = ov[c] ?? {};
            return (
              <li key={c} className={sel.has(c) ? "adm-tile sel" : "adm-tile"} data-open={open === c || undefined}>
                <label className="adm-tile-check"><input type="checkbox" checked={sel.has(c)} onChange={() => toggle(c)} aria-label={c} /></label>
                <button type="button" className="adm-tile-main" onClick={() => setOpen(c)} aria-label={`${t("admin.media.edit")}: ${c}`}>
                  <span className="adm-thumb"><Thumb code={c} o={x} /></span>
                  <bdi dir="ltr" className="adm-tile-name">{c.replace(/_/g, " ")}</bdi>
                  <span className="adm-badges">
                    {x.photo === false && <em>{t("admin.media.photo")} ✕</em>}
                    {x.video === false && <em>{t("admin.media.video")} ✕</em>}
                    {x.anim3d === false && <em>{t("admin.media.3d")} ✕</em>}
                    {x.photo_file && <em className="ok">{t("admin.media.uploaded")}</em>}
                    {x.reviewed && <em className="ok">{t("admin.media.reviewed")}</em>}
                  </span>
                </button>
              </li>);
          })}
        </ul>)}
      {rows.length > shown && <button type="button" className="adm-more" onClick={() => setShown((s) => s + PAGE)}>{t("admin.media.more", { n: rows.length - shown })}</button>}

      {sel.size > 0 && (
        <div className="adm-bulk" role="region" aria-label={t("admin.media.bulk")}>
          <b>{t("admin.media.selected", { n: sel.size })}</b>
          <button type="button" disabled={busy} onClick={() => bulk({ anim3d: false })}>{t("admin.media.bulk.hide3d")}</button>
          <button type="button" disabled={busy} onClick={() => bulk({ anim3d: true })}>{t("admin.media.bulk.show3d")}</button>
          <button type="button" disabled={busy} onClick={() => bulk({ photo: false })}>{t("admin.media.bulk.hidePhoto")}</button>
          <button type="button" disabled={busy} onClick={() => bulk({ video: false })}>{t("admin.media.bulk.hideVideo")}</button>
          <button type="button" disabled={busy} onClick={() => bulk({ photo: null, video: null, anim3d: null, default: null })}>{t("admin.media.bulk.auto")}</button>
          <button type="button" className="adm-ghost" onClick={() => setSel(new Set())}>{t("admin.media.clear")}</button>
        </div>)}

      {open && o && (
        <>
          <div className="adm-scrim" onClick={() => setOpen(null)} />
          <aside className="adm-drawer" role="dialog" aria-modal="true" aria-label={open}>
            <header><bdi dir="ltr"><h2>{open.replace(/_/g, " ")}</h2></bdi><button type="button" className="adm-x" aria-label={t("admin.media.close")} onClick={() => setOpen(null)}>✕</button></header>
            <div className="adm-drawer-body">
              <ExerciseAnim key={`${open}-${ver}`} code={open} height={240} />
              <h3>{t("admin.media.show")}</h3>
              <div className="adm-switches">
                {KINDS.map(([k, label]) => (
                  <label key={k} className="adm-switch"><input type="checkbox" role="switch" disabled={busy} checked={o[k] !== false} onChange={(e) => save(open, { [k]: e.target.checked ? null : false })} /><span>{t(label)}</span></label>))}
              </div>
              <h3>{t("admin.media.default")}</h3>
              <div className="adm-chips" role="group" aria-label={t("admin.media.default")}>
                {([["", "admin.media.auto"], ["photo", "admin.media.photo"], ["video", "admin.media.video"], ["3d", "admin.media.3d"]] as [View | "", string][]).map(([v, l]) => (
                  <button key={v} type="button" disabled={busy} aria-pressed={(o.default ?? "") === v} onClick={() => save(open, { default: v || null })}>{t(l)}</button>))}
              </div>
              <h3>{t("admin.media.videoLink")}</h3>
              <div className="adm-inline"><input dir="ltr" value={video} placeholder="https://youtu.be/…" aria-label={t("admin.media.videoLink")} onChange={(e) => setVideo(e.target.value)} /><button type="button" disabled={busy} onClick={() => saveVideo(open)}>{t("admin.media.saveVideo")}</button></div>
              <h3>{t("admin.media.upload")}</h3>
              <input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} aria-label={t("admin.media.upload")} onChange={(e) => { upload(open, e.target.files?.[0]); e.currentTarget.value = ""; }} />
              <p className="adm-foot">{t("admin.media.uploadHint")}</p>
              {o.photo_file && <button type="button" className="adm-ghost" disabled={busy} onClick={() => save(open, { photo_file: null })}>{t("admin.media.removeUpload")}</button>}
              <h3>{t("admin.media.note")}</h3>
              <div className="adm-inline"><input value={note} maxLength={200} aria-label={t("admin.media.note")} onChange={(e) => setNote(e.target.value)} /><button type="button" disabled={busy} onClick={() => save(open, { note: note.trim() || null })}>{t("admin.media.saveNote")}</button></div>
            </div>
            <footer>
              <button type="button" disabled={busy} onClick={() => save(open, { reviewed: !o.reviewed })}>{o.reviewed ? t("admin.media.unreview") : t("admin.media.markReviewed")}</button>
              {ov[open] && <button type="button" className="adm-ghost" disabled={busy} onClick={() => reset(open)}>{t("admin.media.reset")}</button>}
            </footer>
          </aside>
        </>)}
      {toast && <div className={`adm-toast ${toast.kind}`} role={toast.kind === "error" ? "alert" : "status"}>{toast.text}</div>}
    </>
  );
}
