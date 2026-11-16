"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { L, bounds, motionFor, poseAt, solve, variantFor, type Pose, type Prop, type Skeleton, type V } from "../lib/motion.ts";
import { muscleRegion } from "../lib/body3d.ts";
import { useApi, useT } from "../lib/react/context.tsx";

const P = (v: V) => `${v[0].toFixed(1)},${(-v[1]).toFixed(1)}`;
const mix = (a: V, b: V, t: number): V => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];

/** Where each muscle region is painted on the skeleton: [from joint, to joint, t0, t1, width]. */
function zones(s: Skeleton, region: string): Array<[V, V, number, number, number]> {
  switch (region) {
    case "quadriceps": case "hamstrings": case "adductors": return [[s.hip, s.kneeA, 0.12, 0.92, 15], [s.hip, s.kneeB, 0.12, 0.92, 13]];
    case "glutes": return [[s.hip, mix(s.hip, s.kneeA, 0.2), 0, 1, 24]];
    case "calves": return [[s.kneeA, s.ankleA, 0.1, 0.8, 11], [s.kneeB, s.ankleB, 0.1, 0.8, 10]];
    case "chest": return [[mix(s.hip, s.shoulder, 0.62), mix(s.hip, s.shoulder, 0.95), 0, 1, 24]];
    case "lats": case "middle back": case "traps": return [[mix(s.hip, s.shoulder, 0.45), mix(s.hip, s.shoulder, 0.98), 0, 1, 20]];
    case "lower back": return [[mix(s.hip, s.shoulder, 0.02), mix(s.hip, s.shoulder, 0.4), 0, 1, 20]];
    case "abdominals": return [[mix(s.hip, s.shoulder, 0.08), mix(s.hip, s.shoulder, 0.6), 0, 1, 22]];
    case "shoulders": return [[mix(s.shoulder, s.elbowA, 0, ), mix(s.shoulder, s.elbowA, 0.35), 0, 1, 18]];
    case "biceps": case "triceps": return [[s.shoulder, s.elbowA, 0.2, 0.9, 12], [s.shoulder, s.elbowB, 0.2, 0.9, 11]];
    case "forearms": return [[s.elbowA, s.handA, 0.1, 0.9, 10], [s.elbowB, s.handB, 0.1, 0.9, 9]];
    default: return [];
  }
}

function Seg({ a, b, w, cls }: { a: V; b: V; w: number; cls: string }) {
  return <line className={cls} x1={a[0]} y1={-a[1]} x2={b[0]} y2={-b[1]} strokeWidth={w} strokeLinecap="round" />;
}

function Figure({ s, regions, ghost }: { s: Skeleton; regions: readonly string[]; ghost?: boolean }) {
  const far = ghost ? "an-far an-ghost" : "an-far", near = ghost ? "an-near an-ghost" : "an-near";
  return (
    <g>
      <Seg a={s.hip} b={s.kneeB} w={15} cls={far} /><Seg a={s.kneeB} b={s.ankleB} w={11} cls={far} /><Seg a={s.ankleB} b={s.toeB} w={7} cls={far} />
      <Seg a={s.shoulder} b={s.elbowB} w={11} cls={far} /><Seg a={s.elbowB} b={s.handB} w={9} cls={far} />
      <Seg a={s.hip} b={s.shoulder} w={30} cls={near} />
      <Seg a={s.hip} b={s.kneeA} w={17} cls={near} /><Seg a={s.kneeA} b={s.ankleA} w={12} cls={near} /><Seg a={s.ankleA} b={s.toeA} w={8} cls={near} />
      {!ghost && regions.flatMap((r) => zones(s, r).map(([a, b, t0, t1, w], i) => <Seg key={`${r}${i}`} a={mix(a, b, t0)} b={mix(a, b, t1)} w={w} cls="an-muscle" />))}
      <Seg a={s.shoulder} b={s.elbowA} w={12} cls={near} /><Seg a={s.elbowA} b={s.handA} w={10} cls={near} />
      <Seg a={s.shoulder} b={s.neck} w={11} cls={near} />
      <circle className={ghost ? "an-head an-ghost" : "an-head"} cx={s.head[0]} cy={-s.head[1]} r={L.head} />
      {!ghost && <circle className="an-joint" cx={s.handA[0]} cy={-s.handA[1]} r={4.5} />}
    </g>
  );
}

