# app/routes/public.py
import os
from urllib.parse import quote

from flask import (
    render_template, send_from_directory, request, abort,
    redirect, url_for, session, make_response, current_app, flash
)

from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_express_lands_cached
from ..utils.storage import load_express_partners, load_landing_views, save_landing_views, load_express_reposts
from ..utils.storage import load_express_views, save_express_views, load_express_assignments
from ..utils.share_tokens import decode_partner_ref
from ..utils.images import (
    prepare_variants_dict,
    variant_headers_for_width,
)
from datetime import datetime
from time import time as _now

# --- very small in-memory microcache (5-20s) for public pages ---
_MICROCACHE: dict = {}  # key -> (expires_at, payload)
_SETTINGS_CACHE: dict = {}  # Cache for settings
def _mc_get(key: str):
    try:
        exp, val = _MICROCACHE.get(key, (0, None))
        if exp and exp > _now():
            return val
    except Exception:
        return None
    return None
def _mc_set(key: str, val, ttl: int = 10):
    try:
        _MICROCACHE[key] = (_now() + max(1, int(ttl)), val)
    except Exception:
        pass
def _get_cached_settings():
    """Cache settings برای 60 ثانیه"""
    cache_key = "settings"
    cached = _mc_get(cache_key)
    if cached is not None:
        return cached
    try:
        from ..utils.storage import load_settings
        settings = load_settings()
        _mc_set(cache_key, settings, ttl=60)
        return settings
    except Exception:
        return {}
# ثابت‌ها
FIRST_VISIT_COOKIE = "vinor_first_visit_done"

# -------------------------
# Context (برای استفادهٔ ساده در تمام قالب‌ها)
# -------------------------
@main_bp.app_context_processor
def inject_vinor_globals():
    """
    متغیرهای عمومیِ وینور برای استفاده در تمپلیت‌ها
    """
    # همکار اکسپرس تأییدشده
    try:
        me = str(session.get("user_phone") or "").strip()
        _partners = load_express_partners()
        is_express_partner = any(
            isinstance(p, dict)
            and str(p.get("phone") or "").strip() == me
            and (str(p.get("status") or "").lower() == "approved" or p.get("status") is True)
            for p in (_partners or [])
        )
    except Exception:
        is_express_partner = False

    return {
        "VINOR_IS_LOGGED_IN": bool(session.get("user_id")),
        "VINOR_HOME_URL": url_for("main.index"),
        "VINOR_BRAND": "وینور اکسپرس",
        "VINOR_DOMAIN": "vinor.ir",
        # نقش‌ها
        "VINOR_IS_EXPRESS_PARTNER": is_express_partner,
    }

# -------------------------
# Routes
# -------------------------

