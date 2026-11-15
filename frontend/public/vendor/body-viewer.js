// VitaForge anatomical body viewer (our own code; uses vendored three.js r170, MIT).
// Model: public/vendor/anatomy/anatomy.glb, derived from Z-Anatomy / BodyParts3D, CC BY-SA 4.0 (see NOTICE.txt). Every muscle mesh carries
// userData { kind, label, side, group }; `group` uses the free-exercise-db muscle vocabulary that the exercise catalogue also uses.
// Exposes window.VFBody.create(canvas, options) once loaded; dispatches "vfbody:ready" on window.
import * as THREE from "./three/three.module.min.js";
import { GLTFLoader } from "./three/GLTFLoader.js";
import { DRACOLoader } from "./three/DRACOLoader.js";
import { RoomEnvironment } from "./three/RoomEnvironment.js";

const MODEL_URL = "/vendor/anatomy/anatomy.glb";
const ALIAS = { abductors: "glutes" };           // statuses given for one group also colour its alias

let modelPromise = null;
function loadModel() {
  if (!modelPromise) {
    modelPromise = new Promise((resolve, reject) => {
      const draco = new DRACOLoader();
      draco.setDecoderPath("/vendor/draco/");
      const loader = new GLTFLoader();
      loader.setDRACOLoader(draco);
      loader.load(MODEL_URL, (g) => resolve(g.scene), undefined, reject);
    });
  }
  return modelPromise;
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const ease = (t) => 1 - Math.pow(1 - t, 3);

function create(canvas, options = {}) {
  const opts = { onPick() {}, onHover() {}, onReady() {}, onError() {}, ...options };
  const reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch (e) {
    opts.onError(e);
    return null;
  }
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.localClippingEnabled = true;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.55;
  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 30);
  const key = new THREE.DirectionalLight(0xfff1e2, 2.6); key.position.set(-1.4, 2.4, 2.2);
  const rim = new THREE.DirectionalLight(0x78a8ff, 2.4); rim.position.set(2.2, 1.4, -2.4);
  const kick = new THREE.DirectionalLight(0xffb27a, 0.9); kick.position.set(1.8, 0.2, 1.4);
  scene.add(key, rim, kick, new THREE.HemisphereLight(0x9db2cf, 0x2a1d18, 0.55));

  const rig = new THREE.Group();            // the body turns inside a fixed lighting rig, like a studio turntable
  scene.add(rig);

  const palette = { base: "#8f3d33", low: "#4f8fd6", ok: "#3fae7a", high: "#e0a23a", focus: "#ff5a1f", bone: "#e7dfcf", glow: "#ff5a1f" };
  const state = {
    yaw: 0.5, pitch: 0.06, vyaw: 0, targetYaw: null, dist: 3.4, targetDist: 3.4, auto: !reduce, drag: false, moved: 0, lastX: 0, lastY: 0,
    status: {}, selected: null, hover: null, bones: false, ready: false, alive: true, visible: true, t0: performance.now(), scan: 0,
  };
  const groups = new Map();                  // group -> { mats: Material, meshes: Mesh[], center: Vector3, color: Color, target: Color, glow: number }
  const meshes = [];
  const clip = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0);
  let scanRing = null, floorGlow = null, head = null, bonesMat = null;

  function groupOf(name) { return ALIAS[name] ?? name; }
  function entry(name) { return groups.get(groupOf(name)) ?? null; }

  function applyPalette() {
    for (const [name, g] of groups) {
      const st = state.status[name] ?? (name === "glutes" ? state.status.abductors : undefined);
      const sel = state.selected === name;
      const anyFocus = Object.values(state.status).includes("focus");
      const col = new THREE.Color(sel ? palette.focus : st ? palette[st] : palette.base);
      if (!st && !sel && anyFocus) col.lerp(new THREE.Color(palette.dim ?? "#241c19"), 0.45);   // dim the rest so the target reads at a glance
      g.target.copy(col);
      g.glowTarget = sel || st === "focus" ? 1 : st ? 0.18 : 0;
    }
    if (floorGlow) floorGlow.material.color.set(palette.glow);
    if (scanRing) scanRing.material.color.set(palette.glow);
    if (bonesMat) bonesMat.color.set(palette.bone);
    if (head) head.material.color.set(palette.head ?? "#2b2522");
  }

  function build(root) {
    const model = root.clone(true);
    model.updateMatrixWorld(true);
    model.traverse((o) => {
      if (!o.isMesh) return;
      const { kind, group } = o.userData;
      if (kind === "muscle" && group) {
        let g = groups.get(group);
        if (!g) {
          const mat = new THREE.MeshPhysicalMaterial({ color: palette.base, roughness: 0.44, metalness: 0, clearcoat: 0.45, clearcoatRoughness: 0.42, sheen: 0.7,
            sheenColor: new THREE.Color("#ffb7a3"), sheenRoughness: 0.5, emissive: new THREE.Color(palette.glow), emissiveIntensity: 0, clippingPlanes: [clip] });
          g = { mat, meshes: [], box: new THREE.Box3(), color: new THREE.Color(palette.base), target: new THREE.Color(palette.base), glow: 0, glowTarget: 0, tris: 0, zsum: 0 };
          groups.set(group, g);
        }
        o.material = g.mat; g.meshes.push(o); meshes.push(o);
        const b = new THREE.Box3().setFromObject(o); g.box.union(b);
        const tr = (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
        g.tris += tr; g.zsum += ((b.min.z + b.max.z) / 2) * tr;
        o.visible = true;
      } else if (kind === "bone") {
        bonesMat ??= new THREE.MeshStandardMaterial({ color: palette.bone, roughness: 0.55, transparent: true, opacity: 0.32, depthWrite: false, clippingPlanes: [clip] });
        o.material = bonesMat; o.visible = false; o.userData.isBone = true; o.renderOrder = 2;
      } else if (kind === "muscle") {          // ungrouped (face / scalp / feet): drawn, not selectable
        o.material = new THREE.MeshStandardMaterial({ color: "#6e3a33", roughness: 0.6, clippingPlanes: [clip] });
      } else {
        o.visible = false;
      }
    });
    rig.add(model);
    for (const g of groups.values()) g.center = g.box.getCenter(new THREE.Vector3());
    // mannequin head: the source model has no skin/face, so a faceless satin head is fitted around the skull bones to keep the figure readable as a person
    const sk = new THREE.Box3();
    model.traverse((o) => { if (o.isMesh && /^\(?(Frontal_bone|Parietal_bone|Occipital_bone|Temporal_bone|Mandible|Maxilla|Zygomatic_bone|Nasal_bone|Sphenoid_bone)/i.test(o.name)) sk.union(new THREE.Box3().setFromObject(o)); });
    if (sk.isEmpty()) sk.set(new THREE.Vector3(-0.08, 1.6, -0.09), new THREE.Vector3(0.08, 1.8, 0.1));
    const sc = sk.getCenter(new THREE.Vector3()), ss = sk.getSize(new THREE.Vector3());
    head = new THREE.Mesh(new THREE.SphereGeometry(1, 56, 40), new THREE.MeshPhysicalMaterial({ color: palette.head ?? "#2b2522", roughness: 0.3, clearcoat: 0.8, clearcoatRoughness: 0.25, clippingPlanes: [clip] }));
    head.scale.set(ss.x * 0.62, ss.y * 0.6, ss.z * 0.58); head.position.set(sc.x, sc.y + ss.y * 0.04, sc.z - ss.z * 0.02); rig.add(head);
    state.top = sk.max.y + 0.01;
    // contact shadow + accent ring on the floor, and the scan ring used by the intro
    const tex = (() => { const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d"); const gr = x.createRadialGradient(64, 64, 4, 64, 64, 62);
      gr.addColorStop(0, "rgba(0,0,0,0.55)"); gr.addColorStop(1, "rgba(0,0,0,0)"); x.fillStyle = gr; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c); })();
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 1.5), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.002; scene.add(shadow);
    floorGlow = new THREE.Mesh(new THREE.RingGeometry(0.36, 0.385, 96), new THREE.MeshBasicMaterial({ color: palette.glow, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false }));
    floorGlow.rotation.x = -Math.PI / 2; floorGlow.position.y = 0.004; scene.add(floorGlow);
    scanRing = new THREE.Mesh(new THREE.RingGeometry(0.2, 0.3, 64), new THREE.MeshBasicMaterial({ color: palette.glow, transparent: true, opacity: 0.8, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
    scanRing.rotation.x = -Math.PI / 2; scene.add(scanRing);
    state.ready = true;
    state.t0 = performance.now();
    applyPalette();
    for (const g of groups.values()) { g.color.copy(g.target); g.mat.color.copy(g.color); }
    opts.onReady();
  }

  // ---- input -------------------------------------------------------------------------------------------------------------------------
  const pointers = new Map();
  let pinch = 0;
  const ray = new THREE.Raycaster(); const ndc = new THREE.Vector2();
  function pickAt(clientX, clientY) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(meshes, false).find((h) => h.object.visible);
    if (!hit) return null;
    const u = hit.object.userData;
    return { group: u.group, label: u.label, side: u.side };
  }
  canvas.style.touchAction = "pan-y";
  canvas.addEventListener("pointerdown", (e) => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    canvas.setPointerCapture(e.pointerId);
    state.drag = true; state.auto = false; state.moved = 0; state.vyaw = 0; state.targetYaw = null;
    state.lastX = e.clientX; state.lastY = e.clientY;
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
  });
  canvas.addEventListener("pointermove", (e) => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (state.drag) {
      if (pointers.size >= 2) {
        const [a, b] = [...pointers.values()]; const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) state.targetDist = clamp(state.targetDist * (pinch / d), 1.5, 4.8); pinch = d; return;
      }
      const dx = e.clientX - state.lastX, dy = e.clientY - state.lastY;
      state.moved += Math.abs(dx) + Math.abs(dy); state.lastX = e.clientX; state.lastY = e.clientY;
      state.yaw += dx * 0.011; state.vyaw = dx * 0.011; state.pitch = clamp(state.pitch + dy * 0.004, -0.35, 0.5);
    } else if (e.pointerType === "mouse") {
      hoverReq = [e.clientX, e.clientY];
    }
  });
  const end = (e) => {
    pointers.delete(e.pointerId); pinch = 0;
    if (pointers.size === 0 && state.drag) {
      state.drag = false;
      if (state.moved < 6) { const p = pickAt(e.clientX, e.clientY); opts.onPick(p); }
    }
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", (e) => { pointers.delete(e.pointerId); state.drag = pointers.size > 0; });
  canvas.addEventListener("pointerleave", () => { hoverReq = null; setHover(null); });
  canvas.addEventListener("wheel", (e) => { if (!e.ctrlKey && !e.metaKey) return; e.preventDefault(); state.targetDist = clamp(state.targetDist * (1 + e.deltaY * 0.0012), 1.5, 4.8); }, { passive: false });
  canvas.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") { state.yaw -= 0.25; state.auto = false; e.preventDefault(); }
    else if (e.key === "ArrowRight") { state.yaw += 0.25; state.auto = false; e.preventDefault(); }
    else if (e.key === "ArrowUp") { state.targetDist = clamp(state.targetDist - 0.3, 1.5, 4.8); e.preventDefault(); }
    else if (e.key === "ArrowDown") { state.targetDist = clamp(state.targetDist + 0.3, 1.5, 4.8); e.preventDefault(); }
  });
  let hoverReq = null, hoverKey = "";
  function setHover(p) {
    const k = p ? `${p.group}|${p.label}|${p.side}` : "";
    if (k === hoverKey) return;
    hoverKey = k; state.hover = p?.group ?? null; opts.onHover(p); applyPalette();
  }

  // ---- loop --------------------------------------------------------------------------------------------------------------------------
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth || 300, h = canvas.clientHeight || 400;
    renderer.setPixelRatio(dpr); renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  const ro = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null; ro?.observe(canvas);
  const io = typeof IntersectionObserver === "function" ? new IntersectionObserver((en) => { state.visible = en[0]?.isIntersecting ?? true; }) : null; io?.observe(canvas);
  resize();

  let raf = 0, last = performance.now();
  const tmp = new THREE.Color();
  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (!state.alive || !state.visible || document.hidden) { last = now; return; }
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (!state.ready) return;
    if (!state.drag) {
      if (state.targetYaw !== null) {
        let d = state.targetYaw - state.yaw; d = Math.atan2(Math.sin(d), Math.cos(d));
        state.yaw += d * Math.min(1, dt * 6); if (Math.abs(d) < 0.002) state.targetYaw = null;
      } else if (Math.abs(state.vyaw) > 0.0004) { state.yaw += state.vyaw; state.vyaw *= 0.94; }
      else if (state.auto) state.yaw += dt * 0.35;
    }
    state.dist += (state.targetDist - state.dist) * Math.min(1, dt * 7);
    const hgt = (state.top ?? 1.85) + 0.06, fit = (0.5 * hgt * 1.1) / Math.tan((camera.fov * Math.PI) / 360);
    const dist = Math.max(fit * (camera.aspect < 0.5 ? 0.5 / camera.aspect : 1), 1.2) * (state.dist / 3.4);
    rig.rotation.y = state.yaw;
    const cy = (state.top ?? 1.85) / 2;
    camera.position.set(0, cy + 0.12 + Math.sin(state.pitch) * dist * 0.5, Math.cos(state.pitch) * dist);
    camera.lookAt(0, cy, 0);
    if (hoverReq && !state.drag) { const p = pickAt(hoverReq[0], hoverReq[1]); hoverReq = null; setHover(p); }
    // intro scan: a ring sweeps up and reveals the body
    const since = (performance.now() - state.t0) / 1000;
    const scanning = !reduce && since < 1.6;
    clip.constant = scanning ? ease(since / 1.6) * 2.0 : 5;
    scanRing.visible = scanning; if (scanning) { scanRing.position.y = clip.constant; scanRing.scale.setScalar(1 + Math.sin(since * 9) * 0.04); }
    floorGlow.material.opacity = 0.35 + 0.2 * Math.sin(now * 0.002);
    const tt = now / 1000;
    for (const [name, g] of groups) {
      g.color.lerp(g.target, Math.min(1, dt * 7));
      g.glow += (g.glowTarget - g.glow) * Math.min(1, dt * 6);
      tmp.copy(g.color);
      const hov = state.hover && groupOf(state.hover) === name;
      if (hov) tmp.offsetHSL(0, 0.05, 0.1);
      g.mat.color.copy(tmp);
      g.mat.emissive.copy(g.color);
      g.mat.emissiveIntensity = g.glow * (0.18 + 0.14 * Math.sin(tt * 3.1)) + (hov ? 0.18 : 0);
    }
    renderer.render(scene, camera);
  }
  raf = requestAnimationFrame(frame);

  loadModel().then((root) => { if (state.alive) { build(root); } }).catch((e) => opts.onError(e));

  const api = {
    setPalette(p) { Object.assign(palette, p); applyPalette(); },
    setStatus(map) { state.status = { ...map }; applyPalette(); },
    setSelected(g) { state.selected = g; applyPalette(); },
    setView(view) { state.auto = false; state.vyaw = 0; state.targetYaw = { front: 0, back: Math.PI, left: -Math.PI / 2, right: Math.PI / 2 }[view] ?? 0; state.pitch = 0.06; },
    /** Turn to the side the given groups are mostly on. */
    faceGroups(names) {
      let z = 0, n = 0;
      for (const nm of names) { const g = entry(nm); if (g) { z += g.zsum / Math.max(1, g.tris); n++; } }
      if (n) { state.auto = false; state.targetYaw = z / n < -0.01 ? Math.PI : 0; }
    },
    setAutoRotate(v) { state.auto = !!v && !reduce; },
    setBones(v) { state.bones = !!v; rig.traverse((o) => { if (o.userData?.isBone) o.visible = state.bones; }); },
    zoom(f) { state.targetDist = clamp(state.targetDist * f, 1.5, 4.8); },
    groupsPresent() { return [...groups.keys()]; },
    resize,
    dispose() {
      state.alive = false; cancelAnimationFrame(raf); ro?.disconnect(); io?.disconnect();
      for (const g of groups.values()) g.mat.dispose();
      envRT.dispose(); pmrem.dispose(); renderer.dispose(); renderer.forceContextLoss();
    },
  };
  return api;
}

window.VFBody = { create, preload: loadModel };
window.dispatchEvent(new Event("vfbody:ready"));
