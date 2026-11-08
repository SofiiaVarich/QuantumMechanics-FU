from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class AuthenticationError(ValueError):
    pass


def authenticate_init_data(
    init_data: str,
    bot_token: str,
    allowed_user_ids: tuple[int, ...],
    *,
    now: float | None = None,
    max_age: int = 3600,
) -> int:
    """Validate Telegram Web App initData; never trust initDataUnsafe/user IDs alone."""
    if not init_data or len(init_data) > 16384:
        raise AuthenticationError("Open the app from Telegram to sign in.")
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        values = dict(pairs)
        if len(pairs) != len(values):
            raise ValueError("Duplicate authentication fields")
        supplied_hash = values.pop("hash")
        check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied_hash):
            raise ValueError("Invalid signature")
        timestamp = int(values["auth_date"])
        current = time.time() if now is None else now
        if timestamp > current + 30 or current - timestamp > max_age:
            raise ValueError("Expired authentication")
        user = json.loads(values["user"])
        user_id = user["id"]
        if type(user_id) is not int:
            raise ValueError("Invalid user")
    except (ValueError, KeyError, TypeError) as error:
        raise AuthenticationError("Telegram sign-in is invalid or expired. Close and reopen the app.") from error
    if user_id not in allowed_user_ids:
        raise PermissionError("This is a private learning app.")
    return user_id