function Props({ props, s, barY, minX, maxX }: { props: readonly Prop[]; s: Skeleton; barY: number; minX: number; maxX: number }) {
  const h = s.handA;
  return (
    <g>
      {props.map((p) => {
        switch (p) {
          case "dumbbell": return <g key={p} className="an-weight"><Seg a={[h[0] - 8, h[1]]} b={[h[0] + 8, h[1]]} w={4} cls="an-metal" /><rect x={h[0] - 13} y={-h[1] - 8} width={6} height={16} rx={2} /><rect x={h[0] + 7} y={-h[1] - 8} width={6} height={16} rx={2} /></g>;
          case "kettlebell": return <g key={p} className="an-weight"><circle cx={h[0]} cy={-h[1] + 9} r={10} /><path d={`M${h[0] - 6},${-h[1] + 2} a6,7 0 0 1 12,0`} fill="none" className="an-metal" strokeWidth={3} /></g>;
          case "barbell-hands": return <g key={p} className="an-weight"><Seg a={[h[0] - 4, h[1]]} b={[h[0] + 4, h[1]]} w={4} cls="an-metal" /><circle cx={h[0]} cy={-h[1]} r={16} /><circle cx={h[0]} cy={-h[1]} r={5} className="an-metal-fill" /></g>;
          case "barbell-back": return <g key={p} className="an-weight"><circle cx={s.shoulder[0] - 6} cy={-s.shoulder[1] - 4} r={15} /><circle cx={s.shoulder[0] - 6} cy={-s.shoulder[1] - 4} r={5} className="an-metal-fill" /></g>;
          case "barbell-front": return <g key={p} className="an-weight"><circle cx={s.shoulder[0] + 8} cy={-s.shoulder[1] + 4} r={15} /><circle cx={s.shoulder[0] + 8} cy={-s.shoulder[1] + 4} r={5} className="an-metal-fill" /></g>;
          case "barbell-hip": return <g key={p} className="an-weight"><circle cx={s.hip[0]} cy={-s.hip[1] - 10} r={14} /><circle cx={s.hip[0]} cy={-s.hip[1] - 10} r={4} className="an-metal-fill" /></g>;
          case "bench-back": return <rect key={p} className="an-furn" x={s.shoulder[0] - 34} y={-(s.shoulder[1] - 12)} width={Math.max(60, s.hip[0] - s.shoulder[0] + 46)} height={14} rx={5} />;
          case "bench-seat": return <rect key={p} className="an-furn" x={s.handA[0] - 60} y={-s.handA[1] + 4} width={84} height={12} rx={4} />;
          case "box-foot": return <rect key={p} className="an-furn" x={s.ankleA[0] - 14} y={-s.ankleA[1] + 2} width={60} height={Math.max(8, s.ankleA[1] - 2)} rx={3} />;
          case "box-feet": return <rect key={p} className="an-furn" x={s.ankleA[0] - 6} y={-30} width={70} height={30} rx={3} />;
          case "bar-hang": return <g key={p}><Seg a={[h[0] - 60, barY]} b={[h[0] + 60, barY]} w={5} cls="an-metal" /></g>;
          case "band-hands": return <Seg key={p} a={[minX - 4, h[1]]} b={h} w={2.5} cls="an-band" />;
          case "cable-hands": return <g key={p}><Seg a={[maxX + 10, Math.max(h[1], 20)]} b={h} w={2} cls="an-band" /><circle cx={maxX + 10} cy={-Math.max(h[1], 20)} r={5} className="an-metal-fill" /></g>;
          case "wall": return <rect key={p} className="an-furn" x={s.hip[0] - 62} y={-150} width={10} height={150} rx={3} />;
        }
        return null;
      })}
    </g>
  );
}

