// Abgelöst durch ../../offline-sw.js (gemeinsamer Offline-Speicher für den ganzen Sport-Bereich).
// Diese Datei bleibt nur, damit sich alte Installationen auf den iPads selbst abmelden.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.registration.unregister()));
