// Levoberezhny quarter — documentary 3D reconstruction (MUP-CS-012).
// Every geometric parameter is sourced; floors=null renders as a marked placeholder, never a guess.
// Massing / series-based Reconstruction / Memorial modes, satellite-only basemap.

// ---- series specification (inlined — see series-research.html for the full dossier) ----
const BRICK_WINDOW = { w: 1.35, h: 1.34, sill: 0.9 };
const DOOR = { w: 1.1, h: 2.1 };
const STAIR_WINDOW = { w: 0.9, h: 1.2 };

const SERIES_FAMILIES = {
  brick_1447_1438: {
    key: 'brick_1447_1438', label: '1-447 / 1-438 family — brick 5-storey (hypothesis default)',
    kind: 'brick', massing: 'bar', floors: 5, floorH: 2.8, ceiling: 2.48,
    aptsPerLanding: 4, sectionLen: 16, bayStep: 3.2, span: 6.0, wall: 0.4,
    window: BRICK_WINDOW, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.4, d: 0.9, slab: 0.12, fromFloor: 2 }, hypothesis: true,
    basis: 'Regional default for unresolved 5-storey buildings ONLY — no longer asserted quarter-wide.',
  },
  brick_1437: {
    key: 'brick_1437', label: '1-437 — brick 5-storey (confirmed, domophoto.ru)',
    kind: 'brick', massing: 'bar', floors: 5, floorH: 2.8, ceiling: 2.48,
    aptsPerLanding: 4, sectionLen: 16, bayStep: 3.2, span: 6.0, wall: 0.4,
    window: BRICK_WINDOW, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.4, d: 0.9, slab: 0.12, fromFloor: 2 }, facadeTint: 0xa08578,
    basis: '50 лет Октября 20 carries domophoto.ru project code "1-437" (building/291080).',
  },
  panel_5st: {
    key: 'panel_5st', label: 'Panel 5-storey (панельная хрущёвка)',
    kind: 'panel', massing: 'bar', floors: 5, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 16, bayStep: 3.2, wall: 0.35,
    window: { w: 1.45, h: 1.41, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.4, d: 0.9, slab: 0.12, fromFloor: 2 }, panelSeam: { vStep: 3.2, perFloor: true },
    basis: 'domophoto.ru lists 50 лет Октября 4/6/8 and Комсомольский 34 as "Панельные жилые дома".',
  },
  panel_9st_1464d83: {
    key: 'panel_9st_1464d83', label: '1-464Д-83 — panel 9-storey slab (confirmed, domophoto.ru)',
    kind: 'panel', massing: 'bar', floors: 9, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 18, bayStep: 3.2, wall: 0.35,
    window: { w: 1.45, h: 1.41, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.6, d: 0.9, slab: 0.12, fromFloor: 1 }, panelSeam: { vStep: 3.2, perFloor: true },
    basis: 'Ломизова 9, 11 and 13 all carry domophoto.ru project code "1-464Д-83".',
  },
  panel_9st_1439a: {
    key: 'panel_9st_1439a', label: '1-439А-41 — panel 9-storey, single entrance (confirmed, domophoto.ru)',
    kind: 'panel', massing: 'bar', floors: 9, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 26, bayStep: 3.2, wall: 0.35,
    window: { w: 1.45, h: 1.41, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.6, d: 0.9, slab: 0.12, fromFloor: 1 }, panelSeam: { vStep: 3.2, perFloor: true }, entrances: 1,
    basis: 'Комсомольский 30 and 36 carry domophoto.ru project code "1-439А-41".',
  },
  panel_9st_generic: {
    key: 'panel_9st_generic', label: 'Panel 9-storey (photo-identified, series code pending)',
    kind: 'panel', massing: 'bar', floors: 9, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 18, bayStep: 3.2, wall: 0.35,
    window: { w: 1.45, h: 1.41, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.6, d: 0.9, slab: 0.12, fromFloor: 1 }, panelSeam: { vStep: 3.2, perFloor: true }, hypothesis: true,
    basis: '9-storey panel buildings photo-identified but without a confirmed catalogue code.',
  },
  panel_point_10st: {
    key: 'panel_point_10st', label: 'Panel point-tower, 10-storey (точечный дом)',
    kind: 'panel', massing: 'point', floors: 10, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 999, bayStep: 3.0, wall: 0.35,
    window: { w: 1.45, h: 1.41, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.4, d: 0.9, slab: 0.12, fromFloor: 1, longFacadeOnly: true }, panelSeam: { vStep: 3.0, perFloor: true },
    basis: 'Азовстальская 21 photo-confirmed (Wikimapia photo 4346220).',
  },
  tower_14st: {
    key: 'tower_14st', label: '14-storey tower, rounded corner bay (Ломизова 17, one-off)',
    kind: 'panel', massing: 'point', floors: 14, floorH: 2.8, ceiling: 2.5,
    aptsPerLanding: 4, sectionLen: 999, bayStep: 3.0, wall: 0.35,
    window: { w: 1.45, h: 1.5, sill: 0.85 }, stairWindow: STAIR_WINDOW, door: DOOR,
    balcony: { w: 2.4, d: 1.0, slab: 0.14, fromFloor: 1 }, panelSeam: { vStep: 3.0, perFloor: true }, accent: 0xd88a7a,
    basis: '14 floors triple-confirmed: dashcam still + Yandex panorama + domophoto.ru building/308439.',
  },
  dormitory_5st: {
    key: 'dormitory_5st', label: 'Dormitory 5-storey (общежитие, no balconies)',
    kind: 'brick', massing: 'bar', floors: 5, floorH: 2.8, ceiling: 2.48,
    aptsPerLanding: 8, sectionLen: 20, bayStep: 3.2, wall: 0.4,
    window: BRICK_WINDOW, stairWindow: STAIR_WINDOW, door: DOOR, balcony: null,
    basis: 'Facade-mounted sign: «ГУРТОЖИТОК МАРІУПОЛЬСЬКОГО БУДІВЕЛЬНОГО КОЛЕДЖУ».',
  },
  civic: {
    key: 'civic', label: 'Civic / commercial building (kindergarten, school, clinic, shops)',
    kind: 'civic', massing: 'bar', floors: 2, floorH: 3.3, ceiling: 3.0,
    aptsPerLanding: 0, sectionLen: 999, bayStep: 3.0, wall: 0.4,
    window: { w: 1.8, h: 1.6, sill: 0.8 }, stairWindow: STAIR_WINDOW, door: { w: 1.6, h: 2.2 }, balcony: null,
    basis: 'Six confirmed non-residential buildings in the quarter (kindergartens, school, clinic, employment centre, shops).',
  },
};

function familyFor(b) {
  if (b.actual_use && b.actual_use !== 'residential') return SERIES_FAMILIES.civic;
  const s = (b.series || '').toLowerCase();
  if (s.includes('1-464')) return SERIES_FAMILIES.panel_9st_1464d83;
  if (s.includes('1-439')) return SERIES_FAMILIES.panel_9st_1439a;
  if (s.includes('1-437')) return SERIES_FAMILIES.brick_1437;
  if (s.includes('точечн') || s.includes('point-tower')) return SERIES_FAMILIES.panel_point_10st;
  if (s.includes('dormitory') || s.includes('общежит')) return SERIES_FAMILIES.dormitory_5st;
  if (b.floors === 14) return SERIES_FAMILIES.tower_14st;
  if (b.floors === 10) return SERIES_FAMILIES.panel_point_10st;
  if ((s.includes('panel') || s.includes('панель')) && (b.floors || 5) >= 9)
    return SERIES_FAMILIES.panel_9st_generic;
  if (s.includes('panel') || s.includes('панель')) return SERIES_FAMILIES.panel_5st;
  if ((b.floors || 0) >= 9) return SERIES_FAMILIES.panel_9st_generic;
  return SERIES_FAMILIES.brick_1447_1438;
}