@main_bp.route("/", endpoint="index")
def index():
    """
    لندینگ همکاران وینور – معرفی فرصت‌های همکاری
    اگر کاربر وارد شده باشد، مستقیم به داشبورد همکاران می‌رود.
    """
    # بررسی سریع session برای redirect فوری (قبل از هر کار دیگری)
    # این بررسی باید در ابتدا انجام شود تا redirect فوراً انجام شود
    user_phone = session.get("user_phone")
    user_id = session.get("user_id")
    is_admin = bool(session.get('logged_in'))
    is_logged_in = bool(user_phone or user_id or is_admin)
    
    # اگر کاربر لاگین شده باشد، فوراً redirect می‌کنیم (بدون اجرای کدهای بعدی)
    if is_logged_in:
        # بررسی next parameter برای redirect به مسیر هدف
        nxt = request.args.get('next')
        if nxt and nxt.startswith('/') and not nxt.startswith('//'):
            # اطمینان از اینکه next یک مسیر معتبر است
            resp = redirect(nxt)
            # اضافه کردن cache headers برای redirect سریع‌تر
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp
        
        # Redirect به داشبورد مناسب
        if is_admin:
            resp = redirect(url_for("admin.dashboard"))
        else:
            # برای همکاران اکسپرس، به داشبورد همکاران redirect می‌کنیم
            # اگر session معتبر نباشد، require_partner_access در داشبورد handle می‌کند
            resp = redirect(url_for("express_partner.dashboard"))
        
        # اضافه کردن cache headers برای redirect سریع‌تر
        # مهم: نباید cache شود چون redirect بر اساس session است
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        resp.headers["Vary"] = "Cookie"  # برای Service Worker که نباید cache کند
        return resp
    
    # ثبت بازدید لندینگ (فقط برای کاربران غیرلاگین و غیرادمین)
    # بررسی referer برای جلوگیری از tracking درخواست‌های داخلی و رفرش
    referer = request.headers.get('Referer', '') or ''
    is_refresh = referer and (request.url in referer or request.path in referer)
    should_track = (
        not is_logged_in and 
        not is_refresh and  # جلوگیری از tracking در رفرش
        '/admin' not in referer and 
        '/express/partner' not in referer
    )
    
    # Tracking فقط برای بازدیدهای جدید (نه رفرش)
    if should_track:
        try:
            visitor_ip = request.remote_addr or ''
            if visitor_ip:
                # بررسی سریع با cache برای جلوگیری از I/O غیرضروری
                cache_track_key = f"tracked:{visitor_ip}:{datetime.utcnow().strftime('%Y-%m-%d')}"
                if _mc_get(cache_track_key):
                    # قبلاً امروز track شده، skip
                    pass
                else:
                    views = load_landing_views() or []
                    if not isinstance(views, list):
                        views = []
                    
                    now = datetime.utcnow()
                    today_str = now.strftime('%Y-%m-%d')
                    
                    # بررسی بازدیدهای امروز برای این IP
                    already_viewed_today = False
                    for v in views:
                        try:
                            v_ip = v.get('ip', '')
                            v_ts_str = v.get('timestamp', '')
                            if v_ip == visitor_ip and v_ts_str:
                                v_dt = datetime.fromisoformat(v_ts_str.replace('Z', '+00:00'))
                                if v_dt.tzinfo:
                                    v_dt = v_dt.replace(tzinfo=None)
                                v_date_str = v_dt.strftime('%Y-%m-%d')
                                if v_date_str == today_str:
                                    already_viewed_today = True
                                    break
                        except Exception:
                            continue
                    
                    # اگر این IP امروز بازدید نداشته، ثبت کن
                    if not already_viewed_today:
                        views.append({
                            'timestamp': now.isoformat(),
                            'ip': visitor_ip,
                            'user_agent': request.headers.get('User-Agent', '')[:200]
                        })
                        # نگه داشتن فقط 10000 بازدید اخیر
                        if len(views) > 10000:
                            views = views[-10000:]
                        save_landing_views(views)
                        # Cache برای جلوگیری از track مجدد در همان روز
                        _mc_set(cache_track_key, True, ttl=86400)  # 24 ساعت
        except Exception as e:
            current_app.logger.error(f"Error tracking landing view: {e}", exc_info=True)
    
    # بارگذاری تنظیمات با cache
    _settings = _get_cached_settings()
    
    # Microcache فقط برای کاربران مهمان (غیرلاگین)
    # برای کاربران لاگین شده cache نمی‌کنیم چون ممکن است محتوای شخصی‌سازی شده داشته باشند
    if not is_logged_in:
        cache_key = "page:index"
        cached = _mc_get(cache_key)
        if cached:
            resp = make_response(cached)
            # استفاده از cache برای رفرش سریع‌تر
            resp.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
            resp.headers["ETag"] = f'"{hash(cached) % 1000000}"'
            return resp
    
    # رندر صفحه لندینگ
    html = render_template(
        "home/partners.html",
        brand="وینور",
        domain="vinor.ir",
        android_apk_url=_settings.get('android_apk_url') or '',
        android_apk_version=_settings.get('android_apk_version') or ''
    )
    
    # ذخیره در cache فقط برای کاربران مهمان
    if not is_logged_in:
        try:
            # افزایش TTL برای رفرش سریع‌تر
            _mc_set("page:index", html, ttl=30)
        except Exception:
            pass
    
    resp = make_response(html)
    # بهبود cache headers برای رفرش سریع‌تر
    if not is_logged_in:
        resp.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        resp.headers["ETag"] = f'"{hash(html) % 1000000}"'
    else:
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp

