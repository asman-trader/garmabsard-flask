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
        express_lands = [land for land in lands if land.get('is_express', False) and land.get('status') == 'approved']
        
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
        add_notification(
            title="درخواست مشاوره اکسپرس",
            message=f"درخواست مشاوره برای آگهی {express_land.get('title', '')} از {name} ({phone})",
            notification_type="express_contact",
            data={
                "land_code": code,
                "land_title": express_land.get('title', ''),
                "contact_name": name,
                "contact_phone": phone,
                "message": message
            }
        )
        
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