const stage = document.getElementById('stage');
const $ = (id) => document.getElementById(id);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

const C = { ink: 0x1C232B, paper: 0xE3E7E7, concrete: 0x8B8D85, blueprint: 0x2F4858, ash: 0x46433E, window: 0xE8A33D, civic: 0x6f7f74 };
const FLOOR_H = 2.9, PLACEHOLDER_H = 3.2, CIVIC_PLACEHOLDER_H = 6.6;

const dataP = (window.__resources && window.__resources.quarterData
  ? fetch(window.__resources.quarterData).then(r => r.json())
  : fetch('uploads/levoberezhny_reconstruction.json')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .catch(() => fetch('uploads/levoberezhny-3d/levoberezhny_reconstruction.json').then(r => r.json())));
const fontsP = Promise.allSettled([
  document.fonts.load('700 32px "PT Sans"'), document.fonts.load('16px "PT Mono"'),
]);

let data, THREE, buildings = [], byPid = new Map();
let massing, pickMeshes = [], windowMeshes = [];
let reconMassing, compGroup, reconPick = [];
let memorialGroup, memorialPick = [];
let mode = 'recon'; // 'recon' | 'memorial'
let lonMin, lonMax, latMin, latMax;
const SAT_BASE = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile';
let hovered = null, selected = null, selectedB = null;

function demoBounds(b) {
  // -> {start, end, basis} start=first possible demolition instant, end=last
  if (b.demolition && b.demolition.date) {
    const t = Date.parse(b.demolition.date);
    return { start: t, end: t, basis: 'dated', source: b.demolition.source };
  }
  const ps = b.satellite && b.satellite.post_siege && Date.parse(b.satellite.post_siege.target_date);
  const cl = b.satellite && b.satellite.cleared && Date.parse(b.satellite.cleared.target_date);
  const FALLBACK_START = Date.parse('2022-10-24'), FALLBACK_END = Date.parse('2023-06-15');
  const start = ps || FALLBACK_START, end = cl || FALLBACK_END;
  return { start: Math.min(start, end), end: Math.max(start, end), basis: 'interval' };
}

function computeStats() {
  buildings = data.buildings;
  let dead = 0, miss = 0, claims = 0, res = 0, civ = 0;
  for (const b of buildings) {
    byPid.set(b.pid, b);
    dead += b.casualties.dead; miss += b.casualties.missing; claims += b.compensation.n_claims;
    if (b.actual_use && b.actual_use !== 'residential') civ++; else res++;
  }
  $('stDead').textContent = dead; $('stMiss').textContent = miss; $('stClaims').textContent = claims;
  $('stBld').textContent = buildings.length;
  const split = $('stBldSub'); if (split) split.textContent = res + ' RESIDENTIAL + ' + civ + ' CIVIC/COMMERCIAL';
  const lb = $('btnList'); if (lb) lb.textContent = 'LIST — ' + buildings.length;
}

// ---- geometry helpers ----
let lat0 = 0, lon0 = 0, mPerLon = 1, mPerLat = 1;
function toLocal(lon, lat) { return { x: (lon - lon0) * mPerLon, z: -(lat - lat0) * mPerLat }; }

function ringLocal(b) {
  return b.footprint.coordinates[0].map(([lon, lat]) => toLocal(lon, lat));
}
function fallbackRing(b) {
  // No sourced footprint: a small marked square around the geocoded point,
  // clearly a placeholder (paired with the panel's missing-footprint note).
  const c = toLocal(b.lon, b.lat), r = 7;
  return [{ x: c.x - r, z: c.z - r }, { x: c.x + r, z: c.z - r },
          { x: c.x + r, z: c.z + r }, { x: c.x - r, z: c.z + r }, { x: c.x - r, z: c.z - r }];
}
function ringFor(b) {
  if (!b.footprint) return fallbackRing(b);
  const ring = ringLocal(b);
  const c = ringCentroid(ring);
  const p = toLocal(b.lon, b.lat);
  // guard against corrupt footprint geometry far from the building's own geocoded point
  if (Math.hypot(c.x - p.x, c.z - p.z) > 60) { console.warn('discarding corrupt footprint for', b.pid, b.building_id); return fallbackRing(b); }
  return ring;
}
function ringCentroid(ring) {
  let x = 0, z = 0; const n = ring.length - 1;
  for (let i = 0; i < n; i++) { x += ring[i].x; z += ring[i].z; }
  return { x: x / n, z: z / n };
}
function longestEdge(ring) {
  let best = null, bl = -1;
  for (let i = 0; i < ring.length - 1; i++) {
    const a = ring[i], b = ring[i + 1];
    const l = Math.hypot(b.x - a.x, b.z - a.z);
    if (l > bl) { bl = l; best = [a, b]; }
  }
  return { a: best[0], b: best[1], len: bl };
}

function hatchTexture() {
  const cv = document.createElement('canvas'); cv.width = cv.height = 32;
  const g = cv.getContext('2d');
  g.fillStyle = '#B9BBB2'; g.fillRect(0, 0, 32, 32);
  g.strokeStyle = '#8B8D85'; g.lineWidth = 3;
  g.beginPath();
  for (let i = -32; i < 64; i += 8) { g.moveTo(i, 32); g.lineTo(i + 32, 0); }
  g.stroke();
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function textPlane(text, opts = {}) {
  const px = 64, pad = opts.pad != null ? opts.pad : 24;
  const cv = document.createElement('canvas');
  let g2 = cv.getContext('2d');
  const font = `${opts.weight || 700} ${px}px "${opts.font || 'PT Sans'}"`;
  g2.font = font;
  cv.width = Math.ceil(g2.measureText(text).width) + pad * 2; cv.height = px + pad * 2;
  g2 = cv.getContext('2d');
  g2.font = font;
  g2.textBaseline = 'middle';
  if (opts.bg) {
    g2.fillStyle = opts.bg;
    const r = Math.min(16, cv.height / 2);
    g2.beginPath();
    g2.moveTo(r, 0); g2.arcTo(cv.width, 0, cv.width, cv.height, r); g2.arcTo(cv.width, cv.height, 0, cv.height, r);
    g2.arcTo(0, cv.height, 0, 0, r); g2.arcTo(0, 0, cv.width, 0, r); g2.closePath(); g2.fill();
  }
  if (opts.stroke) { g2.lineWidth = opts.strokeW || 9; g2.lineJoin = 'round'; g2.strokeStyle = opts.stroke; g2.strokeText(text, pad, cv.height / 2); }
  g2.fillStyle = opts.color || '#2F4858';
  g2.fillText(text, pad, cv.height / 2);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  const hM = opts.height || 10;
  const geo = new THREE.PlaneGeometry(hM * cv.width / cv.height, hM);
  const mat = new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, depthTest: opts.onTop ? false : true });
  const m = new THREE.Mesh(geo, mat);
  if (opts.onTop) m.renderOrder = opts.renderOrder || 5;
  return m;
}

