// VitaForge exercise figure viewer (our own code; vendored three.js r170, MIT).
// Character: "Mannequin" from the Mesh2Motion / Quaternius Universal Animation Library, CC0 (see NOTICE.txt). public/vendor/anatomy/figure.glb holds the
// skinned mesh plus five CC0 clips (Jog, Sprint, Walk, Jumping Jacks, Pushup). Every other exercise is driven by our own sagittal-plane IK solver
// (src/lib/motion.ts): the solved 2D joints are retargeted onto the mannequin bones, so one rig performs all movements.
// Exposes window.VFFigure.create(canvas, options); dispatches "vffigure:ready" on window.
import * as THREE from "./three/three.module.min.js";
import { GLTFLoader } from "./three/GLTFLoader.js";
import { RoomEnvironment } from "./three/RoomEnvironment.js";

const URL_ = "/vendor/anatomy/figure.glb";
const K = 0.00754;                                   // figure units (motion.ts) -> metres
const REGIONS = ["quadriceps", "hamstrings", "glutes", "calves", "chest", "abdominals", "lower back", "middle back", "lats", "traps", "shoulders", "biceps", "triceps", "forearms", "adductors"];
const ALIAS = { "middle back": "middle back", traps: "traps" };

let gltfPromise = null;
const load = () => (gltfPromise ||= new Promise((res, rej) => new GLTFLoader().load(URL_, res, undefined, rej)));

const css = (name, fb) => { const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); return v || fb; };