@main_bp.route("/partners", endpoint="partners")
def partners():
    """
    لندینگ همکاران وینور – معرفی فرصت‌های همکاری
    اگر کاربر وارد شده باشد، مستقیم به داشبورد می‌رود.
    """
    # بررسی اینکه آیا کاربر در پنل ادمین است یا نه
    referer = request.headers.get('Referer', '') or ''
    is_admin = (
        session.get('logged_in') or 
        request.path.startswith('/admin') or
        '/admin' in referer
    )
    
    if session.get("user_phone") or session.get("user_id") or is_admin:
        nxt = request.args.get('next')
        if nxt and nxt.startswith('/'):
            return redirect(nxt)
        if is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("express_partner.dashboard"))
    
    # ثبت بازدید لندینگ (فقط برای کاربران غیرلاگین و غیرادمین و درخواست‌های مستقیم)
    # اگر referer از admin یا express/partner باشد، tracking نمی‌کنیم
    if '/admin' not in referer and '/express/partner' not in referer:
        try:
            views = load_landing_views() or []
            if not isinstance(views, list):
                views = []
            
            # بررسی اینکه آیا این IP در امروز قبلاً بازدید داشته یا نه
            visitor_ip = request.remote_addr or ''
            now = datetime.utcnow()
            today_str = now.strftime('%Y-%m-%d')
            
            # بررسی بازدیدهای امروز برای این IP
            already_viewed_today = False
            for v in views:
                try:
                    v_ip = v.get('ip', '')
                    v_ts_str = v.get('timestamp', '')
                    if v_ip == visitor_ip and v_ts_str:
                        v_dt = datetime.fromisoformat(v_ts_str.replace('Z', '+00:00'))
                        if v_dt.tzinfo:
                            v_dt = v_dt.replace(tzinfo=None)
                        v_date_str = v_dt.strftime('%Y-%m-%d')
                        if v_date_str == today_str:
                            already_viewed_today = True
                            break
                except Exception:
                    continue
            
            # اگر این IP امروز بازدید نداشته، ثبت کن
            if not already_viewed_today and visitor_ip:
                views.append({
                    'timestamp': now.isoformat(),
                    'ip': visitor_ip,
                    'user_agent': request.headers.get('User-Agent', '')[:200]
                })
                # نگه داشتن فقط 10000 بازدید اخیر
                if len(views) > 10000:
                    views = views[-10000:]
                save_landing_views(views)
        except Exception as e:
            current_app.logger.error(f"Error tracking landing view: {e}", exc_info=True)
    
    try:
        from ..utils.storage import load_settings
        _settings = load_settings()
    except Exception:
        _settings = {}
    # Microcache only for guests
    if not (session.get("user_phone") or session.get("user_id") or is_admin):
        k = f"page:partners"
        cached = _mc_get(k)
        if cached:
            resp = make_response(cached)
            resp.headers["Cache-Control"] = "no-cache"
            return resp
    html = render_template("home/partners.html",
                           brand="وینور",
                           domain="vinor.ir",
                           android_apk_url=_settings.get('android_apk_url') or '',
                           android_apk_version=_settings.get('android_apk_version') or '')
    try:
        if not (session.get("user_phone") or session.get("user_id") or is_admin):
            _mc_set("page:partners", html, ttl=15)
    except Exception:
        pass
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-cache"
    return resp

@main_bp.route("/start", endpoint="start")
def start():
    """
    CTA لندینگ → ست‌کردن کوکی «اولین بازدید انجام شد»
    سپس به صفحه اصلی (لندینگ همکاران) می‌رویم.
    """
    target = url_for("main.index")
    resp = make_response(redirect(target))
    resp.set_cookie(FIRST_VISIT_COOKIE, "1", max_age=60 * 60 * 24 * 365, samesite="Lax")
    session.permanent = True
    return resp

