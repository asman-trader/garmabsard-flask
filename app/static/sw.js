// app/static/sw.js — Vinor PWA (cache + push)
// تجربه سریع، امن و شفاف

// ================== Cache ==================
const CACHE_NAME = 'vinor-cache-v4';
const API_CACHE_NAME = 'vinor-api-cache-v1';
const ASSETS = [
  '/',                         // لندینگ
  '/app',                      // اپ اصلی (Mobile-first)
  '/manifest.webmanifest',     // مانیفست
  '/static/sw.js',             // خود SW (مسیر صحیح)
  '/static/favicon-32x32.png',
  '/static/icons/icon-192.png'
  // در صورت نیاز، فایل‌های استاتیک حیاتی دیگر را اضافه کنید.
];

// نصب و پرکردن کش اولیه
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(
        ASSETS.map((u) => new Request(u, { cache: 'reload' }))
      ))
      .catch(() => null)
  );
});

// فعال‌سازی، پاکسازی کش‌های قدیمی و فعال‌کردن navigation preload (در صورت پشتیبانی)
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // پاکسازی کش‌های قدیمی
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME && k !== API_CACHE_NAME).map(k => caches.delete(k)));

    // فعال‌سازی فوری کنترل SW
    await self.clients.claim();

    // فعال‌سازی navigation preload (اختیاری)
    if ('navigationPreload' in self.registration) {
      try { await self.registration.navigationPreload.enable(); } catch (e) {}
    }
  })());
});

// استراتژی: شبکه‌اول با fallback به کش
// - فقط درخواست‌های GET کش می‌شوند
// - مسیرهای API و ادمین کش نمی‌شوند
// - برای ناوبری (HTML) در حالت آفلاین، به /app fallback می‌دهیم
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // ===== Background Sync for JSON POSTs (e.g., /api/push/subscribe) =====
  if (req.method === 'POST' && url.pathname.startsWith('/api/')) {
    event.respondWith(handleJsonPostWithQueue(req));
    return;
  }

  // فقط GET
  if (req.method !== 'GET') return;

  // Dynamic offline for a safe GET API
  if (url.pathname === '/api/lands/approved') {
    event.respondWith(networkFirstApi(req));
    return;
  }

  // عدم کش برای سایر مسیرهای API و ادمین
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/')) {
    return; // allow default fetch
  }

  // ناوبری (صفحات HTML)
  const isNavigation = req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');

  event.respondWith((async () => {
    try {
      // اگر navigation preload فعال است، اول آن را تست کن
      const preload = await event.preloadResponse;
      if (preload) {
        const respClone = preload.clone();
        if (respClone.ok && respClone.type === 'basic') {
          caches.open(CACHE_NAME).then((c) => c.put(req, respClone)).catch(()=>{});
        }
        return preload;
      }

      // تلاش شبکه
      const networkResp = await fetch(req);
      if (networkResp && networkResp.ok && networkResp.type === 'basic') {
        const clone = networkResp.clone();
        caches.open(CACHE_NAME).then((c) => c.put(req, clone)).catch(()=>{});
      }
      return networkResp;
    } catch (e) {
      // آفلاین یا خطا → fallback
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(req);
      if (cached) return cached;

      if (isNavigation) {
        const appFallback = await cache.match('/app');
        if (appFallback) return appFallback;
      }

      const any = await caches.match(req);
      if (any) return any;

      throw e;
    }
  })());
});

// ===== Helpers: API network-first with cache fallback =====
async function networkFirstApi(request) {
  try {
    const net = await fetch(request);
    if (net && net.ok) {
      const clone = net.clone();
      caches.open(API_CACHE_NAME).then((c) => c.put(request, clone)).catch(()=>{});
    }
    return net;
  } catch (e) {
    const cache = await caches.open(API_CACHE_NAME);
    const cached = await cache.match(request);
    if (cached) return cached;
    throw e;
  }
}

// ===== Background Sync Queue (IndexedDB) =====
function openQueueDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('vinor-sync-db', 1);
    req.onupgradeneeded = (e) => {
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
      if (cursor) {
        out.push({ id: cursor.key, ...cursor.value });
        cursor.continue();
      } else {
        resolve(out);
      }
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
    } catch (e) {
      // همچنان در صف بماند
    }
  }
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'vinor-sync') {
    event.waitUntil(replayQueue());
  }
});

async function handleJsonPostWithQueue(request) {
  try {
    // تلاش عادی شبکه
    return await fetch(request);
  } catch (e) {
    // آفلاین/خطا → صف
    try {
      const cloned = request.clone();
      let body = null;
      try {
        body = await cloned.text();
      } catch (_) {}
      const headers = {};
      request.headers.forEach((v, k) => { headers[k] = v; });

      await queueRequest({
        url: request.url,
        method: request.method,
        headers,
        body,
        credentials: 'include',
        ts: Date.now(),
      });
      if (self.registration && self.registration.sync) {
        try { await self.registration.sync.register('vinor-sync'); } catch (_) {}
      }
    } catch (_) {}

    return new Response(JSON.stringify({ ok: true, queued: true }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// ================== Push Notifications ==================
// نکته: پخش مستقیم صدا از SW ممکن نیست؛
// به کلاینت‌ها پیام می‌دهیم تا صدا را در صفحه پخش کنند.
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'اعلان جدید', body: event.data ? event.data.text() : '' };
  }

  const title = data.title || 'وینور – اعلان جدید';
  const body  = data.body  || 'پیام جدیدی از وینور';
  const url   = data.url   || '/notifications';
  const icon  = data.icon  || '/static/icons/icon-192.png';
  const badge = data.badge || '/static/icons/icon-192.png';
  const tag   = data.tag   || 'vinor-push';

  const options = {
    body,
    icon,
    badge,
    tag,
    renotify: true,
    data: { url },
    // ویبره روی موبایل (در دسکتاپ بی‌اثر است)
    vibrate: [100, 50, 100],
    // می‌توانید اکشن‌ها را نیز اضافه کنید (اختیاری):
    // actions: [{action:'open', title:'باز کردن'}]
  };

  event.waitUntil((async () => {
    // پیام به تمام پنجره‌های باز برای پخش صدا/آپدیت UI
    const clientsList = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
    clientsList.forEach(c => c.postMessage({ type: 'PUSH_RECEIVED', payload: data }));

    // نمایش نوتیف سیستم
    await self.registration.showNotification(title, options);
  })());
});

// کلیک روی نوتیف: فوکوس تب موجود یا بازکردن URL هدف
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/notifications';

  event.waitUntil((async () => {
    const allClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    // اگر تب مقصد باز است، همان را فوکوس کن
    for (const client of allClients) {
      try {
        const u = new URL(client.url);
        const target = new URL(url, self.registration.scope);
        if (u.pathname === target.pathname) {
          return client.focus();
        }
      } catch (e) {}
    }
    // در غیر این صورت یک تب جدید باز کن
    if (clients.openWindow) {
      return clients.openWindow(url);
    }
  })());
});

// (اختیاری) بستن نوتیف — جای مناسب برای لاگ/آنالیتیکس
self.addEventListener('notificationclose', (event) => {
  // console.log('notification closed', event.notification?.tag);
});
