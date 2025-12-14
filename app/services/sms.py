# app/services/sms.py
import os, requests
from flask import current_app
SMS_API_KEY = os.environ.get("SMS_API_KEY") or "AcEcwFoGsqya9QdAii8QWhU51eie84sEbB9I4mJ0gknvm7lg"
# Updated template to the new requested one (WebOTP-friendly template configured in panel)
TEMPLATE_ID = 878451
# شماره خط اختصاصی پیش‌فرض
DEFAULT_LINE_NUMBER = "300089930616"

def send_sms_code(phone: str, code: str):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {"Content-Type":"application/json","Accept":"application/json","x-api-key":SMS_API_KEY}
    # Note: parameter name must match the template variable in sms.ir panel
    data = {"mobile": phone, "templateId": TEMPLATE_ID, "parameters":[{"name":"CODE","value":str(code)}]}
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except Exception as e:
        try: current_app.logger.error("❌ SMS error: %s", e)
        except Exception: print("❌ SMS error:", e)


def send_sms_template(mobile: str, template_id: int, parameters: dict | None = None, api_key: str | None = None) -> dict:
    """
    ارسال پیامک با استفاده از قالب‌های آماده (Ultra Fast/Verify API در sms.ir).
    parameters: دیکشنری نام→مقدار برای پارامترهای قالب.
    خروجی: دیکشنری شامل کلیدهای ok, status, body.
    """
    url = "https://api.sms.ir/v1/send/verify"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": (api_key or SMS_API_KEY),
    }
    params_list = []
    if parameters:
        for name, value in parameters.items():
            params_list.append({"name": str(name), "value": str(value)})
    payload = {
        "mobile": str(mobile),
        "templateId": int(template_id),
        "parameters": params_list,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        content_type = resp.headers.get("content-type", "")
        body = resp.json() if content_type.lower().startswith("application/json") else {"raw": resp.text}
        ok = 200 <= resp.status_code < 300
        return {"ok": ok, "status": resp.status_code, "body": body}
    except Exception as e:
        try:
            current_app.logger.error("❌ SMS template error: %s", e)
        except Exception:
            print("❌ SMS template error:", e)
        return {"ok": False, "status": 0, "body": {"error": str(e)}}


def send_sms_direct(mobile: str, message: str, line_number: str | None = None, api_key: str | None = None) -> dict:
    """
    ارسال پیامک مستقیم بدون قالب (Simple SMS API در sms.ir).
    mobile: شماره موبایل گیرنده
    message: متن پیامک
    line_number: شماره خط اختصاصی (اختیاری، در صورت عدم ارسال از پیش‌فرض استفاده می‌شود)
    api_key: کلید API (اختیاری)
    خروجی: دیکشنری شامل کلیدهای ok, status, body.
    """
    # استفاده از خط پیش‌فرض در صورت عدم ارسال line_number
    final_line_number = line_number or DEFAULT_LINE_NUMBER
    
    # sms.ir برای ارسال مستقیم از endpoint /v1/send/bulk استفاده می‌کند
    url = "https://api.sms.ir/v1/send/bulk"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": (api_key or SMS_API_KEY),
    }
    payload = {
        "lineNumber": str(final_line_number),
        "messageText": str(message),
        "mobiles": [str(mobile)],  # لیست شماره‌ها (حتی برای یک شماره)
        "sendDateTime": None  # ارسال فوری
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        content_type = resp.headers.get("content-type", "")
        body = resp.json() if content_type.lower().startswith("application/json") else {"raw": resp.text}
        ok = 200 <= resp.status_code < 300
        return {"ok": ok, "status": resp.status_code, "body": body}
    except Exception as e:
        try:
            current_app.logger.error("❌ SMS direct error: %s", e)
        except Exception:
            print("❌ SMS direct error:", e)
        return {"ok": False, "status": 0, "body": {"error": str(e)}}