// Dependency-free procedural 3D body: ellipsoid "muscle" parts, perspective projection, Lambert shading, painter's algorithm.
// Original geometry (no third-party model or license). Pure functions so the maths is unit-testable; drawing lives in the component.

export type Part = { region: string; c: [number, number, number]; r: [number, number, number]; mirror: boolean };
export type Tri = { x: [number, number, number]; y: [number, number, number]; depth: number; light: number; region: string };
export type Mesh = { regions: string[]; verts: Float32Array; norms: Float32Array; idx: Uint32Array; triRegion: Uint16Array };

// x right, y up (0..1.8 m), z toward the viewer at yaw 0. Muscles that sit on the back have negative z.
export const PARTS: readonly Part[] = [
  { region: "none", c: [0, 1.68, 0], r: [0.1, 0.12, 0.11], mirror: false },          // head
  { region: "neck", c: [0, 1.55, 0], r: [0.05, 0.07, 0.05], mirror: false },
  { region: "traps", c: [0, 1.5, -0.04], r: [0.15, 0.06, 0.07], mirror: false },
  { region: "none", c: [0, 1.3, 0], r: [0.15, 0.16, 0.08], mirror: false },           // rib cage fill
  { region: "chest", c: [0.09, 1.36, 0.07], r: [0.1, 0.08, 0.06], mirror: true },
  { region: "shoulders", c: [0.21, 1.43, 0], r: [0.075, 0.075, 0.075], mirror: true },
  { region: "biceps", c: [0.27, 1.27, 0.025], r: [0.045, 0.11, 0.045], mirror: true },
  { region: "triceps", c: [0.27, 1.27, -0.03], r: [0.045, 0.11, 0.04], mirror: true },
  { region: "forearms", c: [0.3, 1.05, 0], r: [0.038, 0.13, 0.038], mirror: true },
  { region: "none", c: [0.31, 0.88, 0], r: [0.03, 0.05, 0.02], mirror: true },        // hand
  { region: "abdominals", c: [0, 1.15, 0.06], r: [0.1, 0.14, 0.05], mirror: false },
  { region: "lats", c: [0.12, 1.3, -0.07], r: [0.1, 0.12, 0.045], mirror: true },
  { region: "middle back", c: [0, 1.28, -0.08], r: [0.07, 0.07, 0.04], mirror: false },
  { region: "lower back", c: [0, 1.08, -0.07], r: [0.09, 0.07, 0.04], mirror: false },
  { region: "none", c: [0, 0.97, 0], r: [0.15, 0.08, 0.09], mirror: false },          // pelvis
  { region: "glutes", c: [0.07, 0.93, -0.09], r: [0.08, 0.08, 0.07], mirror: true },
  { region: "quadriceps", c: [0.09, 0.68, 0.03], r: [0.07, 0.2, 0.065], mirror: true },
  { region: "hamstrings", c: [0.09, 0.68, -0.04], r: [0.065, 0.19, 0.055], mirror: true },
  { region: "adductors", c: [0.045, 0.72, 0], r: [0.035, 0.15, 0.04], mirror: true },
  { region: "none", c: [0.09, 0.46, 0], r: [0.045, 0.04, 0.045], mirror: true },     // knee
  { region: "calves", c: [0.09, 0.3, -0.02], r: [0.05, 0.13, 0.05], mirror: true },
  { region: "none", c: [0.09, 0.12, 0.03], r: [0.035, 0.1, 0.035], mirror: true },    // shin
  { region: "none", c: [0.09, 0.03, 0.06], r: [0.04, 0.03, 0.08], mirror: true },     // foot
];

export const BODY_REGIONS = Array.from(new Set(PARTS.map((p) => p.region).filter((r) => r !== "none")));

const LAT = 8, LON = 14;

