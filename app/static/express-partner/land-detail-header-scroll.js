/**
 * جزئیات فایل همکار — مخفی شدن هدر شفاف هنگام اسکرول به پایین
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

  function unbind() {
    if (!abort) return;
    try { abort.abort(); } catch (_) {}
    abort = null;
  }

  function flushPartnerGalleryTop() {
    var gallery = document.getElementById('landGallery');
    var slot = document.querySelector('.land-detail-partner-gallery-hero') || document.querySelector('.land-detail-partner-gallery-top');
    if (!gallery || !slot) return;
    slot.style.marginTop = '';
    var top = gallery.getBoundingClientRect().top;
    if (top > 0.5) {
      slot.style.marginTop = (-Math.ceil(top)) + 'px';
    }
  }

  function scheduleGalleryFlush() {
    flushPartnerGalleryTop();
    requestAnimationFrame(flushPartnerGalleryTop);
    window.setTimeout(flushPartnerGalleryTop, 60);
    window.setTimeout(flushPartnerGalleryTop, 280);
  }

  function bind() {
    unbind();
    var header = document.getElementById('landDetailPartnerHeader');
    if (!header) return;

    abort = new AbortController();
    var signal = abort.signal;
    var opts = { passive: true, signal: signal };

    hidden = false;
    lastY = scrollYNow();
    header.classList.remove('is-header-hidden');
    header.removeAttribute('aria-hidden');

    window.addEventListener('scroll', queueUpdate, opts);
    document.addEventListener('scroll', queueUpdate, Object.assign({ capture: true }, opts));
    window.addEventListener('resize', scheduleGalleryFlush, opts);
    var shell = document.getElementById('tg-page-shell');
    if (shell) shell.addEventListener('scroll', queueUpdate, opts);
    queueUpdate();
    scheduleGalleryFlush();
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
