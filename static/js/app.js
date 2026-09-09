(function () {
  "use strict";

  // ------------------------------------------------------------
  // Shared fetch helpers
  // ------------------------------------------------------------
  var busyEls = new Set();
  var featureState = {};

  window.rg = {
    post: function (url, data) {
      return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: data ? JSON.stringify(data) : undefined,
      }).then(function (res) {
        return res.json();
      });
    },
    get: function (url) {
      return fetch(url).then(function (res) {
        return res.json();
      });
    },
    loading: function (el, on) {
      if (!el) return;
      if (on) {
        busyEls.add(el);
        el.disabled = true;
      } else {
        busyEls.delete(el);
        el.disabled = false;
      }
    },
    setFeatureState: function (feature, on) {
      featureState[feature] = !!on;
      applyFeatureState(featureState);
    },
  };

  // ------------------------------------------------------------
  // Feature state sync (toggle switches)
  // ------------------------------------------------------------
  function applyFeatureState(state) {
    featureState = state || {};
    document.querySelectorAll("[role='switch'][data-feature]").forEach(
      function (sw) {
        if (busyEls.has(sw)) return;
        sw.setAttribute(
          "aria-checked",
          featureState[sw.dataset.feature] ? "true" : "false",
        );
      },
    );
  }

  function pollFeatureState() {
    rg.get("/hotkeys/state")
      .then(function (res) {
        if (res.status === 200 && res.state) {
          applyFeatureState(res.state);
        }
      })
      .catch(function () {});
  }

  function startFeatureStatePolling() {
    pollFeatureState();
    setInterval(pollFeatureState, 2000);
  }

  // ------------------------------------------------------------
  // Mobile drawer (hamburger) toggle
  // ------------------------------------------------------------
  function openDrawer() {
    var drawer = document.getElementById("mobileDrawer");
    var overlay = document.getElementById("mobileDrawerOverlay");
    var toggle = document.getElementById("sidebarToggle");
    if (drawer) {
      drawer.classList.add("rg-drawer--open");
      drawer.setAttribute("aria-hidden", "false");
    }
    if (overlay) overlay.classList.add("rg-sidebar-overlay--visible");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
  }

  function closeDrawer() {
    var drawer = document.getElementById("mobileDrawer");
    var overlay = document.getElementById("mobileDrawerOverlay");
    var toggle = document.getElementById("sidebarToggle");
    if (drawer) {
      drawer.classList.remove("rg-drawer--open");
      drawer.setAttribute("aria-hidden", "true");
    }
    if (overlay) overlay.classList.remove("rg-sidebar-overlay--visible");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  function isDrawerOpen() {
    var drawer = document.getElementById("mobileDrawer");
    return drawer && drawer.classList.contains("rg-drawer--open");
  }

  // ------------------------------------------------------------
  // Theme
  // ------------------------------------------------------------
  function applyTheme(theme) {
    var root = document.documentElement;
    root.classList.toggle("dark", theme !== "light");
    root.classList.toggle("light", theme === "light");
  }

  function toggleTheme() {
    var root = document.documentElement;
    var theme = root.classList.contains("dark") ? "light" : "dark";
    rg.post("/settings/theme", { theme: theme })
      .then(function (res) {
        if (res.status === 200) {
          applyTheme(res.theme);
          if (window.toast) {
            window.toast.success(
              "Theme",
              "Theme set to " + (res.theme === "light" ? "Light" : "Dark"),
            );
          }
        } else if (window.toast) {
          window.toast.error("Theme", "Failed to save theme");
        }
      })
      .catch(function () {
        if (window.toast) {
          window.toast.error("Theme", "Failed to save theme");
        }
      });
  }

  // ------------------------------------------------------------
  // Emulator bit version selector (32-bit / 64-bit)
  // ------------------------------------------------------------
  function bindBitSelector() {
    var btn1 = document.getElementById("btn1");
    var btn2 = document.getElementById("btn2");
    if (!btn1 || !btn2) return;

    function select(active, inactive) {
      active.classList.add("rg-segmented__btn--active");
      inactive.classList.remove("rg-segmented__btn--active");
    }

    btn1.addEventListener("click", function () {
      rg.loading(btn1, true);
      rg.post("/update-bit32")
        .then(function (res) {
          if (res.status === 200) {
            select(btn1, btn2);
            if (window.toast) {
              window.toast.success("Bit Version", "32 bit FreeFire selected");
            }
          } else if (window.toast) {
            window.toast.error("Bit Version", "Failed to select 32 bit");
          }
        })
        .catch(function () {
          if (window.toast) {
            window.toast.error("Bit Version", "Failed to select 32 bit");
          }
        })
        .finally(function () {
          rg.loading(btn1, false);
        });
    });
    btn2.addEventListener("click", function () {
      rg.loading(btn2, true);
      rg.post("/update-bit64")
        .then(function (res) {
          if (res.status === 200) {
            select(btn2, btn1);
            if (window.toast) {
              window.toast.success("Bit Version", "64 bit FreeFire selected");
            }
          } else if (window.toast) {
            window.toast.error("Bit Version", "Failed to select 64 bit");
          }
        })
        .catch(function () {
          if (window.toast) {
            window.toast.error("Bit Version", "Failed to select 64 bit");
          }
        })
        .finally(function () {
          rg.loading(btn2, false);
        });
    });
  }

  // ------------------------------------------------------------
  // Connection status (HD-Player.exe)
  // ------------------------------------------------------------
  function checkStatus() {
    rg.post("/get-process").then(function (res) {
      var online = res.status === 200;
      var btn = document.getElementById("onlinebtn");
      var pill = document.getElementById("sidebarStatus");
      var pillText = document.getElementById("sidebarStatusText");

      if (btn) {
        btn.textContent = online ? "Online" : "Offline";
        btn.classList.toggle("rg-btn--success", online);
      }
      if (pill) {
        pill.classList.toggle("rg-status-pill--online", online);
        pill.classList.toggle("rg-status-pill--offline", !online);
      }
      if (pillText) {
        pillText.textContent = online ? "Online" : "Offline";
      }
    });
  }

  function startStatusPolling() {
    checkStatus();
    setInterval(checkStatus, 5000);
  }

  // ------------------------------------------------------------
  // Hotkey event polling (backend hotkey toasts)
  // ------------------------------------------------------------
  var lastSeq = 0;
  var pollTimer = null;

  function pollHotkeyEvents() {
    rg.get("/hotkeys/events?after=" + lastSeq)
      .then(function (res) {
        if (res && res.events && res.events.length) {
          res.events.forEach(function (ev) {
            lastSeq = ev.seq;
            if (window.toast) {
              window.toast.add({
                type: ev.type || "info",
                title: ev.title || "Hotkey",
                description: ev.message || "",
              });
            }
          });
        }
      })
      .catch(function () {})
      .then(function () {
        pollTimer = setTimeout(pollHotkeyEvents, 2000);
      });
  }

  // ------------------------------------------------------------
  // Init
  // ------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("sidebarToggle");
    var overlay = document.getElementById("mobileDrawerOverlay");
    var themeBtn = document.getElementById("headerThemeToggle");

    if (toggle) {
      toggle.addEventListener("click", function (event) {
        event.stopPropagation();
        if (isDrawerOpen()) {
          closeDrawer();
        } else {
          openDrawer();
        }
      });
    }

    if (overlay) {
      overlay.addEventListener("click", closeDrawer);
    }

    if (themeBtn) {
      themeBtn.addEventListener("click", toggleTheme);
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeDrawer();
    });

    bindBitSelector();
    startStatusPolling();
    startFeatureStatePolling();
    pollHotkeyEvents();
  });
})();