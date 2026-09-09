"""Flask-safe LicenseAuth client for REGIX Studio.

Wraps the LicenseAuth 1.3 API without the CLI behaviors of
``licenseauth.py`` (no ``os._exit``, no ``sleep``, no ``print``).
``licenseauth.py`` stays untouched as reference.

Credentials are hardcoded per project decision (see AGENTS.md).
Checksum uses a stable exempt value until the EXE hash is
whitelisted in the LicenseAuth dashboard.
"""

import hashlib
import hmac
import threading
from uuid import uuid4

import requests

APP_NAME = "regix bios"
OWNER_ID = "RTgStl6UQK"
APP_SECRET = "d7b3c14090d628116c0497ab4fe0852dc550af73fdd73afabaa2d8ca9c133eac"
APP_VERSION = "1.0"
# Stable exempt checksum (see AGENTS.md / plan). Replace with a real
# file hash once the EXE hash is whitelisted in the dashboard.
HASH_TO_CHECK = ""

API_URL = "https://licenseauth.help/api/1.3/"
REQUEST_TIMEOUT = 12

_lock = threading.Lock()
_sessionid = ""
_enckey = ""
_initialized = False
_init_error = ""
_last_user = {}


def get_hwid():
    """Best-effort HWID without raising. Falls back to a stable hash."""
    try:
        from licenseauth import others

        hwid = others.get_hwid()
        if hwid:
            return str(hwid).strip()
    except Exception:
        pass
    try:
        import getpass
        import platform

        raw = "{}-{}-{}".format(
            getpass.getuser(), platform.node(), platform.machine()
        )
    except Exception:
        raw = "regix-studio-fallback"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _do_request(post_data):
    """POST to LicenseAuth. Returns (ok, payload_or_error)."""
    try:
        resp = requests.post(API_URL, data=post_data, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        return False, "Request timed out. Server is probably down or slow."
    except Exception as exc:
        return False, "Network error: {}".format(exc)
    if resp is None or not getattr(resp, "text", None):
        return False, "Empty response from auth server."
    key = APP_SECRET if post_data.get("type") == "init" else _enckey
    if post_data.get("type") == "log":
        return True, resp.text
    try:
        signature = resp.headers.get("signature", "")
        computed = hmac.new(
            key.encode("utf-8"), resp.text.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not signature or not hmac.compare_digest(computed, signature):
            return False, "Signature check failed. Session may have ended."
    except Exception:
        return False, "Signature check failed. Session may have ended."
    return True, resp.text


def _parse_json(text):
    import json as jsond

    try:
        return True, jsond.loads(text)
    except Exception:
        return False, "Invalid response from auth server."


def _extract_user(info):
    subs = info.get("subscriptions") or []
    first = subs[0] if subs else {}
    for sub in subs:
        try:
            sub["expiry_label"] = format_expiry(sub.get("expiry"))
        except Exception:
            sub["expiry_label"] = sub.get("expiry", "")
    return {
        "username": info.get("username", ""),
        "ip": info.get("ip", ""),
        "hwid": info.get("hwid") or "N/A",
        "expires": first.get("expiry", ""),
        "subscription": first.get("subscription", ""),
        "subscriptions": subs,
        "createdate": info.get("createdate", ""),
        "lastlogin": info.get("lastlogin", ""),
    }


def init_session(force=False):
    """Init LicenseAuth session. Returns (ok, message). Never exits."""
    global _sessionid, _enckey, _initialized, _init_error
    with _lock:
        if _initialized and not force:
            return True, "Already initialized."
        sent_key = str(uuid4())[:16]
        _enckey = sent_key + "-" + APP_SECRET
        post_data = {
            "type": "init",
            "ver": APP_VERSION,
            "hash": HASH_TO_CHECK,
            "enckey": sent_key,
            "name": APP_NAME,
            "ownerid": OWNER_ID,
        }
    ok, text = _do_request(post_data)
    if not ok:
        with _lock:
            _initialized = False
            _init_error = text
        return False, text
    if text == "LicenseAuth_Invalid":
        msg = "Auth application not found. Check ownerid."
        with _lock:
            _initialized = False
            _init_error = msg
        return False, msg
    ok_json, data = _parse_json(text)
    if not ok_json or not isinstance(data, dict):
        msg = data if isinstance(data, str) else "Invalid response from auth server."
        with _lock:
            _initialized = False
            _init_error = msg
        return False, msg
    if data.get("message") == "invalidver":
        msg = "Invalid version. Update the app version in the dashboard."
        with _lock:
            _initialized = False
            _init_error = msg
        return False, msg
    if not data.get("success"):
        msg = str(data.get("message", "Init failed."))
        with _lock:
            _initialized = False
            _init_error = msg
        return False, msg
    with _lock:
        _sessionid = data.get("sessionid", "")
        _initialized = True
        _init_error = ""
    return True, "Initialized."


def ensure_init():
    if _initialized and _sessionid:
        return True, ""
    return init_session()


def login_user(username, password, hwid=None):
    """Username plus password login. Returns (ok, message, user_dict)."""
    username = (username or "").strip()
    if not username or not password:
        return False, "Enter username and password.", {}
    ok, msg = ensure_init()
    if not ok:
        return False, msg, {}
    hwid = hwid or get_hwid()
    with _lock:
        sessionid = _sessionid
    post_data = {
        "type": "login",
        "username": username,
        "pass": password,
        "hwid": hwid,
        "sessionid": sessionid,
        "name": APP_NAME,
        "ownerid": OWNER_ID,
    }
    ok, text = _do_request(post_data)
    if not ok:
        return False, text, {}
    ok_json, data = _parse_json(text)
    if not ok_json or not isinstance(data, dict):
        return False, data if isinstance(data, str) else "Invalid response.", {}
    if not data.get("success"):
        return False, str(data.get("message", "Login failed.")), {}
    user = _extract_user(data.get("info", {}))
    global _last_user
    with _lock:
        _last_user = user
    return True, str(data.get("message", "Logged in.")), user


def login_license(key, hwid=None):
    """License key only login. Returns (ok, message, user_dict)."""
    key = (key or "").strip()
    if not key:
        return False, "Enter your license key.", {}
    ok, msg = ensure_init()
    if not ok:
        return False, msg, {}
    hwid = hwid or get_hwid()
    with _lock:
        sessionid = _sessionid
    post_data = {
        "type": "license",
        "key": key,
        "hwid": hwid,
        "sessionid": sessionid,
        "name": APP_NAME,
        "ownerid": OWNER_ID,
    }
    ok, text = _do_request(post_data)
    if not ok:
        return False, text, {}
    ok_json, data = _parse_json(text)
    if not ok_json or not isinstance(data, dict):
        return False, data if isinstance(data, str) else "Invalid response.", {}
    if not data.get("success"):
        return False, str(data.get("message", "License failed.")), {}
    user = _extract_user(data.get("info", {}))
    global _last_user
    with _lock:
        _last_user = user
    return True, str(data.get("message", "Logged in.")), user


def check_session():
    """Revalidate the current LicenseAuth session. Returns True/False."""
    with _lock:
        sessionid = _sessionid
        ready = _initialized and bool(sessionid)
    if not ready:
        return False
    post_data = {
        "type": "check",
        "sessionid": sessionid,
        "name": APP_NAME,
        "ownerid": OWNER_ID,
    }
    ok, text = _do_request(post_data)
    if not ok:
        return False
    ok_json, data = _parse_json(text)
    if not ok_json or not isinstance(data, dict):
        return False
    return bool(data.get("success"))


def init_error():
    return _init_error


def get_state():
    with _lock:
        return {"sessionid": _sessionid, "enckey": _enckey, "ready": _initialized}


def set_state(sessionid, enckey):
    global _sessionid, _enckey, _initialized
    with _lock:
        _sessionid = sessionid or ""
        _enckey = enckey or ""
        _initialized = bool(_sessionid and _enckey)


def format_expiry(value):
    """Format a unix timestamp to YYYY-MM-DD HH:MM. Pass through otherwise."""
    try:
        import datetime

        stamp = int(str(value).strip())
        return datetime.datetime.utcfromtimestamp(stamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value or "")
