import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from quantum_tutor.web.auth import AuthenticationError, authenticate_init_data

TOKEN = "123456:test-only-token"


def signed_data(user_id: int = 123, timestamp: int = 1000) -> str:
    values = {"auth_date": str(timestamp), "user": json.dumps({"id": user_id}), "query_id": "test"}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_signed_login_and_allowlist() -> None:
    assert authenticate_init_data(signed_data(), TOKEN, (123,), now=1001) == 123
    with pytest.raises(PermissionError):
        authenticate_init_data(signed_data(456), TOKEN, (123,), now=1001)


@pytest.mark.parametrize("value,now", [
    ("", 1001), ("user=fake", 1001),
    (signed_data().replace("auth_date=1000", "auth_date=1001"), 1001),
    (signed_data() + "&auth_date=1000", 1001),
    (signed_data(), 10000), (signed_data(timestamp=2000), 1001),
])
def test_forged_duplicate_stale_or_future_logins_are_rejected(value: str, now: int) -> None:
    with pytest.raises(AuthenticationError):
        authenticate_init_data(value, TOKEN, (123,), now=now)
