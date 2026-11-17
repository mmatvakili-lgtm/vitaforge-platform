// Procedural exercise motion: a side-view skeleton driven by keyframed poses, solved with 2-bone IK.
// Original work (no third-party animation or images). Pure functions so geometry is unit-testable; drawing lives in the component.
// Coordinates: x forward (the figure faces +x), y UP from the floor. Units are "figure pixels" (standing height ~ 190).

export type V = readonly [number, number];
export const L = { thigh: 56, shin: 54, torso: 76, upper: 42, fore: 40, ankle: 8, neck: 16, head: 13, foot: 20 } as const;

/** One keyframe. `mode` says how the hip is found:
 *  hip: given hip position + torso angle (deg from vertical, + = leaning toward +x); legs by IK to pinned feet or by absolute angles.
 *  rigid: ankle pinned, legs straight at elevation `legUp` (deg above +x axis toward the hip); torso elevation `torsoUp`.
 *  shoulder: shoulder pinned (hanging/lying), hip derived from `torso`. */
export type Pose = {
  mode?: "hip" | "rigid" | "shoulder";
  hip?: V; torso?: number; shoulder?: V; ankle?: V; legUp?: number; torsoUp?: number;
  footA?: V; footB?: V; legs?: readonly [number, number, number, number];     // absolute angles from straight down: thighA, shinA, thighB, shinB
  handA?: V; handB?: V; arms?: readonly [number, number, number, number];     // upperA, foreA, upperB, foreB (from straight down, + toward +x)
  knee?: 1 | -1; elbow?: 1 | -1; head?: number;
};

export type Prop = "barbell-hands" | "barbell-back" | "barbell-front" | "barbell-hip" | "dumbbell" | "kettlebell" | "bench-back" | "bench-seat" | "box-foot" | "box-feet" | "bar-hang" | "band-hands" | "cable-hands" | "wall";
export type Template = { key: string; frames: readonly Pose[]; loop: "pingpong" | "cycle"; period: number; props: readonly Prop[]; targets: readonly string[]; hold?: boolean };

export type Skeleton = {
  head: V; neck: V; shoulder: V; hip: V;
  kneeA: V; ankleA: V; toeA: V; kneeB: V; ankleB: V; toeB: V;
  elbowA: V; handA: V; elbowB: V; handB: V;
};

const rad = (d: number) => (d * Math.PI) / 180;
const add = (a: V, b: V): V => [a[0] + b[0], a[1] + b[1]];
const dirDown = (a: number): V => [Math.sin(rad(a)), -Math.cos(rad(a))];      // angle from straight down, + toward +x
const dirUp = (a: number): V => [Math.sin(rad(a)), Math.cos(rad(a))];         // angle from straight up, + toward +x
const scale = (v: V, k: number): V => [v[0] * k, v[1] * k];

/** Two-bone IK in the plane. `side` picks which way the joint bends (perpendicular to p0->p1). Out-of-reach targets give a straight limb. */
export function ik(p0: V, p1: V, l1: number, l2: number, side: 1 | -1): { mid: V; end: V } {
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1];
  const raw = Math.hypot(dx, dy) || 1e-6;
  const d = Math.min(raw, l1 + l2 - 1e-3), ux = dx / raw, uy = dy / raw;
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(l1 * l1 - a * a, 0));
  const mid: V = [p0[0] + ux * a + -uy * h * side, p0[1] + uy * a + ux * h * side];
  return { mid, end: [p0[0] + ux * d, p0[1] + uy * d] };
}

function limb(root: V, pose: Pose, pin: V | undefined, angs: readonly [number, number] | undefined, l1: number, l2: number, side: 1 | -1): { mid: V; end: V } {
  if (pin) return ik(root, pin, l1, l2, side);
  const [a1, a2] = angs ?? [0, 0];
  const mid = add(root, scale(dirDown(a1), l1));
  return { mid, end: add(mid, scale(dirDown(a2), l2)) };
}

