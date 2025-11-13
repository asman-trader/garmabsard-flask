import base64


def encode_partner_ref(phone: str) -> str:
    """Return a compact token that encodes the partner phone."""
    phone = (phone or "").strip()
    if not phone:
        return ""
    token = base64.urlsafe_b64encode(phone.encode()).decode()
    return token.rstrip("=")


def decode_partner_ref(token: str) -> str:
    """Decode partner token back to phone; return empty string on failure."""
    token = (token or "").strip()
    if not token:
        return ""
    padding = "=" * (-len(token) % 4)
    try:
        return base64.urlsafe_b64decode(token + padding).decode()
    except Exception:
        return ""
