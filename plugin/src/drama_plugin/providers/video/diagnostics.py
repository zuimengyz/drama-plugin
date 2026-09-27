"""Allowlisted vendor errors; never retain raw requests, responses or headers."""
import re
from typing import Any
import httpx


def safe_message(value: Any, secret: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.replace(secret, '[REDACTED]') if secret else value
    text = re.sub(r'data:[^\s\"\'<>]+', '[REDACTED_DATA_URL]', text, flags=re.I)
    text = re.sub(r'https?://[^\s\"\'<>]+', '[REDACTED_URL]', text, flags=re.I)
    text = re.sub(r'Bearer\s+[^\s,;\"\']+', 'Bearer [REDACTED]', text, flags=re.I)
    text = re.sub(r'(?i)(authorization|api[_ -]?key|access[_ -]?token|cookie)\s*[\"\']?\s*[:=]\s*[\"\']?[^\s,;\"\']+', r'\1=[REDACTED]', text)
    text = re.sub(r'[A-Za-z0-9+/=_-]{128,}', '[REDACTED_LONG_TOKEN]', text)
    return ' '.join(text.replace('\x00', '').split())[:500] or None


def identifier(value: Any, secret: str) -> str | None:
    return value if isinstance(value, str) and (not secret or secret not in value) and re.fullmatch(r'[\w.:-]{1,200}', value, re.ASCII) else None


def seedance_error(response: httpx.Response, secret: str) -> dict[str, str | int]:
    result: dict[str, str | int] = {'http_status': response.status_code}
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get('error', {}) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        error = {}
    code = identifier(error.get('code'), secret)
    message = safe_message(error.get('message'), secret)
    request_id = identifier(response.headers.get('x-request-id') or response.headers.get('x-tt-logid')
                            or (body.get('request_id') if isinstance(body, dict) else None), secret)
    if code: result['official_error_code'] = code
    if message: result['official_error_message'] = message
    if request_id: result['request_id'] = request_id
    return result
