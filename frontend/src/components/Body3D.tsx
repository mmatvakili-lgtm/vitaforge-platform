"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useT } from "../lib/react/context.tsx";
import { Body2D, type RegionStatus } from "./Body2D.tsx";

export type { RegionStatus };
export type MuscleInfo = { group?: string; label?: string; side?: string } | null;

type Viewer = {
  setPalette(p: Record<string, string>): void;
  setStatus(m: Record<string, string>): void;
  setSelected(g: string | null): void;
  setView(v: "front" | "back" | "left" | "right"): void;
  faceGroups(names: string[]): void;
  setAutoRotate(v: boolean): void;
  setBones(v: boolean): void;
  zoom(f: number): void;
  dispose(): void;
};
type Api = { create(canvas: HTMLCanvasElement, o: Record<string, unknown>): Viewer | null; preload(): Promise<unknown> };
declare global { interface Window { VFBody?: Api } }

let scriptPromise: Promise<Api> | null = null;
/** The viewer (three.js + anatomy model) is plain same-origin static files under /vendor, loaded on demand so it never touches the app bundle. */
function loadViewer(): Promise<Api> {
  if (typeof window === "undefined") return Promise.reject(new Error("ssr"));
  if (window.VFBody) return Promise.resolve(window.VFBody);
  scriptPromise ??= new Promise<Api>((resolve, reject) => {
    const done = () => (window.VFBody ? resolve(window.VFBody) : reject(new Error("viewer missing")));
    window.addEventListener("vfbody:ready", done, { once: true });
    const s = document.createElement("script");
    s.type = "module"; s.src = "/vendor/body-viewer.js"; s.onerror = () => reject(new Error("viewer script"));
    document.head.appendChild(s);
  });
  return scriptPromise;
}

function readPalette(el: HTMLElement): Record<string, string> {
  const cs = getComputedStyle(el);
  const g = (k: string, d: string) => (cs.getPropertyValue(k).trim() || d);
  return {
    base: g("--muscle", "#8f3d33"), low: g("--body-low", "#4f8fd6"), ok: g("--body-ok", "#3fae7a"), high: g("--body-high", "#e0a23a"),
    focus: g("--body-focus", "#ff5a1f"), glow: g("--body-focus", "#ff5a1f"), dim: g("--body-dim", "#3a2623"), head: g("--body-head", "#2f2724"), bone: g("--body-bone", "#e7dfcf"),
  };
}

/** Anatomical 3D body (real muscle model, 17 selectable groups). Drag to turn, tap a muscle to select, buttons for front/back/skeleton.
 *  Falls back to the procedural canvas body when WebGL or the model is unavailable. */
export function Body3D({ status, label, onPick, selected, height = 360, controls = true, faceFocus = true }: {
  status: Readonly<Record<string, RegionStatus>>;
  label: string;
  onPick?: (region: string | null) => void;
  selected?: string | null;
  height?: number;
  controls?: boolean;
  faceFocus?: boolean;
}) {
  const { t } = useT();
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const cb = useRef({ onPick });
  cb.current = { onPick };
  const [phase, setPhase] = useState<"loading" | "ready" | "fallback">("loading");
  const [info, setInfo] = useState<MuscleInfo>(null);
  const [spin, setSpin] = useState(true);
  const [bones, setBones] = useState(false);

  useEffect(() => {
    let dead = false;
    let v: Viewer | null = null;
    loadViewer().then((api) => {
      if (dead || !canvas.current) return;
      v = api.create(canvas.current, {
        onReady: () => { if (!dead) setPhase("ready"); },
        onError: () => { if (!dead) setPhase("fallback"); },
        onPick: (p: MuscleInfo) => { setInfo(p); cb.current.onPick?.(p?.group ?? null); },
        onHover: (p: MuscleInfo) => setInfo(p),
      });
      if (!v) { setPhase("fallback"); return; }
      viewer.current = v;
      v.setPalette(readPalette(wrap.current ?? document.documentElement));
    }).catch(() => { if (!dead) setPhase("fallback"); });
    return () => { dead = true; viewer.current = null; v?.dispose(); };
  }, []);

  const key = JSON.stringify(status);
  useEffect(() => {
    const v = viewer.current;
    if (!v || phase !== "ready") return;
    v.setStatus(status);
    const foc = Object.keys(status).filter((k) => status[k] === "focus");
    if (faceFocus && foc.length > 0) v.faceGroups(foc);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, phase, faceFocus]);
  useEffect(() => { if (phase === "ready") viewer.current?.setSelected(selected ?? null); }, [selected, phase]);

  const toggleSpin = useCallback(() => setSpin((s) => { viewer.current?.setAutoRotate(!s); return !s; }), []);
  const toggleBones = useCallback(() => setBones((b) => { viewer.current?.setBones(!b); return !b; }), []);

  if (phase === "fallback") return <Body2D status={status} label={label} onPick={onPick} selected={selected} height={height} />;
  return (
    <div ref={wrap} className="body3d-wrap" style={{ blockSize: height }}>
      <canvas ref={canvas} className="body3d-gl" role="img" aria-label={label} tabIndex={0} />
      {phase === "loading" && <div className="body3d-skel" aria-live="polite"><i /><span>{t("body3d.loading")}</span></div>}
      {phase === "ready" && controls && (
        <div className="body3d-ctl" role="group" aria-label={t("body3d.controls")}>
          <button type="button" onClick={() => { viewer.current?.setView("front"); setSpin(false); }}>{t("body3d.front")}</button>
          <button type="button" onClick={() => { viewer.current?.setView("back"); setSpin(false); }}>{t("body3d.back")}</button>
          <button type="button" aria-pressed={spin} onClick={toggleSpin}>{t("body3d.spin")}</button>
          <button type="button" aria-pressed={bones} onClick={toggleBones}>{t("body3d.bones")}</button>
        </div>
      )}
      {phase === "ready" && info?.group && (
        <div className="body3d-info" aria-live="polite"><strong>{t(`muscle.${info.group}`)}</strong><span dir="ltr">{info.label}{info.side ? ` · ${info.side === "l" ? "L" : "R"}` : ""}</span></div>
      )}
    </div>
  );
}
