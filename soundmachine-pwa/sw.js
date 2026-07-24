// Service worker: cache the app shell so the PWA opens offline once installed.
// Device API calls (to a different origin) are never cached — they pass through.
const CACHE = 'soundmachine-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-180.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;              // only cache GETs
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;          // device API -> network
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
