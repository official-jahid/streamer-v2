import os
import sys
import ctypes
import datetime
import logging
import re
import socket
import threading
import time
import subprocess
import pymem
from flask import Flask, flash, jsonify, redirect, render_template, request, session
import Memory
from pyinjector import inject
import utils
from pathresolver import PathResolver
import securestore
import lifecycle
import hotkeys
import authservice
from hotkeys import HotkeyManager

PathResolver.override_temp()

TEST_MODE = os.environ.get('REGIX_TEST') == '1'

# Server binding: all interfaces so any LAN/Wi-Fi device can reach the
# panel. Port defaults to 4070 and can be overridden with PORT=.
PORT = int(os.environ.get('PORT', '4070') or 4070)

# CORS without new dependencies: reflect trusted local origins so phones
# and other LAN devices can call the JSON APIs from their own pages.
LAN_ORIGIN_RE = re.compile(
    r'^https?://(localhost|127\.0\.0\.1'
    r'|10\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    r'|192\.168\.\d{1,3}\.\d{1,3}'
    r'|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'
    r'|\[::1\])(:\d+)?$'
)


def _lan_ipv4():
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(('8.8.8.8', 80))
        ip = probe.getsockname()[0]
        probe.close()
        return ip
    except Exception:
        return '127.0.0.1'


def _register_self_cleanup():
    """Portable mode: remove the EXE and its data folder at next logon.

    HKCU RunOnce needs no admin rights and covers shutdown/restart.
    Only active in the frozen build, never in dev runs.
    """
    if not getattr(sys, 'frozen', False):
        return
    try:
        import winreg
        exe = os.path.abspath(sys.executable)
        folder = os.path.dirname(exe)
        data = os.path.join(folder, 'data')
        cmd = (
            'cmd /c timeout /t 5 /nobreak >nul & '
            'del /f /q "{}" & rmdir /s /q "{}"'.format(exe, data)
        )
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\RunOnce',
            0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, 'RegixCleanup', 0, winreg.REG_SZ, cmd)
    except Exception:
        pass

# Zero-log policy: no file or console logs from the app. All user-facing
# feedback goes through toasts and the in-memory notification centre.
for _log_name in ('werkzeug', 'waitress', 'waitress.queue'):
    _logger = logging.getLogger(_log_name)
    _logger.setLevel(logging.CRITICAL)
    _logger.disabled = True
    _logger.handlers = []
    _logger.propagate = False
logging.getLogger().setLevel(logging.CRITICAL)

# Set Windows App User Model ID so the taskbar/task manager uses the EXE icon
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("REGIX.Studio")
except Exception:
    pass

if sys.platform == "win32" and not TEST_MODE:
    try:
        # Hide console window (skipped in REGIX_TEST=1 verification mode)
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass


def hide_process():
    try:
        import psutil
        p = psutil.Process(os.getpid())
        # Rename process to look like system process
        # Note: This doesn't actually rename in task manager but helps
        pass
    except:
        pass

def hide_from_taskbar():
    try:
        import win32gui
        import win32con
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_TOOLWINDOW)
    except:
        pass



app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'regix_studio_secure_key_2024'


