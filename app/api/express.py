# app/api/express.py
# -*- coding: utf-8 -*-
"""
Express Listings API endpoints for Vinor Express feature
"""

from flask import Blueprint, jsonify, request, current_app
from app.utils.storage import load_ads_cached
from app.services.notifications import add_notification

express_api_bp = Blueprint('express_api', __name__, url_prefix='/api')

@express_api_bp.route('/express-listings')
def get_express_listings():
    """Get all express listings"""
    try:
        lands = load_ads_cached()
        express_lands = [land for land in lands if land.get('is_express', False) and land.get('express_status') == 'approved']
        
        # Sort by creation date (newest first)
        express_lands.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'lands': express_lands,
            'count': len(express_lands)
        })
    except Exception as e:
        current_app.logger.error(f"Error loading express listings: {e}")
        return jsonify({
            'success': False,
            'error': 'خطا در بارگذاری آگهی‌های اکسپرس'
        }), 500

@express_api_bp.route('/express-search')
def express_search():
    """جستجوی زنده در فایل‌های اکسپرس"""
    try:
        query = request.args.get('q', '').strip().lower()
        lands = load_ads_cached() or []
        
        # فیلتر فایل‌های اکسپرس (فقط approved)
        express_lands = [
            l for l in lands 
            if l.get('is_express', False) and l.get('express_status') != 'sold'
        ]
        
        # جستجو
        if query:
            def _matches(land):
                title = str(land.get('title', '')).lower()
                location = str(land.get('location', '')).lower()
                category = str(land.get('category', '')).lower()
                description = str(land.get('description', '')).lower()
                return (query in title or 
                        query in location or 
                        query in category or
                        query in description)
            express_lands = [l for l in express_lands if _matches(l)]
        
        # مرتب‌سازی بر اساس تاریخ ایجاد (جدیدترین اول)
        express_lands.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'lands': express_lands,
            'count': len(express_lands)
        })
    except Exception as e:
        current_app.logger.error(f"Error in express search: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'خطا در جستجو'
        }), 500

@express_api_bp.route('/express/<string:code>')
def get_express_detail(code):
    """Get express listing detail"""
    try:
        lands = load_ads_cached()
        express_land = next((land for land in lands if land.get('code') == code and land.get('is_express', False)), None)
        
        if not express_land:
            return jsonify({
                'success': False,
                'error': 'آگهی اکسپرس یافت نشد'
            }), 404
        
        return jsonify({
            'success': True,
            'land': express_land
        })
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
        
        # Get express land details
        lands = load_ads_cached()
        express_land = next((land for land in lands if land.get('code') == code and land.get('is_express', False)), None)
        
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
