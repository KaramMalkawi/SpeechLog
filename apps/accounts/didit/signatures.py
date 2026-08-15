from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any


def _shorten_floats(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _shorten_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_shorten_floats(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_json(payload: dict) -> str:
    return json.dumps(
        _shorten_floats(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def verify_signature_v2(payload: dict, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_signature_raw(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_signature_simple(payload: dict, signature: str, secret: str) -> bool:
    canonical = ":".join(
        [
            str(payload.get("timestamp", "")),
            str(payload.get("session_id", "")),
            str(payload.get("status", "")),
            str(payload.get("webhook_type", "")),
        ]
    )
    expected = hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_timestamp_header(timestamp_header: str | None, *, max_skew_seconds: int = 300) -> bool:
    if not timestamp_header:
        return False
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        return False
    return abs(int(time.time()) - timestamp) <= max_skew_seconds


def verify_didit_webhook(
    *,
    raw_body: bytes,
    headers: dict[str, str],
    secret: str,
) -> tuple[dict | None, bool, str]:
    """Return (payload, verified, verification_method)."""
    timestamp = headers.get("X-Timestamp") or headers.get("x-timestamp")
    if not verify_timestamp_header(timestamp):
        return None, False, ""

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, False, ""

    sig_v2 = headers.get("X-Signature-V2") or headers.get("x-signature-v2")
    if sig_v2 and verify_signature_v2(payload, sig_v2, secret):
        return payload, True, "v2"

    sig_raw = headers.get("X-Signature") or headers.get("x-signature")
    if sig_raw and verify_signature_raw(raw_body, sig_raw, secret):
        return payload, True, "raw"

    sig_simple = headers.get("X-Signature-Simple") or headers.get("x-signature-simple")
    if sig_simple and verify_signature_simple(payload, sig_simple, secret):
        return payload, True, "simple"

    return payload, False, ""