function create(canvas, options = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(2, 4, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0xffa070, 1.4); rim.position.set(-3, 2, -3); scene.add(rim);
  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 50);
  const stage = new THREE.Group(); scene.add(stage);

  const floorMat = new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.2, side: THREE.DoubleSide });
  const floor = new THREE.Mesh(new THREE.CircleGeometry(1.0, 64), floorMat); floor.rotation.x = -Math.PI / 2; floor.position.y = 0.002; stage.add(floor);
  const floorRing = new THREE.Mesh(new THREE.RingGeometry(0.98, 1.0, 96), new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.7, side: THREE.DoubleSide }));
  floorRing.rotation.x = -Math.PI / 2; floorRing.position.y = 0.004; stage.add(floorRing);

  const S = { model: null, bones: {}, rest: {}, mixer: null, actions: {}, clip: null, fwd: new THREE.Vector3(), lat: new THREE.Vector3(), nearSide: "l", farSide: "r",
    props: new THREE.Group(), frame: { cx: 0, cy: 1, h: 2.2 }, ground: true, hang: false, targets: [], uOn: new Float32Array(16), disposed: false, yaw: 0.5, drag: false, last: null, clock: new THREE.Clock(), t: 0, autoYaw: true };
  stage.add(S.props);

  const resize = () => {
    const w = canvas.clientWidth || 300, h = canvas.clientHeight || 300;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); place();
  };

  function place() {
    const { cx, cy, h } = S.frame;
    const dist = (h / 2) / Math.tan((camera.fov * Math.PI) / 360) * Math.max(1.15, 1 / Math.min(camera.aspect, 1.6));
    const a = S.yaw;
    camera.position.set(Math.sin(a) * dist * 0.35 + 0, cy + 0.15, dist);
    // the stage is rotated so +fwd faces screen right; yaw swings the view a little for depth
    stage.rotation.y = 0; camera.position.set(Math.sin(a) * dist, cy + h * 0.04, Math.cos(a) * dist);
    camera.lookAt(cx, cy, 0);
  }

  function init(gltf) {
    const model = gltf.scene; S.model = model;
    model.traverse((o) => { if (o.isBone) S.bones[o.name] = o; });
    model.updateMatrixWorld(true);
    const wp = (n) => S.bones[n].getWorldPosition(new THREE.Vector3());
    // forward = foot -> ball direction projected to the ground plane; lateral = right thigh -> left thigh
    S.fwd.copy(wp("ball_l")).sub(wp("foot_l")); S.fwd.y = 0; S.fwd.normalize();
    S.lat.copy(wp("thigh_l")).sub(wp("thigh_r")); S.lat.y = 0; S.lat.normalize();
    // we look from the side whose screen-right equals fwd: right = view x up with view = -sideDir
    const up = new THREE.Vector3(0, 1, 0);
    const right = (side) => new THREE.Vector3().crossVectors(side.clone().negate(), up);
    S.camSide = right(S.lat).dot(S.fwd) > 0 ? S.lat.clone() : S.lat.clone().negate();
    S.nearSide = S.camSide.dot(S.lat) > 0 ? "l" : "r"; S.farSide = S.nearSide === "l" ? "r" : "l";
    // rotate the whole model so that fwd -> +X, lateral(cam side) -> +Z (camera sits on +Z)
    const m = new THREE.Matrix4().makeBasis(S.fwd, up, S.camSide).transpose();      // world -> stage basis
    model.applyMatrix4(m); model.updateMatrixWorld(true);
    S.fwd.set(1, 0, 0); S.lat.set(0, 0, 1);
    for (const n of Object.keys(S.bones)) { const b = S.bones[n]; S.rest[n] = { q: b.quaternion.clone(), p: b.position.clone(), wq: b.getWorldQuaternion(new THREE.Quaternion()), wp: b.getWorldPosition(new THREE.Vector3()) }; }
    stage.add(model);
    // materials + muscle regions
    const mesh = model.getObjectByProperty("isSkinnedMesh", true);
    S.mesh = mesh; mesh.frustumCulled = false;
    const mat = new THREE.MeshStandardMaterial({ map: mesh.material.map, roughness: 0.55, metalness: 0.05, color: new THREE.Color(0xd9d4cf) });
    S.hi = new THREE.Color(css("--body-focus", "#ff5a1f"));
    const uni = { uOn: { value: S.uOn }, uHi: { value: S.hi }, uPulse: { value: 1 } };
    mat.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, uni);
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nattribute float aReg;\nvarying float vReg;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvReg = aReg;");
      sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nuniform float uOn[16];\nuniform vec3 uHi;\nuniform float uPulse;\nvarying float vReg;")
        .replace("#include <color_fragment>", "#include <color_fragment>\nfloat mk = uOn[int(vReg + 0.5)];\ndiffuseColor.rgb = mix(diffuseColor.rgb, uHi, 0.78 * mk);")
        .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += uHi * mk * (0.35 + 0.35 * uPulse);");
    };
    mesh.material = mat; S.uni = uni;
    buildRegions(mesh);
    // clips
    S.mixer = new THREE.AnimationMixer(model);
    for (const c of gltf.animations) S.actions[c.name] = S.mixer.clipAction(c);
    restPose();
    options.onReady && options.onReady(api);
  }

  const bn = (n) => S.bones[n];
  function restPose() { for (const n in S.rest) { S.bones[n].position.copy(S.rest[n].p); S.bones[n].quaternion.copy(S.rest[n].q); } S.model.updateMatrixWorld(true); }

  function buildRegions(mesh) {
    const g = mesh.geometry, pos = g.attributes.position, nor = g.attributes.normal, jn = g.attributes.skinIndex, wt = g.attributes.skinWeight;
    const names = mesh.skeleton.bones.map((b) => b.name);
    const reg = new Float32Array(pos.count), v = new THREE.Vector3();
    mesh.updateMatrixWorld(true);
    const bindPose = (i) => { v.fromBufferAttribute(pos, i).applyMatrix4(mesh.bindMatrix ?? new THREE.Matrix4()); return v; };
    for (let i = 0; i < pos.count; i++) {
      let bi = 0, bw = -1;
      for (let k = 0; k < 4; k++) { const w = wt.getComponent(i, k); if (w > bw) { bw = w; bi = jn.getComponent(i, k); } }
      const name = names[bi] || "";
      // position relative to the dominant bone, in stage space (rest pose)
      const p = new THREE.Vector3().fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
      const bp = S.rest[name]?.wp ?? new THREE.Vector3();
      const front = p.x - bp.x > 0;                      // fwd is +X in stage space
      const side = Math.abs(p.z - (S.rest.pelvis?.wp.z ?? 0));
      const hy = p.y;
      let r = -1;
      if (/^thigh_/.test(name)) r = front ? 0 : 1;
      else if (/^calf_/.test(name)) r = front ? -1 : 3;
      else if (name === "pelvis") r = front ? 5 : 2;
      else if (name === "spine_01") r = front ? 5 : 6;
      else if (name === "spine_02") r = front ? 5 : (side > 0.13 ? 8 : 7);
      else if (name === "spine_03") r = front ? 4 : (side > 0.17 ? 8 : 7);
      else if (/^(neck_01|clavicle_)/.test(name)) r = front ? -1 : 9;
      else if (/^upperarm_/.test(name)) { const top = hy > (S.rest[name].wp.y - 0.05) && front === false ? true : false; r = hy > S.rest[name].wp.y - 0.07 ? 10 : (front ? 11 : 12); void top; }
      else if (/^(lowerarm_|hand_)/.test(name)) r = 13;
      reg[i] = r < 0 ? 15 : r;
    }
    g.setAttribute("aReg", new THREE.BufferAttribute(reg, 1));
  }

  function setTargets(list) {
    S.uOn.fill(0);
    for (const r of list || []) { const i = REGIONS.indexOf(ALIAS[r] ?? r); if (i >= 0) S.uOn[i] = 1; if (r === "adductors") S.uOn[0] = 1; }
  }

  const V = (x, y, z = 0) => new THREE.Vector3(x * K, y * K, z);
  const dirOf = (a, b) => new THREE.Vector3(b[0] - a[0], b[1] - a[1], 0).normalize();

  // Rotate `bone` so that its rest direction to `child` points along `target` (stage space). Parents must already be posed.
  function aim(boneName, childName, target) {
    const b = bn(boneName), c = bn(childName); if (!b || !c) return;
    const r = S.rest[boneName], rc = S.rest[childName];
    const restDir = rc.wp.clone().sub(r.wp).normalize();
    const delta = new THREE.Quaternion().setFromUnitVectors(restDir, target);
    const want = delta.multiply(r.wq);
    const parentQ = b.parent.getWorldQuaternion(new THREE.Quaternion());
    b.quaternion.copy(parentQ.invert().multiply(want));
    b.updateMatrixWorld(true);
  }

  /** Pose from a solved 2D skeleton (figure units, x forward, y up). */
  function setSolved(sk, opts = {}) {
    if (!S.model) return;
    if (S.clip) stopClip();
    restPose();
    const n = S.nearSide, f = S.farSide;
    const torso = dirOf(sk.hip, sk.shoulder);
    const pel = bn("pelvis"), rp = S.rest.pelvis;
    // pelvis: align rest torso axis (pelvis -> spine_03) to the torso direction, then place at hip
    const restTorso = S.rest.spine_03.wp.clone().sub(rp.wp).normalize();
    const dq = new THREE.Quaternion().setFromUnitVectors(restTorso, torso);
    const parentQ = pel.parent.getWorldQuaternion(new THREE.Quaternion());
    pel.quaternion.copy(parentQ.invert().multiply(dq.multiply(rp.wq)));
    const hip = V(sk.hip[0], sk.hip[1]);
    const pw = pel.parent.worldToLocal(hip.clone());
    pel.position.copy(pw);
    pel.updateMatrixWorld(true);
    const leg = (s, knee, ankle, toe) => {
      aim(`thigh_${s}`, `calf_${s}`, dirOf(sk.hip, knee));
      aim(`calf_${s}`, `foot_${s}`, dirOf(knee, ankle));
      aim(`foot_${s}`, `ball_${s}`, new THREE.Vector3(toe[0] - ankle[0], toe[1] - ankle[1] - 3, 0).normalize());
    };
    leg(n, sk.kneeA, sk.ankleA, sk.toeA); leg(f, sk.kneeB, sk.ankleB, sk.toeB);
    const arm = (s, elbow, hand) => {
      aim(`upperarm_${s}`, `lowerarm_${s}`, dirOf(sk.shoulder, elbow));
      aim(`lowerarm_${s}`, `hand_${s}`, dirOf(elbow, hand));
    };
    arm(n, sk.elbowA, sk.handA); arm(f, sk.elbowB, sk.handB);
    // fingers: closed around a held prop (dumbbell, bar, handle, cable), softly curled otherwise
    const grip = S.grip ?? 0.3;
    if (grip > 0) {
      const FING = { index: [1.15, 1.5, 0.9], middle: [1.2, 1.55, 0.9], ring: [1.25, 1.55, 0.9], pinky: [1.3, 1.5, 0.85] };
      for (const sd of [n, f]) {
        for (const [fg, ang] of Object.entries(FING)) ang.forEach((a, k) => { const b = bn(`${fg}_0${k + 1}_${sd}`); if (b) b.rotateZ(GRIP_SIGN * a * grip); });
        const t1 = bn(`thumb_02_${sd}`), t2 = bn(`thumb_03_${sd}`);
        if (t1) t1.rotateZ(GRIP_SIGN * 0.7 * grip); if (t2) t2.rotateZ(GRIP_SIGN * 0.8 * grip);
        bn(`hand_${sd}`)?.updateMatrixWorld(true);
      }
    }
    // head follows the neck direction
    aim("neck_01", "head", dirOf(sk.neck, sk.head));
    S.model.updateMatrixWorld(true);
    // keep the lowest support point on the floor
    let lift = 0;
    if (S.ground && !S.hang) {
      // lowest support point rests on whatever is under it: the floor, or the box top where a foot is over the box
      let need = -Infinity; const v3 = new THREE.Vector3();
      for (const nm of ["ball_l", "ball_r", "ball_leaf_l", "ball_leaf_r", "foot_l", "foot_r", "hand_l", "hand_r", "calf_l", "calf_r"]) {
        bn(nm).getWorldPosition(v3);
        const under = S.box && /ball|foot/.test(nm) && Math.abs(v3.x - S.box.x * K) < (S.box.w ?? 0.5) / 2 + 0.02 ? S.box.h * K : 0;
        need = Math.max(need, under - (v3.y - (/ball|foot/.test(nm) ? 0.02 : 0.045)));
      }
      const lift0 = need;
      lift = S.box ? Math.max(0, lift0) : lift0;
      if (Math.abs(lift) < 0.25) { S.model.position.y = lift; S.model.updateMatrixWorld(true); }
    } else S.model.position.y = 0;
    S.pose = sk; updateProps(sk, lift);
    S.dirty = true;
  }

  // ---------------------------------------------------------------- props (3D primitives)
  const matMetal = new THREE.MeshStandardMaterial({ color: 0x8e9aa6, metalness: 0.8, roughness: 0.3 });
  const matPlate = new THREE.MeshStandardMaterial({ color: 0x23272b, metalness: 0.4, roughness: 0.5 });
  const matWood = new THREE.MeshStandardMaterial({ color: 0x3b3f45, roughness: 0.8 });
  const matBand = new THREE.LineBasicMaterial({ color: 0xe0a23a });
  function clearProps() { while (S.props.children.length) { const o = S.props.children.pop(); o.geometry?.dispose?.(); } }
  function lat(len, r, mat) { const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 20), mat); m.rotation.x = Math.PI / 2; return m; }
  function plate(r, w, z) { const m = lat(w, r, matPlate); m.position.z = z; return m; }
  const GRIP_SIGN = 1;
  // Test hook: names of body bones that sit inside a solid prop (box, seat, bench, wall); skin tolerance keeps resting contact legal.
  function collisions() {
    S.model.updateMatrixWorld(true); S.props.updateMatrixWorld(true);
    const out = [], v = new THREE.Vector3();
    const rad = (nm) => /spine|pelvis|neck|head|thigh|upperarm|clavicle/.test(nm) ? (/spine|pelvis/.test(nm) ? 0.085 : /neck|upperarm|clavicle/.test(nm) ? 0.03 : 0.05) : /finger|index|middle|ring|pinky|thumb|leaf/.test(nm) ? 0.01 : 0.035;
    for (const o of S.props.children) {
      if (!o.geometry || o.geometry.type !== "BoxGeometry" || o.userData.noCheck) continue;
      const base = new THREE.Box3().setFromObject(o);
      for (const [nm, b] of Object.entries(S.bones)) {
        if (/^(root|ik_)|index|middle|ring|pinky|thumb/.test(nm)) continue;
        b.getWorldPosition(v); const r = rad(nm) - 0.012;
        const bx = base.clone().expandByScalar(r);
        if (bx.containsPoint(v) && Math.min(bx.max.y - v.y, v.y - bx.min.y, v.x - bx.min.x, bx.max.x - v.x) > 0.012) out.push(nm + ":dy" + Math.round((bx.max.y - v.y) * 100) + "/dx" + Math.round(Math.min(v.x - bx.min.x, bx.max.x - v.x) * 100));
      }
    }
    return out;
  }
  // Place the box from the rig itself (not the stick skeleton): at the given solved frame its top meets the sole of the supporting
  // foot/feet and it spans heel..toe, so the feet stand on it instead of inside it.
  function calibrateBox(sk, feet) {
    const g = S.ground; S.ground = false; S.box = null; setSolved(sk); S.ground = g;
    const P = (n) => bn(n).getWorldPosition(new THREE.Vector3());
    const sides = ["l", "r"].map((d) => ({ heel: P(`foot_${d}`), ball: P(`ball_${d}`), toe: P(`ball_leaf_${d}`) }));
    const use = feet === "both" ? sides : [sides.sort((a, b) => b.ball.y - a.ball.y)[0]];
    const x0 = Math.min(...use.map((s2) => Math.min(s2.heel.x, s2.toe.x))) - 0.05, x1 = Math.max(...use.map((s2) => Math.max(s2.heel.x, s2.toe.x))) + 0.05;
    const top = Math.min(...use.map((s2) => Math.min(s2.ball.y, s2.toe.y))) - 0.02;
    S.box = { x: (x0 + x1) / 2 / K, w: x1 - x0, h: Math.max(0.1, top) / K };
  }
  function setBox(b) { S.box = b || null; }
  function setProps(list) { S.propList = list || []; clearProps(); S.grip = S.propList.some((p) => /^(dumbbell|kettlebell|barbell|bar-hang|band-hands|cable-hands)/.test(p)) ? 1 : 0.3; }
  function updateProps(sk, lift) {
    clearProps();
    const add = (o, x, y, z = 0) => { o.position.set(x * K, y * K + lift, z); S.props.add(o); return o; };
    const hand = sk.handA;
    // centre of the closed fist in world space (already includes the floor lift): props are placed here so the grip really holds them
    const fist = (sd) => { const a = bn(`hand_${sd}`).getWorldPosition(new THREE.Vector3()), b = bn(`middle_02_${sd}`).getWorldPosition(new THREE.Vector3()); return a.add(b).multiplyScalar(0.5); };
    const fA = fist("l"), fB = fist("r");
    for (const p of S.propList || []) {
      if (p === "dumbbell") for (const f of [fA, fB]) { const g = new THREE.Group(); g.add(lat(0.16, 0.012, matMetal)); g.add(plate(0.05, 0.03, 0.07)); g.add(plate(0.05, 0.03, -0.07)); g.position.copy(f); S.props.add(g); }
      else if (p === "kettlebell") { const g = new THREE.Group(); g.add(new THREE.Mesh(new THREE.SphereGeometry(0.09, 24, 16), matPlate)); const t = new THREE.Mesh(new THREE.TorusGeometry(0.055, 0.012, 8, 20, Math.PI), matMetal); t.position.y = 0.08; g.add(t); const f = fA.clone().lerp(fB, 0.5); g.position.set(f.x, f.y - 0.14, f.z); S.props.add(g); }
      else if (/^barbell/.test(p)) {
        const g = new THREE.Group(); g.add(lat(1.7, 0.014, matMetal)); for (const s of [-1, 1]) { g.add(plate(0.14, 0.035, s * 0.52)); }
        const at = p === "barbell-back" ? [sk.shoulder[0] - 6, sk.shoulder[1] + 2] : p === "barbell-front" ? [sk.shoulder[0] + 8, sk.shoulder[1] - 2] : p === "barbell-hip" ? [sk.hip[0], sk.hip[1] + 10] : null;
        if (at) add(g, at[0], at[1]); else { const f = fA.clone().lerp(fB, 0.5); g.position.set(f.x, f.y, 0); S.props.add(g); }
      }
      else if (p === "seat" || p === "bench-back" || p === "bench-shoulder" || p === "bench-seat") {
        const P = (n) => bn(n).getWorldPosition(new THREE.Vector3());
        const R = { spine: 0.085, pelvis: 0.085 };
        let top, cx, len;
        if (p === "seat") { const pv = P("pelvis"); top = pv.y - R.pelvis - 0.012; cx = pv.x; len = 0.55; }
        else if (p === "bench-seat") { const hy = Math.min(P("hand_l").y, P("hand_r").y), hx = (P("hand_l").x + P("hand_r").x) / 2; top = hy - 0.03; cx = hx - 0.18; len = 0.5; }
        else { const ns = p === "bench-back" ? ["spine_01", "spine_02", "spine_03", "pelvis"] : ["spine_03", "spine_02"]; const ps = ns.map(P); top = Math.min(...ps.map((q) => q.y)) - R.spine - 0.012; cx = (Math.min(...ps.map((q) => q.x)) + Math.max(...ps.map((q) => q.x))) / 2; len = p === "bench-back" ? 0.95 : 0.4; }
        const th = 0.07, m = new THREE.Mesh(new THREE.BoxGeometry(len, th, 0.34), matWood); m.position.set(cx, top - th / 2, 0); S.props.add(m);
        for (const sx of [-1, 1]) { const h = top - th; const leg = new THREE.Mesh(new THREE.BoxGeometry(0.06, Math.max(0.02, h), 0.28), matWood); leg.position.set(cx + sx * (len / 2 - 0.05), h / 2, 0); S.props.add(leg); }
      }
      else if (p === "sled") {
        // leg-press seat: a reclined pad resting against the back/hips and a foot platform that rides with the feet
        const P = (n) => bn(n).getWorldPosition(new THREE.Vector3());
        const a = P("pelvis"), b = P("spine_03"), ang = Math.atan2(b.y - a.y, b.x - a.x), ct = Math.cos(ang), st = Math.sin(ang);
        const mid = a.clone().lerp(b, 0.5), off = 0.085 + 0.012 + 0.03; let nx = st, ny = -ct; if (ny > 0) { nx = -nx; ny = -ny; }
        const pad = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.06, 0.4), matWood); pad.rotation.z = ang; pad.position.set(mid.x + nx * off, mid.y + ny * off, 0); pad.userData.noCheck = true; S.props.add(pad);
        const t1 = P("ball_leaf_l"), t2 = P("ball_leaf_r"), fx = Math.max(t1.x, t2.x) + 0.05, fy = (t1.y + t2.y) / 2;
        const top = fy + 0.25, plate2 = new THREE.Mesh(new THREE.BoxGeometry(0.04, top, 0.5), matMetal); plate2.position.set(fx + 0.02, top / 2, 0); S.props.add(plate2);
        for (const e of [-1, 1]) { const ex = mid.x + nx * off + e * 0.475 * ct, ey = mid.y + ny * off + e * 0.475 * st; const post = new THREE.Mesh(new THREE.BoxGeometry(0.05, Math.max(0.02, ey), 0.4), matWood); post.position.set(ex, Math.max(0.02, ey) / 2, 0); post.userData.noCheck = true; S.props.add(post); }
      }
      else if (p === "box-foot" || p === "box-feet") { const bx = S.box ?? { x: sk.ankleA[0], h: 30, w: 0.5 }; const h = bx.h * K; const m = new THREE.Mesh(new THREE.BoxGeometry(bx.w ?? 0.5, h, 0.5), matWood); m.position.set(bx.x * K, h / 2, 0); S.props.add(m); }
      else if (p === "bar-hang") { const barY = (S.hangBar ?? 188); { const f = fA.clone().lerp(fB, 0.5); const m = lat(1.1, 0.014, matMetal); m.position.set(f.x, f.y, 0); S.props.add(m); } }
      else if (p === "wall") { const m = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2, 1.2), matWood); add(m, sk.hip[0] - 62, 100); }
      else if (p === "band-hands" || p === "cable-hands") {
        const a = p === "band-hands" ? new THREE.Vector3(-0.9, hand[1] * K + lift, 0) : new THREE.Vector3(1.0, Math.max(hand[1] * K, 0.2) + lift, 0);
        const b = fA.clone().lerp(fB, 0.5);
        S.props.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), matBand));
      }
    }
  }

  // ---------------------------------------------------------------- clips
  function playClip(name) {
    const a = S.actions[name]; if (!a) return false;
    if (S.clip) S.actions[S.clip].stop();
    S.clip = name; a.reset().play(); S.model.position.y = 0; S.dirty = true; return true;
  }
  function stopClip() { if (S.clip) S.actions[S.clip].stop(); S.clip = null; restPose(); }
  function setClipTime(t) { const a = S.actions[S.clip]; if (!a) return; a.paused = true; a.time = t % a.getClip().duration; S.mixer.update(0); }

  function frame(minX, maxX, minY, maxY, ground = true, hang = false, hangBar = 188) {
    S.frame = { cx: ((minX + maxX) / 2) * K, cy: ((minY + maxY + 24) / 2) * K, h: Math.max((maxY - minY + 46) * K * 1.12, (maxX - minX + 60) * K * 0.82, 1.5) };
    S.ground = ground; S.hang = hang; S.hangBar = hangBar;
    floor.visible = floorRing.visible = !hang; place();
  }

  // pointer: horizontal drag swings the camera around the figure
  let down = null;
  canvas.addEventListener("pointerdown", (e) => { down = e.clientX; S.autoYaw = false; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => { if (down === null) return; S.yaw = Math.max(-1.4, Math.min(1.4, S.yaw + (e.clientX - down) * 0.008)); down = e.clientX; place(); });
  canvas.addEventListener("pointerup", () => { down = null; });
  canvas.style.touchAction = "pan-y";

  let raf = 0;
  const loop = () => {
    raf = requestAnimationFrame(loop);
    const dt = S.clock.getDelta(); S.t += dt;
    if (S.clip && !S.mixer._actions.every((a) => a.paused)) S.mixer.update(dt);
    S.uni && (S.uni.uPulse.value = 0.5 + 0.5 * Math.sin(S.t * 4));
    if (S.autoYaw) { S.yaw = 0.42 + Math.sin(S.t * 0.35) * 0.22; place(); }
    renderer.render(scene, camera);
  };
  const ro = new ResizeObserver(resize); ro.observe(canvas); resize();
  load().then((g) => { if (!S.disposed) { init({ scene: g.scene.clone ? cloneSkinned(g.scene) : g.scene, animations: g.animations }); raf = requestAnimationFrame(loop); } }).catch((e) => options.onError && options.onError(e));

  // SkeletonUtils.clone equivalent (kept local so the vendor folder stays small)
  function cloneSkinned(src) {
    const clone = src.clone(true); const map = new Map(); const a = [], b = [];
    src.traverse((n) => a.push(n)); clone.traverse((n) => b.push(n)); a.forEach((n, i) => map.set(n, b[i]));
    a.forEach((n, i) => { if (n.isSkinnedMesh) { const c = b[i]; const bones = n.skeleton.bones.map((bb) => map.get(bb)); c.skeleton = new THREE.Skeleton(bones, n.skeleton.boneInverses); c.bind(c.skeleton, n.bindMatrix); c.geometry = n.geometry; } });
    return clone;
  }

  const api = {
    setSolved, setTargets, setProps, setBox, calibrateBox, collisions, frame, playClip, stopClip, setClipTime, hasClip: (n) => !!S.actions[n],
    setAutoRotate(on) { S.autoYaw = !!on; },
    dispose() { S.disposed = true; cancelAnimationFrame(raf); ro.disconnect(); renderer.dispose(); },
  };
  return api;
}

window.VFFigure = { create, preload: () => load().catch(() => {}) };
window.dispatchEvent(new Event("vffigure:ready"));