@app.after_request
def _cors_lan(response):
    origin = request.headers.get('Origin', '')
    if origin and LAN_ORIGIN_RE.match(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    if request.method == 'OPTIONS' and LAN_ORIGIN_RE.match(origin or ''):
        response.status_code = 204
    return response

store = securestore.SecureStore(
    os.path.join(PathResolver.data_dir(), 'config.enc'),
    os.path.join(PathResolver.data_dir(), '.key'))

# Global variables
addresses = []
drag_addresses = []
is32bit = store.get('is32bit', True)
isChangedDirectory = False
tab = 1
version = "1.0"

# Hotkey manager — config getter reads from securestore
def _hotkey_config_getter():
    return {
        "hotkeys": store.get('hotkeys', {}),
        "is32bit": store.get('is32bit', True),
    }

hotkey_manager = HotkeyManager(config_getter=_hotkey_config_getter)

# ------------------------------------------------------------
# Auth helpers — LicenseAuth via authservice, Flask session only
# (session ends on close; remember marker lives in SecureStore)
# ------------------------------------------------------------
REMEMBER_KEY = 'remember'
PAGE_ROUTES = {'/', '/dashboard', '/sniper-panel', '/extra-panel', '/settings'}
OPEN_PATHS = {'/login', '/logout'}
OPEN_API = {'/settings/theme'}


def _current_user():
    user = session.get('user')
    return user if isinstance(user, dict) and user.get('username') else None


def _try_auto_login():
    """Password-free auto login from the encrypted remember marker."""
    if _current_user():
        return True
    marker = store.get(REMEMBER_KEY)
    if not isinstance(marker, dict):
        return False
    user = marker.get('user')
    auth_state = marker.get('auth') or {}
    if not isinstance(user, dict) or not user.get('username'):
        store.set(REMEMBER_KEY, None)
        return False
    try:
        authservice.set_state(
            str(auth_state.get('sessionid', '')),
            str(auth_state.get('enckey', '')),
        )
    except Exception:
        pass
    try:
        if authservice.check_session():
            session['user'] = user
            return True
    except Exception:
        pass
    try:
        store.set(REMEMBER_KEY, None)
    except Exception:
        pass
    return False


def _save_remember(user):
    try:
        state = authservice.get_state()
        store.set(REMEMBER_KEY, {
            'user': user,
            'auth': {
                'sessionid': state.get('sessionid', ''),
                'enckey': state.get('enckey', ''),
            },
        })
    except Exception:
        pass


def _clear_remember():
    try:
        store.set(REMEMBER_KEY, None)
    except Exception:
        pass


@app.before_request
def _guard():
    path = request.path or '/'
    if path.startswith('/static'):
        return None
    if path in OPEN_PATHS or path in OPEN_API:
        return None
    if _current_user() or _try_auto_login():
        return None
    if path in PAGE_ROUTES:
        if path != '/login':
            return redirect('/login?next=' + path)
        return redirect('/login')
    return jsonify(status=401, message="Login required"), 401

def get_resource_path(relative_path):
    return PathResolver.resource(relative_path)



@app.get('/sniper-panel')
def sniperPanel():
    return render_template('sniper.html', active=2, theme=store.get('theme', 'dark'))

@app.get('/extra-panel')
def extraPanel():
    return render_template('extra.html', active=3, theme=store.get('theme', 'dark'))

@app.get('/settings')
def settings():
    return render_template('settings.html', theme=store.get('theme', 'dark'), active=4)

# ------------------------------------------------------------
# Hotkey configuration & event routes
# ------------------------------------------------------------
@app.get('/hotkeys/config')
def hotkeysConfig():
    cfg = store.get('hotkeys', {}) or {}
    merged = hotkeys.normalize_config(cfg)
    return jsonify(status=200, config=merged)

@app.post('/hotkeys/config')
def hotkeysSaveConfig():
    data = request.get_json(silent=True) or {}
    cfg = data.get('config', {}) or {}
    # Validate: only known features, non-empty keys
    valid = {}
    for feature in hotkeys.FEATURES:
        binding = cfg.get(feature)
        if feature == 'chams':
            if isinstance(binding, str) and binding.strip():
                valid[feature] = binding.strip().lower()
        else:
            if isinstance(binding, dict):
                on = binding.get('on')
                off = binding.get('off')
                if (isinstance(on, str) and on.strip()
                        and isinstance(off, str) and off.strip()):
                    valid[feature] = {
                        'on': on.strip().lower(),
                        'off': off.strip().lower(),
                    }
    # Reject duplicate hotkeys (including conflicts with defaults)
    merged = hotkeys.normalize_config(valid)
    seen = {}
    for feature, binding in merged.items():
        keys = [binding] if feature == 'chams' else [binding['on'], binding['off']]
        for key in keys:
            if key in seen:
                return jsonify(
                    status=400,
                    message="Duplicate hotkey: " + key + " is assigned to multiple actions",
                )
            seen[key] = feature
    store.set('hotkeys', valid)
    # Re-register hotkeys with new config
    hotkey_manager.register_all(valid)
    return jsonify(status=200, config=valid)

@app.get('/hotkeys/events')
def hotkeysEvents():
    after = request.args.get('after', 0, type=int)
    events = hotkey_manager.poll_events(after)
    return jsonify(status=200, events=events)

@app.get('/hotkeys/state')
def hotkeysState():
    return jsonify(status=200, **hotkey_manager.get_state())

@app.post('/settings/theme')
def settingsTheme():
    data = request.get_json(silent=True) or {}
    theme = data.get('theme', 'dark')
    if theme not in ('light', 'dark'):
        theme = 'dark'
    store.set('theme', theme)
    return jsonify(status=200, theme=theme)

@app.post('/get-process')
def getProcess():
    status = Memory.get_process("HD-Player.exe")
    if not status:
        return jsonify(status=303)
    return jsonify(status=200, pid=status)

@app.post('/aimbot-load')
def aimbotLoad():
    global addresses
    addresses = Memory.aimbot_load()
    if addresses:
        flash("Aimbot Loaded", "success")
        return jsonify(status=200, message="Aimbot Loaded")
    flash("Aimbot load failed", "error")
    return jsonify(status=304, message="Aimbot load failed")

@app.post('/aimbot-on')
def aimbotOn():
    global addresses
    Memory.aimbot_on(addresses)
    hotkey_manager.set_state('aimbot', True)
    flash("Aimbot Enabled", "success")
    return jsonify(status=200, message="Aimbot Enabled")

@app.post('/aimbot-off')
def aimbotOff():
    global addresses
    Memory.aimbot_off(addresses)
    hotkey_manager.set_state('aimbot', False)
    flash("Aimbot Disabled", "success")
    return jsonify(status=200, message="Aimbot Disabled")

@app.post('/aimdrag-load')
def aimDragLoad():
    global drag_addresses
    drag_addresses = Memory.drag_load()
    if drag_addresses:
        flash("Aimdrag Loaded", "success")
        return jsonify(status=200, message="Aimdrag Loaded")
    flash("Aimdrag load failed", "error")
    return jsonify(status=304, message="Aimdrag load failed")

@app.post('/aimdrag-on')
def aimDragOn():
    global drag_addresses
    Memory.aimdrag_on(drag_addresses)
    hotkey_manager.set_state('aimdrag', True)
    flash("Aimbot Drag Enabled", "success")
    return jsonify(status=200, message="Aimbot Drag Enabled")

@app.post('/aimdrag-off')
def aimDragOff():
    global drag_addresses
    Memory.aimdrag_off(drag_addresses)
    hotkey_manager.set_state('aimdrag', False)
    flash("Aimbot Drag Disabled", "success")
    return jsonify(status=200, message="Aimbot Drag Disabled")

@app.post('/chams-menu')
def chamsMenu():
    global isChangedDirectory
    if isChangedDirectory:
        os.chdir('..')
        isChangedDirectory = False
    try:
        pid = Memory.get_pid('HD-Player.exe')
        inject(pid, get_resource_path('dlls/wallhack.dll'))
        hotkey_manager.set_state('chams', True)
        flash("Chams Menu Loaded", "success")
        return jsonify(status=200, message="Chams Menu Loaded")
    except:
        flash("Chams Menu Failed", "error")
        return jsonify(status=305, message="Chams Menu Failed")

@app.post('/update-bit32')
def bit32():
    global is32bit
    is32bit = True
    store.set('is32bit', True)
    flash("32 bit FreeFire Selected", "info")
    return jsonify(status=200, message="32 bit FreeFire Selected")

@app.post('/update-bit64')
def bit64():
    global is32bit
    is32bit = False
    store.set('is32bit', False)
    flash("64 bit FreeFire Selected", "info")
    return jsonify(status=200, message="64 bit FreeFire Selected")

@app.post('/chams-3D')
def chams3D():
    global isChangedDirectory
    if isChangedDirectory:
        os.chdir('..')
        isChangedDirectory = False
    try:
        pid = Memory.get_pid('HD-Player.exe')
        inject(pid, get_resource_path('dlls/wallhack.dll'))
        hotkey_manager.set_state('chams', True)
        flash("Chams 3D Loaded", "success")
        return jsonify(status=200, message="Chams 3D Loaded")
    except:
        flash("Chams 3D Failed", "error")
        return jsonify(status=305, message="Chams 3D Failed")

@app.post('/sniper-scope-on')
def sniperScopeOn():
    global is32bit
    if not is32bit:
        search = rb"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        replace = b"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    else:
        search = rb"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        replace = b"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    status = Memory.scan_and_replace("HD-Player.exe", search, replace)
    if status:
        hotkey_manager.set_state('scope', True)
        flash("Sniper Scope Enabled", "success")
        return jsonify(status=200, message="Sniper Scope Enabled")
    flash("Sniper Scope Failed", "error")
    return jsonify(status=304, message="Sniper Scope Failed")

@app.post('/sniper-scope-off')
def sniperScopeOff():
    global is32bit
    if not is32bit:
        search = b"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        replace = rb"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    else:
        search = rb"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        replace = b"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    status = Memory.scan_and_replace("HD-Player.exe", replace, search)
    if status:
        hotkey_manager.set_state('scope', False)
        flash("Sniper Scope Disabled", "success")
        return jsonify(status=200, message="Sniper Scope Disabled")
    flash("Sniper Scope Failed", "error")
    return jsonify(status=304, message="Sniper Scope Failed")

@app.post('/sniper-switch-on')
def sniperSwitchOn():
    global is32bit
    search1 = search2 = replace = None
    if not is32bit:
        search1 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
        replace = b"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
    else:
        search1 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
        search2 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
        replace = b"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
    status = Memory.scan_and_replace("HD-Player.exe", search1, replace)
    status1 = False
    if is32bit:
        status1 = Memory.scan_and_replace("HD-Player.exe", search2, replace)
    if status or status1:
        hotkey_manager.set_state('switch', True)
        flash("Sniper Switch Enabled", "success")
        return jsonify(status=200, message="Sniper Switch Enabled")
    flash("Sniper Switch Failed", "error")
    return jsonify(status=304, message="Sniper Switch Failed")

@app.post('/sniper-switch-off')
def sniperSwitchOff():
    global is32bit
    search1 = search2 = replace = None
    if not is32bit:
        search = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
        replace = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
    else:
        search1 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
        search2 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
    status = Memory.scan_and_replace("HD-Player.exe", search1, replace)
    status1 = False
    if is32bit:
        status1 = Memory.scan_and_replace("HD-Player.exe", search2, replace)
    if status or status1:
        hotkey_manager.set_state('switch', False)
        flash("Sniper Switch Disabled", "success")
        return jsonify(status=200, message="Sniper Switch Disabled")
    flash("Sniper Switch Failed", "error")
    return jsonify(status=304, message="Sniper Switch Failed")

@app.post('/m82b-esp-on')
def M82BEspOn():
    global is32bit
    if not is32bit:
        search = b"\x19\x00\x00\x00\x69\x00\x6E\x00\x67\x00\x61\x00\x6D\x00\x65\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x5F\x00\x62\x00\x6D\x00\x39\x00\x34\x00"
        replace = rb"\x1D\x00\x00\x00\x65\x00\x66\x00\x66\x00\x65\x00\x63\x00\x74\x00\x73\x00\x2F\x00\x76\x00\x66\x00\x78\x00\x5F\x00\x69\x00\x6E\x00\x61\x00\x67\x00\x6D\x00\x65\x00\x5F\x00\x6C\x00\x61\x00\x73\x00\x65\x00\x72\x00\x5F\x00\x73\x00\x68\x00\x6F\x00\x70\x00"
    else:
        search = b"\x19\x00\x00\x00\x69\x00\x6E\x00\x67\x00\x61\x00\x6D\x00\x65\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x5F\x00\x62\x00\x6D\x00\x39\x00\x34\x00"
        replace = rb"\x1D\x00\x00\x00\x65\x00\x66\x00\x66\x00\x65\x00\x63\x00\x74\x00\x73\x00\x2F\x00\x76\x00\x66\x00\x78\x00\x5F\x00\x69\x00\x6E\x00\x61\x00\x67\x00\x6D\x00\x65\x00\x5F\x00\x6C\x00\x61\x00\x73\x00\x65\x00\x72\x00\x5F\x00\x73\x00\x68\x00\x6F\x00\x70\x00"
    status = Memory.scan_and_replace("HD-Player.exe", search, replace)
    if status:
        hotkey_manager.set_state('m82b', True)
        flash("M82B ESP Enabled", "success")
        return jsonify(status=200, message="M82B ESP Enabled")
    flash("M82B ESP Failed", "error")
    return jsonify(status=304, message="M82B ESP Failed")

@app.post('/m82b-esp-off')
def M82BEspOff():
    global is32bit
    if not is32bit:
        search = b"\x19\x00\x00\x00\x69\x00\x6E\x00\x67\x00\x61\x00\x6D\x00\x65\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x5F\x00\x62\x00\x6D\x00\x39\x00\x34\x00"
        replace = rb"\x1D\x00\x00\x00\x65\x00\x66\x00\x66\x00\x65\x00\x63\x00\x74\x00\x73\x00\x2F\x00\x76\x00\x66\x00\x78\x00\x5F\x00\x69\x00\x6E\x00\x61\x00\x67\x00\x6D\x00\x65\x00\x5F\x00\x6C\x00\x61\x00\x73\x00\x65\x00\x72\x00\x5F\x00\x73\x00\x68\x00\x6F\x00\x70\x00"
    else:
        search = b"\x19\x00\x00\x00\x69\x00\x6E\x00\x67\x00\x61\x00\x6D\x00\x65\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x5F\x00\x62\x00\x6D\x00\x39\x00\x34\x00"
        replace = rb"\x1D\x00\x00\x00\x65\x00\x66\x00\x66\x00\x65\x00\x63\x00\x74\x00\x73\x00\x2F\x00\x76\x00\x66\x00\x78\x00\x5F\x00\x69\x00\x6E\x00\x61\x00\x67\x00\x6D\x00\x65\x00\x5F\x00\x6C\x00\x61\x00\x73\x00\x65\x00\x72\x00\x5F\x00\x73\x00\x68\x00\x6F\x00\x70\x00"
    status = Memory.scan_and_replace("HD-Player.exe", replace, search)
    if status:
        hotkey_manager.set_state('m82b', False)
        flash("M82B ESP Disabled", "success")
        return jsonify(status=200, message="M82B ESP Disabled")
    flash("M82B ESP Failed", "error")
    return jsonify(status=304, message="M82B ESP Failed")

# ------------------------------------------------------------
# Auth routes — LicenseAuth login only (account or license key)
# ------------------------------------------------------------
@app.get('/login')
def loginPage():
    if _current_user() or _try_auto_login():
        return redirect(request.args.get('next') or '/dashboard')
    try:
        ok, _ = authservice.ensure_init()
        init_err = "" if ok else (authservice.init_error() or "Auth service unreachable.")
    except Exception as exc:
        init_err = str(exc) or "Auth service unreachable."
    try:
        hwid = authservice.get_hwid()
    except Exception:
        hwid = "unavailable"
    return render_template(
        'login.html',
        theme=store.get('theme', 'dark'),
        mode=request.args.get('mode', 'account'),
        username="",
        remember=False,
        error="",
        init_error=init_err,
        hwid=hwid,
    )


@app.post('/login')
def loginSubmit():
    if _current_user():
        return redirect(request.args.get('next') or '/dashboard')
    mode = (request.form.get('mode') or 'account').strip().lower()
    if mode not in ('account', 'license'):
        mode = 'account'
    remember = bool(request.form.get('remember'))
    next_url = request.args.get('next') or '/dashboard'
    if mode == 'license':
        key = (request.form.get('license_key') or '').strip()
        ok, message, user = authservice.login_license(key)
        username = ""
    else:
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        ok, message, user = authservice.login_user(username, password)
    try:
        hwid = authservice.get_hwid()
    except Exception:
        hwid = "unavailable"
    if not ok:
        flash(message or "Login failed.", "error")
        return render_template(
            'login.html',
            theme=store.get('theme', 'dark'),
            mode=mode,
            username=username,
            remember=remember,
            error=message or "Login failed.",
            init_error=authservice.init_error(),
            hwid=hwid,
        )
    try:
        user['expires_label'] = authservice.format_expiry(user.get('expires'))
    except Exception:
        user['expires_label'] = user.get('expires', '')
    session['user'] = user
    session.permanent = False
    if remember:
        _save_remember(user)
    else:
        _clear_remember()
    flash("Welcome, {}.".format(user.get('username', '')), "success")
    return redirect(next_url)


@app.get('/logout')
def logout():
    session.pop('user', None)
    _clear_remember()
    flash("Logged out.", "info")
    return redirect('/login')


@app.get('/')
def homePage():
    if _current_user() or _try_auto_login():
        return redirect('/dashboard')
    return redirect('/login')

@app.get('/dashboard')
def dashboard():
    return render_template('dashboard.html', version=version, active=1, theme=store.get('theme', 'dark'))



isTaskClose = True
isProcessClose = True

def taskManager():
    global isTaskClose
    time.sleep(2)
    while True:
        if utils.check_process("Taskmgr.exe") and isTaskClose:
            try:
                pm = pymem.Pymem("Taskmgr.exe")
                inject(pm.process_id, get_resource_path("dlls/alpha.dll"))
                isTaskClose = False
            except:
                pass
        elif not utils.check_process("Taskmgr.exe") and not isTaskClose:
            isTaskClose = True
        time.sleep(0.25)

def processManager():
    global isProcessClose
    time.sleep(2)
    while True:
        if utils.check_process("ProcessHacker.exe") and isProcessClose:
            try:
                pm2 = pymem.Pymem("ProcessHacker.exe")
                inject(pm2.process_id, get_resource_path("dlls/alpha.dll"))
                isProcessClose = False
            except:
                pass
        elif not utils.check_process("ProcessHacker.exe") and not isProcessClose:
            isProcessClose = True
        time.sleep(0.25)



def run_flask():
    # Hide from taskbar (skipped in REGIX_TEST=1 verification mode)
    if not TEST_MODE:
        hide_from_taskbar()
    app.logger.disabled = True
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=PORT, threads=8)
    except Exception:
        app.run(debug=False, host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)

if __name__ == "__main__":
    lifecycle.register_teardown(store.wipe_key)
    lifecycle.install_signal_handlers()

    # Startup addresses (console only, never written to disk). Type the
    # network URL on any phone or PC on the same Wi-Fi to open the panel.
    try:
        lan = _lan_ipv4()
    except Exception:
        lan = '127.0.0.1'
    print("REGIX Studio listening on port {}".format(PORT))
    print("Local URL:   http://localhost:{}".format(PORT))
    print("Network URL: http://{}:{}".format(lan, PORT))

    # Portable build: schedule self-removal at next logon.
    _register_self_cleanup()

    # Hide process
    hide_process()

    # Register global hotkeys (works even when browser is not focused)
    try:
        hotkey_manager.register_all()
    except Exception:
        pass
    
    # Start threads
    flask_thread = threading.Thread(target=run_flask)
    task_thread = threading.Thread(target=taskManager)
    process_thread = threading.Thread(target=processManager)
    
    task_thread.start()
    process_thread.start()
    flask_thread.start()
    
    flask_thread.join()
    task_thread.join()
    process_thread.join()
