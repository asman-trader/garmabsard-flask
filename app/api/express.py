# app/api/express.py
# -*- coding: utf-8 -*-
"""
Express Listings API endpoints for Vinor Express feature
"""

from flask import Blueprint, jsonify, request, current_app, make_response
from app.utils.storage import load_express_lands_cached, get_lands_file_stats
from app.utils.images import prepare_variants_dict
from app.services.notifications import add_notification

express_api_bp = Blueprint('express_api', __name__, url_prefix='/api')

@express_api_bp.route('/express-listings')
def get_express_listings():
    """Get all express listings (بهینه شده)"""
    try:
        express_lands = load_express_lands_cached()
        stats = get_lands_file_stats()
        etag = stats.get("etag")

        # ETag short-circuit
        inm = request.headers.get("If-None-Match")
        if inm and etag and inm == etag:
            resp = make_response(("", 304))
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
            return resp

        # فیلتر فقط approved
        express_lands = [l for l in express_lands if l.get('express_status') == 'approved']
        
        response = make_response(jsonify({
            'success': True,
            'lands': express_lands,
            'count': len(express_lands)
        }))
        response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
        if etag:
            response.headers['ETag'] = etag
        return response
    except Exception as e:
        current_app.logger.error(f"Error loading express listings: {e}")
        return jsonify({
            'success': False,
            'error': 'خطا در بارگذاری آگهی‌های اکسپرس'
        }), 500

@express_api_bp.route('/express-search')
def express_search():
    """جستجوی زنده در فایل‌های اکسپرس (بهینه شده)"""
    try:
        query = request.args.get('q', '').strip().lower()
        
        # استفاده از کش بهینه شده
        express_lands = load_express_lands_cached() or []
        stats = get_lands_file_stats()
        # ETag را به پارامتر جستجو وابسته می‌کنیم
        base_etag = stats.get("etag") or 'W/"lands"'
        etag = f'{base_etag}-search-{hash(query) & 0xffff:x}'
        inm = request.headers.get("If-None-Match")
        if inm and etag and inm == etag:
            resp = make_response(("", 304))
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=30, stale-while-revalidate=60'
            return resp
        
        # جستجو (بهینه شده)
        if query:
            search_terms = query.split()
            def _matches(land):
                search_text = ' '.join([
                    str(land.get('title', '')),
                    str(land.get('location', '')),
                    str(land.get('category', '')),
                    str(land.get('description', ''))
                ]).lower()
                return all(term in search_text for term in search_terms)
            express_lands = [l for l in express_lands if _matches(l)]
        
        # کاهش حجم داده + افزودن لینک thumb/full برای کاور
        minimal_lands = []
        for land in express_lands[:50]:  # محدود کردن به 50 نتیجه اول
            images = land.get('images', []) or []
            cover = images[0] if images else None
            cover_variants = prepare_variants_dict(cover)
            minimal_lands.append({
                'code': land.get('code'),
                'title': land.get('title'),
                'location': land.get('location'),
                'images': images[:1],
                'image_thumb': cover_variants.get('thumb'),
                'image_full': cover_variants.get('full'),
                'image_raw': cover_variants.get('raw'),
                'images_v2': [prepare_variants_dict(i) for i in images],
                'video': land.get('video')
            })
        
        response = make_response(jsonify({
            'success': True,
            'lands': minimal_lands,
            'count': len(express_lands)
        }))
        response.headers['Cache-Control'] = 'public, max-age=30, stale-while-revalidate=60'
        response.headers['Vary'] = 'Accept-Encoding'
        if etag:
            response.headers['ETag'] = etag
        return response
    except Exception as e:
        current_app.logger.error(f"Error in express search: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'خطا در جستجو'
        }), 500