// apartment -> (entrance, floor, slot) via the dataset's own arithmetic
function aptSlot(apt, floors, aptsPerLanding) {
  const perEntrance = floors * aptsPerLanding;
  const a = apt - 1;
  return { e: Math.floor(a / perEntrance), f: Math.floor((a % perEntrance) / aptsPerLanding), k: a % aptsPerLanding };
}

function boot() {
  computeStats();
  buildList();
  $('loadmsg').remove();

  lat0 = buildings.reduce((s, b) => s + b.lat, 0) / buildings.length;
  lon0 = buildings.reduce((s, b) => s + b.lon, 0) / buildings.length;
  mPerLat = 111132;
  mPerLon = 111320 * Math.cos(lat0 * Math.PI / 180);

  for (const b of buildings) b._demo = demoBounds(b);

  const scene = stage._scene;

  // materials (named — they become usemtl entries in the OBJ export)
  const matConcrete = new THREE.MeshStandardMaterial({ color: C.concrete, roughness: 0.95, metalness: 0 });
  matConcrete.name = 'concrete_sourced';
  const matPlaceholder = new THREE.MeshStandardMaterial({ map: hatchTexture(), roughness: 1, metalness: 0 });
  matPlaceholder.name = 'concrete_floors_undetermined';
  const matCivic = new THREE.MeshStandardMaterial({ color: C.civic, roughness: 0.9, metalness: 0 });
  matCivic.name = 'civic_building';
  const matMarker = new THREE.MeshStandardMaterial({ color: C.window, emissive: C.window, emissiveIntensity: 0.55, roughness: 0.6 });
  matMarker.name = 'household_presence';
  const matWinLit = new THREE.MeshStandardMaterial({ color: C.window, emissive: C.window, emissiveIntensity: 0.85, side: THREE.DoubleSide });
  matWinLit.name = 'window_compensation_record';
  const matWinFaint = new THREE.MeshBasicMaterial({ color: C.ink, transparent: true, opacity: 0.16, side: THREE.DoubleSide });
  matWinFaint.name = 'window_unmapped';
  const edgeMatBase = new THREE.LineBasicMaterial({ color: C.blueprint, transparent: true, opacity: 0.85 });

  massing = new THREE.Group();
  massing.name = 'levoberezhny_massing';
  compGroup = new THREE.Group();
  compGroup.name = 'compensation_windows';

  for (const b of buildings) {
    const ring = ringFor(b);
    const civic = b.actual_use && b.actual_use !== 'residential';
    const shape = new THREE.Shape(ring.map(p => new THREE.Vector2(p.x, -p.z)));
    const known = b.floors != null;
    const h = known ? b.floors * FLOOR_H : (civic ? CIVIC_PLACEHOLDER_H : PLACEHOLDER_H);
    const geo = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false, steps: 1 });
    geo.rotateX(-Math.PI / 2);
    const baseMat = civic ? matCivic : (known ? matConcrete : matPlaceholder);
    const mesh = new THREE.Mesh(geo, baseMat.clone());
    mesh.material.name = civic ? 'civic_building' : (known ? 'concrete_sourced' : 'concrete_floors_undetermined');
    mesh.name = 'bld_' + (b.pid ?? b.building_id);
    mesh.userData.b = b;
    const edgeMat = edgeMatBase.clone();
    if (!b.footprint) { edgeMat.color.setHex(C.window); } // placeholder square flagged amber
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 20), edgeMat);
    edges.raycast = () => {};
    mesh.add(edges);
    mesh.userData.edgeMat = edgeMat;
    mesh.userData.baseEdge = b.footprint ? C.blueprint : C.window;
    massing.add(mesh);
    pickMeshes.push(mesh);
    b._mesh = mesh;
    b._center = ringCentroid(ring);
    b._height = h;
    b._ring = ring;

    if (civic) {
      const lbl = textPlane((b.actual_use_name || b.actual_use).split('(')[0].trim(), {
        height: 5, color: '#F4F7F7', bg: 'rgba(47,72,88,0.92)', pad: 30, onTop: true, renderOrder: 6,
      });
      lbl.position.set(b._center.x, h + 7, b._center.z);
      lbl.userData.billboard = true;
      lbl.raycast = () => {};
      massing.add(lbl);
      b._civicLabel = lbl;
    }

    if (b.casualties.dead + b.casualties.missing > 0) {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.5, 24), matMarker);
      m.name = 'presence_marker_' + b.pid;
      m.position.set(b._center.x, h + 0.3, b._center.z);
      m.raycast = () => {};
      massing.add(m);
    }

    // window-level mapping — only where floor + entrance data exists in the record
    if (known && b.entrances && b.footprint) {
      const { a, b: eB } = longestEdge(ring);
      const dx = eB.x - a.x, dz = eB.z - a.z;
      const len = Math.hypot(dx, dz);
      const ux = dx / len, uz = dz / len;
      let nx = -uz, nz = ux;
      const mid = { x: (a.x + eB.x) / 2, z: (a.z + eB.z) / 2 };
      if (nx * (mid.x - b._center.x) + nz * (mid.z - b._center.z) < 0) { nx = -nx; nz = -nz; }
      const rotY = Math.atan2(nx, nz);
      const aptsPerLanding = 4;
      const cols = b.entrances * aptsPerLanding;
      const maxApt = Math.max(b.max_apt_no || 0, ...b.compensation.apartments.map(Number), b.floors * b.entrances * aptsPerLanding);
      const compSet = new Set(b.compensation.apartments.map(Number));
      const winGeo = new THREE.PlaneGeometry(1.4, 1.6);
      for (let apt = 1; apt <= maxApt; apt++) {
        const s = aptSlot(apt, b.floors, aptsPerLanding);
        if (s.e >= b.entrances) break;
        const col = s.e * aptsPerLanding + s.k;
        const t = (col + 0.5) / cols;
        const lit = compSet.has(apt);
        const w = new THREE.Mesh(winGeo, lit ? matWinLit : matWinFaint);
        w.name = (lit ? 'window_apt_' : 'winslot_') + b.pid + '_' + apt;
        w.position.set(a.x + dx * t + nx * 0.25, (s.f + 0.55) * FLOOR_H, a.z + dz * t + nz * 0.25);
        w.rotation.y = rotY;
        w.userData = lit ? { b, apt } : {};
        if (!lit) w.raycast = () => {};
        compGroup.add(w);
        if (lit) windowMeshes.push(w);
      }
    }
  }

  stage.setObject(massing);

  // tighter documentary 3/4 framing than the stage default
  {
    const bb = new THREE.Box3().setFromObject(massing);
    const sph = bb.getBoundingSphere(new THREE.Sphere());
    const dir = new THREE.Vector3(0.55, 0.62, 1).normalize();
    const dist = (sph.radius / Math.tan((stage._camera.fov * Math.PI) / 360)) * 0.84;
    stage._camera.position.copy(sph.center).add(dir.multiplyScalar(dist));
    const w = stage.clientWidth || 1200, h = stage.clientHeight || 800;
    stage._camera.setViewOffset(w, h, -Math.round(w * 0.10), Math.round(h * 0.03), w, h);
    stage._controls.target.copy(sph.center);
    stage._controls.update();
  }

  buildSatelliteGround(scene);

  // stage polish: constrain orbit, restyle shadow-DOM chrome
  stage._controls.maxPolarAngle = 1.45;
  stage._controls.minDistance = 40;
  stage._controls.maxDistance = 4200;
  if (reducedMotion) stage._controls.enableDamping = false;
  const st = document.createElement('style');
  st.textContent = `
    .toolbar button{border-radius:0;border:1px solid #2F4858;background:#E3E7E7;color:#1C232B;font-family:"PT Mono",monospace;font-size:11px;letter-spacing:.04em}
    .toolbar button:hover{background:#fff}
    .note{left:auto;right:16px;bottom:46px;text-align:right;font-family:"PT Mono",monospace;color:rgba(28,35,43,.5);font-size:11px}`;
  stage.shadowRoot.appendChild(st);

  scene.add(compGroup);
  buildReconstruction(scene);
  buildMemorial(scene);
  applyScene();
  wirePicking();
  wireControls();
  wireBillboard();
}

