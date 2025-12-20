# app/routes/public.py
import os

from flask import (
    render_template, send_from_directory, request, abort,
    redirect, url_for, session, make_response, current_app, flash
)

from . import main_bp
from ..utils.storage import data_dir, legacy_dir, load_ads_cached
from ..utils.storage import load_express_partners, load_landing_views, save_landing_views
from ..utils.storage import load_express_views, save_express_views
from ..utils.share_tokens import decode_partner_ref
from datetime import datetime

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
        "VINOR_BRAND": "وینور",
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
                # نگه داشتن فقط 10000 بازدید اخیر (برای جلوگیری از رشد بی‌حد فایل)
                if len(views) > 10000:
                    views = views[-10000:]
                save_landing_views(views)
        except Exception as e:
            current_app.logger.error(f"Error tracking landing view: {e}", exc_info=True)
    
    return render_template("home/partners.html", brand="وینور", domain="vinor.ir")

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
    
    return render_template("home/partners.html", brand="وینور", domain="vinor.ir")

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
    صفحه عمومی لیست فایل‌های اکسپرس - سبک دیوار
    """
    try:
        lands = load_ads_cached() or []
        # فیلتر فایل‌های اکسپرس (فقط approved)
        express_lands = [
            l for l in lands 
            if l.get('is_express', False) and l.get('express_status') != 'sold'
        ]
        
        # جستجو
        search_query = request.args.get('q', '').strip().lower()
        if search_query:
            def _matches(land):
                title = str(land.get('title', '')).lower()
                location = str(land.get('location', '')).lower()
                category = str(land.get('category', '')).lower()
                description = str(land.get('description', '')).lower()
                return (search_query in title or 
                        search_query in location or 
                        search_query in category or
                        search_query in description)
            express_lands = [l for l in express_lands if _matches(l)]
        
        # مرتب‌سازی بر اساس تاریخ ایجاد (جدیدترین اول)
        express_lands.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # صفحه‌بندی ساده
        page = int(request.args.get('page', 1) or 1)
        per_page = 20
        total = len(express_lands)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_lands = express_lands[start_idx:end_idx]
        
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
    
    return render_template(
        'public/express_list.html',
        lands=paginated_lands,
        pagination={'page': page, 'pages': pages, 'total': total},
        show_back_button=show_back_button,
        search_query=search_query,
        seo={
            'title': 'فایل‌های اکسپرس وینور | خرید و فروش ملک',
            'description': f'لیست کامل فایل‌های اکسپرس وینور. {total} فایل معتبر برای خرید و فروش ملک. مشاهده قیمت، موقعیت و جزئیات کامل.',
            'keywords': 'فایل اکسپرس, خرید ملک, فروش ملک, زمین, ویلایی, آپارتمان, وینور, vinor',
            'canonical': canonical_url,
            'og_type': 'website',
            'og_image': f"{base_url}/static/icons/icon-512.png"
        }
    )

@main_bp.route("/express/<code>", endpoint="express_detail")
def express_detail(code):
    """
    صفحهٔ جزئیات آگهی اکسپرس
    """
    lands = load_ads_cached()
    land = next((l for l in lands if l.get('code') == code and l.get('is_express', False)), None)

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

    ref_token = request.args.get('ref', '').strip()
    ref_phone = decode_partner_ref(ref_token)
    ref_partner = None
    if ref_phone:
        partners = load_express_partners() or []
        ref_partner = next((p for p in partners if str(p.get('phone')) == ref_phone), None)

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
    
    return render_template(
        "public/express_public_detail.html",
        land=land,
        ref_partner=ref_partner,
        ref_token=ref_token,
        show_back_button=show_back_button,
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

@main_bp.route("/uploads/<path:filename>", endpoint="uploaded_file")
def uploaded_file(filename):
    """
    سرو فایل‌های آپلود:
      1) ابتدا از UPLOAD_FOLDER (مسیر جدید تاریخ‌محور)
      2) سپس از instance/data/uploads
      3) سپس از <root>/data/uploads (legacy)
    """
    # اول مسیر تنظیم‌شده در کانفیگ
    try:
        base_cfg = current_app.config.get("UPLOAD_FOLDER")
        if base_cfg:
            fp_cfg = os.path.join(base_cfg, filename)
            if os.path.isfile(fp_cfg):
                resp = send_from_directory(base_cfg, filename)
                try:
                    resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
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
            resp = send_from_directory(folder, filename)
            try:
                resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
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
                try:
                    resp.headers["Cache-Control"] = "public, max-age=86400, immutable"
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
    """صفحه راهنمای عمومی"""
    base_url = request.url_root.rstrip('/')
    return render_template(
        'public/help.html',
        seo={
            'title': 'راهنما | وینور',
            'description': 'راهنمای استفاده از پلتفرم وینور، سوالات پرتکرار، راهنمای خرید امن و اطلاعات تماس پشتیبانی',
            'keywords': 'راهنما, سوالات پرتکرار, خرید امن, پشتیبانی, وینور',
            'canonical': f"{base_url}/help",
            'og_type': 'website',
            'og_image': f"{base_url}/static/icons/icon-512.png"
        }
    )