/** Solves one pose into joint positions. */
export function solve(p: Pose): Skeleton {
  const mode = p.mode ?? "hip";
  let hip: V, shoulder: V;
  if (mode === "rigid") {
    const an = p.ankle ?? [0, L.ankle];
    hip = [an[0] + (L.thigh + L.shin) * Math.cos(rad(p.legUp ?? 0)), an[1] + (L.thigh + L.shin) * Math.sin(rad(p.legUp ?? 0))];
    const te = rad(p.torsoUp ?? 0);
    shoulder = [hip[0] + L.torso * Math.cos(te), hip[1] + L.torso * Math.sin(te)];
  } else if (mode === "shoulder") {
    shoulder = p.shoulder ?? [0, 150];
    hip = add(shoulder, scale(dirUp(p.torso ?? 180), L.torso));
  } else {
    hip = p.hip ?? [0, 114];
    shoulder = add(hip, scale(dirUp(p.torso ?? 0), L.torso));
  }
  const kd = p.knee ?? 1, ed = p.elbow ?? -1;
  const pinA = mode === "rigid" ? (p.ankle ?? [0, L.ankle]) : p.footA;
  const lA = limb(hip, p, pinA, p.legs ? [p.legs[0], p.legs[1]] : undefined, L.thigh, L.shin, kd);
  const lB = limb(hip, p, mode === "rigid" ? add(p.ankle ?? [0, L.ankle], [4, 0]) : p.footB, p.legs ? [p.legs[2], p.legs[3]] : undefined, L.thigh, L.shin, kd);
  const aA = limb(shoulder, p, p.handA, p.arms ? [p.arms[0], p.arms[1]] : undefined, L.upper, L.fore, ed);
  const aB = limb(shoulder, p, p.handB ?? p.handA, p.arms ? [p.arms[2], p.arms[3]] : undefined, L.upper, L.fore, ed);
  const tdir: V = mode === "rigid" ? [Math.cos(rad(p.torsoUp ?? 0)), Math.sin(rad(p.torsoUp ?? 0))] : mode === "shoulder" ? scale(dirUp(p.torso ?? 180), -1) : dirUp(p.torso ?? 0);
  const neck = add(shoulder, scale(tdir, L.neck));
  const head = add(neck, scale(dirUp(Math.atan2(tdir[0], tdir[1]) * 180 / Math.PI + (p.head ?? 0)), L.head + 4));
  return { head, neck, shoulder, hip, kneeA: lA.mid, ankleA: lA.end, toeA: add(lA.end, [L.foot, 0]), kneeB: lB.mid, ankleB: lB.end, toeB: add(lB.end, [L.foot, 0]),
    elbowA: aA.mid, handA: aA.end, elbowB: aB.mid, handB: aB.end };
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpV = (a: V | undefined, b: V | undefined, t: number): V | undefined => (a && b ? [lerp(a[0], b[0], t), lerp(a[1], b[1], t)] : (t < 0.5 ? a : b));
const lerpN = (a: number | undefined, b: number | undefined, t: number): number | undefined => (a !== undefined && b !== undefined ? lerp(a, b, t) : (t < 0.5 ? a : b));
const lerpT = <T extends readonly number[]>(a: T | undefined, b: T | undefined, t: number): T | undefined =>
  (a && b ? (a.map((x, i) => lerp(x, b[i], t)) as unknown as T) : (t < 0.5 ? a : b));
export const ease = (t: number) => t * t * (3 - 2 * t);

export function blend(a: Pose, b: Pose, t: number): Pose {
  const m = t < 0.5 ? a : b;
  return { mode: m.mode, knee: m.knee, elbow: m.elbow, hip: lerpV(a.hip, b.hip, t), torso: lerpN(a.torso, b.torso, t), shoulder: lerpV(a.shoulder, b.shoulder, t),
    ankle: lerpV(a.ankle, b.ankle, t), legUp: lerpN(a.legUp, b.legUp, t), torsoUp: lerpN(a.torsoUp, b.torsoUp, t), footA: lerpV(a.footA, b.footA, t), footB: lerpV(a.footB, b.footB, t),
    legs: lerpT(a.legs, b.legs, t), handA: lerpV(a.handA, b.handA, t), handB: lerpV(a.handB, b.handB, t), arms: lerpT(a.arms, b.arms, t), head: lerpN(a.head, b.head, t) };
}

/** Per-exercise modifiers layered on a shared motion template so that variants of one pattern do not look identical. */
export type Variant = { amp: number; pause: number; speed: number; single: boolean; wide: boolean; tilt: number; tags: readonly string[] };
export const NEUTRAL: Variant = { amp: 1, pause: 0, speed: 1, single: false, wide: false, tilt: 0, tags: [] };
export function variantFor(code: string): Variant {
  const c = code.toLowerCase(), tags: string[] = [];
  const v = { ...NEUTRAL };
  if (/paused|pause_|_pause|isometric/.test(c)) { v.pause = 0.38; tags.push("pause"); }
  if (/tempo|slow|eccentric|negative/.test(c)) { v.speed = 1.7; tags.push("tempo"); }
  if (/jump|explosive|power|plyo|clean|snatch|swing|burpee|skater/.test(c)) { v.speed = 0.62; tags.push("explosive"); }
  if (/single_leg|one_leg|bulgarian|rear_foot|split_squat|pistol|single_arm|one_arm|unilateral|step_up|step_down/.test(c)) { v.single = true; tags.push("single"); }
  if (/wide|sumo|cossack|lateral/.test(c)) { v.wide = true; tags.push("wide"); }
  if (/half|partial|mini|quarter|short_range/.test(c)) { v.amp = 0.62; tags.push("partial"); }
  else if (/deep|full_range|atg|ass_to_grass/.test(c)) { v.amp = 1.1; tags.push("deep"); }
  if (/incline|elevated|decline/.test(c)) { v.tilt = /decline|feet_elevated/.test(c) ? -1 : 1; tags.push(v.tilt > 0 ? "incline" : "decline"); }
  return { ...v, tags };
}

const shift = (p: V | undefined, dx: number, dy: number): V | undefined => (p ? [p[0] + dx, p[1] + dy] : p);
function applyVariant(p: Pose, v: Variant): Pose {
  if (!v.single && !v.wide && !v.tilt) return p;
  const q: Pose = { ...p };
  if (v.wide && q.footA) { q.footA = shift(q.footA, 10, 0); q.footB = shift(q.footB, -14, 0); }
  if (v.single && q.footB && (p.mode ?? "hip") === "hip" && q.hip && q.hip[1] > 40) q.footB = shift(q.footB, 34, 30);      // free leg held off the floor
  if (v.tilt && q.handA && (p.mode ?? "hip") === "rigid") {
    const lift = v.tilt > 0 ? 28 : 0;                                       // hands on a raised surface (incline) / feet raised (decline)
    q.handA = shift(q.handA, 0, lift); q.handB = shift(q.handB, 0, lift);
    if (v.tilt < 0 && q.ankle) q.ankle = shift(q.ankle, 0, 26);
    q.legUp = (q.legUp ?? 0) + (v.tilt > 0 ? -10 : 8); q.torsoUp = (q.torsoUp ?? 0) + (v.tilt > 0 ? -8 : 8);
  }
  return q;
}

/** Pose at normalised time u in [0,1) of one repetition. pingpong: frame0 -> last -> frame0; cycle: frames loop. */
export function poseAt(tpl: Template, u: number, v: Variant = NEUTRAL): Pose {
  return applyVariant(poseBase(tpl, u, v), v);
}

function poseBase(tpl: Template, u: number, v: Variant): Pose {
  const f = tpl.frames, n = f.length;
  if (n === 1) return f[0];
  const x = ((u % 1) + 1) % 1;
  if (tpl.loop === "cycle") {
    const s = x * n, i = Math.floor(s) % n;
    return blend(f[i], f[(i + 1) % n], ease(s - Math.floor(s)));
  }
  let tri = x < 0.5 ? x * 2 : (1 - x) * 2;               // 0 -> 1 -> 0
  if (v.pause > 0) tri = Math.min(1, tri / (1 - v.pause));   // dwell at the hardest point (paused reps)
  tri *= v.amp;                                            // partial / deep range of motion
  const s = tri * (n - 1), i = Math.min(Math.floor(s), n - 2);
  return blend(f[i], f[i + 1], ease(s - i));
}

// ---------------------------------------------------------------- keyframe library
const F = (hipx: number, hipy: number, torso: number, rest: Partial<Pose> = {}): Pose => ({ mode: "hip", hip: [hipx, hipy], torso, footA: [0, L.ankle], footB: [-10, L.ankle], ...rest });
const STAND = F(0, 114, 0);
const ARMS_FWD = { arms: [88, 90, 84, 88] as const };
const ARMS_HANG = { arms: [0, 0, -3, -3] as const };
const ARMS_CHEST = { arms: [8, 150, 4, 148] as const };
const SQ_BOT = F(-42, 62, 40, { footA: [0, L.ankle], footB: [-10, L.ankle] });

function T(key: string, frames: readonly Pose[], o: Partial<Omit<Template, "key" | "frames">> & { targets: readonly string[] }): Template {
  return { key, frames, loop: o.loop ?? "pingpong", period: o.period ?? 3.4, props: o.props ?? [], targets: o.targets, hold: o.hold };
}

const PLANK_TOP: Pose = { mode: "rigid", ankle: [-113, L.ankle], legUp: 27, torsoUp: 20, handA: [58, 0], handB: [52, 0], elbow: -1 };
const PUSH_BOT: Pose = { mode: "rigid", ankle: [-113, L.ankle], legUp: 4, torsoUp: 5, handA: [58, 0], handB: [52, 0], elbow: -1 };
const FOREARM_PLANK: Pose = { mode: "rigid", ankle: [-113, L.ankle], legUp: 12, torsoUp: 8, handA: [30, 0], handB: [26, 0], elbow: -1 };
const LEG_ROW: Pose = { mode: "hip", hip: [-40, 80], torso: 68, footA: [0, L.ankle], footB: [-8, L.ankle], elbow: -1 };

export const TEMPLATES: Record<string, Template> = {
  squat: T("squat", [{ ...STAND, ...ARMS_FWD }, { ...SQ_BOT, ...ARMS_FWD }], { targets: ["quadriceps", "glutes"] }),
  squat_goblet: T("squat_goblet", [{ ...STAND, ...ARMS_CHEST }, { ...F(-38, 60, 28), ...ARMS_CHEST }], { props: ["dumbbell"], targets: ["quadriceps", "glutes"] }),
  squat_back: T("squat_back", [{ ...STAND, arms: [-30, 170, -26, 168] }, { ...SQ_BOT, arms: [-30, 170, -26, 168] }], { props: ["barbell-back"], targets: ["quadriceps", "glutes", "lower back"] }),
  squat_front: T("squat_front", [{ ...STAND, arms: [60, 140, 56, 138] }, { ...F(-38, 62, 28, { arms: [60, 140, 56, 138] }) }], { props: ["barbell-front"], targets: ["quadriceps", "abdominals"] }),
  wall_sit: T("wall_sit", [{ ...F(-52, 62, 0, { footA: [0, L.ankle], footB: [-8, L.ankle], arms: [20, 70, 16, 68] }) }, { ...F(-52, 62, 0, { footA: [0, L.ankle], footB: [-8, L.ankle], arms: [20, 70, 16, 68] }) }], { hold: true, props: ["wall"], targets: ["quadriceps", "glutes"] }),
  leg_press: T("leg_press", [{ ...F(-48, 70, -58, { footA: [28, 96], footB: [24, 92], arms: [30, 80, 30, 80] }), mode: "hip" }, { ...F(-50, 56, -58, { footA: [86, 30], footB: [82, 26], arms: [30, 80, 30, 80] }), mode: "hip" }], { targets: ["quadriceps", "glutes"] }),
  pistol: T("pistol", [{ ...STAND, ...ARMS_FWD }, { ...F(-44, 54, 44, { footA: [0, L.ankle], footB: [66, 56], arms: [88, 90, 84, 88] }) }], { props: ["box-feet"], targets: ["quadriceps", "glutes"] }),
  jump: T("jump", [{ ...F(-30, 70, 30, { arms: [-30, -10, -30, -10] }) }, { ...F(0, 138, 0, { footA: [0, 30], footB: [-10, 26], arms: [150, 160, 146, 158] }) }], { loop: "pingpong", period: 1.5, targets: ["quadriceps", "glutes", "calves"] }),
  box_jump: T("box_jump", [{ ...F(-34, 70, 34, { arms: [-30, -10, -30, -10] }) }, { ...F(10, 138, 6, { footA: [24, 40], footB: [16, 40], arms: [100, 100, 96, 98] }) }], { props: ["box-feet"], period: 1.8, targets: ["quadriceps", "glutes", "calves"] }),
  hinge: T("hinge", [{ ...STAND, ...ARMS_HANG }, { ...F(-52, 92, 70, { footA: [0, L.ankle], footB: [-10, L.ankle], ...ARMS_HANG }) }], { props: ["dumbbell"], targets: ["hamstrings", "glutes", "lower back"] }),
  hinge_bar: T("hinge_bar", [{ ...STAND, ...ARMS_HANG }, { ...F(-52, 92, 70, { ...ARMS_HANG }) }], { props: ["barbell-hands"], targets: ["hamstrings", "glutes", "lower back"] }),
  deadlift: T("deadlift", [{ ...F(-40, 58, 52, { ...ARMS_HANG }) }, { ...STAND, ...ARMS_HANG }], { props: ["barbell-hands"], targets: ["glutes", "hamstrings", "lower back", "quadriceps"] }),
  good_morning: T("good_morning", [{ ...STAND, arms: [-30, 170, -26, 168] }, { ...F(-54, 90, 72, { arms: [-30, 170, -26, 168] }) }], { props: ["barbell-back"], targets: ["hamstrings", "lower back", "glutes"] }),
  swing: T("swing", [{ ...F(-56, 94, 66, { arms: [30, 24, 28, 22] }) }, { ...F(2, 116, 4, { arms: [88, 90, 84, 88] }) }], { loop: "pingpong", period: 1.8, props: ["kettlebell"], targets: ["glutes", "hamstrings", "lower back"] }),
  bridge: T("bridge", [{ mode: "hip", hip: [0, 12], torso: -90, footA: [62, L.ankle], footB: [58, L.ankle], arms: [90, 90, 90, 90], knee: 1 }, { mode: "hip", hip: [0, 64], torso: -122, footA: [62, L.ankle], footB: [58, L.ankle], arms: [90, 90, 90, 90], knee: 1 }], { targets: ["glutes", "hamstrings"] }),
  hip_thrust: T("hip_thrust", [{ mode: "hip", hip: [0, 30], torso: -90, footA: [62, L.ankle], footB: [58, L.ankle], arms: [60, 100, 58, 98] }, { mode: "hip", hip: [0, 76], torso: -104, footA: [62, L.ankle], footB: [58, L.ankle], arms: [60, 100, 58, 98] }], { props: ["bench-back", "barbell-hip"], targets: ["glutes", "hamstrings"] }),
  lunge: T("lunge", [{ ...F(0, 114, 0, { footA: [20, L.ankle], footB: [-20, L.ankle], ...ARMS_HANG }) }, { ...F(2, 66, 4, { footA: [34, L.ankle], footB: [-52, 22], ...ARMS_HANG }) }], { props: ["dumbbell"], targets: ["quadriceps", "glutes"] }),
  step_up: T("step_up", [{ ...F(0, 112, 6, { footA: [26, 36], footB: [-14, L.ankle], ...ARMS_HANG }) }, { ...F(24, 146, 2, { footA: [26, 36], footB: [20, 62], ...ARMS_HANG }) }], { props: ["box-foot"], targets: ["quadriceps", "glutes"] }),
  side_lunge: T("side_lunge", [{ ...STAND, ...ARMS_CHEST }, { ...F(-30, 64, 24, { footA: [8, L.ankle], footB: [-26, L.ankle], ...ARMS_CHEST }) }], { targets: ["adductors", "quadriceps", "glutes"] }),
  pushup: T("pushup", [PLANK_TOP, PUSH_BOT], { targets: ["chest", "triceps", "shoulders"] }),
  pushup_knee: T("pushup_knee", [{ mode: "hip", hip: [-34, 42], torso: 66, footA: [-60, L.ankle], footB: [-64, L.ankle], handA: [58, 0], handB: [52, 0], elbow: -1, knee: -1 }, { mode: "hip", hip: [-30, 24], torso: 80, footA: [-60, L.ankle], footB: [-64, L.ankle], handA: [58, 0], handB: [52, 0], elbow: -1, knee: -1 }], { targets: ["chest", "triceps", "shoulders"] }),
  pushup_wall: T("pushup_wall", [{ mode: "rigid", ankle: [-70, L.ankle], legUp: 66, torsoUp: 70, handA: [60, 118], handB: [60, 112], elbow: -1 }, { mode: "rigid", ankle: [-70, L.ankle], legUp: 72, torsoUp: 76, handA: [60, 118], handB: [60, 112], elbow: -1 }], { props: ["wall"], targets: ["chest", "triceps", "shoulders"] }),
  plank: T("plank", [FOREARM_PLANK, { ...FOREARM_PLANK, torsoUp: 9 }], { hold: true, targets: ["abdominals", "shoulders", "glutes"] }),
  press_floor: T("press_floor", [{ mode: "hip", hip: [-6, 14], torso: -90, footA: [60, L.ankle], footB: [56, L.ankle], handA: [-72, 38], handB: [-74, 38], elbow: 1 }, { mode: "hip", hip: [-6, 14], torso: -90, footA: [60, L.ankle], footB: [56, L.ankle], handA: [-70, 90], handB: [-72, 90], elbow: 1 }], { props: ["bench-back", "dumbbell"], targets: ["chest", "triceps", "shoulders"] }),
  press_overhead: T("press_overhead", [{ ...STAND, arms: [10, 150, 8, 148] }, { ...STAND, handA: [4, 266], handB: [0, 266], elbow: 1 }], { props: ["dumbbell"], targets: ["shoulders", "triceps"] }),
  raise: T("raise", [{ ...STAND, ...ARMS_HANG }, { ...STAND, arms: [90, 92, 86, 88] }], { props: ["dumbbell"], targets: ["shoulders"] }),
  fly: T("fly", [{ mode: "hip", hip: [-6, 14], torso: -90, footA: [60, L.ankle], footB: [56, L.ankle], handA: [-70, 30], handB: [-72, 30], elbow: 1 }, { mode: "hip", hip: [-6, 14], torso: -90, footA: [60, L.ankle], footB: [56, L.ankle], handA: [-70, 90], handB: [-72, 90], elbow: 1 }], { props: ["bench-back", "dumbbell"], targets: ["chest", "shoulders"] }),
  dip: T("dip", [{ mode: "shoulder", shoulder: [0, 144], torso: 180, handA: [-12, 62], handB: [-12, 62], elbow: -1, footA: [60, 8], footB: [64, 8] }, { mode: "shoulder", shoulder: [0, 102], torso: 180, handA: [-12, 62], handB: [-12, 62], elbow: -1, footA: [60, 8], footB: [64, 8] }], { props: ["bench-seat"], targets: ["triceps", "chest", "shoulders"] }),
  row_bent: T("row_bent", [{ ...LEG_ROW, arms: [0, 0, -2, -2] }, { ...LEG_ROW, handA: [-14, 86], handB: [-14, 84], elbow: -1 }], { props: ["barbell-hands"], targets: ["lats", "middle back", "biceps"] }),
  row_cable: T("row_cable", [{ mode: "hip", hip: [-44, 38], torso: 14, footA: [10, 46], footB: [6, 42], arms: [88, 90, 84, 88], knee: 1 }, { mode: "hip", hip: [-44, 38], torso: -6, footA: [10, 46], footB: [6, 42], handA: [-20, 86], handB: [-22, 84], elbow: -1 }], { props: ["cable-hands"], targets: ["middle back", "lats", "biceps"] }),
  row_inverted: T("row_inverted", [{ mode: "rigid", ankle: [-110, L.ankle], legUp: 4, torsoUp: 2, arms: [178, 180, 176, 178], elbow: -1 }, { mode: "rigid", ankle: [-110, L.ankle], legUp: 14, torsoUp: 10, handA: [70, 100], handB: [66, 100], elbow: -1 }], { props: ["bar-hang"], targets: ["lats", "middle back", "biceps"] }),
  row_band: T("row_band", [{ mode: "hip", hip: [-6, 70], torso: 0, footA: [26, L.ankle], footB: [20, L.ankle], arms: [88, 90, 84, 88], knee: 1 }, { mode: "hip", hip: [-6, 70], torso: 0, footA: [26, L.ankle], footB: [20, L.ankle], handA: [-12, 100], handB: [-14, 98], elbow: -1 }], { props: ["band-hands"], targets: ["middle back", "lats", "biceps"] }),
  pulldown: T("pulldown", [{ mode: "hip", hip: [-24, 52], torso: 4, footA: [20, L.ankle], footB: [16, L.ankle], handA: [30, 198], handB: [26, 198], elbow: 1, knee: 1 }, { mode: "hip", hip: [-24, 52], torso: -8, footA: [20, L.ankle], footB: [16, L.ankle], handA: [-2, 124], handB: [-6, 122], elbow: -1, knee: 1 }], { props: ["cable-hands", "seat"], targets: ["lats", "biceps", "middle back"] }),
  pullup: T("pullup", [{ mode: "shoulder", shoulder: [0, 106], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [10, 20, 14, 26] }, { mode: "shoulder", shoulder: [0, 150], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [10, 20, 14, 26] }], { props: ["bar-hang"], targets: ["lats", "biceps", "middle back"] }),
  hang: T("hang", [{ mode: "shoulder", shoulder: [0, 106], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [4, 8, 8, 12] }, { mode: "shoulder", shoulder: [0, 108], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [4, 8, 8, 12] }], { hold: true, props: ["bar-hang"], targets: ["forearms", "lats"] }),
  curl: T("curl", [{ ...STAND, arms: [0, 4, -2, 2] }, { ...STAND, arms: [4, 150, 2, 148] }], { props: ["dumbbell"], targets: ["biceps", "forearms"] }),
  triceps_ext: T("triceps_ext", [{ ...STAND, arms: [170, -20, 166, -22] }, { ...STAND, arms: [172, 176, 168, 174] }], { props: ["dumbbell"], targets: ["triceps"] }),
  pushdown: T("pushdown", [{ ...STAND, arms: [4, 150, 2, 148] }, { ...STAND, arms: [4, 6, 2, 4] }], { props: ["cable-hands"], targets: ["triceps"] }),
  calf_raise: T("calf_raise", [{ ...F(0, 114, 0, { ...ARMS_HANG }) }, { ...F(0, 128, 0, { footA: [0, 22], footB: [-10, 22], ...ARMS_HANG }) }], { props: ["dumbbell"], period: 2.4, targets: ["calves"] }),
  crunch: T("crunch", [{ mode: "hip", hip: [-6, 14], torso: -90, footA: [56, L.ankle], footB: [52, L.ankle], arms: [-86, -80, -84, -78], knee: 1 }, { mode: "hip", hip: [-6, 14], torso: -62, footA: [56, L.ankle], footB: [52, L.ankle], arms: [-60, -20, -58, -18], knee: 1 }], { targets: ["abdominals"] }),
  leg_raise: T("leg_raise", [{ mode: "hip", hip: [-6, 14], torso: -90, legs: [90, 90, 88, 88], arms: [90, 90, 88, 88], knee: 1 }, { mode: "hip", hip: [-6, 14], torso: -90, legs: [172, 172, 170, 170], arms: [90, 90, 88, 88], knee: 1 }], { targets: ["abdominals", "quadriceps"] }),
  hang_raise: T("hang_raise", [{ mode: "shoulder", shoulder: [0, 106], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [4, 8, 8, 12] }, { mode: "shoulder", shoulder: [0, 106], torso: 180, handA: [8, 188], handB: [4, 188], elbow: -1, legs: [84, 90, 88, 92] }], { props: ["bar-hang"], targets: ["abdominals", "forearms"] }),
  carry: T("carry", [{ ...F(2, 114, 0, { footA: [18, L.ankle], footB: [-18, L.ankle], ...ARMS_HANG }) }, { ...F(2, 114, 0, { footA: [-18, L.ankle], footB: [18, L.ankle], ...ARMS_HANG }) }], { props: ["dumbbell"], period: 2.4, targets: ["forearms", "abdominals", "shoulders"] }),
  rotation: T("rotation", [{ ...STAND, arms: [60, 100, 56, 98], head: 0 }, { ...F(0, 114, 0, { arms: [100, 100, 96, 98] }) }], { props: ["cable-hands"], targets: ["abdominals", "abdominals"] }),
  walk: T("walk", [F(8, 112, 2, { footA: [28, L.ankle], footB: [-26, L.ankle], arms: [-24, -10, 28, 40] }), F(0, 118, 2, { footA: [2, L.ankle], footB: [-6, 16], arms: [0, 20, 0, 20] }), F(-8, 112, 2, { footA: [-26, L.ankle], footB: [28, L.ankle], arms: [28, 40, -24, -10] }), F(0, 118, 2, { footA: [-6, 16], footB: [2, L.ankle], arms: [0, 20, 0, 20] })], { loop: "cycle", period: 1.6, targets: ["quadriceps", "calves", "glutes"] }),
  jog: T("jog", [F(8, 108, 10, { footA: [36, 26], footB: [-40, 34], arms: [-40, 80, 48, 100] }), F(0, 114, 10, { footA: [10, L.ankle], footB: [-20, 52], arms: [0, 90, 0, 90] }), F(-8, 108, 10, { footA: [-40, 34], footB: [36, 26], arms: [48, 100, -40, 80] }), F(0, 114, 10, { footA: [-20, 52], footB: [10, L.ankle], arms: [0, 90, 0, 90] })], { loop: "cycle", period: 1.0, targets: ["quadriceps", "calves", "hamstrings"] }),
  high_knees: T("high_knees", [F(0, 114, 4, { footA: [0, L.ankle], footB: [30, 90], arms: [-30, 80, 40, 100] }), F(0, 118, 4, { footA: [0, 18], footB: [-6, 18], arms: [0, 90, 0, 90] }), F(0, 114, 4, { footA: [30, 90], footB: [0, L.ankle], arms: [40, 100, -30, 80] }), F(0, 118, 4, { footA: [-6, 18], footB: [0, 18], arms: [0, 90, 0, 90] })], { loop: "cycle", period: 0.9, targets: ["quadriceps", "abdominals", "calves"] }),
  jacks: T("jacks", [{ ...STAND, arms: [4, 6, 0, 4] }, { ...F(0, 122, 0, { footA: [14, 14], footB: [-24, 14], arms: [170, 172, 166, 170] }) }], { period: 1.2, targets: ["shoulders", "calves", "quadriceps"] }),
  burpee: T("burpee", [{ ...STAND, arms: [4, 6, 0, 4] }, { ...F(-40, 56, 55, { handA: [20, 0], handB: [16, 0], elbow: -1 }) }, PLANK_TOP, { ...F(0, 138, 0, { footA: [0, 30], footB: [-10, 26], arms: [150, 160, 146, 158] }) }], { loop: "cycle", period: 3.2, targets: ["quadriceps", "chest", "abdominals"] }),
  bike: T("bike", [F(-20, 90, 28, { footA: [34, 38], footB: [-34, 14], handA: [56, 98], handB: [52, 96], elbow: -1 }), F(-20, 90, 28, { footA: [8, 10], footB: [-8, 44], handA: [56, 98], handB: [52, 96], elbow: -1 }), F(-20, 90, 28, { footA: [-34, 14], footB: [34, 38], handA: [56, 98], handB: [52, 96], elbow: -1 }), F(-20, 90, 28, { footA: [-8, 44], footB: [8, 10], handA: [56, 98], handB: [52, 96], elbow: -1 })], { loop: "cycle", period: 1.2, targets: ["quadriceps", "calves", "glutes"] }),
  rower: T("rower", [{ mode: "hip", hip: [-60, 36], torso: 34, footA: [10, 44], footB: [6, 40], arms: [88, 90, 84, 88], knee: 1 }, { mode: "hip", hip: [-24, 36], torso: -16, footA: [30, 18], footB: [26, 16], handA: [-8, 72], handB: [-10, 70], elbow: -1, knee: 1 }], { period: 2.2, targets: ["quadriceps", "lats", "glutes"] }),
  kickback: T("kickback", [{ ...F(-14, 100, 30, { footA: [0, L.ankle], footB: [-14, 30], handA: [44, 120], handB: [40, 118], elbow: -1 }) }, { ...F(-14, 100, 30, { footA: [0, L.ankle], footB: [-84, 78], handA: [44, 120], handB: [40, 118], elbow: -1 }) }], { props: ["cable-hands"], targets: ["glutes", "hamstrings"] }),
  stretch: T("stretch", [{ ...STAND, arms: [10, 20, 8, 18] }, { ...F(2, 114, 4, { arms: [170, 172, 166, 170] }) }], { period: 5, targets: ["shoulders"] }),
  stretch_lunge: T("stretch_lunge", [{ ...F(0, 80, 0, { footA: [34, L.ankle], footB: [-62, 16], arms: [30, 60, 28, 58] }) }, { ...F(14, 70, 0, { footA: [34, L.ankle], footB: [-64, 12], arms: [20, 50, 18, 48] }) }], { hold: true, period: 5, targets: ["quadriceps", "quadriceps"] }),
  mobility_floor: T("mobility_floor", [{ mode: "hip", hip: [-36, 40], torso: 70, footA: [-70, L.ankle], footB: [-74, L.ankle], handA: [30, 0], handB: [26, 0], elbow: -1, knee: -1 }, { mode: "hip", hip: [-36, 52], torso: 56, footA: [-70, L.ankle], footB: [-74, L.ankle], handA: [30, 0], handB: [26, 0], elbow: -1, knee: -1 }], { period: 4, targets: ["lower back", "abdominals"] }),
  superman: T("superman", [{ mode: "hip", hip: [-4, 14], torso: 90, legs: [-90, -90, -88, -88], arms: [90, 90, 88, 88], knee: -1 }, { mode: "hip", hip: [-4, 20], torso: 70, legs: [-110, -110, -106, -106], arms: [120, 120, 116, 116], knee: -1 }], { targets: ["lower back", "glutes"] }),
  bird_dog: T("bird_dog", [{ mode: "hip", hip: [-30, 60], torso: 84, handA: [30, 0], handB: [26, 0], footA: [-60, 0], footB: [-62, 0], elbow: -1, knee: -1 }, { mode: "hip", hip: [-30, 60], torso: 84, handA: [30, 0], handB: [90, 70], footA: [-60, 0], footB: [-100, 68], elbow: -1, knee: -1 }], { period: 3.6, targets: ["lower back", "glutes", "abdominals"] }),
  mountain: T("mountain", [{ ...PLANK_TOP, ankle: [-113, L.ankle] }, { mode: "hip", hip: [-14, 56], torso: 70, footA: [-20, 40], footB: [-113, L.ankle], handA: [58, 0], handB: [52, 0], elbow: -1, knee: 1 }], { period: 1.2, targets: ["abdominals", "quadriceps", "shoulders"] }),
};

// ---------------------------------------------------------------- classification
const RULES: ReadonlyArray<readonly [RegExp, string]> = [
  [/wall_push/, "pushup_wall"], [/knee_push|incline_push/, "pushup_knee"], [/push_up|pseudo_planche/, "pushup"],
  [/inchworm|bear_crawl|bear_plank|plank_shoulder|plank_reach|incline_plank|^plank$|side_plank|copenhagen|reverse_snow|prone_(y|t|w)|dead_bug|pike_hold/, "plank"],
  [/mountain/, "mountain"], [/burpee/, "burpee"], [/box_jump/, "box_jump"], [/jump_squat|skater|jumping_lunge|jump_rope|stair/, "jump"], [/jumping_jacks|shadow/, "jacks"],
  [/high_knees|marching/, "high_knees"], [/easy_jog|brisk_walk|monster_walk/, "walk"], [/stationary_bike/, "bike"], [/rowing_machine/, "rower"],
  [/wall_sit|deep_squat_hold/, "wall_sit"], [/pistol|cossack|sit_to_stand|box_squat/, "pistol"],
  [/leg_press|hack_squat|leg_extension|seated_leg_curl|lying_hamstring|hip_abduction|hip_adduction/, "leg_press"],
  [/goblet|dumbbell_squat|dumbbell_sumo|heel_elevated|dumbbell_front/, "squat_goblet"], [/front_squat/, "squat_front"], [/back_squat|pause_back|barbell_box/, "squat_back"],
  [/squat/, "squat"],
  [/kickback|donkey|fire_hydrant/, "kickback"], [/hip_thrust|single_leg_glute|glute_bridge|clamshell|side_lying/, "bridge"], [/swing/, "swing"], [/good_morning/, "good_morning"],
  [/barbell_(deadlift|sumo)/, "deadlift"], [/barbell_romanian|romanian|rdl|kettlebell_deadlift|dumbbell_deadlift|pull_through|wall_hip_hinge|back_extension|nordic/, "hinge"],
  [/step_up|step_down/, "step_up"], [/lateral_lunge|curtsy/, "side_lunge"], [/lunge|split_squat/, "lunge"],
  [/bench_dip/, "dip"], [/floor_press|bench_press|chest_press|incline_press/, "press_floor"], [/fly|rear_delt|face_pull|reverse_fly/, "fly"],
  [/lateral_raise|front_raise/, "raise"], [/overhead_press|shoulder_press|dumbbell_press|z_press|arnold|landmine_press|kettlebell_press|pike_push/, "press_overhead"],
  [/inverted_row|towel_door/, "row_inverted"], [/bent_over_row|pendlay|dumbbell_row|chest_supported/, "row_bent"], [/cable_row|machine_row|single_arm_cable_row/, "row_cable"], [/band_row|single_arm_band_row/, "row_band"],
  [/hanging_(knee|leg)/, "hang_raise"], [/dead_hang|scapular|negative/, "hang"], [/pull_up|chin_up/, "pullup"], [/pulldown/, "pulldown"],
  [/triceps_pushdown|rope_triceps|pushdown/, "pushdown"], [/triceps_extension|skullcrusher/, "triceps_ext"], [/curl|wrist/, "curl"], [/calf|tibialis/, "calf_raise"],
  [/lying_leg_raise|flutter|v_up|reverse_crunch|hollow/, "leg_raise"], [/crunch|russian|bicycle|side_bend|hip_dip/, "crunch"],
  [/carry/, "carry"], [/pallof|woodchop|chop|landmine_rotation|rotation|open_book|thread_the/, "rotation"],
  [/couch|hip_flexor|kneeling_hip/, "stretch_lunge"], [/cat_cow|childs|world_greatest|hip_90|hip_cars|frog|figure_four/, "mobility_floor"], [/superman|prone/, "superman"], [/bird_dog/, "bird_dog"],
  [/stretch|wall_slide|shoulder_cars|pass_through|dorsiflexion/, "stretch"],
];
const BY_PATTERN: Record<string, string> = { squat: "squat", hinge: "hinge", lunge: "lunge", push_horizontal: "pushup", push_vertical: "press_overhead", pull_horizontal: "row_bent", pull_vertical: "pulldown", core: "crunch", carry: "carry", rotation: "rotation", other: "stretch" };

/** Picks the animation template for an exercise (code like `goblet_squat`; falls back to the movement pattern). */
export function motionFor(code: string, pattern?: string): { template: Template; exact: boolean } {
  const c = code.toLowerCase();
  for (const [re, key] of RULES) if (re.test(c)) return { template: adaptProps(TEMPLATES[key], c), exact: true };
  return { template: TEMPLATES[(pattern && BY_PATTERN[pattern]) || "stretch"], exact: false };
}

/** The same motion with the implement the exercise name implies (bodyweight, dumbbell, kettlebell, barbell, band). */
function adaptProps(t: Template, code: string): Template {
  if (t.props.length === 0) return t;
  let props: Prop[] = [...t.props];
  const swap = (from: Prop, to: Prop | null) => { props = props.flatMap((p) => (p === from ? (to ? [to] : []) : [p])); };
  if (/kettlebell/.test(code)) swap("dumbbell", "kettlebell"); else if (/barbell/.test(code)) { swap("dumbbell", "barbell-hands"); }
  else if (/band/.test(code)) swap("dumbbell", "band-hands"); else if (/cable|machine/.test(code)) swap("dumbbell", "cable-hands");
  else if (!/dumbbell|goblet|farmer|suitcase|waiter|rack/.test(code) && props.includes("dumbbell")) swap("dumbbell", null);
  if (/bench|incline|seated|chest_supported|dip/.test(code) === false) props = props.filter((p) => p !== "bench-back" && p !== "bench-seat" || /hip_thrust|dip|press|fly/.test(code));
  return { ...t, props };
}

/** Joint-space bounds for fitting the figure into a viewBox. */
export function bounds(frames: readonly Pose[]): { minX: number; maxX: number; minY: number; maxY: number } {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const f of frames) for (let i = 0; i <= 16; i++) {
    const s = solve(blend(f, frames[(frames.indexOf(f) + 1) % frames.length], i / 16));
    for (const p of Object.values(s)) { minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]); minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]); }
  }
  return { minX, maxX, minY, maxY };
}