@main_bp.route("/public", endpoint="express_public_list")
def express_public_list():
    """
    صفحه عمومی لیست فایل‌های اکسپرس - سبک دیوار (بهینه شده برای سرعت)
    """
    try:
        # استفاده از کش بهینه شده
        express_lands = load_express_lands_cached() or []
        
        # جستجو (فقط در صورت نیاز)
        search_query = request.args.get('q', '').strip().lower()
        if search_query:
            search_terms = search_query.split()
            def _matches(land):
                search_text = ' '.join([
                    str(land.get('title', '')),
                    str(land.get('location', '')),
                    str(land.get('category', '')),
                    str(land.get('description', ''))
                ]).lower()
                return all(term in search_text for term in search_terms)
            express_lands = [l for l in express_lands if _matches(l)]
        
        # اعمال تقویت بازنشر: افزودن آیتم‌های boost به ابتدای لیست
        try:
            reposts = load_express_reposts() or []
        except Exception:
            reposts = []
        # آماده‌سازی شمارش بازنشرها و ساخت آیتم‌های بازنشر (سبک ریتوییت)
        code_to_repost_count = {}
        if reposts:
            for r in reposts:
                c = str(r.get('code') or '')
                if not c:
                    continue
                code_to_repost_count[c] = code_to_repost_count.get(c, 0) + 1
            # به ازای هر رکورد، آیتم تقویتی بساز
            code_to_land = {str(l.get('code')): l for l in express_lands}
            # برای نمایش نام همکار بازنشرکننده
            try:
                partners = load_express_partners() or []
            except Exception:
                partners = []
            phone_to_name = {str(p.get('phone') or ''): (p.get('name') or 'همکار') for p in partners if isinstance(p, dict)}

            boost_items = []
            from ..utils.share_tokens import encode_partner_ref
            # آخرین 100 بازنشر (جدیدترین‌ها جلوتر)
            for r in reposts[-100:][::-1]:
                c = str(r.get('code') or '')
                land = code_to_land.get(c)
                phone = str(r.get('partner_phone') or '')
                if land and phone:
                    item = dict(land)
                    # تزریق ref همکار برای نمایش کارت همکار در جزئیات
                    try:
                        item['_share_token'] = encode_partner_ref(phone)
                    except Exception:
                        item['_share_token'] = ''
                    # نام همکار بازنشرکننده برای نشان کوچک
                    item['_repost_by_name'] = phone_to_name.get(phone) or 'همکار'
                    boost_items.append(item)
            # افزودن به ابتدای لیست
            express_lands = boost_items + express_lands

        # صفحه‌بندی ساده
        page = int(request.args.get('page', 1) or 1)
        per_page = 20
        total = len(express_lands)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_lands = express_lands[start_idx:end_idx]

        def _cover_and_variants(l):
            imgs = l.get('images') or []
            cover = imgs[0] if imgs else None
            variants = prepare_variants_dict(cover)
            return cover, variants, [prepare_variants_dict(i) for i in imgs]

        # کاهش حجم داده برای تمپلیت (کمینه‌سازی) + واریانت‌ها
        lands_min = []
        for land in paginated_lands:
            cover_raw, cover_variants, images_v2 = _cover_and_variants(land)
            lands_min.append({
                'code': land.get('code'),
                'title': land.get('title'),
                'location': land.get('location'),
                'size': land.get('size'),
                'price_total': land.get('price_total'),
                'images': land.get('images', [])[:1],
                'video': land.get('video'),
                'image_thumb': cover_variants.get('thumb'),
                'image_full': cover_variants.get('full'),
                'image_raw': cover_variants.get('raw'),
                'images_v2': images_v2,
                '_share_token': land.get('_share_token',''),
                '_repost_by_name': land.get('_repost_by_name',''),
                '_repost_count': code_to_repost_count.get(str(land.get('code')), 0),
            })
        
    except Exception as e:
        current_app.logger.error(f"Error loading express listings: {e}", exc_info=True)
        express_lands = []
        paginated_lands = []
        page = 1
        pages = 1
        total = 0
    
    # آماده‌سازی داده‌های SEO
    base_url = request.url_root.rstrip('/')
    canonical_url = f"{base_url}/public"
    if page > 1:
        canonical_url += f"?page={page}"
    
    # بررسی اینکه آیا کاربر از پنل همکاران آمده یا نه
    referer = request.headers.get('Referer', '')
    show_back_button = '/express/partner/' in referer or session.get('user_phone')
    
    # بررسی اینکه آیا کاربر همکار اکسپرس است
    is_partner = False
    if session.get('user_phone'):
        try:
            me = str(session.get("user_phone") or "").strip()
            _partners = load_express_partners()
            is_partner = any(
                isinstance(p, dict)
                and str(p.get("phone") or "").strip() == me
                and (str(p.get("status") or "").lower() == "approved" or p.get("status") is True)
                for p in (_partners or [])
            )
        except Exception:
            is_partner = False
    
    # اگر کاربر همکار است، از قالب express_partner استفاده کن
    template_name = 'express_partner/explore.html' if is_partner else 'public/express_list.html'
    
    # Microcache only for guests (no session, not partner)
    if not session.get('user_phone'):
        key = f"page:public:list:{page}:{(search_query or '')}"
        cached = _mc_get(key)
        if cached:
            resp = make_response(cached)
            resp.headers["Cache-Control"] = "public, max-age=20, stale-while-revalidate=40"
            # ETag بر اساس وضعیت فایل آگهی + پارامترها
            try:
                from ..utils.storage import get_lands_file_stats
                stats = get_lands_file_stats()
                base_etag = stats.get("etag") or 'W/"lands"'
                etag = f'{base_etag}-page-{page}-q{hash(search_query) & 0xffff:x}'
                resp.headers["ETag"] = etag
            except Exception:
                pass
            return resp

    html = render_template(
        template_name,
        lands=lands_min,
        pagination={'page': page, 'pages': pages, 'total': total},
        show_back_button=show_back_button,
        search_query=search_query,
        seo={
            'title': 'فایل‌های اکسپرس وینور اکسپرس | خرید و فروش ملک',
            'description': f'لیست کامل فایل‌های اکسپرس وینور اکسپرس. {total} فایل معتبر برای خرید و فروش ملک. مشاهده قیمت، موقعیت و جزئیات کامل.',
            'keywords': 'فایل اکسپرس, خرید ملک, فروش ملک, زمین, ویلایی, آپارتمان, وینور اکسپرس, vinor express',
            'canonical': canonical_url,
            'og_type': 'website',
            'og_image': f"{base_url}/static/icons/icon-512.png"
        }
    )
    try:
        if not session.get('user_phone'):
            _mc_set(key, html, ttl=20)
    except Exception:
        pass
    resp = make_response(html)
    resp.headers["Cache-Control"] = "public, max-age=20, stale-while-revalidate=40"
    if not session.get('user_phone'):
        try:
            from ..utils.storage import get_lands_file_stats
            stats = get_lands_file_stats()
            base_etag = stats.get("etag") or 'W/"lands"'
            etag = f'{base_etag}-page-{page}-q{hash(search_query) & 0xffff:x}'
            resp.headers["ETag"] = etag
        except Exception:
            pass
    return resp