export function buildMesh(parts: readonly Part[] = PARTS): Mesh {
  const regions: string[] = [];
  const verts: number[] = [], norms: number[] = [], idx: number[] = [], triRegion: number[] = [];
  const expanded = parts.flatMap((p) => (p.mirror ? [p, { ...p, c: [-p.c[0], p.c[1], p.c[2]] as [number, number, number] }] : [p]));
  for (const p of expanded) {
    let ri = regions.indexOf(p.region);
    if (ri < 0) { regions.push(p.region); ri = regions.length - 1; }
    const base = verts.length / 3;
    for (let i = 0; i <= LAT; i++) {
      const th = (i / LAT) * Math.PI;
      for (let j = 0; j <= LON; j++) {
        const ph = (j / LON) * Math.PI * 2;
        const ux = Math.sin(th) * Math.cos(ph), uy = Math.cos(th), uz = Math.sin(th) * Math.sin(ph);
        verts.push(p.c[0] + p.r[0] * ux, p.c[1] + p.r[1] * uy, p.c[2] + p.r[2] * uz);
        const nx = ux / p.r[0], ny = uy / p.r[1], nz = uz / p.r[2], l = Math.hypot(nx, ny, nz) || 1;
        norms.push(nx / l, ny / l, nz / l);
      }
    }
    for (let i = 0; i < LAT; i++) for (let j = 0; j < LON; j++) {
      const a = base + i * (LON + 1) + j, b = a + LON + 1;
      idx.push(a, b, a + 1, a + 1, b, b + 1);
      triRegion.push(ri, ri);
    }
  }
  return { regions, verts: Float32Array.from(verts), norms: Float32Array.from(norms), idx: Uint32Array.from(idx), triRegion: Uint16Array.from(triRegion) };
}

const LIGHT = (() => { const l = [-0.45, 0.6, 0.66]; const m = Math.hypot(l[0], l[1], l[2]); return l.map((v) => v / m) as [number, number, number]; })();

/** Project the mesh; returns only front-facing triangles, farthest first (draw in order). */
export function renderMesh(mesh: Mesh, o: { yaw: number; pitch: number; width: number; height: number }): Tri[] {
  const { verts, norms, idx, triRegion, regions } = mesh;
  const n = verts.length / 3;
  const cy = Math.cos(o.yaw), sy = Math.sin(o.yaw), cp = Math.cos(o.pitch), sp = Math.sin(o.pitch);
  const px = new Float32Array(n), py = new Float32Array(n), pz = new Float32Array(n), nl = new Float32Array(n);
  const D = 4.2, ppm = (0.9 * o.height) / 1.8;      // pixels per metre: the 1.8 m body fills 90% of the height
  for (let i = 0; i < n; i++) {
    let x = verts[i * 3], y = verts[i * 3 + 1] - 0.9, z = verts[i * 3 + 2];
    let x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    let y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    const f = D / (D - z2);
    px[i] = o.width / 2 + x1 * f * ppm; py[i] = o.height / 2 - y1 * f * ppm; pz[i] = z2;
    const nx = norms[i * 3], ny = norms[i * 3 + 1], nz = norms[i * 3 + 2];
    const nx1 = nx * cy + nz * sy, nz1 = -nx * sy + nz * cy;
    const ny1 = ny * cp - nz1 * sp, nz2 = ny * sp + nz1 * cp;
    nl[i] = Math.max(0, nx1 * LIGHT[0] + ny1 * LIGHT[1] + nz2 * LIGHT[2]);
  }
  const out: Tri[] = [];
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t], b = idx[t + 1], c = idx[t + 2];
    const cross = (px[b] - px[a]) * (py[c] - py[a]) - (py[b] - py[a]) * (px[c] - px[a]);
    if (cross >= 0) continue;                                    // back face (or degenerate pole triangle)
    out.push({ x: [px[a], px[b], px[c]], y: [py[a], py[b], py[c]], depth: (pz[a] + pz[b] + pz[c]) / 3, light: (nl[a] + nl[b] + nl[c]) / 3, region: regions[triRegion[t / 3]] });
  }
  out.sort((p, q) => p.depth - q.depth);                         // far (small z) first
  return out;
}

/** Region under a point: the nearest (last drawn) triangle containing it; null for background or an un-mapped part. */
export function pickRegion(tris: readonly Tri[], x: number, y: number): string | null {
  for (let i = tris.length - 1; i >= 0; i--) {
    const t = tris[i];
    const d1 = (x - t.x[1]) * (t.y[0] - t.y[1]) - (t.x[0] - t.x[1]) * (y - t.y[1]);
    const d2 = (x - t.x[2]) * (t.y[1] - t.y[2]) - (t.x[1] - t.x[2]) * (y - t.y[2]);
    const d3 = (x - t.x[0]) * (t.y[2] - t.y[0]) - (t.x[2] - t.x[0]) * (y - t.y[0]);
    if (!((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0))) return t.region === "none" ? null : t.region;
  }
  return null;
}

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.trim().replace("#", "");
  const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const v = Number.parseInt(f.padEnd(6, "0").slice(0, 6), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

/** Lambert-style shading of a base colour: ambient + diffuse, clamped. */
export function shade(rgb: readonly [number, number, number], light: number): string {
  const k = 0.38 + 0.82 * light;
  const c = rgb.map((v) => Math.max(0, Math.min(255, Math.round(v * k))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
