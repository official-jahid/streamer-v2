"""
hotkeys.py — Global keyboard hotkey manager for REGIX Studio.

Uses the `keyboard` library to register system-wide hotkeys that work even
when the browser window is not focused. Each hotkey toggles a Memory.py
feature on/off and records an event that the web frontend polls to show
toasts in the notification centre.
"""

import threading
import time
import Memory

# ============================================================
# Byte-swap patterns used by the sniper-scope / sniper-switch /
# M82B-ESP toggles. These mirror the patterns defined in app.py
# so hotkey toggles work without an HTTP round-trip.
# ============================================================

# --- Sniper Scope ---
_SCOPE_OFF_STATE = rb"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
_SCOPE_ON_STATE = b"\xFF\xFF\x08\x00\x00\x00\x00\x00\x60\x40\xCD\xCC\x8C\x3F\x8F\xC2\xF5\x3C\xCD\xCC\xCC\x3D\x06\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

# --- M82B ESP ---
_M82B_OFF_STATE = b"\x19\x00\x00\x00\x69\x00\x6E\x00\x67\x00\x61\x00\x6D\x00\x65\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x2F\x00\x70\x00\x69\x00\x63\x00\x6B\x00\x75\x00\x70\x00\x5F\x00\x62\x00\x6D\x00\x39\x00\x34\x00"
_M82B_ON_STATE = rb"\x1D\x00\x00\x00\x65\x00\x66\x00\x66\x00\x65\x00\x63\x00\x74\x00\x73\x00\x2F\x00\x76\x00\x66\x00\x78\x00\x5F\x00\x69\x00\x6E\x00\x61\x00\x67\x00\x6D\x00\x65\x00\x5F\x00\x6C\x00\x61\x00\x73\x00\x65\x00\x72\x00\x5F\x00\x73\x00\x68\x00\x6F\x00\x70\x00"

# --- Sniper Switch ---
_SWITCH_ON_REPLACE = b"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_ON_SEARCH_64 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_ON_SEARCH_32_1 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_ON_SEARCH_32_2 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"

_SWITCH_OFF_SEARCH_64 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_OFF_REPLACE = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_OFF_SEARCH_32_1 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"
_SWITCH_OFF_SEARCH_32_2 = rb"\x00\x00\x01\x00\x00\x00\xC3\xF5\xE8\x3F\x01\x00\x00\x00\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x00\x00\xC3\xF5\xE8\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\xCD\xCC\xCC\x3D\x00\x00\x00\x00\x00\x00\x5C\x43\x00\x00\x90\x42\x00\x00\xB4\x42\x96\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x09\x00\x00\x80\x3E\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x20\x41\x00\x00\x34\x42\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x3F\x0A\xD7\x23\x3F\x9A\x99\x99\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x3F\x00\x00\x00\x00\x00\x00\x40\x3F\x00\x00\x00\x00\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x80\x3F\x00\x00\x00\x00\x01"

FEATURES = [
    "aimbot",
    "aimdrag",
    "scope",
    "switch",
    "m82b",
    "chams",
]

FEATURE_LABELS = {
    "aimbot": "Aimbot",
    "aimdrag": "Aimbot Drag",
    "scope": "Sniper Scope",
    "switch": "Sniper Switch",
    "m82b": "M82B ESP",
    "chams": "Chams 3D",
}

DEFAULT_HOTKEYS = {
    "aimbot": {"on": "f1", "off": "f2"},
    "aimdrag": {"on": "f3", "off": "f4"},
    "scope": {"on": "f5", "off": "f6"},
    "switch": {"on": "f7", "off": "f8"},
    "m82b": {"on": "f9", "off": "f10"},
    "chams": "f11",
}


def normalize_config(config):
    """Merge a stored hotkey config with defaults.

    Returns the canonical schema: {feature: {"on": key, "off": key}} for
    toggle features and {chams: "key"} for the single-key chams feature.
    Legacy single-key configs (feature -> "key") are migrated to the new
    schema by mapping the stored key to the "on" action and keeping the
    default "off" key.
    """
    merged = {}
    for feature in FEATURES:
        default = DEFAULT_HOTKEYS[feature]
        stored = (config or {}).get(feature)
        if feature == "chams":
            merged[feature] = stored if isinstance(stored, str) and stored else default
        else:
            if isinstance(stored, dict):
                on = stored.get("on")
                off = stored.get("off")
            elif isinstance(stored, str) and stored:
                on = stored
                off = default.get("off")
            else:
                on = default.get("on")
                off = default.get("off")
            merged[feature] = {"on": on, "off": off}
    return merged


