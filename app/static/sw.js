// static/sw.js — Vinor PWA (dev-friendly)
const CACHE_NAME = 'vinor-cache-v1';
const ASSETS = [
  '/', // ممکنه روی روت کش لازم باشه
  '/app',
  '/static/favicon-32x32.png',
  '/static/icons/icon-192.png',
  '/static/site.webmanifest' // اگر نام مانیفست فرق داره، این رو همگام کن
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS).catch(()=>null))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// شبکه‌اول، کشِ پشتیبان (برای توسعه بهتره)
self.addEventListener('fetch', (event) => {
  const req = event.request;
  event.respondWith(
    fetch(req).then(res => {
      const resClone = res.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(req, resClone)).catch(()=>{});
      return res;
    }).catch(() => caches.match(req).then(cached => cached || caches.match('/app')))
  );
});