// ---- series-based façade reconstruction ----
function wallFacadeTexture(L, H, storeys, fam, opts) {
  const ppm = 18;
  let W = Math.round(L * ppm), Hpx = Math.round(H * ppm);
  const sc = Math.min(1, 2000 / Math.max(W, Hpx));
  W = Math.max(8, Math.round(W * sc)); Hpx = Math.max(8, Math.round(Hpx * sc));
  const cv = document.createElement('canvas'); cv.width = W; cv.height = Hpx;
  const g = cv.getContext('2d');
  const isPanel = fam.kind === 'panel';
  const base = opts.sourced ? (isPanel ? '#8a9094' : '#8f857a') : '#9aa2a6';
  g.fillStyle = base; g.fillRect(0, 0, W, Hpx);
  if (fam.facadeTint && opts.sourced) {
    g.fillStyle = 'rgba(160,110,95,0.18)'; g.fillRect(0, 0, W, Hpx); // pinkish brick variant wash
  }
  const storeyH = Hpx / storeys;
  if (isPanel) {
    // panel seams: horizontal per floor + vertical on the seam step
    g.strokeStyle = 'rgba(28,35,43,0.32)'; g.lineWidth = 1.6;
    for (let f = 1; f < storeys; f++) { const y = Hpx - f * storeyH; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    const vStep = (fam.panelSeam ? fam.panelSeam.vStep : 3.2) * ppm * sc;
    for (let x = vStep; x < W; x += vStep) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, Hpx); g.stroke(); }
  } else {
    // brick coursing: faint dense horizontals + storey lines
    g.strokeStyle = 'rgba(0,0,0,0.05)'; g.lineWidth = 1;
    for (let y = 0; y < Hpx; y += Math.max(3, 6 * sc)) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.strokeStyle = 'rgba(28,35,43,0.26)'; g.lineWidth = 1.4;
    for (let f = 1; f < storeys; f++) { const y = Hpx - f * storeyH; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
  }
  const bay = fam.bayStep || 3.2;
  const cols = Math.max(1, Math.round(L / bay));
  const colW = W / cols;
  const win = fam.window || { w: 1.35, h: 1.34, sill: 0.9 };
  const winW = win.w * ppm * sc, winH = win.h * ppm * sc, sill = win.sill * ppm * sc;
  const sections = Math.max(1, Math.round(L / (fam.sectionLen || 16)));
  const entranceCols = new Set();
  const wantEntrances = opts.isLong && fam.kind !== 'civic';
  if (wantEntrances) for (let s = 0; s < sections; s++) entranceCols.add(Math.floor((s + 0.5) / sections * cols));
  const balc = fam.balcony;
  for (let f = 0; f < storeys; f++) {
    const baseY = Hpx - f * storeyH;
    for (let c = 0; c < cols; c++) {
      const cx = colW * (c + 0.5);
      if (f === 0 && entranceCols.has(c)) {
        const dw = Math.min(colW * 0.5, (fam.door ? fam.door.w : 1.1) * ppm * sc), dh = Math.min(storeyH * 0.82, (fam.door ? fam.door.h : 2.1) * ppm * sc);
        g.fillStyle = '#202c35'; g.fillRect(cx - dw / 2, baseY - dh, dw, dh);
        g.strokeStyle = 'rgba(227,231,231,0.5)'; g.lineWidth = 1; g.strokeRect(cx - dw / 2, baseY - dh, dw, dh);
        continue;
      }
      const wy = baseY - sill - winH;
      g.fillStyle = '#26343f'; g.fillRect(cx - winW / 2, wy, winW, winH);
      g.strokeStyle = 'rgba(227,231,231,0.55)'; g.lineWidth = 1; g.strokeRect(cx - winW / 2, wy, winW, winH);
      g.beginPath(); g.moveTo(cx, wy); g.lineTo(cx, wy + winH); g.moveTo(cx - winW / 2, wy + winH * 0.5); g.lineTo(cx + winW / 2, wy + winH * 0.5); g.stroke();
      if (balc && opts.isLong && f >= (balc.fromFloor != null ? balc.fromFloor - 1 : 1)) {
        const bw = Math.min(colW * 0.9, winW * 1.55), bh = Math.min(1.0 * ppm * sc, storeyH * 0.42), by = baseY - bh;
        g.fillStyle = 'rgba(28,35,43,0.15)'; g.fillRect(cx - bw / 2, by, bw, bh);
        g.strokeStyle = 'rgba(28,35,43,0.5)'; g.lineWidth = 1.3; g.strokeRect(cx - bw / 2, by, bw, bh);
        g.lineWidth = 0.7; for (let rx = cx - bw / 2 + 3; rx < cx + bw / 2; rx += 4) { g.beginPath(); g.moveTo(rx, by); g.lineTo(rx, by + bh); g.stroke(); }
      }
    }
  }
  if (!opts.sourced) { g.fillStyle = 'rgba(150,168,178,0.18)'; g.fillRect(0, 0, W, Hpx); }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

function windowTileTexture(fam, sourced) {
  const cv = document.createElement('canvas'); cv.width = 64; cv.height = 72;
  const g = cv.getContext('2d');
  const isPanel = fam.kind === 'panel';
  g.fillStyle = sourced ? (isPanel ? '#8a9094' : '#8f857a') : '#9aa2a6'; g.fillRect(0, 0, 64, 72);
  g.fillStyle = '#26343f'; g.fillRect(20, 16, 24, 34);
  g.strokeStyle = 'rgba(227,231,231,0.5)'; g.lineWidth = 1.5; g.strokeRect(20, 16, 24, 34);
  g.beginPath(); g.moveTo(32, 16); g.lineTo(32, 50); g.moveTo(20, 33); g.lineTo(44, 33); g.stroke();
  g.strokeStyle = isPanel ? 'rgba(28,35,43,0.34)' : 'rgba(28,35,43,0.22)'; g.lineWidth = 2;
  g.beginPath(); g.moveTo(0, 71); g.lineTo(64, 71); g.stroke();
  if (isPanel) { g.beginPath(); g.moveTo(63, 0); g.lineTo(63, 72); g.stroke(); }
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

function addBalconies(group, a, ux, uz, nx, nz, L, storeys, fam) {
  const balc = fam.balcony;
  if (!balc) return;
  const bay = fam.bayStep || 3.2;
  const cols = Math.max(1, Math.round(L / bay));
  const bmat = new THREE.MeshStandardMaterial({ color: 0x7c7469, roughness: 1 });
  bmat.name = 'balcony';
  const bw = Math.min(balc.w || 2.2, (L / cols) * 0.7), bd = balc.d || 0.85, bh = 1.05;
  const geo = new THREE.BoxGeometry(bw, bh, bd);
  const rotY = Math.atan2(nx, nz);
  const from = balc.fromFloor != null ? balc.fromFloor - 1 : 1;
  for (let f = Math.max(1, from); f < storeys; f++) {
    for (let c = 0; c < cols; c++) {
      const t = (c + 0.5) / cols;
      const m = new THREE.Mesh(geo, bmat);
      m.position.set(a.x + ux * L * t + nx * (bd / 2 + 0.1), f * FLOOR_H + bh / 2 + 0.15, a.z + uz * L * t + nz * (bd / 2 + 0.1));
      m.rotation.y = rotY;
      m.raycast = () => {};
      group.add(m);
    }
  }
}

function buildReconstruction(scene) {
  reconMassing = new THREE.Group();
  reconMassing.name = 'levoberezhny_reconstruction';
  const amber = C.window, blue = C.blueprint;
  const markerMat = new THREE.MeshStandardMaterial({ color: C.window, emissive: C.window, emissiveIntensity: 0.55, roughness: 0.6 });
  markerMat.name = 'household_presence';
  for (const b of buildings) {
    const fam = familyFor(b);
    const ring = ringFor(b);
    const corners = ring.slice(0, ring.length - 1);
    const civic = fam.key === 'civic';
    const sourced = b.floors != null;
    const storeys = sourced ? b.floors : fam.floors;
    const height = storeys * FLOOR_H;
    const g = new THREE.Group();
    g.name = 'recon_' + (b.pid ?? b.building_id);
    const shape = new THREE.Shape(ring.map(p => new THREE.Vector2(p.x, -p.z)));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, steps: 1 });
    geo.rotateX(-Math.PI / 2);
    const baseColor = civic ? C.civic : (sourced ? (fam.kind === 'panel' ? 0x8a9094 : 0x8f857a) : 0x9aa2a6);
    const coreMat = new THREE.MeshStandardMaterial({ color: baseColor, roughness: 0.95, metalness: 0 });
    coreMat.name = civic ? 'civic_building' : (sourced ? (fam.kind + '_sourced') : (fam.kind + '_series_inferred'));
    const core = new THREE.Mesh(geo, coreMat);
    core.name = 'recon_core_' + (b.pid ?? b.building_id);
    core.userData.b = b;
    g.add(core);
    reconPick.push(core);
    b._reconPick = core;
    const edgeMat = new THREE.LineBasicMaterial({ color: civic ? blue : (sourced ? blue : amber), transparent: true, opacity: 0.85 });
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 20), edgeMat);
    edges.raycast = () => {};
    core.add(edges);
    core.userData.edgeMat = edgeMat;
    core.userData.baseEdge = civic ? blue : (sourced ? blue : amber);
    if (civic && b._civicLabel) {
      const lbl2 = b._civicLabel.clone();
      lbl2.position.set(b._center.x, height + 7, b._center.z);
      lbl2.userData.billboard = true;
      lbl2.raycast = () => {};
      g.add(lbl2);
    }
    const isQuad = corners.length === 4;
    let perim = 0;
    for (let i = 0; i < corners.length; i++) { const p = corners[i], q = corners[(i + 1) % corners.length]; perim += Math.hypot(q.x - p.x, q.z - p.z); }
    if (isQuad && b.footprint) {
      const wl = corners.map((p, i) => { const q = corners[(i + 1) % 4]; return Math.hypot(q.x - p.x, q.z - p.z); });
      const med = wl.slice().sort((p, q) => p - q)[2];
      for (let i = 0; i < 4; i++) {
        const p = corners[i], q = corners[(i + 1) % 4];
        const dx = q.x - p.x, dz = q.z - p.z, L = Math.hypot(dx, dz);
        if (L < 2) continue;
        const ux = dx / L, uz = dz / L;
        let nx = -uz, nz = ux;
        const mx = (p.x + q.x) / 2, mz = (p.z + q.z) / 2;
        if (nx * (mx - b._center.x) + nz * (mz - b._center.z) < 0) { nx = -nx; nz = -nz; }
        const isLong = fam.massing === 'point' ? (L >= med - 0.5) : (L >= med - 0.5);
        const plane = new THREE.Mesh(new THREE.PlaneGeometry(L, height),
          new THREE.MeshStandardMaterial({ map: wallFacadeTexture(L, height, storeys, fam, { isLong, sourced }), roughness: 0.92, metalness: 0 }));
        plane.material.name = (sourced ? 'facade_sourced_' : 'facade_series_inferred_') + fam.key;
        plane.position.set(mx + nx * 0.09, height / 2, mz + nz * 0.09);
        plane.rotation.y = Math.atan2(nx, nz);
        plane.raycast = () => {};
        g.add(plane);
        const balcOK = fam.balcony && (!fam.balcony.longFacadeOnly || isLong);
        if (isLong && sourced && balcOK && !civic) addBalconies(g, p, ux, uz, nx, nz, L, storeys, fam);
      }
    } else {
      core.material.map = windowTileTexture(fam, sourced);
      core.material.map.repeat.set(Math.max(2, Math.round(perim / (fam.bayStep || 3.2))), storeys);
      core.material.needsUpdate = true;
    }
    if (b.casualties.dead + b.casualties.missing > 0) {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.5, 24), markerMat);
      m.position.set(b._center.x, height + 0.3, b._center.z);
      m.raycast = () => {};
      g.add(m);
    }
    reconMassing.add(g);
  }
  reconMassing.visible = false;
  scene.add(reconMassing);
}