@main_bp.route("/express/<code>", endpoint="express_detail")
def express_detail(code):
    """
    صفحهٔ جزئیات آگهی اکسپرس (بهینه شده)
    """
    express_lands = load_express_lands_cached()
    land = next((l for l in express_lands if l.get('code') == code), None)

    if not land:
        flash('آگهی اکسپرس یافت نشد.', 'warning')
        return redirect(url_for('main.index'))

    # ثبت بازدید فایل اکسپرس (هر IP در هر روز فقط یک بازدید)
    try:
        views = load_express_views() or []
        if not isinstance(views, list):
            views = []
        
        visitor_ip = request.remote_addr or ''
        now = datetime.utcnow()
        today_str = now.strftime('%Y-%m-%d')
        
        # بررسی اینکه آیا این IP در امروز برای این فایل قبلاً بازدید داشته یا نه
        already_viewed_today = False
        for v in views:
            try:
                v_ip = v.get('ip', '')
                v_code = v.get('code', '')
                v_ts_str = v.get('timestamp', '')
                if v_ip == visitor_ip and v_code == code and v_ts_str:
                    v_dt = datetime.fromisoformat(v_ts_str.replace('Z', '+00:00'))
                    if v_dt.tzinfo:
                        v_dt = v_dt.replace(tzinfo=None)
                    v_date_str = v_dt.strftime('%Y-%m-%d')
                    if v_date_str == today_str:
                        already_viewed_today = True
                        break
            except Exception:
                continue
        
        # اگر این IP امروز برای این فایل بازدید نداشته، ثبت کن
        if not already_viewed_today and visitor_ip and code:
            views.append({
                'timestamp': now.isoformat(),
                'code': code,
                'ip': visitor_ip,
                'user_agent': request.headers.get('User-Agent', '')[:200]
            })
            # نگه داشتن فقط 50000 بازدید اخیر
            if len(views) > 50000:
                views = views[-50000:]
            save_express_views(views)
    except Exception as e:
        current_app.logger.error(f"Error tracking express listing view: {e}", exc_info=True)

    # آماده‌سازی واریانت‌های تصویر (thumb/full)
    try:
        imgs = land.get('images') or []
        images_v2 = [prepare_variants_dict(i) for i in imgs]
        land['images_v2'] = images_v2
        if images_v2:
            land['image_thumb'] = images_v2[0].get('thumb')
            land['image_full'] = images_v2[0].get('full')
            land['image_raw'] = images_v2[0].get('raw')
    except Exception:
        pass

    ref_token = request.args.get('ref', '').strip()
    ref_phone = decode_partner_ref(ref_token)
    ref_partner = None
    if ref_phone:
        partners = load_express_partners() or []
        ref_partner = next((p for p in partners if str(p.get('phone')) == ref_phone), None)
    
    # اگر ref_partner وجود نداشت، از assignments استفاده کنیم تا ببینیم کدام همکار این فایل را دارد
    if not ref_partner:
        try:
            assignments = load_express_assignments() or []
            # پیدا کردن assignment فعال برای این فایل
            assignment = next((a for a in assignments if a.get('land_code') == code and a.get('status') in (None, 'active', 'pending', 'approved', 'in_transaction')), None)
            if assignment:
                partner_phone = assignment.get('partner_phone')
                if partner_phone:
                    partners = load_express_partners() or []
                    ref_partner = next((p for p in partners if str(p.get('phone')) == str(partner_phone)), None)
        except Exception as e:
            current_app.logger.error(f"Error loading assignments for contact info: {e}", exc_info=True)

    # بررسی اینکه آیا کاربر از پنل همکاران آمده یا نه
    referer = request.headers.get('Referer', '')
    show_back_button = '/express/partner/' in referer or session.get('user_phone')

    # آماده‌سازی داده‌های SEO
    base_url = request.url_root.rstrip('/')
    canonical_url = f"{base_url}/express/{land.get('code', '')}"
    
    # تصویر اصلی برای OG
    images = land.get('images', [])
    og_image = None
    if images:
        if isinstance(images, list) and len(images) > 0:
            img = images[0]
        elif isinstance(images, str):
            img = images
        else:
            img = None
        
        if img:
            if "://" in str(img):
                og_image = str(img)
            elif str(img).startswith('/uploads/'):
                og_image = f"{base_url}{img}"
            elif str(img).startswith('uploads/'):
                og_image = f"{base_url}/uploads/{str(img)[8:]}"
            else:
                og_image = f"{base_url}/uploads/{img}"
    
    if not og_image:
        og_image = f"{base_url}/static/icons/icon-512.png"
    
    # ساخت description از اطلاعات فایل
    desc_parts = []
    if land.get('location'):
        desc_parts.append(f"موقعیت: {land.get('location')}")
    if land.get('size'):
        desc_parts.append(f"متراژ: {land.get('size')} متر")
    if land.get('price_total'):
        desc_parts.append(f"قیمت: {land.get('price_total'):,} تومان")
    description = f"{land.get('title', 'فایل اکسپرس')} - {' | '.join(desc_parts)}" if desc_parts else f"{land.get('title', 'فایل اکسپرس')} - خرید و فروش ملک در وینور"
    
    # پیدا کردن فایل‌های قبلی و بعدی برای infinite scroll (حلقه‌ای - نامحدود)
    
    current_index = next((i for i, l in enumerate(express_lands) if l.get('code') == code), -1)
    
    # حلقه‌ای کردن: وقتی به آخر رسید به اول برگردد و برعکس
    if current_index >= 0 and len(express_lands) > 0:
        next_land = express_lands[(current_index + 1) % len(express_lands)]
        prev_land = express_lands[(current_index - 1) % len(express_lands)]
    else:
        next_land = None
        prev_land = None
    
    # Microcache detail for guests (short TTL)
    if not session.get('user_phone'):
        _k = f"page:public:detail:{code}"
        _c = _mc_get(_k)
        if _c:
            r = make_response(_c)
            r.headers["Cache-Control"] = "public, max-age=10"
            return r

    html = render_template(
        "public/express_public_detail.html",
        land=land,
        ref_partner=ref_partner,
        ref_token=ref_token,
        show_back_button=show_back_button,
        next_land=next_land,
        prev_land=prev_land,
        all_lands=express_lands,  # برای infinite scroll
        current_index=current_index,
        seo={
            'title': f"{land.get('title', 'فایل اکسپرس')} | وینور",
            'description': description,
            'keywords': f"فایل اکسپرس, {land.get('location', '')}, {land.get('category', '')}, خرید ملک, فروش ملک, وینور",
            'canonical': canonical_url,
            'og_type': 'product',
            'og_image': og_image,
            'price': land.get('price_total'),
            'currency': 'IRR'
        }
    )
    try:
        if not session.get('user_phone'):
            _mc_set(_k, html, ttl=10)
    except Exception:
        pass
    r = make_response(html)
    r.headers["Cache-Control"] = "public, max-age=10"
    return r

