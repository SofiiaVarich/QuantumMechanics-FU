import hashlib
import hmac
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

import pytest

from quantum_tutor.web.auth import AuthenticationError, authenticate_init_data

TOKEN = "123456:test-only-token"


def signed_data(user_id: int = 123, timestamp: int = 1000, **extra: str) -> str:
    values = {"auth_date": str(timestamp), "user": json.dumps({"id": user_id}), "query_id": "test", **extra}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


@pytest.mark.parametrize("value,now,code", [
    ("", 1001, "auth_missing"),
    ("user=fake", 1001, "auth_invalid"),
    (signed_data(), 4601, "auth_expired"),
    (signed_data(timestamp=1032), 1001, "auth_invalid"),
    (signed_data().replace("hash=", "hash=bad"), 4601, "auth_invalid"),
])
def test_authentication_error_codes(value, now, code):
    with pytest.raises(AuthenticationError) as caught:
        authenticate_init_data(value, TOKEN, (123,), now=now)
    assert caught.value.code == code


def test_signature_field_is_included_in_bot_token_hmac():
    value = signed_data(signature="telegram_signature-_/+")
    assert authenticate_init_data(value, TOKEN, (123,), now=4600) == 123
    with pytest.raises(AuthenticationError) as caught:
        authenticate_init_data(value.replace("telegram_signature", "tampered"), TOKEN, (123,), now=1001)
    assert caught.value.code == "auth_invalid"


def test_frontend_authentication_handling():
    if not shutil.which("node"):
        pytest.skip("Node.js is required for frontend authentication tests")
    app = Path(__file__).resolve().parents[1] / "src/quantum_tutor/web/static/app.js"
    harness = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const tg = {initData: 'signed-data'};
let response, calls = 0;
const context = {
  document: {getElementById: () => ({})}, window: {Telegram: {WebApp: tg}},
  AbortController, setTimeout, clearTimeout,
  fetch: async (path, options) => {
    calls++;
    assert.equal(options.headers.Authorization, 'tma signed-data');
    return response;
  }
};
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.slice(0, source.indexOf('  function percent(')) +
  'globalThis.auth = {api, errorMessage}; })();';
vm.runInNewContext(source, context);
(async () => {
  for (const [status, code, expected] of [
    [401, 'auth_missing', /missing/], [401, 'auth_expired', /expired/],
    [401, 'auth_invalid', /invalid/], [403, 'auth_forbidden', /access list/],
    [401, undefined, /invalid/], [403, undefined, /access list/]
  ]) {
    response = {ok: false, status, json: async () => {
      if (!code) throw new Error('non-JSON proxy response');
      return {code, error: 'server detail'};
    }};
    await assert.rejects(context.auth.api('/topics'), error => {
      assert.equal(error.status, status);
      assert.equal(error.code, code);
      assert.match(context.auth.errorMessage(error), expected);
      return true;
    });
  }
  tg.initData = '';
  const before = calls;
  await assert.rejects(context.auth.api('/topics'), error => {
    assert.equal(error.status, 401);
    assert.equal(error.code, 'auth_missing');
    return true;
  });
  assert.equal(calls, before);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    subprocess.run(["node", "-e", harness, str(app)], check=True, timeout=20)


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
