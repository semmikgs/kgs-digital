// Offline-Cache für die Technik-Analysen Weitsprung, Hochsprung, Wurf (alles lokal, kein Netz nötig)
// Beide Seiten registrieren diesen Worker (gleicher Ordner = gleicher Scope).
const CACHE = 'technik-analyse-v5';
const FILES = [
  'weitsprung-analyse.html', 'hochsprung-analyse.html', 'wurf-analyse.html',
  'lib/mediapipe-pose/pose.js', 'lib/jspdf.umd.min.js', 'lib/mediapipe-pose/pose_web.binarypb',
  'lib/mediapipe-pose/pose_solution_packed_assets.data', 'lib/mediapipe-pose/pose_solution_packed_assets_loader.js',
  'lib/mediapipe-pose/pose_solution_simd_wasm_bin.js', 'lib/mediapipe-pose/pose_solution_simd_wasm_bin.wasm',
  'lib/mediapipe-pose/pose_solution_wasm_bin.js', 'lib/mediapipe-pose/pose_solution_wasm_bin.wasm',
  'lib/mediapipe-pose/pose_landmark_lite.tflite', 'lib/mediapipe-pose/pose_landmark_full.tflite'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  const f = FILES.find(x => url.pathname.endsWith('/' + x));
  if (!f) return; // andere Seiten (z. B. Sprint-Zeitmessung) nicht anfassen
  if (f.endsWith('.html')) {
    // Seite: erst Netz (für Updates), ohne Netz aus dem Cache
    e.respondWith(fetch(e.request, { cache: 'no-store' }).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(f, cp)); return r; }).catch(() => caches.match(f)));
  } else {
    e.respondWith(caches.match(f).then(r => r || fetch(e.request)));
  }
});
self.addEventListener('message', e => {
  if (e.data === 'status' && e.ports[0]) {
    caches.open(CACHE).then(c => Promise.all(FILES.map(f => c.match(f)))).then(rs => e.ports[0].postMessage({ ok: rs.every(Boolean) }));
  }
});