class HotkeyManager:
    """Manages global hotkeys, feature toggle state and event queue."""

    def __init__(self, config_getter=None):
        self._lock = threading.Lock()
        self._config_getter = config_getter or (lambda: {})
        self._state = {f: False for f in FEATURES}
        self._addresses = {}   # feature -> list of addresses (aimbot/aimdrag)
        self._events = []
        self._event_seq = 0
        self._last_event_seq = 0
        self._handles = {}
        self._current_config = {}

    # ----------------------------------------------------------
    # Public state / event API (used by Flask routes)
    # ----------------------------------------------------------
    def get_state(self):
        with self._lock:
            return {
                "state": dict(self._state),
                "config": dict(self._current_config),
            }

    def set_state(self, feature, value):
        with self._lock:
            self._state[feature] = bool(value)

    def get_state_for(self, feature):
        with self._lock:
            return self._state.get(feature, False)

    def add_event(self, etype, title, message):
        with self._lock:
            self._event_seq += 1
            self._events.append({
                "seq": self._event_seq,
                "type": etype,
                "title": title,
                "message": message,
                "time": time.strftime("%H:%M:%S"),
            })
            if len(self._events) > 300:
                self._events = self._events[-300:]
            self._last_event_seq = self._event_seq

    def poll_events(self, after_seq=0):
        with self._lock:
            return [e for e in self._events if e["seq"] > after_seq]

    def reset(self):
        """Reset all toggle state and cached addresses (used on app shutdown)."""
        with self._lock:
            self._state = {f: False for f in FEATURES}
            self._addresses = {}

    # ----------------------------------------------------------
    # Hotkey registration
    # ----------------------------------------------------------
    def register_all(self, config=None):
        """Register (or re-register) global hotkeys.

        `config` uses the canonical schema: {feature: {"on": key, "off": key}}
        for toggle features and {chams: "key"} for the single-key chams
        feature. If None, the config getter passed at construction is used.
        """
        import keyboard  # lazy import — only needed when registering

        if config is None:
            cfg = self._config_getter() or {}
            config = cfg.get("hotkeys", {}) or {}

        merged = normalize_config(config)

        self.unregister_all()
        self._current_config = dict(merged)

        for feature, binding in merged.items():
            if feature not in FEATURES or not binding:
                continue
            if feature == "chams":
                key = binding if isinstance(binding, str) else binding.get("on")
                if not key:
                    continue
                try:
                    keyboard.add_hotkey(key, lambda f=feature: self._safe_action(f, "on"), suppress=False)
                    self._handles["chams:on"] = key
                except Exception as exc:
                    self.add_event("error", "Hotkey Error",
                                   f"Could not bind {FEATURE_LABELS.get(feature, feature)} to {key}")
            else:
                on_key = binding.get("on") if isinstance(binding, dict) else binding
                off_key = binding.get("off") if isinstance(binding, dict) else None
                for action, key in (("on", on_key), ("off", off_key)):
                    if not key:
                        continue
                    try:
                        keyboard.add_hotkey(
                            key,
                            lambda f=feature, a=action: self._safe_action(f, a),
                            suppress=False,
                        )
                        self._handles[f"{feature}:{action}"] = key
                    except Exception as exc:
                        self.add_event("error", "Hotkey Error",
                                       f"Could not bind {FEATURE_LABELS.get(feature, feature)} {action} to {key}")

        active = list(self._handles.values())

    def unregister_all(self):
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self._handles = {}
        self._current_config = {}

    # ----------------------------------------------------------
    # Hotkey toggle dispatch
    # ----------------------------------------------------------
    def _safe_action(self, feature, action):
        try:
            self._run_action(feature, action)
        except Exception as exc:
            self.add_event("error", FEATURE_LABELS.get(feature, feature),
                           f"Hotkey failed: {exc}")

    def _is32bit(self):
        cfg = self._config_getter() or {}
        return bool(cfg.get("is32bit", True))

    def _run_action(self, feature, action):
        if feature == "aimbot":
            if action == "on":
                self._enable_aimbot()
            else:
                self._disable_aimbot()
        elif feature == "aimdrag":
            if action == "on":
                self._enable_aimdrag()
            else:
                self._disable_aimdrag()
        elif feature == "scope":
            if action == "on":
                self._enable_scope()
            else:
                self._disable_scope()
        elif feature == "switch":
            if action == "on":
                self._enable_switch()
            else:
                self._disable_switch()
        elif feature == "m82b":
            if action == "on":
                self._enable_m82b()
            else:
                self._disable_m82b()
        elif feature == "chams":
            self._enable_chams()

    # ---- Aimbot ----
    def _enable_aimbot(self):
        if not self._addresses.get("aimbot"):
            self._addresses["aimbot"] = Memory.aimbot_load()
        res = Memory.aimbot_on(self._addresses.get("aimbot"))
        if res:
            self.set_state("aimbot", True)
            self.add_event("success", "Aimbot", "Aimbot enabled via hotkey")
        else:
            self.add_event("error", "Aimbot", "Failed to enable aimbot")

    def _disable_aimbot(self):
        res = Memory.aimbot_off(self._addresses.get("aimbot"))
        if res:
            self.set_state("aimbot", False)
            self.add_event("success", "Aimbot", "Aimbot disabled via hotkey")
        else:
            self.add_event("error", "Aimbot", "Failed to disable aimbot")

    # ---- Aimbot drag ----
    def _enable_aimdrag(self):
        if not self._addresses.get("aimdrag"):
            self._addresses["aimdrag"] = Memory.drag_load()
        res = Memory.aimdrag_on(self._addresses.get("aimdrag"))
        if res:
            self.set_state("aimdrag", True)
            self.add_event("success", "Aimbot Drag", "Aimbot drag enabled via hotkey")
        else:
            self.add_event("error", "Aimbot Drag", "Failed to enable aimbot drag")

    def _disable_aimdrag(self):
        res = Memory.aimdrag_off(self._addresses.get("aimdrag"))
        if res:
            self.set_state("aimdrag", False)
            self.add_event("success", "Aimbot Drag", "Aimbot drag disabled via hotkey")
        else:
            self.add_event("error", "Aimbot Drag", "Failed to disable aimbot drag")

    # ---- Sniper scope ----
    def _enable_scope(self):
        ok = Memory.scan_and_replace("HD-Player.exe", _SCOPE_OFF_STATE, _SCOPE_ON_STATE)
        if ok:
            self.set_state("scope", True)
            self.add_event("success", "Sniper Scope", "Sniper scope enabled via hotkey")
        else:
            self.add_event("error", "Sniper Scope", "Failed to enable sniper scope")

    def _disable_scope(self):
        ok = Memory.scan_and_replace("HD-Player.exe", _SCOPE_ON_STATE, _SCOPE_OFF_STATE)
        if ok:
            self.set_state("scope", False)
            self.add_event("success", "Sniper Scope", "Sniper scope disabled via hotkey")
        else:
            self.add_event("error", "Sniper Scope", "Failed to disable sniper scope")

    # ---- Sniper switch ----
    def _enable_switch(self):
        is32 = self._is32bit()
        if is32:
            ok1 = Memory.scan_and_replace("HD-Player.exe", _SWITCH_ON_SEARCH_32_1, _SWITCH_ON_REPLACE)
            ok2 = Memory.scan_and_replace("HD-Player.exe", _SWITCH_ON_SEARCH_32_2, _SWITCH_ON_REPLACE)
            ok = ok1 or ok2
        else:
            ok = Memory.scan_and_replace("HD-Player.exe", _SWITCH_ON_SEARCH_64, _SWITCH_ON_REPLACE)
        if ok:
            self.set_state("switch", True)
            self.add_event("success", "Sniper Switch", "Sniper switch enabled via hotkey")
        else:
            self.add_event("error", "Sniper Switch", "Failed to enable sniper switch")

    def _disable_switch(self):
        is32 = self._is32bit()
        if is32:
            ok1 = Memory.scan_and_replace("HD-Player.exe", _SWITCH_OFF_SEARCH_32_1, _SWITCH_OFF_REPLACE)
            ok2 = Memory.scan_and_replace("HD-Player.exe", _SWITCH_OFF_SEARCH_32_2, _SWITCH_OFF_REPLACE)
            ok = ok1 or ok2
        else:
            ok = Memory.scan_and_replace("HD-Player.exe", _SWITCH_OFF_SEARCH_64, _SWITCH_OFF_REPLACE)
        if ok:
            self.set_state("switch", False)
            self.add_event("success", "Sniper Switch", "Sniper switch disabled via hotkey")
        else:
            self.add_event("error", "Sniper Switch", "Failed to disable sniper switch")

    # ---- M82B ESP ----
    def _enable_m82b(self):
        ok = Memory.scan_and_replace("HD-Player.exe", _M82B_OFF_STATE, _M82B_ON_STATE)
        if ok:
            self.set_state("m82b", True)
            self.add_event("success", "M82B ESP", "M82B ESP enabled via hotkey")
        else:
            self.add_event("error", "M82B ESP", "Failed to enable M82B ESP")

    def _disable_m82b(self):
        ok = Memory.scan_and_replace("HD-Player.exe", _M82B_ON_STATE, _M82B_OFF_STATE)
        if ok:
            self.set_state("m82b", False)
            self.add_event("success", "M82B ESP", "M82B ESP disabled via hotkey")
        else:
            self.add_event("error", "M82B ESP", "Failed to disable M82B ESP")

    # ---- Chams 3D (injection, single hotkey = inject again) ----
    def _enable_chams(self):
        import os
        from pathresolver import PathResolver

        dll_path = PathResolver.resource(os.path.join("dlls", "wallhack.dll"))
        try:
            from pyinjector import inject
            pid = Memory.get_pid("HD-Player.exe")
            inject(pid, dll_path)
            self.set_state("chams", True)
            self.add_event("success", "Chams 3D", "Chams 3D injected via hotkey")
        except Exception as exc:
            self.add_event("error", "Chams 3D", f"Failed to inject: {exc}")