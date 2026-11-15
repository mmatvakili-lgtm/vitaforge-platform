"use client";
import { useEffect, useMemo, useRef } from "react";
import { buildMesh, hexToRgb, pickRegion, renderMesh, shade, type Tri } from "../lib/body3d.ts";

export type RegionStatus = "low" | "ok" | "high" | "focus";
const FALLBACK: Record<string, string> = { base: "#6b625b", low: "#4f8fd6", ok: "#3fae7a", high: "#e0a23a", focus: "#ff5a1f" };

/** Interactive procedural 3D body: drag / arrow keys to rotate, tap a muscle to select it. Colours come from the active theme's --body-* tokens. */
export function Body3D({ status, label, onPick, selected, height = 360 }: {
  status: Readonly<Record<string, RegionStatus>>;
  label: string;
  onPick?: (region: string | null) => void;
  selected?: string | null;
  height?: number;
}) {
  const mesh = useMemo(() => buildMesh(), []);
  const canvas = useRef<HTMLCanvasElement>(null);
  const st = useRef({ yaw: 0.5, pitch: 0.08, drag: false, moved: 0, x: 0, y: 0, tris: [] as Tri[], auto: true });
  const props = useRef({ status, selected, onPick });
  props.current = { status, selected, onPick };

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;
    const reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0, alive = true, w = 0;
    const colors = () => {
      const cs = getComputedStyle(el);
      const g = (k: string) => hexToRgb(cs.getPropertyValue(`--body-${k}`) || FALLBACK[k]);
      return { base: g("base"), low: g("low"), ok: g("ok"), high: g("high"), focus: g("focus") };
    };
    const draw = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      w = el.clientWidth;
      if (el.width !== Math.round(w * dpr) || el.height !== Math.round(height * dpr)) { el.width = Math.round(w * dpr); el.height = Math.round(height * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, height);
      const c = colors();
      const s = st.current;
      s.tris = renderMesh(mesh, { yaw: s.yaw, pitch: s.pitch, width: w, height });
      const sel = props.current.selected;
      for (const t of s.tris) {
        const stt = props.current.status[t.region];
        const base = t.region === sel ? c.focus : stt ? c[stt] : c.base;
        ctx.fillStyle = shade(base, t.light);
        ctx.strokeStyle = ctx.fillStyle;
        ctx.lineWidth = 0.6;
        ctx.beginPath(); ctx.moveTo(t.x[0], t.y[0]); ctx.lineTo(t.x[1], t.y[1]); ctx.lineTo(t.x[2], t.y[2]); ctx.closePath();
        ctx.fill(); ctx.stroke();
      }
    };
    let last = 0;
    const loop = (now: number) => {
      if (!alive) return;
      if (!st.current.drag && st.current.auto && !reduce) st.current.yaw += (now - last) * 0.00035;
      last = now;
      draw();
      raf = requestAnimationFrame(loop);
    };
    if (reduce) draw(); else raf = requestAnimationFrame(loop);
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(() => { if (reduce) draw(); }) : null;
    ro?.observe(el);
    const redraw = () => { if (reduce) draw(); };
    (el as HTMLCanvasElement & { _redraw?: () => void })._redraw = redraw;
    return () => { alive = false; cancelAnimationFrame(raf); ro?.disconnect(); };
  }, [mesh, height]);

  const s = st.current;
  const poke = () => (canvas.current as (HTMLCanvasElement & { _redraw?: () => void }) | null)?._redraw?.();
  return (
    <canvas
      ref={canvas}
      className="body3d"
      style={{ inlineSize: "100%", blockSize: height, touchAction: "pan-y", cursor: "grab" }}
      role="img"
      aria-label={label}
      tabIndex={0}
      onPointerDown={(e) => { s.drag = true; s.auto = false; s.moved = 0; s.x = e.clientX; s.y = e.clientY; e.currentTarget.setPointerCapture(e.pointerId); }}
      onPointerMove={(e) => {
        if (!s.drag) return;
        const dx = e.clientX - s.x, dy = e.clientY - s.y;
        s.moved += Math.abs(dx) + Math.abs(dy); s.x = e.clientX; s.y = e.clientY;
        s.yaw += dx * 0.012; s.pitch = Math.max(-0.45, Math.min(0.45, s.pitch + dy * 0.004)); poke();
      }}
      onPointerUp={(e) => {
        s.drag = false;
        if (s.moved < 6) {
          const r = e.currentTarget.getBoundingClientRect();
          props.current.onPick?.(pickRegion(s.tris, e.clientX - r.left, e.clientY - r.top));
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") { s.yaw -= 0.2; s.auto = false; e.preventDefault(); poke(); }
        if (e.key === "ArrowRight") { s.yaw += 0.2; s.auto = false; e.preventDefault(); poke(); }
      }}
    />
  );
}
