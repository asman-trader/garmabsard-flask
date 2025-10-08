/*
  Vinor Service Worker – offline-first shell with runtime caching
  Scope: '/'
*/

const VERSION = 'v1.0.0-2025-10-01';
const PRECACHE = `vinor-precache-${VERSION}`;
const RUNTIME = `vinor-runtime-${VERSION}`;
const API_CACHE = `vinor-api-${VERSION}`;
const ICONS_CACHE = `vinor-icons-${VERSION}`;
async function trimCache(name, maxEntries) {
  try {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    if (keys.length > maxEntries) {
      const toDelete = keys.slice(0, keys.length - maxEntries);
      await Promise.all(toDelete.map((req) => cache.delete(req)));
    }
  } catch (_) {}
}

// URLs to precache at install
const OFFLINE_URL = '/static/offline.html';
const PRECACHE_URLS = [
  '/',
  '/start',
  '/app',
  '/login',
  '/verify',
  '/search',
  '/about',
  '/help',
  '/faq',
  '/guide/safe-buy',
  '/connection',
  '/city',
  '/city/multi',
  // careers & consultant
  '/careers/consultant',
  '/careers/consultant/apply',
  '/consultant/dashboard',
  // user pages (will cache shell or redirect)
  '/favorites',
  '/profile',
  '/settings',
  '/my-lands',
  '/notifications',
  // submit/ad flows (shell)
  '/submit-ad',
  '/lands/add/step1',
  '/lands/add',
  '/lands/add/details',
  '/lands/add/step3',
  // manifests and offline fallback
  '/manifest.webmanifest',
  OFFLINE_URL,
  // Icons/sounds (best-effort if exist)
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/sounds/notify.mp3'
];
// Precache local icon/font assets for full offline
const LOCAL_ICON_FONT_ASSETS = [
  '/static/vendor/fontawesome/css/all.min.css',
  '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
  '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2',
  '/static/vendor/fontawesome/webfonts/fa-brands-400.woff2',
  '/static/fonts/vazirmatn.css',
  // optional if you add specific woff2 files
  '/static/fonts/vazirmatn-regular.woff2',
  '/static/fonts/vazirmatn-bold.woff2',
  '/static/fonts/vazirmatn-medium.woff2',
  '/static/fonts/vazirmatn-light.woff2'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(PRECACHE);
    try { await cache.addAll(PRECACHE_URLS.concat(LOCAL_ICON_FONT_ASSETS).map((u) => new Request(u, { credentials: 'same-origin' }))); } catch(_) {}
    // Best-effort: prewarm external CSS/fonts/icons into dedicated ICONS cache for offline rendering
    try {
      const icache = await caches.open(ICONS_CACHE);
      await Promise.all(EXTERNAL_WARM.map(async (url) => {
        try { const resp = await fetch(url, { mode: 'no-cors' }); await icache.put(url, resp.clone()); } catch(_) {}
      }));
    } catch(_) {}
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((k) => ![PRECACHE, RUNTIME, API_CACHE].includes(k)).map((k) => caches.delete(k))
    );
    // Enable Navigation Preload for faster nav when online
    try { if (self.registration.navigationPreload) await self.registration.navigationPreload.enable(); } catch(_) {}
    await self.clients.claim();
  })());
});

function isSameOrigin(url) {
  try { return new URL(url, self.location.origin).origin === self.location.origin; } catch { return false; }
}

// Whitelisted external origins to cache (CDN scripts/fonts)
const EXTERNAL_ORIGINS = [
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com',
  'https://unpkg.com',
  'https://cdn.jsdelivr.net',
  'https://fonts.googleapis.com',
  'https://fonts.gstatic.com'
];

// External assets to prewarm/cache for offline icons/fonts (best-effort)
const EXTERNAL_WARM = [
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-solid-900.woff2',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-regular-400.woff2',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-brands-400.woff2',
  'https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap'
];

function isAPI(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/api/');
}

function isStaticAsset(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/static/');
}

