/*
  Vinor Express Partner Service Worker – offline-first shell with runtime caching
  Scope: '/express/partner/'
*/

const VERSION = 'v1.0.0-2025-01-15';
const PRECACHE = `express-partner-precache-${VERSION}`;
const RUNTIME = `express-partner-runtime-${VERSION}`;
const API_CACHE = `express-partner-api-${VERSION}`;
const ICONS_CACHE = `express-partner-icons-${VERSION}`;

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

// URLs to precache at install (Express Partner specific)
const OFFLINE_URL = '/static/offline.html';
const PRECACHE_URLS = [
  '/express/partner/login',
  '/express/partner/dashboard',
  '/express/partner/profile',
  '/express/partner/commissions',
  '/express/partner/notes',
  '/express/partner/apply',
  // Manifest and offline fallback
  '/express/partner/manifest.webmanifest',
  OFFLINE_URL,
  // Icons/sounds (best-effort if exist)
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

// Precache local icon/font assets for full offline
const LOCAL_ICON_FONT_ASSETS = [
  '/static/vendor/fontawesome/css/all.min.css',
  '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
  '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2',
  '/static/vendor/fontawesome/webfonts/fa-brands-400.woff2',
  '/static/fonts/vazirmatn.css'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(PRECACHE);
    try { 
      await cache.addAll(PRECACHE_URLS.concat(LOCAL_ICON_FONT_ASSETS).map((u) => new Request(u, { credentials: 'same-origin' }))); 
    } catch(_) {}
    // Best-effort: prewarm external CSS/fonts/icons into dedicated ICONS cache
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
      keys.filter((k) => !k.startsWith('express-partner-')).map((k) => caches.delete(k))
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
  return url.pathname.startsWith('/api/express/');
}

function isStaticAsset(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/static/');
}

function isExpressPartnerRoute(url) {
  return url.pathname.startsWith('/express/partner/');
}

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle Express Partner routes
  const url = new URL(request.url);
  if (!isExpressPartnerRoute(url) && !isStaticAsset(request) && !isAPI(request)) {
    return; // Let browser handle non-Express Partner routes
  }

  // Queue POST requests for offline (API JSON and non-multipart form posts)
  if (request.method === 'POST') {
    try {
      if (isSameOrigin(url.href)) {
        const ct = request.headers.get('content-type') || '';
        // API JSON posts (Express Partner APIs)
        if (isAPI(request)) {
          event.respondWith((async () => {
            try {
              return await fetch(request);
            } catch (_) {
              // Fallback: queue and show offline page
              const pc = await caches.open(PRECACHE);
              const off = await pc.match(OFFLINE_URL);
              return off || new Response('queued', { status: 202 });
            }
          })());
          return;
        }
        // Form posts (exclude multipart uploads)
        if (isExpressPartnerRoute(url) && !ct.includes('multipart/form-data')) {
          event.respondWith((async () => {
            try {
              return await fetch(request);
            } catch (_) {
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

  // Navigation requests: Express Partner Shell network-first → offline fallback
  if (request.mode === 'navigate' && isExpressPartnerRoute(url)) {
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
        // Prefer exact cached page; else try cached dashboard shell; else offline
        const cached = await cache.match(request);
        if (cached) return cached;
        const dashboardShell = await cache.match('/express/partner/dashboard');
        if (dashboardShell) return dashboardShell;
        return await cache.match(OFFLINE_URL);
      }
    })());
    return;
  }

  // Static assets: Cache-first with runtime update
  if (isStaticAsset(request)) {
    event.respondWith((async () => {
      const cache = await caches.open(RUNTIME);
      const cached = await cache.match(request);
      if (cached) {
        // Update in background
        fetch(request).then((resp) => {
          if (resp.ok) cache.put(request, resp);
        }).catch(() => {});
        return cached;
      }
      try {
        const resp = await fetch(request);
        if (resp.ok) cache.put(request, resp.clone());
        return resp;
      } catch (_) {
        return new Response('Offline', { status: 503 });
      }
    })());
    return;
  }

  // Express Partner API: Network-first with cache fallback
  if (isAPI(request)) {
    event.respondWith((async () => {
      const cache = await caches.open(API_CACHE);
      try {
        const resp = await fetch(request);
        if (resp.ok) {
          await trimCache(API_CACHE, 50);
          cache.put(request, resp.clone());
        }
        return resp;
      } catch (_) {
        const cached = await cache.match(request);
        if (cached) return cached;
        return new Response(JSON.stringify({ error: 'Offline' }), { 
          status: 503, 
          headers: { 'Content-Type': 'application/json' } 
        });
      }
    })());
    return;
  }
});

// Background Sync for queued requests (Express Partner specific)
self.addEventListener('sync', (event) => {
  if (event.tag.startsWith('express-partner-')) {
    event.waitUntil((async () => {
      // Handle background sync for Express Partner
      // Implementation can be added based on specific needs
    })());
  }
});

// Push notifications for Express Partner (if needed)
self.addEventListener('push', (event) => {
  if (event.data) {
    try {
      const data = event.data.json();
      const title = data.title || 'وینور اکسپرس';
      const options = {
        body: data.body || 'پیام جدید',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-48.png',
        tag: 'express-partner-notification',
        data: data.url || '/express/partner/dashboard'
      };
      event.waitUntil(self.registration.showNotification(title, options));
    } catch (_) {
      event.waitUntil(self.registration.showNotification('وینور اکسپرس', {
        body: 'پیام جدید',
        icon: '/static/icons/icon-192.png'
      }));
    }
  }
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data || '/express/partner/dashboard';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/express/partner/') && 'focus' in client) {
          return client.focus().then(() => client.navigate(url));
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

