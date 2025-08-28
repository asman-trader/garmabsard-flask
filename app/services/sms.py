# app/services/sms.py
import os, requests
from flask import current_app
SMS_API_KEY = os.environ.get("SMS_API_KEY") or "cwDc9dmxkF4c1avGDTBFnlRPyJQkxk2TVhpZCj6ShGrVx9y4"
TEMPLATE_ID = 373657

def send_sms_code(phone: str, code: str):
    url = "https://api.sms.ir/v1/send/verify"
    headers = {"Content-Type":"application/json","Accept":"application/json","x-api-key":SMS_API_KEY}
    data = {"mobile": phone, "templateId": TEMPLATE_ID, "parameters":[{"name":"code","value":code}]}
    try:
        requests.post(url, headers=headers, json=data, timeout=10)
    except Exception as e:
        try: current_app.logger.error("❌ SMS error: %s", e)
        except Exception: print("❌ SMS error:", e)