// ---- memorial mode ----
// Buildings dim to ash. Each DOCUMENTED person (confirmed dead or listed
// missing at this address) is one amber point in a column rising above the
// building — deliberately NOT a window: casualty records are building-level,
// and placing people at invented apartment positions would fabricate
// precision the sources don't carry. Compensation-mapped windows (sourced to
// apartment numbers) stay lit, cooler, where entrance data exists.
function buildMemorial(scene) {
  memorialGroup = new THREE.Group();
  memorialGroup.name = 'levoberezhny_memorial';
  memorialPick = [];
  const dimMat = new THREE.MeshStandardMaterial({ color: 0x3c4248, roughness: 1, metalness: 0 });
  dimMat.name = 'memorial_dim_massing';
  const dotMatDead = new THREE.MeshStandardMaterial({ color: C.window, emissive: C.window, emissiveIntensity: 1.0 });
  dotMatDead.name = 'memorial_person_dead';
  const dotMatMissing = new THREE.MeshStandardMaterial({ color: 0xd8b46a, emissive: 0xd8b46a, emissiveIntensity: 0.5, transparent: true, opacity: 0.75 });
  dotMatMissing.name = 'memorial_person_missing';
  const dotGeo = new THREE.SphereGeometry(0.9, 12, 8);
  const step = 2.6;

  for (const b of buildings) {
    const ring = ringFor(b);
    const known = b.floors != null;
    const h = known ? b.floors * FLOOR_H : (b.actual_use !== 'residential' ? CIVIC_PLACEHOLDER_H : PLACEHOLDER_H);
    const shape = new THREE.Shape(ring.map(p => new THREE.Vector2(p.x, -p.z)));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false, steps: 1 });
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, dimMat);
    mesh.userData.b = b;
    memorialGroup.add(mesh);
    memorialPick.push(mesh);
    b._memorialPick = mesh;

    const nDead = b.casualties.dead, nMiss = b.casualties.missing;
    const total = nDead + nMiss;
    if (!total) continue;
    for (let i = 0; i < total; i++) {
      const dot = new THREE.Mesh(dotGeo, i < nDead ? dotMatDead : dotMatMissing);
      dot.position.set(b._center.x, h + 3 + i * step, b._center.z);
      dot.raycast = () => {};
      memorialGroup.add(dot);
    }
  }
  memorialGroup.visible = false;
  scene.add(memorialGroup);
}

