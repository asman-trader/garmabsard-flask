/*
  وینور اکسپرس - Service Worker جداگانه برای پنل همکاران اکسپرس
  Scope: '/express/partner/'
  این Service Worker کاملاً مجزا از PWA اصلی وینور است
*/

const VERSION = 'v1.0.1-2025-12-23';
const PRECACHE = `express-partner-precache-${VERSION}`;
const RUNTIME = `express-partner-runtime-${VERSION}`;
const API_CACHE = `express-partner-api-${VERSION}`;
const ICONS_CACHE = `express-partner-icons-${VERSION}`;

// تابع برای محدود کردن اندازه cache
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

// URLs برای precache در نصب (مختص Express Partner)
// توجه: dashboard و صفحات session-based را precache نمی‌کنیم
const PRECACHE_URLS = [
  '/express/partner/login',
  // dashboard را precache نمی‌کنیم چون محتوای آن session-based است
  // '/express/partner/dashboard',
  // profile و commissions هم session-based هستند
  // '/express/partner/profile',
  // '/express/partner/commissions',
  '/express/partner/notes',
  '/express/partner/apply',
  '/express/partner/thanks',
  // Manifest
  '/express/partner/manifest.webmanifest',
  // Icons (استفاده از آیکون‌های مشترک)
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

// Assets محلی برای offline
const LOCAL_ASSETS = [
  '/static/vendor/fontawesome/css/all.min.css',
  '/static/vendor/fontawesome/webfonts/fa-solid-900.woff2',
  '/static/vendor/fontawesome/webfonts/fa-regular-400.woff2',
  '/static/vendor/fontawesome/webfonts/fa-brands-400.woff2',
  '/static/fonts/vazirmatn.css'
];

// نصب Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(PRECACHE);
    try {
      await cache.addAll(PRECACHE_URLS.concat(LOCAL_ASSETS).map((u) => new Request(u, { credentials: 'same-origin' })));
    } catch (err) {
      console.error('Express Partner SW: Cache install error', err);
    }
    await self.skipWaiting();
  })());
});

// فعال‌سازی Service Worker
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    // فقط cache های مربوط به Express Partner را نگه دار
    await Promise.all(
      keys.filter((k) => !k.startsWith('express-partner-')).map((k) => caches.delete(k))
    );
    // فعال‌سازی Navigation Preload برای سرعت بیشتر
    try {
      if (self.registration.navigationPreload) {
        await self.registration.navigationPreload.enable();
      }
    } catch (_) {}
    await self.clients.claim();
  })());
});

// بررسی same-origin
function isSameOrigin(url) {
  try {
    return new URL(url, self.location.origin).origin === self.location.origin;
  } catch {
    return false;
  }
}

// بررسی Express Partner route
function isExpressPartnerRoute(url) {
  return url.pathname.startsWith('/express/partner/');
}

// بررسی API های Express Partner
function isExpressPartnerAPI(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/api/express/') || url.pathname.startsWith('/express/partner/api/');
}

// بررسی static assets
function isStaticAsset(request) {
  const url = new URL(request.url);
  if (!isSameOrigin(url.href)) return false;
  return url.pathname.startsWith('/static/');
}

