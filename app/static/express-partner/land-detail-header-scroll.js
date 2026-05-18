/**
 * جزئیات فایل همکار — مخفی شدن هدر شفاف + چسباندن گالری به لبهٔ بالای viewport
 */
(function () {
  'use strict';

  var abort = null;
  var lastY = 0;
  var hidden = false;
  var ticking = false;

  var HIDE_AFTER_Y = 20;
  var SHOW_AT_TOP_Y = 6;
  var MIN_DELTA = 5;

  function scrollYNow() {
    if (typeof window.scrollY === 'number' && !Number.isNaN(window.scrollY)) {
      return window.scrollY;
    }
    var shell = document.getElementById('tg-page-shell');
    if (shell && shell.scrollTop) return shell.scrollTop;
    var se = document.scrollingElement;
    return se && se.scrollTop ? se.scrollTop : 0;
  }

  function resetScrollTop() {
    try {
      window.scrollTo(0, 0);
      var shell = document.getElementById('tg-page-shell');
      if (shell) shell.scrollTop = 0;
      var se = document.scrollingElement;
      if (se) se.scrollTop = 0;
    } catch (_) {}
  }

  function setHeaderHidden(header, on) {
    var want = !!on;
    if (!header || want === hidden) return;
    hidden = want;
    header.classList.toggle('is-header-hidden', want);
    header.setAttribute('aria-hidden', want ? 'true' : 'false');
  }

  function updateHeader() {
    var header = document.getElementById('landDetailPartnerHeader');
    if (!header) return;

    var y = scrollYNow();
    var dy = y - lastY;

    if (y <= SHOW_AT_TOP_Y) {
      setHeaderHidden(header, false);
    } else if (dy > MIN_DELTA && y > HIDE_AFTER_Y) {
      setHeaderHidden(header, true);
    } else if (dy < -MIN_DELTA) {
      setHeaderHidden(header, false);
    }

    lastY = y;
  }

  function queueUpdate() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      ticking = false;
      updateHeader();
    });
  }

  function clearGalleryPull() {
    var gallery = document.getElementById('landGallery');
    if (gallery) gallery.style.removeProperty('margin-top');
  }

  function flushPartnerGalleryTop() {
    var gallery = document.getElementById('landGallery');
    if (!gallery) return;

    var top = gallery.getBoundingClientRect().top;
    var safe = 'env(safe-area-inset-top, 0px)';
    if (top <= 0.5) {
      gallery.style.setProperty('margin-top', 'calc(-1 * ' + safe + ')', 'important');
      return;
    }

    var pull = Math.ceil(top);
    gallery.style.setProperty('margin-top', 'calc(-1 * ' + safe + ' - ' + pull + 'px)', 'important');
  }

  function scheduleGalleryFlush() {
    flushPartnerGalleryTop();
    requestAnimationFrame(flushPartnerGalleryTop);
    window.setTimeout(flushPartnerGalleryTop, 50);
    window.setTimeout(flushPartnerGalleryTop, 200);
  }

  function bindMediaFlush() {
    var video = document.getElementById('landVideo');
    var img = document.getElementById('landMainImage');
    if (video) {
      video.addEventListener('loadeddata', scheduleGalleryFlush, { once: true });
      video.addEventListener('loadedmetadata', scheduleGalleryFlush, { once: true });
    }
    if (img) {
      if (img.complete) scheduleGalleryFlush();
      else img.addEventListener('load', scheduleGalleryFlush, { once: true });
    }
  }

  function unbind() {
    if (!abort) return;
    try { abort.abort(); } catch (_) {}
    abort = null;
    clearGalleryPull();
  }

  function bind() {
    unbind();
    var header = document.getElementById('landDetailPartnerHeader');
    if (!header) return;

    abort = new AbortController();
    var signal = abort.signal;
    var opts = { passive: true, signal: signal };

    hidden = false;
    resetScrollTop();
    lastY = scrollYNow();
    header.classList.remove('is-header-hidden');
    header.removeAttribute('aria-hidden');

    window.addEventListener('scroll', queueUpdate, opts);
    document.addEventListener('scroll', queueUpdate, Object.assign({ capture: true }, opts));
    window.addEventListener('resize', scheduleGalleryFlush, opts);
    window.addEventListener('orientationchange', scheduleGalleryFlush, opts);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', scheduleGalleryFlush, opts);
      window.visualViewport.addEventListener('scroll', scheduleGalleryFlush, opts);
    }
    var shell = document.getElementById('tg-page-shell');
    if (shell) shell.addEventListener('scroll', queueUpdate, opts);

    queueUpdate();
    scheduleGalleryFlush();
    bindMediaFlush();
  }

  function scheduleBind() {
    requestAnimationFrame(bind);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scheduleBind);
  } else {
    scheduleBind();
  }

  document.addEventListener('vinor:express-page-swap', scheduleBind);
})();