@express_api_bp.route('/express-list')
def express_list():
    """API برای infinite scroll - لیست فایل‌های اکسپرس با صفحه‌بندی (بهینه شده برای سرعت)"""
    try:
        page = int(request.args.get('page', 1) or 1)
        per_page = int(request.args.get('per_page', 30) or 30)
        search_query = request.args.get('q', '').strip().lower()
        
        # استفاده از کش بهینه شده برای فایل‌های اکسپرس
        express_lands = load_express_lands_cached() or []
        stats = get_lands_file_stats()
        base_etag = stats.get("etag") or 'W/"lands"'
        etag = f'{base_etag}-list-p{page}-pp{per_page}-q{hash(search_query) & 0xffff:x}'
        inm = request.headers.get("If-None-Match")
        if inm and etag and inm == etag:
            resp = make_response(("", 304))
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
            return resp
        
        # جستجو (فقط در صورت نیاز)
        if search_query:
            # بهینه‌سازی: استفاده از list comprehension سریع‌تر
            search_terms = search_query.split()
            def _matches(land):
                # ساخت یک رشته واحد برای جستجوی سریع‌تر
                search_text = ' '.join([
                    str(land.get('title', '')),
                    str(land.get('location', '')),
                    str(land.get('category', '')),
                    str(land.get('description', ''))
                ]).lower()
                return all(term in search_text for term in search_terms)
            express_lands = [l for l in express_lands if _matches(l)]
        
        # صفحه‌بندی
        total = len(express_lands)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_lands = express_lands[start_idx:end_idx]
        
        # کاهش حجم داده: فقط فیلدهای ضروری + thumb/full
        minimal_lands = []
        for land in paginated_lands:
            images = land.get('images', []) or []
            cover = images[0] if images else None
            cover_variants = prepare_variants_dict(cover)
            minimal_lands.append({
                'code': land.get('code'),
                'title': land.get('title'),
                'location': land.get('location'),
                'category': land.get('category'),
                'images': images[:1],  # فقط اولین تصویر
                'image_thumb': cover_variants.get('thumb'),
                'image_full': cover_variants.get('full'),
                'image_raw': cover_variants.get('raw'),
                'images_v2': [prepare_variants_dict(i) for i in images],
                'video': land.get('video'),
                'price_total': land.get('price_total'),
                'created_at': land.get('created_at')
            })
        
        response = make_response(jsonify({
            'success': True,
            'lands': minimal_lands,
            'pagination': {
                'page': page,
                'pages': pages,
                'total': total,
                'per_page': per_page,
                'has_next': page < pages,
                'has_prev': page > 1
            }
        }))
        
        # اضافه کردن cache headers برای سرعت بیشتر
        response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=120'
        response.headers['Vary'] = 'Accept-Encoding'
        if etag:
            response.headers['ETag'] = etag
        
        return response
    except Exception as e:
        current_app.logger.error(f"Error in express list API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'خطا در بارگذاری فایل‌ها'
        }), 500

@express_api_bp.route('/express/<string:code>')
def get_express_detail(code):
    """Get express listing detail (بهینه شده)"""
    try:
        express_lands = load_express_lands_cached()
        stats = get_lands_file_stats()
        base_etag = stats.get("etag") or 'W/"lands"'
        express_land = next((land for land in express_lands if land.get('code') == code), None)
        
        if not express_land:
            return jsonify({
                'success': False,
                'error': 'آگهی اکسپرس یافت نشد'
            }), 404
        
        etag = f'{base_etag}-detail-{code}'
        inm = request.headers.get("If-None-Match")
        if inm and etag and inm == etag:
            resp = make_response(("", 304))
            resp.headers['ETag'] = etag
            resp.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=600'
            return resp

        images = express_land.get('images') or []
        cover_variants = prepare_variants_dict(images[0] if images else None)
        express_land = dict(express_land)
        express_land.update({
            'image_thumb': cover_variants.get('thumb'),
            'image_full': cover_variants.get('full'),
            'image_raw': cover_variants.get('raw'),
            'images_v2': [prepare_variants_dict(i) for i in images],
        })

        response = make_response(jsonify({
            'success': True,
            'land': express_land
        }))
        response.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=600'
        response.headers['Vary'] = 'Accept-Encoding'
        response.headers['ETag'] = etag
        return response
    except Exception as e:
        current_app.logger.error(f"Error loading express detail: {e}")
        return jsonify({
            'success': False,
            'error': 'خطا در بارگذاری جزئیات آگهی'
        }), 500

@express_api_bp.route('/express/<string:code>/contact', methods=['POST'])
def express_contact_request(code):
    """Handle contact request for express listing"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        message = data.get('message', '').strip()
        
        if not name or not phone:
            return jsonify({
                'success': False,
                'error': 'نام و شماره تماس الزامی است'
            }), 400
        
        # Get express land details (بهینه شده)
        express_lands = load_express_lands_cached()
        express_land = next((land for land in express_lands if land.get('code') == code), None)
        
        if not express_land:
            return jsonify({
                'success': False,
                'error': 'آگهی اکسپرس یافت نشد'
            }), 404
        
        # Add notification for admin
        # نیاز به user_id برای ارسال نوتیفیکیشن
        # در صورت نیاز می‌توان به ادمین یا کاربر خاصی ارسال کرد
        # add_notification(
        #     user_id="admin",
        #     title="درخواست مشاوره اکسپرس",
        #     body=f"درخواست مشاوره برای آگهی {express_land.get('title', '')} از {name} ({phone})",
        #     ntype="info",
        #     ad_id=code
        # )
        
        return jsonify({
            'success': True,
            'message': 'درخواست شما با موفقیت ارسال شد. تیم پشتیبانی وینور با شما تماس خواهد گرفت.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error handling express contact request: {e}")
        return jsonify({
            'success': False,
            'error': 'خطا در ارسال درخواست'
        }), 500