// Handle fetch events
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // فقط Express Partner routes را handle کن
  if (!isExpressPartnerRoute(url) && !isExpressPartnerAPI(request) && !isStaticAsset(request)) {
    return; // بگذار browser آن را handle کند
  }

  // POST requests (API و form submissions)
  if (request.method === 'POST') {
    try {
      if (isSameOrigin(url.href)) {
        const ct = request.headers.get('content-type') || '';
        // API JSON posts
        if (isExpressPartnerAPI(request)) {
          event.respondWith((async () => {
            try {
              return await fetch(request);
            } catch (_) {
              return new Response(JSON.stringify({ error: 'Offline', message: 'شما آفلاین هستید' }), { 
                status: 503, 
                headers: { 'Content-Type': 'application/json' } 
              });
            }
          })());
          return;
        }
        // Form posts (بدون multipart uploads)
        if (isExpressPartnerRoute(url) && !ct.includes('multipart/form-data')) {
          event.respondWith((async () => {
            try {
              return await fetch(request);
            } catch (_) {
              return new Response('Offline', { status: 503 });
            }
          })());
          return;
        }
      }
    } catch (_) {}
  }

  // Navigation requests: Network-first با offline fallback
  if (request.mode === 'navigate' && isExpressPartnerRoute(url)) {
    event.respondWith((async () => {
      // اگر درخواست AJAX است (X-Requested-With header)، از cache استفاده نکن
      const isAjaxRequest = request.headers.get('X-Requested-With') === 'XMLHttpRequest';
      
      try {
        // استفاده از preloaded response اگر موجود باشد
        const preload = await event.preloadResponse;
        const resp = preload || await fetch(request);
        // نباید redirect responses (302/301) یا responses با Vary: Cookie را cache کنیم
        // چون redirect بر اساس session است و نباید cache شود
        const isRedirect = resp.status >= 300 && resp.status < 400;
        const hasVaryCookie = resp.headers.get('Vary') && resp.headers.get('Vary').includes('Cookie');
        const noCache = resp.headers.get('Cache-Control') && (
          resp.headers.get('Cache-Control').includes('no-store') || 
          resp.headers.get('Cache-Control').includes('no-cache')
        );
        
        // برای AJAX requests یا responses با no-cache، cache نکن
        if (!isAjaxRequest && !isRedirect && !hasVaryCookie && !noCache) {
          // به‌روزرسانی cache
          const cache = await caches.open(PRECACHE);
          try {
            cache.put(request, resp.clone());
          } catch (_) {}
        }
        return resp;
      } catch (_) {
        // برای AJAX requests، از cache استفاده نکن و خطا برگردان
        if (isAjaxRequest) {
          return new Response('Network error', { status: 503 });
        }
        const cache = await caches.open(PRECACHE);
        // جستجوی cached page
        const cached = await cache.match(request);
        if (cached) return cached;
        // Fallback به dashboard shell
        const dashboardShell = await cache.match('/express/partner/dashboard');
        if (dashboardShell) return dashboardShell;
        // بدون صفحه آفلاین: خطای شبکه
        return new Response('Offline', { status: 503 });
      }
    })());
    return;
  }

  // Static assets: Cache-first با background update
  if (isStaticAsset(request)) {
    event.respondWith((async () => {
      const cache = await caches.open(RUNTIME);
      const cached = await cache.match(request);
      if (cached) {
        // به‌روزرسانی در پس‌زمینه
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

  // Express Partner API: Network-first با cache fallback
  if (isExpressPartnerAPI(request)) {
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
        return new Response(JSON.stringify({ error: 'Offline', message: 'شما آفلاین هستید' }), { 
          status: 503, 
          headers: { 'Content-Type': 'application/json' } 
        });
      }
    })());
    return;
  }
});

// Background Sync برای درخواست‌های queued
self.addEventListener('sync', (event) => {
  if (event.tag.startsWith('express-partner-')) {
    event.waitUntil((async () => {
      // Handle background sync برای Express Partner
      // می‌تواند برای sync کردن داده‌ها در پس‌زمینه استفاده شود
      console.log('Express Partner: Background sync', event.tag);
    })());
  }
});

// Push notifications برای Express Partner
self.addEventListener('push', (event) => {
  if (event.data) {
    try {
      const data = event.data.json();
      const title = data.title || 'پنل همکاران وینور';
      const options = {
        body: data.body || 'پیام جدید',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-48.png',
        tag: 'express-partner-notification',
        data: data.url || '/express/partner/dashboard',
        dir: 'rtl',
        lang: 'fa'
      };
      event.waitUntil(self.registration.showNotification(title, options));
    } catch (_) {
      event.waitUntil(self.registration.showNotification('پنل همکاران وینور', {
        body: 'پیام جدید',
        icon: '/static/icons/icon-192.png',
        dir: 'rtl',
        lang: 'fa'
      }));
    }
  }
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data || '/express/partner/dashboard';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // جستجوی window باز Express Partner
      for (const client of clientList) {
        if (client.url.includes('/express/partner/') && 'focus' in client) {
          return client.focus().then(() => {
            if ('navigate' in client) {
              return client.navigate(url);
            }
          });
        }
      }
      // باز کردن window جدید
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
  // برای tracking می‌توان استفاده کرد
  console.log('Express Partner: Notification closed', event.notification.tag);
});

// پیام‌های custom از client
self.addEventListener('message', (event) => {
  if (event.data && event.data.type) {
    switch (event.data.type) {
      case 'VINOR_WARMUP':
        // Warmup کردن routes
        if (event.data.urls && Array.isArray(event.data.urls)) {
          event.data.urls.forEach((url) => {
            fetch(url, { cache: 'no-cache' }).catch(() => {});
          });
        }
        break;
      case 'SKIP_WAITING':
        self.skipWaiting();
        break;
      default:
        console.log('Express Partner SW: Unknown message type', event.data.type);
    }
  }
});