@main_bp.route("/uploads/<path:filename>", endpoint="uploaded_file")
def uploaded_file(filename):
    """
    سرو فایل‌های آپلود:
      1) ابتدا از UPLOAD_FOLDER (مسیر جدید تاریخ‌محور)
      2) سپس از instance/data/uploads
      3) سپس از <root>/data/uploads (legacy)
    """
    try:
        width = int(request.args.get("w", 0) or 0)
        quality = int(request.args.get("q", 0) or 0) or 80
        fmt = (request.args.get("fmt") or "webp").lower()
    except Exception:
        width = 0
        quality = 80
        fmt = "webp"

    def _generate_variant(root: str, safe_name: str):
        if width <= 0:
            return None
        try:
            from app.utils.images import generate_variant  # محلی برای جلوگیری از چرخه

            variant_rel = generate_variant(root, safe_name, width, quality, f"w{width}_q{quality}", fmt.upper())
            if not variant_rel:
                return None
            abs_path = os.path.join(root, variant_rel)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if os.path.isfile(abs_path):
                vdir, vfile = os.path.split(abs_path)
                resp = send_from_directory(vdir, vfile)
                resp.headers["Cache-Control"] = variant_headers_for_width(width)
                resp.headers["Content-Type"] = "image/webp"
                return resp
        except Exception as e:
            current_app.logger.debug("Variant generation failed: %s", e, exc_info=True)
        return None

    def _maybe_set_apk_download_name(resp):
        try:
            fn_norm = (filename or '').replace('\\', '/')
            if fn_norm.lower().endswith('.apk') and fn_norm.startswith('apk/'):
                try:
                    from ..utils.storage import load_settings
                    settings = load_settings()
                except Exception:
                    settings = {}
                wanted_url = str(settings.get('android_apk_url') or '')
                orig_name = str(settings.get('android_apk_original_name') or '').strip()
                if wanted_url and orig_name:
                    # match by basename to ensure we are serving the configured APK
                    try:
                        wanted_base = os.path.basename(wanted_url)
                    except Exception:
                        wanted_base = ''
                    if wanted_base and wanted_base == os.path.basename(fn_norm):
                        # Force download with the original client filename
                        try:
                            disp = "attachment; filename*=UTF-8''" + quote(orig_name) + f"; filename=\"{orig_name}\""
                            resp.headers['Content-Disposition'] = disp
                        except Exception:
                            resp.headers['Content-Disposition'] = f'attachment; filename=\"{orig_name}\"'
        except Exception:
            pass
        return resp
    # اول مسیر تنظیم‌شده در کانفیگ
    try:
        base_cfg = current_app.config.get("UPLOAD_FOLDER")
        if base_cfg:
            fp_cfg = os.path.join(base_cfg, filename)
            if os.path.isfile(fp_cfg):
                # تلاش برای سرو واریانت
                variant_resp = _generate_variant(base_cfg, filename)
                if variant_resp:
                    return variant_resp
                resp = send_from_directory(base_cfg, filename)
                resp = _maybe_set_apk_download_name(resp)
                try:
                    if width > 0:
                        resp.headers["Cache-Control"] = variant_headers_for_width(width)
                    else:
                        resp.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=86400"
                except Exception:
                    pass
                return resp
    except Exception:
        pass

    # سپس مسیر instance/data/uploads و legacy data/uploads
    upload_roots = (
        os.path.join(data_dir(), "uploads"),
        os.path.join(legacy_dir(), "uploads"),
    )
    for folder in upload_roots:
        fp = os.path.join(folder, filename)
        if os.path.isfile(fp):
            variant_resp = _generate_variant(folder, filename)
            if variant_resp:
                return variant_resp
            resp = send_from_directory(folder, filename)
            resp = _maybe_set_apk_download_name(resp)
            try:
                resp.headers["Cache-Control"] = variant_headers_for_width(width) if width > 0 else "public, max-age=86400, stale-while-revalidate=86400"
            except Exception:
                pass
            return resp
    # در نهایت: static/uploads (تصاویر ذخیره‌شده در static)
    try:
        static_root = current_app.static_folder
        # پشتیبانی از هر دو ورودی: 'uploads/...' یا فقط '...'
        candidates = []
        if filename.startswith('uploads/'):
            candidates.append(os.path.join(static_root, filename))
            candidates.append(os.path.join(static_root, filename.lstrip('/')))
        else:
            candidates.append(os.path.join(static_root, 'uploads', filename))
        for cand in candidates:
            if os.path.isfile(cand):
                rel_dir = os.path.dirname(os.path.relpath(cand, static_root))
                fn = os.path.basename(cand)
                resp = send_from_directory(os.path.join(static_root, rel_dir), fn)
                resp = _maybe_set_apk_download_name(resp)
                try:
                    resp.headers["Cache-Control"] = variant_headers_for_width(width) if width > 0 else "public, max-age=86400, stale-while-revalidate=86400"
                except Exception:
                    pass
                return resp
    except Exception:
        pass
    abort(404, description="File not found")


@main_bp.route("/express-docs/<filename>")
def serve_express_document(filename):
    """سرو کردن مدارک اکسپرس برای کاربران"""
    try:
        docs_dir = os.path.join(current_app.instance_path, 'data', 'express_docs')
        return send_from_directory(docs_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving express document {filename}: {e}")
        abort(404)

@main_bp.route("/help", endpoint="help")
def help_page():
    """صفحه راهنمای عمومی - فقط برای Express Partner"""
    base_url = request.url_root.rstrip('/')
    return render_template(
        'public/help.html',
        seo={
            'title': 'راهنما | وینور اکسپرس',
            'description': 'راهنمای استفاده از پلتفرم وینور اکسپرس و اطلاعات تماس پشتیبانی',
            'keywords': 'راهنما, پشتیبانی, وینور اکسپرس',
            'canonical': f"{base_url}/help",
            'og_type': 'website',
            'og_image': f"{base_url}/static/icons/icon-512.png"
        }
    )