// ---- satellite basemap (current imagery only) ----
async function buildSatelliteGround(scene) {
  lonMin = Math.min(...buildings.map(b => b.lon)); lonMax = Math.max(...buildings.map(b => b.lon));
  latMin = Math.min(...buildings.map(b => b.lat)); latMax = Math.max(...buildings.map(b => b.lat));
  let urlFn = (z, x, y) => `${SAT_BASE}/${z}/${y}/${x}`, curDate = '';
  try {
    const cfg = await fetch('https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json').then(r => r.json());
    const rels = Object.keys(cfg).map(k => {
      const m = (cfg[k].itemTitle || '').match(/(\d{4}-\d{2}-\d{2})/);
      return { date: m ? m[1] : null, url: cfg[k].itemURL };
    }).filter(r => r.date && r.url).sort((a, b) => a.date < b.date ? -1 : 1);
    if (rels.length) {
      const latest = rels[rels.length - 1];
      urlFn = (z, x, y) => latest.url.replace('{level}', z).replace('{row}', y).replace('{col}', x);
      curDate = latest.date;
    }
  } catch (e) { console.warn('Wayback config unavailable, using default ESRI World Imagery:', e); }
  const plane = await buildSatellitePlane(urlFn);
  if (plane) { plane.name = 'sat_current'; plane.visible = true; scene.add(plane); }
}

async function buildSatellitePlane(urlFn) {
  const mLon = (lonMax - lonMin) * 0.14, mLat = (latMax - latMin) * 0.14;
  const west = lonMin - mLon, east = lonMax + mLon, north = latMax + mLat, south = latMin - mLat;
  const z = 17, n = 2 ** z, TS = 256;
  const lon2x = (lon) => (lon + 180) / 360 * n;
  const lat2y = (lat) => { const r = lat * Math.PI / 180; return (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n; };
  const x2lon = (x) => x / n * 360 - 180;
  const y2lat = (y) => { const t = Math.PI - 2 * Math.PI * y / n; return 180 / Math.PI * Math.atan(0.5 * (Math.exp(t) - Math.exp(-t))); };
  const tx0 = Math.floor(lon2x(west)), tx1 = Math.floor(lon2x(east));
  const ty0 = Math.floor(lat2y(north)), ty1 = Math.floor(lat2y(south));
  const cols = tx1 - tx0 + 1, rows = ty1 - ty0 + 1;
  const cv = document.createElement('canvas'); cv.width = cols * TS; cv.height = rows * TS;
  const g = cv.getContext('2d');
  const load = (tx, ty) => new Promise((res) => {
    const img = new Image(); img.crossOrigin = 'anonymous';
    img.onload = () => res({ img, tx, ty }); img.onerror = () => res(null);
    img.src = urlFn(z, tx, ty);
  });
  const jobs = [];
  for (let ty = ty0; ty <= ty1; ty++) for (let tx = tx0; tx <= tx1; tx++) jobs.push(load(tx, ty));
  const done = await Promise.all(jobs);
  let ok = 0;
  for (const t of done) { if (!t) continue; g.drawImage(t.img, (t.tx - tx0) * TS, (t.ty - ty0) * TS); ok++; }
  if (!ok) return null;
  const mlonW = x2lon(tx0), mlonE = x2lon(tx1 + 1), mlatN = y2lat(ty0), mlatS = y2lat(ty1 + 1);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const wM = (mlonE - mlonW) * mPerLon, dM = (mlatN - mlatS) * mPerLat;
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(wM, dM), new THREE.MeshBasicMaterial({ map: tex }));
  plane.rotation.x = -Math.PI / 2;
  const c = toLocal((mlonW + mlonE) / 2, (mlatN + mlatS) / 2);
  plane.position.set(c.x, 0.0, c.z);
  plane.raycast = () => {};
  return plane;
}

function applyScene() {
  massing.visible = mode === 'massing';
  reconMassing.visible = mode === 'recon';
  memorialGroup.visible = mode === 'memorial';
  compGroup.visible = true;
  stage.setObject(mode === 'recon' ? reconMassing : (mode === 'memorial' ? memorialGroup : massing));
  document.body.classList.toggle('reconmode', mode === 'recon');
  document.body.classList.toggle('memorialmode', mode === 'memorial');
  for (const [id, m] of [['btnRecon', 'recon'], ['btnMem', 'memorial']]) {
    const el = $(id); if (el) el.setAttribute('aria-pressed', String(mode === m));
  }
  if (selectedB) selectMesh(mode === 'recon' ? selectedB._reconPick : (mode === 'memorial' ? selectedB._memorialPick : selectedB._mesh));
}

// ---- picking ----
function wirePicking() {
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const el = stage;
  let downX = 0, downY = 0;
  const activePick = () => mode === 'recon' ? reconPick : (mode === 'memorial' ? memorialPick : pickMeshes);
  const cast = (ev) => {
    const r = el.getBoundingClientRect();
    ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, stage._camera);
    const hitW = ray.intersectObjects(windowMeshes, false)[0];
    if (hitW) return { type: 'window', obj: hitW.object };
    const hitB = ray.intersectObjects(activePick(), false)[0];
    if (hitB) return { type: 'building', obj: hitB.object };
    return null;
  };
  el.addEventListener('pointerdown', (e) => { downX = e.clientX; downY = e.clientY; });
  el.addEventListener('pointerup', (e) => {
    if (Math.hypot(e.clientX - downX, e.clientY - downY) > 5) return;
    const hit = cast(e);
    if (!hit) { closePanel(); return; }
    if (hit.type === 'window') showApartment(hit.obj.userData.b, hit.obj.userData.apt);
    else showBuilding(hit.obj.userData.b);
  });
  el.addEventListener('pointermove', (e) => {
    const hit = cast(e);
    const mesh = hit && hit.type === 'building' ? hit.obj : null;
    if (hovered && hovered !== mesh) setHighlight(hovered, hovered === selected);
    if (mesh && mesh !== selected) setHighlight(mesh, true);
    hovered = mesh;
    el.style.cursor = hit ? 'pointer' : '';
  });
}

function setHighlight(mesh, on) {
  const em = mesh.userData.edgeMat;
  if (!em) { if (mesh.material && mesh.material.emissive) mesh.material.emissiveIntensity = on ? 0.25 : 0; return; }
  const base = mesh.userData.baseEdge != null ? mesh.userData.baseEdge : C.blueprint;
  em.color.setHex(on ? C.ink : base);
  em.opacity = on ? 1 : 0.85;
}