function isUploads(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/uploads/');
}

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Queue POST requests for offline (API JSON and non-multipart form posts)
  if (request.method === 'POST') {
    try {
      const url = new URL(request.url);
      const same = isSameOrigin(url.href);
      if (same) {
        const ct = request.headers.get('content-type') || '';
        // API JSON posts (except uploads)
        if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/uploads/')) {
          event.respondWith(handleJsonPostWithQueue(request));
          return;
        }
        // App form posts (exclude multipart uploads)
        if ((url.pathname.startsWith('/lands/') || url.pathname.startsWith('/ads/')) && !ct.includes('multipart/form-data')) {
          event.respondWith((async () => {
            try {
              return await fetch(request);
            } catch (_) {
              // Fallback: queue and show offline page
              try { await handleJsonPostWithQueue(request); } catch(_e) {}
              const pc = await caches.open(PRECACHE);
              const off = await pc.match(OFFLINE_URL);
              return off || new Response('queued', { status: 202 });
            }
          })());
          return;
        }
      }
    } catch(_) {}
  }

  // Navigation requests: App Shell network-first → offline fallback
  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        // Use preloaded response if available
        const preload = await event.preloadResponse;
        const resp = preload || await fetch(request);
        // Optionally update precache copy of shell routes
        const cache = await caches.open(PRECACHE);
        try { cache.put(request, resp.clone()); } catch(_) {}
        return resp;
      } catch (_) {
        const cache = await caches.open(PRECACHE);
        // Prefer exact cached page; else try cached /app shell; else offline
        const cached = await cache.match(request);
        if (cached) return cached;
        const appShell = await cache.match('/app');
        if (appShell) return appShell;
        return await cache.match(OFFLINE_URL);
      }
    })());
    return;
  }

  // API: stale-while-revalidate
  if (isAPI(request) && request.method === 'GET') {
    event.respondWith((async () => {
      const cache = await caches.open(API_CACHE);
      const cached = await cache.match(request);
      const networkPromise = fetch(request)
        .then(async (resp) => { try { cache.put(request, resp.clone()); await trimCache(API_CACHE, 60); } catch(_) {} return resp; })
        .catch(() => undefined);
      return cached || (await networkPromise) || new Response(JSON.stringify({ ok: false, offline: true }), { status: 503, headers: { 'Content-Type': 'application/json' } });
    })());
    return;
  }

  // Static assets: stale-while-revalidate (return cache immediately, update in background)
  if ((isStaticAsset(request) || isUploads(request)) && request.method === 'GET') {
    event.respondWith((async () => {
      const cache = await caches.open(RUNTIME);
      const cached = await cache.match(request);
      if (cached) {
        // Kick off background update
        event.waitUntil((async () => {
          try {
            const resp = await fetch(request, { credentials: 'same-origin', cache: 'no-store' });
            try { await cache.put(request, resp.clone()); await trimCache(RUNTIME, 150); } catch(_) {}
          } catch(_) {}
        })());
        return cached;
      }
      try {
        const resp = await fetch(request, { credentials: 'same-origin' });
        try { await cache.put(request, resp.clone()); await trimCache(RUNTIME, 150); } catch(_) {}
        return resp;
      } catch (_) {
        // Image fallback placeholder (if asset is an image)
        const accept = request.headers.get('accept') || '';
        if (accept.includes('image')) {
          const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="100%" height="100%" fill="#e5e7eb"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#9ca3af" font-family="sans-serif" font-size="24">Offline</text></svg>';
          return new Response(svg, { headers: { 'Content-Type': 'image/svg+xml' } });
        }
        throw _;
      }
    })());
    return;
  }

  // External CDN assets: cache-first (opaque allowed)
  try {
    const url = new URL(request.url);
    if (EXTERNAL_ORIGINS.includes(url.origin) && request.method === 'GET') {
      event.respondWith((async () => {
        const cache = await caches.open(ICONS_CACHE);
        const cached = await cache.match(request, { ignoreVary: true });
        if (cached) return cached;
        try {
          const resp = await fetch(request, { mode: 'no-cors' }); // may be opaque
          try { cache.put(request, resp.clone()); } catch(_) {}
          return resp;
        } catch (_) {
          return new Response('', { status: 504 });
        }
      })());
      return;
    }
  } catch(_) {}

  // Default: network-first with cache fallback for GET
  if (request.method === 'GET') {
    event.respondWith((async () => {
      const cache = await caches.open(RUNTIME);
      try {
        const resp = await fetch(request);
        try { cache.put(request, resp.clone()); await trimCache(RUNTIME, 150); } catch(_) {}
        return resp;
      } catch (_) {
        const cached = await cache.match(request);
        if (cached) return cached;
        // As a last resort for same-origin HTML, show offline page
        const url = new URL(request.url);
        if (isSameOrigin(url.href) && (request.headers.get('accept') || '').includes('text/html')) {
          const pc = await caches.open(PRECACHE);
          const off = await pc.match(OFFLINE_URL);
          if (off) return off;
        }
        return new Response('Offline', { status: 503 });
      }
    })());
  }
});

