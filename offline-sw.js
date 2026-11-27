// Offline-Speicher für den Sport-Bereich von KGS - Digital
// Wird von der Sport-Übersicht und den Sport-Tools angemeldet. Liegt im Hauptordner,
// damit auch die Startseite und die gemeinsamen Dateien (assets/) offline erreichbar sind.
// Andere Seiten des Portals werden nicht angefasst (normal aus dem Netz).
const CACHE = 'kgs-sport-offline-v1';
const FILES = [
  'index.html', 'assets/kgs.css', 'assets/kgs.js',
  'sport/index.html', 'sport/extern.html', 'sport/dateien.json',
  'sport/tools/sprint-zeitmessung.html',
  'sport/tools/weitsprung-analyse.html', 'sport/tools/hochsprung-analyse.html', 'sport/tools/wurf-analyse.html',
  'sport/tools/lib/jspdf.umd.min.js',
  'sport/tools/lib/mediapipe-pose/pose.js', 'sport/tools/lib/mediapipe-pose/pose_web.binarypb',
  'sport/tools/lib/mediapipe-pose/pose_solution_packed_assets.data', 'sport/tools/lib/mediapipe-pose/pose_solution_packed_assets_loader.js',
  'sport/tools/lib/mediapipe-pose/pose_solution_simd_wasm_bin.js', 'sport/tools/lib/mediapipe-pose/pose_solution_simd_wasm_bin.wasm',
  'sport/tools/lib/mediapipe-pose/pose_solution_wasm_bin.js', 'sport/tools/lib/mediapipe-pose/pose_solution_wasm_bin.wasm',
  'sport/tools/lib/mediapipe-pose/pose_landmark_lite.tflite', 'sport/tools/lib/mediapipe-pose/pose_landmark_full.tflite'
];
const BASE = new URL('./', self.location).pathname;            // z. B. /kgs-digital/
const netzZuerst = (f) => f.endsWith('.html') || f.endsWith('.json') || f.startsWith('assets/');

// Installieren: Datei für Datei laden; was schon da ist, wird übersprungen
// (bricht das Netz ab, geht es beim nächsten Öffnen dort weiter)
self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    for (const f of FILES) {
      if (await c.match(f)) continue;
      const r = await fetch(f, { cache: 'no-cache' });
      if (!r.ok) throw new Error('fehlt: ' + f);
      await c.put(f, r);
    }
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE && (k.startsWith('kgs-sport-offline-') || k.startsWith('technik-analyse-') || k.startsWith('weitsprung-analyse-'))) await caches.delete(k);
    await self.clients.claim();
  })());
});

async function ausNetzOderSpeicher(f, url) {
  const c = await caches.open(CACHE);
  const netz = fetch(url.pathname + url.search, { cache: 'no-store' }).then((r) => { if (r.ok) c.put(f, r.clone()); return r; });
  // schwaches Netz auf dem Sportplatz: nach 3,5 s den gespeicherten Stand nehmen
  try { const r = await Promise.race([netz, new Promise((ok) => setTimeout(ok, 3500))]); if (r && r.ok) return r; } catch (err) {}
  const alt = await c.match(f);
  if (alt) return alt;
  return netz;
}

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin || !url.pathname.startsWith(BASE)) return;
  let f = decodeURIComponent(url.pathname.slice(BASE.length));
  if (f === '' || f.endsWith('/')) f += 'index.html';
  if (!FILES.includes(f)) return;
  if (netzZuerst(f)) e.respondWith(ausNetzOderSpeicher(f, url));
  else e.respondWith(caches.match(f).then((r) => r || fetch(e.request)));
});

// Status für die Anzeige: wie viele Dateien liegen schon im Speicher?
self.addEventListener('message', (e) => {
  if (e.data === 'status' && e.ports[0]) {
    caches.open(CACHE).then((c) => Promise.all(FILES.map((f) => c.match(f)))).then((rs) => {
      const n = rs.filter(Boolean).length;
      e.ports[0].postMessage({ ok: n === FILES.length, n, total: FILES.length });
    });
  }
});