function selectMesh(mesh) {
  if (selected) setHighlight(selected, false);
  selected = mesh || null;
  if (selected) setHighlight(selected, true);
}

// ---- panel (тех. паспорт card) ----
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const kv = (k, v, na) => `<div class="k">${k}</div><div class="v${na ? ' na' : ''}">${v}</div>`;
const sha = (s) => s ? s.slice(0, 12) + '…' : '—';

function showBuilding(b) {
  selectedB = b;
  selectMesh(mode === 'recon' ? b._reconPick : (mode === 'memorial' ? b._memorialPick : b._mesh));
  const fam = familyFor(b);
  const known = b.floors != null;
  const civic = b.actual_use && b.actual_use !== 'residential';
  const cas = b.casualties, comp = b.compensation;
  const mapped = known && b.entrances;
  const demo = b._demo || demoBounds(b);
  const demoV = demo.basis === 'dated'
    ? new Date(demo.start).toISOString().slice(0, 10) + ' (dated)'
    : new Date(demo.start).toISOString().slice(0, 10) + ' … ' + new Date(demo.end).toISOString().slice(0, 10) + ' (interval)';
  const rows = [
    kv('ADDRESS — PRE-WAR (UA)', b.address_prewar ? esc(b.address_prewar) : 'not recorded', !b.address_prewar),
    kv('ADDRESS — OCCUPATION REG.', esc(b.address_occupation || '—'), !b.address_occupation),
    kv('COORDINATES', b.lat.toFixed(6) + ' N · ' + b.lon.toFixed(6) + ' E'),
    ...(civic ? [kv('USE', esc(b.actual_use_name || b.actual_use)),
                 kv('USE SOURCE', esc(b.actual_use_source || '—'))] : []),
    kv('FLOORS', known ? b.floors : 'NOT YET DETERMINED', !known),
    kv('FLOOR SOURCE', esc(b.floor_source || '—'), !b.floor_source),
    kv('ENTRANCES', b.entrances ?? 'not determined', b.entrances == null),
    ...(b.entrance_source ? [kv('ENTRANCE SOURCE', esc(b.entrance_source))] : []),
    ...(b.max_apt_no ? [kv('MAX APARTMENT NO.', b.max_apt_no)] : []),
    kv('SERIES', b.series ? esc(b.series) : 'unassigned — confidence: ' + esc(b.series_confidence || '—'), !b.series),
    ...(b.series_evidence ? [kv('SERIES EVIDENCE', esc(b.series_evidence))] : []),
    kv('DEMOLITION', demoV + (demo.source ? ' — ' + esc(demo.source) : '')),
    kv('FOOTPRINT SOURCE', b.footprint
      ? 'Visicom API · sha256 ' + sha(b.footprint.source_sha256)
      : 'NO SOURCED FOOTPRINT — placeholder square at the geocoded point', !b.footprint),
  ].join('');
  const le = b.footprint ? longestEdge(ringLocal(b)) : { len: 0 };
  const sections = Math.max(1, Math.round((le.len || 0) / (fam.sectionLen || 16)));
  const storeysR = known ? b.floors : fam.floors;
  const seriesSection = civic ? `
    <section><h3>Civic building</h3>
      <p class="srcnote">${esc(b.actual_use_name || b.actual_use)} — one of the quarter's six confirmed
      non-residential buildings. Rendered as civic massing, not residential typology; height is a marked
      placeholder unless individually sourced. The four civic institutions here are the ones residents
      named in their video appeals («два детских сада, школа и реабилитационный центр»).</p>
    </section>` : `
    <section><h3>Series reconstruction basis</h3>
      <div class="kv">
        ${kv('SERIES FAMILY', esc(fam.label) + (fam.hypothesis ? ' — HYPOTHESIS' : ''))}
        ${kv('HEIGHT BASIS', known ? storeysR + ' floors sourced × 2.8 m' : 'family default ' + storeysR + ' floors × 2.8 m (inferred)', !known)}
        ${kv('SECTIONS (EST.)', sections + ' × ~' + (fam.sectionLen || 16) + ' m spacing')}
        ${kv('WALL', fam.kind === 'panel' ? 'panel, seam grid ' + ((fam.panelSeam && fam.panelSeam.vStep) || 3.2) + ' m' : 'unclad brick 38–40 cm')}
        ${kv('WINDOW / BAY', Math.round(fam.window.w * 1000) + '×' + Math.round(fam.window.h * 1000) + ' mm · ~' + fam.bayStep + ' m bay')}
        ${kv('BALCONIES', fam.balcony ? ('from floor ' + fam.balcony.fromFloor + (fam.balcony.longFacadeOnly ? ' (long facade only)' : '')) : 'none (' + fam.key + ')')}
      </div>
      <p class="srcnote">${esc(fam.basis)} <a href="series-research.html">Full series dossier →</a></p>
    </section>`;
  const names = cas.names && cas.names.length
    ? `<ul class="names">${cas.names.map(n => `<li>${esc(n)}</li>`).join('')}</ul>
       <p class="srcnote">Named from the project's loaded public memorial records. Living private owners are not named.</p>`
    : '';
  const memAnn = b.memorial_annotation
    ? `<p class="srcnote" style="border-left:3px solid var(--window);padding-left:8px">${esc(b.memorial_annotation.annotation)}</p>` : '';
  const cult = b.cultural_note
    ? `<section><h3>Cultural record</h3><p class="aptnarr">${esc(b.cultural_note.note)}</p>
       <p class="srcnote">${esc(b.cultural_note.source)}</p></section>` : '';
  const chips = comp.apartments.length
    ? `<div class="chips">${comp.apartments.map(a =>
        mapped ? `<button class="chip" data-apt="${esc(a)}">кв. ${esc(a)}</button>` : `<span class="chip">кв. ${esc(a)}</span>`
      ).join('')}</div>
      <p class="srcnote">${mapped ? 'Click an apartment to locate its window (schematic mapping — see note there).' : 'Window-level mapping requires a floor and entrance count — not yet determined for this building.'}</p>`
    : '<p class="srcnote">No claims recorded at this address.</p>';
  const sat = ['prewar', 'post_siege', 'cleared', 'current'].map(k => {
    const s = b.satellite && b.satellite[k];
    return s ? kv(k.toUpperCase().replace('_', ' '), s.target_date + ' · sha256 ' + sha(s.sha256)) : '';
  }).join('');
  const photos = (b.photos && b.photos.length)
    ? `<ul class="photolist">${b.photos.map(p =>
        `<li>${p.year} — <a href="${esc(p.page_url)}" target="_blank" rel="noopener">${esc(p.title)}</a> · ${p.distance_m} m · ${esc(p.source)}</li>`).join('')}</ul>`
    : '<p class="srcnote">No pre-war photographs located yet for this building.</p>';
  $('panel').innerHTML = `
    <div class="p-head">
      <div><div class="kicker">ТЕХ. ПАСПОРТ — ОБЪЕКТ PID ${b.pid ?? '—'}</div>
      <h2>${esc(b.address_occupation || b.address_prewar || b.building_id)}</h2></div>
      <button class="close" aria-label="Close panel">×</button>
    </div>
    <section><div class="kv">${rows}</div></section>
    ${seriesSection}
    ${cult}
    <section><h3 class="human">Residents — confirmed dead ${cas.dead} · missing ${cas.missing}</h3>${memAnn}${names || '<p class="srcnote">No casualties documented at this address to date.</p>'}</section>
    <section><h3>Compensation register — ${comp.n_claims} claim${comp.n_claims === 1 ? '' : 's'}</h3>${chips}</section>
    <section><h3>Satellite mosaics</h3><div class="kv">${sat}</div></section>
    <section><h3>Pre-war photographs</h3>${photos}</section>
    <section><h3>Source sweep</h3><div class="kv">${kv('DIRECTORY', esc(b.sweep_dir || '—'))}</div>
      <p class="srcnote">Full evidence sweep lives in the project archive; this directory reference is the link-out placeholder.</p></section>`;
  openPanel(b);
}