// Warm-up handler (list of URLs from the app)
self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data && data.type === 'VINOR_WARMUP') {
    const urls = Array.isArray(data.urls) ? data.urls : [];
    event.waitUntil((async () => {
      const cache = await caches.open(PRECACHE);
      await Promise.all(urls.map(async (u) => {
        try { const req = new Request(u, { credentials: 'same-origin' }); const resp = await fetch(req); cache.put(req, resp); } catch(_) {}
      }));
    })());
  }
  // Trigger background sync warmup (if supported)
  if (data && data.type === 'VINOR_WARMUP_SYNC') {
    if (self.registration && 'sync' in self.registration) {
      try { self.registration.sync.register('vinor-warmup'); } catch(_) {}
    }
  }
  // Warm external assets upon request from client
  if (data && data.type === 'VINOR_WARMUP_EXT') {
    event.waitUntil((async () => {
      try {
        const rcache = await caches.open(RUNTIME);
        await Promise.all(EXTERNAL_WARM.map(async (url) => {
          try { const resp = await fetch(url, { mode: 'no-cors', cache: 'no-store' }); await rcache.put(url, resp.clone()); } catch(_) {}
        }));
      } catch(_) {}
    })());
  }
  // Queue a generic request (e.g., finalize GET) from client
  if (data && data.type === 'VINOR_QUEUE') {
    const url = String(data.url || '/');
    const method = String(data.method || 'GET').toUpperCase();
    const headers = data.headers || {};
    const body = data.body || null;
    event.waitUntil((async () => {
      try {
        await queueRequest({ url, method, headers, body, credentials: 'include', ts: Date.now() });
        if (self.registration && 'sync' in self.registration) {
          try { await self.registration.sync.register('vinor-sync'); } catch(_) {}
        }
      } catch(_) {}
    })());
  }
  // Queue a form POST provided by page script
  if (data && data.type === 'VINOR_QUEUE_FORM') {
    const url = String(data.url || '/');
    const method = String(data.method || 'POST').toUpperCase();
    const headers = data.headers || { 'Content-Type': 'application/x-www-form-urlencoded' };
    const body = data.body || '';
    event.waitUntil((async () => {
      try {
        await queueRequest({ url, method, headers, body, credentials: 'include', ts: Date.now() });
        if (self.registration && 'sync' in self.registration) {
          try { await self.registration.sync.register('vinor-sync'); } catch(_) {}
        }
      } catch(_) {}
    })());
  }
});

// Background sync to refresh important URLs when back online
self.addEventListener('sync', (event) => {
  if (event.tag === 'vinor-warmup') {
    event.waitUntil((async () => {
      const urls = ['/', '/app', '/api/lands/approved', '/api/express-listings'];
      const cache = await caches.open(PRECACHE);
      await Promise.all(urls.map(async (u) => {
        try { const req = new Request(u, { credentials: 'same-origin' }); const resp = await fetch(req, { cache: 'no-store' }); cache.put(req, resp); } catch(_) {}
      }));
    })());
  }
});

// Background sync: replay queued requests when back online
self.addEventListener('sync', (event) => {
  if (event.tag === 'vinor-sync') {
    event.waitUntil(replayQueue());
  }
});

// ===== Background Sync Queue (IndexedDB) =====
function openQueueDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('vinor-sync-db', 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('queue')) db.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function queueRequest(entry) {
  try {
    const db = await openQueueDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction('queue', 'readwrite');
      tx.objectStore('queue').add(entry);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {}
}

async function replayQueue() {
  const db = await openQueueDb();
  const entries = await new Promise((resolve, reject) => {
    const out = [];
    const tx = db.transaction('queue', 'readonly');
    const store = tx.objectStore('queue');
    const req = store.openCursor();
    req.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) { out.push({ id: cursor.key, ...cursor.value }); cursor.continue(); }
      else { resolve(out); }
    };
    req.onerror = () => reject(req.error);
  });

  for (const item of entries) {
    try {
      const resp = await fetch(item.url, {
        method: item.method || 'POST',
        headers: item.headers || { 'Content-Type': 'application/json' },
        body: item.body || null,
        credentials: item.credentials || 'same-origin',
      });
      if (resp && resp.ok) {
        await new Promise((resolve, reject) => {
          const tx = db.transaction('queue', 'readwrite');
          tx.objectStore('queue').delete(item.id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
      }
    } catch (_) { /* keep in queue */ }
  }
}

async function handleJsonPostWithQueue(request) {
  try {
    return await fetch(request);
  } catch (e) {
    try {
      const cloned = request.clone();
      let body = null;
      try { body = await cloned.text(); } catch(_) {}
      const headers = {};
      request.headers.forEach((v, k) => { headers[k] = v; });
      await queueRequest({ url: request.url, method: request.method, headers, body, credentials: 'include', ts: Date.now() });
      if (self.registration && 'sync' in self.registration) {
        try { await self.registration.sync.register('vinor-sync'); } catch(_) {}
      }
    } catch(_) {}
    return new Response(JSON.stringify({ ok: true, queued: true }), { status: 202, headers: { 'Content-Type': 'application/json' } });
  }
}

