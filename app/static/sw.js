// app/static/sw.js — Vinor PWA (cache + push)
// تجربه سریع، امن و شفاف

// ================== Cache ==================
const CACHE_NAME = 'vinor-cache-v3';
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
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));

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

  // فقط GET
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // عدم کش برای API و ادمین
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
        // کش فقط اگر پاسخ داخلی و 200 بود
        if (respClone.ok && respClone.type === 'basic') {
          caches.open(CACHE_NAME).then((c) => c.put(req, respClone)).catch(()=>{});
        }
        return preload;
      }

      // تلاش شبکه
      const networkResp = await fetch(req);
      // کش فقط اگر پاسخ داخلی و 200 بود
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
        // fallback آفلاین برای صفحات
        const appFallback = await cache.match('/app');
        if (appFallback) return appFallback;
      }

      // آخرین تلاش: برگرداندن هر چیزی از کش اگر یافت شد
      const any = await caches.match(req);
      if (any) return any;

      // در نهایت، خاموش؛ می‌گذاریم مرورگر خطا را نشان دهد
      throw e;
    }
  })());
});

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