function showApartment(b, apt) {
  selectMesh(b._mesh);
  $('panel').innerHTML = `
    <div class="p-head">
      <div><div class="kicker">ЗАПИСЬ — КВАРТИРА</div>
      <h2>кв. ${esc(apt)} — ${esc(b.address_occupation || b.address_prewar)}</h2></div>
      <button class="close" aria-label="Close panel">×</button>
    </div>
    <section>
      <p class="aptnarr">Apartment ${esc(apt)} appears on the occupation administration's compensation-housing register — a
      «утраченное жильё» ("lost dwelling") claim, one of ${b.compensation.n_claims} recorded at this address. The occupier's own
      paperwork places a household here.</p>
    </section>
    <section><h3>Mapping note</h3>
      <p class="srcnote">Window position is schematic: derived from ${esc(b.entrance_source || 'resident-reported apartment numbers')}
      and floor arithmetic (${esc(b.floor_source || '')}). Treat as provisional, not surveyed.</p>
    </section>
    <section><button class="backlink" id="backToBld">← BUILDING RECORD — PID ${b.pid}</button></section>`;
  openPanel(b);
  $('backToBld').addEventListener('click', () => showBuilding(b));
}

// memorial roll — all documented people, grouped by address
function showMemorialRoll() {
  const groups = buildings
    .filter(b => b.casualties.dead + b.casualties.missing > 0)
    .sort((a, b) => (b.casualties.dead + b.casualties.missing) - (a.casualties.dead + a.casualties.missing));
  const total = groups.reduce((s, b) => s + b.casualties.dead + b.casualties.missing, 0);
  $('panel').innerHTML = `
    <div class="p-head">
      <div><div class="kicker">ПОМИНАЛЬНЫЙ СПИСОК — MEMORIAL ROLL</div>
      <h2>${total} residents — documented dead &amp; missing</h2></div>
      <button class="close" aria-label="Close panel">×</button>
    </div>
    <section><p class="srcnote">One amber point above each building = one documented person (bright — confirmed dead;
    faded — listed missing). Points are counts, not locations: the records are building-level, and this page does not
    invent apartment positions for the dead. Sources: Mariupol Destruction and Victims Map TSV cross-reference +
    resident-chat records (see each building's card).</p></section>
    ${groups.map(b => `
      <section>
        <h3 class="human">${esc(b.address_occupation || b.building_id)} — ${b.casualties.dead} dead · ${b.casualties.missing} missing</h3>
        ${b.memorial_annotation ? `<p class="srcnote" style="border-left:3px solid var(--window);padding-left:8px">${esc(b.memorial_annotation.annotation)}</p>` : ''}
        ${b.casualties.names.length ? `<ul class="names">${b.casualties.names.map(n => `<li>${esc(n)}</li>`).join('')}</ul>` : '<p class="srcnote">No names published; counts only.</p>'}
        <p class="srcnote"><button class="backlink" data-pid="${b.pid}">building record →</button></p>
      </section>`).join('')}`;
  const p = $('panel');
  p.hidden = false; p.scrollTop = 0;
  p.querySelector('.close').addEventListener('click', closePanel);
  p.querySelectorAll('button.backlink').forEach(btn =>
    btn.addEventListener('click', () => showBuilding(byPid.get(Number(btn.dataset.pid)))));
}

function openPanel(b) {
  const p = $('panel');
  p.hidden = false;
  p.scrollTop = 0;
  p.querySelector('.close').addEventListener('click', closePanel);
  p.querySelectorAll('button.chip').forEach(ch =>
    ch.addEventListener('click', () => showApartment(b, Number(ch.dataset.apt))));
}
function closePanel() { $('panel').hidden = true; selectMesh(null); }
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });

// ---- list fallback ----
function buildList() {
  const ol = $('listRows');
  ol.innerHTML = '';
  for (const b of data.buildings) {
    const li = document.createElement('li');
    const cas = b.casualties;
    const hum = cas.dead + cas.missing > 0;
    const civic = b.actual_use && b.actual_use !== 'residential';
    li.innerHTML = `<button class="rowbtn">
      <span class="addr">${esc(b.address_occupation || b.building_id)}${civic ? ` <span class="civictag">${esc((b.actual_use_name || b.actual_use).split('(')[0].trim())}</span>` : ''}${b.address_prewar ? `<small>довоенный: ${esc(b.address_prewar)}</small>` : ''}</span>
      <span class="cell">${b.floors != null ? b.floors + ' — sourced' : (civic ? 'civic' : 'not determined')}</span>
      <span class="cell c3">${hum ? `<span class="hum">${cas.dead} / ${cas.missing}</span>` : '0 / 0'}</span>
      <span class="cell c4">${b.compensation.n_claims}</span>
    </button>`;
    li.querySelector('button').addEventListener('click', () => showBuilding(b));
    ol.appendChild(li);
  }
}

// ---- view + controls ----
function setView(v) {
  $('listView').hidden = v !== 'list';
  $('btn3d').setAttribute('aria-pressed', String(v === '3d'));
  $('btnList').setAttribute('aria-pressed', String(v === 'list'));
  if (v === 'list') { const f = $('listRows').querySelector('button'); f && f.focus(); }
}
$('btn3d').addEventListener('click', () => setView('3d'));
$('btnList').addEventListener('click', () => setView('list'));

function wireControls() {
  const modeBtns = [['btnRecon', 'recon'], ['btnMem', 'memorial']];
  for (const [id, m] of modeBtns) {
    const el = $(id);
    if (el) el.addEventListener('click', () => {
      mode = m; applyScene();
      if (m === 'memorial') showMemorialRoll();
    });
  }
}

function wireBillboard() {
  const tick = () => {
    for (const b of buildings) if (b._civicLabel && b._civicLabel.visible) b._civicLabel.quaternion.copy(stage._camera.quaternion);
    requestAnimationFrame(tick);
  };
  if (!reducedMotion) requestAnimationFrame(tick);
}

// debug/probe hook
window.__lvb = {
  showBuilding: (pid) => showBuilding(byPid.get(pid)),
  showApartment: (pid, apt) => showApartment(byPid.get(pid), apt),
  get data() { return data; },
};

// ---- bootstrap (last: everything above must be initialized first) ----
try {
  [{ THREE }, data] = await Promise.all([stage.ready, dataP, fontsP]);
  boot();
} catch (err) {
  console.error('3D unavailable, falling back to list:', err);
  data = data || await dataP;
  computeStats();
  buildList();
  setView('list');
  $('loadmsg').textContent = '3D VIEW UNAVAILABLE — SHOWING BUILDING LIST';
}