function ExerciseAnim2D({ code, pattern, muscles, height = 260 }: { code: string; pattern?: string; muscles?: readonly string[]; height?: number }) {
  const { t } = useT();
  const { template, exact } = useMemo(() => motionFor(code, pattern), [code, pattern]);
  const regions = useMemo(() => {
    const given = (muscles ?? []).map((m) => muscleRegion(m) ?? m).filter((m, i, a) => !!m && a.indexOf(m) === i);
    return given.length ? given : template.targets;
  }, [muscles, template]);
  const reduced = typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [playing, setPlaying] = useState(!reduced);
  const [u, setU] = useState(reduced ? 0.5 : 0);
  const raf = useRef(0);
  useEffect(() => {
    if (!playing) return;
    let t0: number | null = null, last = 0;
    const base = u * template.period * 1000;
    const tick = (now: number) => {
      if (t0 === null) t0 = now;
      if (now - last > 30) { last = now; setU((((now - t0 + base) / 1000) / template.period) % 1); }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, template]);

  const box = useMemo(() => {
    const b = bounds(template.frames);
    const hanging = template.props.includes("bar-hang");
    const minY = Math.min(b.minY - 14, hanging ? -999 : 0 - 12), maxY = b.maxY + 26;
    let minX = b.minX - 40, maxX = b.maxX + 60;
    const w = maxX - minX, hh = maxY - minY, want = Math.max(w, hh * 1.35);
    minX -= (want - w) / 2; maxX += (want - w) / 2;
    return { minX, maxX, minY, maxY, w: maxX - minX, h: maxY - minY, hanging, bx: b.minX, bX: b.maxX };
  }, [template]);
  const pose: Pose = poseAt(template, u, variantFor(code));
  const s = solve(pose);
  const ghosts = template.loop === "pingpong" ? [template.frames[0], template.frames[template.frames.length - 1]].map(solve) : [];
  const pinned = template.frames.find((f) => f.handA);
  const barY = pinned?.handA ? pinned.handA[1] : 188;
  const reps = template.hold ? t("motion.hold") : "";
  return (
    <figure className="an" aria-label={t("motion.aria")}>
      <svg viewBox={`${box.minX.toFixed(0)} ${(-box.maxY).toFixed(0)} ${box.w.toFixed(0)} ${box.h.toFixed(0)}`} role="img" aria-label={t("motion.aria")} style={{ blockSize: height, inlineSize: "100%" }} preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="an-floor" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="var(--body-focus)" stopOpacity=".22" /><stop offset="1" stopColor="var(--body-focus)" stopOpacity="0" /></linearGradient>
          <radialGradient id="an-glow"><stop offset="0" stopColor="var(--body-focus)" stopOpacity=".28" /><stop offset="1" stopColor="var(--body-focus)" stopOpacity="0" /></radialGradient>
        </defs>
        {!box.hanging && <><rect x={box.minX} y={0} width={box.w} height={26} fill="url(#an-floor)" /><line x1={box.minX + 8} x2={box.maxX - 8} y1={0} y2={0} className="an-floorline" /></>}
        <ellipse cx={s.hip[0]} cy={4} rx={60} ry={7} fill="url(#an-glow)" className="an-shadow" />
        <Props props={template.props} s={s} barY={barY} minX={box.bx} maxX={box.bX} />
        {ghosts.map((g, i) => <Figure key={i} s={g} regions={[]} ghost />)}
        <Figure s={s} regions={regions} />
      </svg>
      <figcaption>
        <span className="an-cue">{t(`motion.cue.${template.key}`)}</span>
        {reps && <span className="tag">{reps}</span>}
        {!exact && <span className="muted">{t("motion.fallback")}</span>}
        <button type="button" className="an-btn" onClick={() => setPlaying((p) => !p)} aria-pressed={playing}>{playing ? t("motion.pause") : t("motion.play")}</button>
      </figcaption>
    </figure>
  );
}

type Fig = {
  setSolved(sk: Skeleton): void; setTargets(r: readonly string[]): void; setProps(p: readonly string[]): void;
  frame(minX: number, maxX: number, minY: number, maxY: number, ground: boolean, hang: boolean, bar: number): void;
  playClip(n: string): boolean; stopClip(): void; setAutoRotate(on: boolean): void; dispose(): void;
};
type FigApi = { create(c: HTMLCanvasElement, o: Record<string, unknown>): Fig | null };
declare global { interface Window { VFFigure?: FigApi } }
let figPromise: Promise<FigApi> | null = null;
function loadFigure(): Promise<FigApi> {
  if (typeof window === "undefined") return Promise.reject(new Error("ssr"));
  if (window.VFFigure) return Promise.resolve(window.VFFigure);
  figPromise ??= new Promise<FigApi>((resolve, reject) => {
    window.addEventListener("vffigure:ready", () => (window.VFFigure ? resolve(window.VFFigure) : reject(new Error("figure missing"))), { once: true });
    const el = document.createElement("script");
    el.type = "module"; el.src = "/vendor/figure-viewer.js"; el.onerror = () => reject(new Error("figure script"));
    document.head.appendChild(el);
  });
  return figPromise;
}

/** Real motion-capture clips (CC0) used where one exists; everything else is driven by our own IK solver. */
function clipFor(code: string, key: string): string | null {
  if (key === "jacks" && /jumping_jacks/.test(code)) return "Jumping Jacks";
  if (key === "jog" && /easy_jog/.test(code)) return "Jog";
  if (key === "walk" && /brisk_walk/.test(code)) return "Walk";
  if (key === "pushup" && /^(push_up|wide_push_up|close_grip_push_up|decline_push_up)$/.test(code)) return "Pushup";
  return null;
}

/** Skinned 3D mannequin performing the exercise (WebGL); falls back to the 2D skeleton when WebGL or the model is unavailable. */
export function ExerciseAnim({ code, pattern, muscles, height = 260 }: { code: string; pattern?: string; muscles?: readonly string[]; height?: number }) {
  const { t } = useT();
  const { template, exact } = useMemo(() => motionFor(code, pattern), [code, pattern]);
  const regions = useMemo(() => {
    const given = (muscles ?? []).map((m) => muscleRegion(m) ?? m).filter((m, i, a) => !!m && a.indexOf(m) === i);
    return given.length ? given : template.targets;
  }, [muscles, template]);
  const canvas = useRef<HTMLCanvasElement>(null);
  const fig = useRef<Fig | null>(null);
  const [phase, setPhase] = useState<"loading" | "ready" | "fallback">("loading");
  const [playing, setPlaying] = useState(true);
  const playRef = useRef(true);
  playRef.current = playing;
  const clip = clipFor(code, template.key);
  const variant = useMemo(() => variantFor(code), [code]);

  useEffect(() => {
    let dead = false;
    let v: Fig | null = null;
    loadFigure().then((api) => {
      if (dead || !canvas.current) return;
      v = api.create(canvas.current, { onReady: () => { if (!dead) setPhase("ready"); }, onError: () => { if (!dead) setPhase("fallback"); } });
      if (!v) return setPhase("fallback");
      fig.current = v;
    }).catch(() => { if (!dead) setPhase("fallback"); });
    return () => { dead = true; fig.current = null; v?.dispose(); };
  }, []);

  useEffect(() => {
    const v = fig.current;
    if (!v || phase !== "ready") return;
    const b = bounds(template.frames);
    const hang = template.props.includes("bar-hang");
    const bar = template.frames.find((f) => f.handA)?.handA?.[1] ?? 188;
    v.frame(b.minX, b.maxX, hang ? b.minY : Math.min(0, b.minY), b.maxY, true, hang, bar);
    v.setProps(clip ? [] : template.props);
    v.setTargets(regions);
    if (clip && v.playClip(clip)) return;
    v.stopClip();
    let acc = 0, prev: number | null = null, last = 0, raf = 0;
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = prev === null ? 0 : now - prev;
      prev = now;
      if (!playRef.current) return;
      acc += dt;
      if (now - last < 24) return;
      last = now;
      v.setSolved(solve(poseAt(template, ((acc / 1000) / (template.period * variant.speed)) % 1, variant)));
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase, template, regions, clip, variant]);

  if (phase === "fallback") return <ExerciseAnim2D code={code} pattern={pattern} muscles={muscles} height={height} />;
  return (
    <figure className="an an3" aria-label={t("motion.aria")}>
      <div className="an3-stage" style={{ blockSize: height }}>
        <canvas ref={canvas} role="img" aria-label={t("motion.aria")} />
        {phase === "loading" && <div className="an-loading" aria-hidden="true" />}
      </div>
      <figcaption>
        <span className="an-cue">{t(`motion.cue.${template.key}`)}</span>
        {template.hold && <span className="tag">{t("motion.hold")}</span>}
        {variant.tags.map((g) => <span key={g} className="tag">{t(`motion.tag.${g}`)}</span>)}
        {clip && <span className="muted">{t("motion.mocap")}</span>}
        {!exact && <span className="muted">{t("motion.fallback")}</span>}
        <button type="button" className="an-btn" onClick={() => { setPlaying((p) => !p); fig.current?.setAutoRotate(false); }} aria-pressed={playing}>{playing ? t("motion.pause") : t("motion.play")}</button>
      </figcaption>
    </figure>
  );
}

/** Loads the exercise (to learn its stable code) and shows its animation. Used where only the opaque id is known (plan). */
const cache = new Map<string, { code: string; pattern?: string }>();
export function ExerciseAnimById({ exerciseId, muscles, height }: { exerciseId: string; muscles?: readonly string[]; height?: number }) {
  const api = useApi();
  const [info, setInfo] = useState<{ code: string; pattern?: string } | null>(cache.get(exerciseId) ?? null);
  useEffect(() => {
    if (cache.has(exerciseId)) { setInfo(cache.get(exerciseId)!); return; }
    let live = true;
    api.call("API-EX-002", { path: { exercise_id: exerciseId } }).then((r) => {
      if (!live || !r.ok || !r.data.code) return;
      const v = { code: r.data.code };
      cache.set(exerciseId, v); setInfo(v);
    });
    return () => { live = false; };
  }, [api, exerciseId]);
  if (!info) return <div className="an an-loading" style={{ blockSize: height ?? 260 }} aria-hidden="true" />;
  return <ExerciseAnim code={info.code} pattern={info.pattern} muscles={muscles} height={height} />;
}
