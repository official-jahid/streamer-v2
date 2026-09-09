(function () {
  "use strict";

  // ------------------------------------------------------------
  // Theme toggle
  // ------------------------------------------------------------
  var root = document.documentElement;
  var themeBtn = document.getElementById("themeToggle");

  function applyTheme(theme) {
    root.classList.toggle("dark", theme !== "light");
    root.classList.toggle("light", theme === "light");
    if (themeBtn) {
      themeBtn.textContent = theme === "light" ? "Light" : "Dark";
    }
  }

  if (themeBtn) {
    applyTheme(themeBtn.dataset.theme === "light" ? "light" : "dark");

    themeBtn.addEventListener("click", function () {
      var theme = root.classList.contains("dark") ? "light" : "dark";
      rg.loading(themeBtn, true);
      rg.post("/settings/theme", { theme: theme })
        .then(function (res) {
          if (res.status === 200) {
            applyTheme(res.theme);
            window.toast.success(
              "Theme",
              "Theme set to " + (res.theme === "light" ? "Light" : "Dark"),
            );
          } else {
            window.toast.error("Theme", "Failed to save theme");
          }
        })
        .catch(function () {
          window.toast.error("Theme", "Failed to save theme");
        })
        .finally(function () {
          rg.loading(themeBtn, false);
        });
    });
  }

  // ------------------------------------------------------------
  // Hotkey configuration UI
  // ------------------------------------------------------------
  var FEATURES = [
    { key: "aimbot", label: "Aimbot", actions: ["on", "off"] },
    { key: "aimdrag", label: "Aimbot Drag", actions: ["on", "off"] },
    { key: "scope", label: "Sniper Scope", actions: ["on", "off"] },
    { key: "switch", label: "Sniper Switch", actions: ["on", "off"] },
    { key: "m82b", label: "M82B ESP", actions: ["on", "off"] },
    { key: "chams", label: "Chams 3D", actions: ["on"] },
  ];

  var DEFAULT_HOTKEYS = {
    aimbot: { on: "f1", off: "f2" },
    aimdrag: { on: "f3", off: "f4" },
    scope: { on: "f5", off: "f6" },
    switch: { on: "f7", off: "f8" },
    m82b: { on: "f9", off: "f10" },
    chams: "f11",
  };

  var hotkeyValues = {};
  var recordingFeature = null;
  var recordingAction = null;
  var list = document.getElementById("hotkeyList");
  var saveBtn = document.getElementById("hotkeySave");

  function formatHotkey(key) {
    if (!key) return "None";
    return key
      .split("+")
      .map(function (part) {
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(" + ");
  }

  function getHotkey(feature, action) {
    var stored = hotkeyValues[feature];
    if (feature === "chams") {
      return stored || DEFAULT_HOTKEYS.chams;
    }
    if (stored && stored[action]) return stored[action];
    return DEFAULT_HOTKEYS[feature][action];
  }

  function actionLabel(action) {
    return action === "on" ? "On" : "Off";
  }

  function renderHotkeyList() {
    if (!list) return;
    list.innerHTML = "";

    FEATURES.forEach(function (feature) {
      var row = document.createElement("div");
      row.className = "flex items-center justify-between gap-4 py-2";

      var info = document.createElement("div");
      var name = document.createElement("h3");
      name.className = "text-sm font-medium text-card-foreground";
      name.textContent = feature.label;
      var sub = document.createElement("p");
      sub.className = "text-xs text-muted-foreground";
      sub.textContent = "Global hotkey";
      info.appendChild(name);
      info.appendChild(sub);

      var actions = document.createElement("div");
      actions.className = "flex items-center gap-2";

      feature.actions.forEach(function (action) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "hotkey-input";
        btn.dataset.feature = feature.key;
        btn.dataset.action = action;
        btn.textContent =
          actionLabel(action) + ": " + formatHotkey(getHotkey(feature.key, action));
        btn.addEventListener("click", function () {
          handleHotkeyClick(feature.key, action, btn);
        });
        actions.appendChild(btn);
      });

      row.appendChild(info);
      row.appendChild(actions);
      list.appendChild(row);
    });
  }

  function handleHotkeyClick(feature, action, btn) {
    if (recordingFeature === feature && recordingAction === action) {
      recordingFeature = null;
      recordingAction = null;
      btn.classList.remove("hotkey-input--recording");
      btn.textContent =
        actionLabel(action) + ": " + formatHotkey(getHotkey(feature, action));
      return;
    }

    document.querySelectorAll(".hotkey-input--recording").forEach(function (el) {
      var prevFeature = el.dataset.feature;
      var prevAction = el.dataset.action;
      el.classList.remove("hotkey-input--recording");
      el.textContent =
        actionLabel(prevAction) +
        ": " +
        formatHotkey(getHotkey(prevFeature, prevAction));
    });

    recordingFeature = feature;
    recordingAction = action;
    btn.classList.add("hotkey-input--recording");
    btn.textContent = "Press a key...";
  }

  function handleKeyCapture(event) {
    if (!recordingFeature) return;

    if (event.key === "Escape") {
      var cancelledFeature = recordingFeature;
      var cancelledAction = recordingAction;
      recordingFeature = null;
      recordingAction = null;
      document.querySelectorAll(".hotkey-input--recording").forEach(function (el) {
        el.classList.remove("hotkey-input--recording");
        el.textContent =
          actionLabel(cancelledAction) +
          ": " +
          formatHotkey(getHotkey(cancelledFeature, cancelledAction));
      });
      return;
    }

    if (
      ["Shift", "Control", "Alt", "Meta", "CapsLock", "Tab"].indexOf(
        event.key,
      ) !== -1
    ) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    var parts = [];
    if (event.ctrlKey) parts.push("ctrl");
    if (event.altKey) parts.push("alt");
    if (event.shiftKey) parts.push("shift");
    if (event.metaKey) parts.push("win");

    var key = event.key.toLowerCase();
    if (key === " ") key = "space";
    if (key === "arrowup") key = "up";
    if (key === "arrowdown") key = "down";
    if (key === "arrowleft") key = "left";
    if (key === "arrowright") key = "right";
    if (key === "escape") key = "esc";

    parts.push(key);
    var hotkey = parts.join("+");

    var duplicate = null;
    FEATURES.forEach(function (f) {
      f.actions.forEach(function (a) {
        if (f.key === recordingFeature && a === recordingAction) return;
        if (getHotkey(f.key, a).toLowerCase() === hotkey) {
          duplicate = f.label + (f.actions.length > 1 ? " " + actionLabel(a) : "");
        }
      });
    });

    if (recordingFeature === "chams") {
      hotkeyValues[recordingFeature] = hotkey;
    } else {
      var current = hotkeyValues[recordingFeature] || {};
      current[recordingAction] = hotkey;
      hotkeyValues[recordingFeature] = current;
    }
    recordingFeature = null;
    recordingAction = null;

    document.querySelectorAll(".hotkey-input--recording").forEach(function (el) {
      el.classList.remove("hotkey-input--recording");
      el.textContent = actionLabel(el.dataset.action) + ": " + formatHotkey(hotkey);
    });

    if (duplicate) {
      window.toast.warning(
        "Hotkeys",
        formatHotkey(hotkey) + " is already assigned to " + duplicate,
      );
    }
  }

  function loadHotkeyConfig() {
    rg.get("/hotkeys/config")
      .then(function (res) {
        if (res.status === 200 && res.config) {
          hotkeyValues = res.config || {};
        }
        renderHotkeyList();
      })
      .catch(function () {
        renderHotkeyList();
      });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      var config = {};
      FEATURES.forEach(function (feature) {
        if (feature.key === "chams") {
          config[feature.key] = getHotkey(feature.key, "on");
        } else {
          config[feature.key] = {
            on: getHotkey(feature.key, "on"),
            off: getHotkey(feature.key, "off"),
          };
        }
      });

      rg.loading(saveBtn, true);
      rg.post("/hotkeys/config", { config: config })
        .then(function (res) {
          if (res.status === 200) {
            hotkeyValues = res.config || {};
            renderHotkeyList();
            window.toast.success("Hotkeys", "Hotkey configuration saved");
          } else {
            window.toast.error(
              "Hotkeys",
              res.message || "Failed to save hotkey configuration",
            );
          }
        })
        .catch(function () {
          window.toast.error("Hotkeys", "Failed to save hotkey configuration");
        })
        .finally(function () {
          rg.loading(saveBtn, false);
        });
    });
  }

  var resetBtn = document.getElementById("hotkeyReset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      hotkeyValues = {};
      renderHotkeyList();
      window.toast.success("Hotkeys", "Hotkeys reset to defaults");
    });
  }

  document.addEventListener("keydown", handleKeyCapture);
  loadHotkeyConfig();
})();