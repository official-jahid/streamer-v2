(function () {
  "use strict";

  // In-memory only: nothing is written to disk. Entries live until the
  // pageunloads; toasts auto dismiss after 3 seconds (see toast.js).
  var memoryItems = [];

  // ------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------
  function load() {
    return memoryItems;
  }

  function save(items) {
    memoryItems = items || [];
  }

  function uid() {
    return "n-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
  }

  function timeAgo(ts) {
    var diff = Date.now() - ts;
    var mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    var hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    return new Date(ts).toLocaleDateString();
  }

  // ------------------------------------------------------------
  // Core API
  // ------------------------------------------------------------
  var NotificationCentre = {
    /**
     * Add a notification.
     * @param {string} type  success | info | warning | error | loading
     * @param {string} title
     * @param {string} description optional
     */
    add: function (type, title, description) {
      var items = load();
      var item = {
        id: uid(),
        type: type || "info",
        title: title || "",
        description: description || "",
        time: Date.now(),
        read: false,
      };
      items.unshift(item);
      if (items.length > 100) {
        items = items.slice(0, 100);
      }
      save(items);
      NotificationCentre.render();
      return item.id;
    },

    remove: function (id) {
      var items = load().filter(function (n) {
        return n.id !== id;
      });
      save(items);
      NotificationCentre.render();
    },

    clearAll: function () {
      save([]);
      NotificationCentre.render();
    },

    markAllRead: function () {
      var items = load().map(function (n) {
        n.read = true;
        return n;
      });
      save(items);
      NotificationCentre.render();
    },

    getAll: function () {
      return load();
    },

    getUnreadCount: function () {
      return load().filter(function (n) {
        return !n.read;
      }).length;
    },

    // ------------------------------------------------------------
    // Rendering
    // ------------------------------------------------------------
    render: function () {
      var items = load();
      var list = document.getElementById("notificationList");
      var badge = document.getElementById("notificationBadge");
      var empty = document.getElementById("notificationEmpty");
      var clearBtn = document.getElementById("notificationClearAll");

      var unread = items.filter(function (n) {
        return !n.read;
      }).length;

      // Badge
      if (badge) {
        if (unread > 0) {
          badge.textContent = unread > 99 ? "99+" : String(unread);
          badge.classList.remove("hidden");
        } else {
          badge.classList.add("hidden");
        }
      }

      // Clear button state
      if (clearBtn) {
        clearBtn.disabled = items.length === 0;
        clearBtn.classList.toggle("opacity-50", items.length === 0);
        clearBtn.classList.toggle("pointer-events-none", items.length === 0);
      }

      // Empty state
      if (empty) {
        empty.classList.toggle("hidden", items.length > 0);
      }

      // List
      if (!list) return;
      list.innerHTML = "";

      items.forEach(function (n) {
        var li = document.createElement("li");
        li.className =
          "notification-item flex items-start gap-3 px-4 py-3 transition-colors hover:bg-[hsl(var(--muted))]";
        if (!n.read) li.classList.add("notification-item--unread");
        li.dataset.id = n.id;

        // Icon
        var icon = document.createElement("span");
        icon.className =
          "notification-item__icon notification-item__icon--" + n.type;
        icon.innerHTML = NotificationCentre._iconFor(n.type);

        // Body
        var body = document.createElement("div");
        body.className = "flex-1 min-w-0";

        var title = document.createElement("div");
        title.className =
          "text-sm font-medium text-[hsl(var(--card-foreground))]";
        title.textContent = n.title || "";

        var desc = document.createElement("div");
        desc.className =
          "text-xs text-[hsl(var(--muted-foreground))] mt-0.5 break-words";
        desc.textContent = n.description || "";

        var time = document.createElement("div");
        time.className =
          "text-[10px] uppercase tracking-wide text-[hsl(var(--muted-foreground))] mt-1";
        time.textContent = timeAgo(n.time);

        body.appendChild(title);
        if (n.description) body.appendChild(desc);
        body.appendChild(time);

        // Dismiss
        var dismiss = document.createElement("button");
        dismiss.type = "button";
        dismiss.className =
          "notification-item__dismiss flex h-6 w-6 shrink-0 items-center justify-center rounded-[calc(var(--radius)-2px)] text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--foreground))]";
        dismiss.setAttribute("aria-label", "Dismiss notification");
        dismiss.innerHTML =
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
        dismiss.addEventListener("click", function (event) {
          event.stopPropagation();
          NotificationCentre.remove(n.id);
        });

        // Click marks as read
        li.addEventListener("click", function () {
          if (!n.read) {
            var items = load().map(function (x) {
              if (x.id === n.id) x.read = true;
              return x;
            });
            save(items);
            NotificationCentre.render();
          }
        });

        li.appendChild(icon);
        li.appendChild(body);
        li.appendChild(dismiss);
        list.appendChild(li);
      });
    },

    _iconFor: function (type) {
      var icons = {
        success:
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        warning:
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        error:
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        loading:
          '<svg class="toast-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>',
      };
      return icons[type] || icons.info;
    },
  };

  // ------------------------------------------------------------
  // Toggle / outside-click / escape handling
  // ------------------------------------------------------------
  function openPanel() {
    var panel = document.getElementById("notificationPanel");
    var btn = document.getElementById("notificationBell");
    if (panel) {
      panel.classList.remove("hidden");
      panel.setAttribute("aria-hidden", "false");
      NotificationCentre.markAllRead();
      if (btn) btn.setAttribute("aria-expanded", "true");
    }
  }

  function closePanel() {
    var panel = document.getElementById("notificationPanel");
    var btn = document.getElementById("notificationBell");
    if (panel) {
      panel.classList.add("hidden");
      panel.setAttribute("aria-hidden", "true");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
  }

  function isPanelOpen() {
    var panel = document.getElementById("notificationPanel");
    return panel && !panel.classList.contains("hidden");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var bell = document.getElementById("notificationBell");
    var clearAll = document.getElementById("notificationClearAll");

    if (bell) {
      bell.addEventListener("click", function (event) {
        event.stopPropagation();
        if (isPanelOpen()) {
          closePanel();
        } else {
          openPanel();
        }
      });
    }

    if (clearAll) {
      clearAll.addEventListener("click", function () {
        NotificationCentre.clearAll();
      });
    }

    document.addEventListener("click", function (event) {
      var panel = document.getElementById("notificationPanel");
      if (panel && !panel.contains(event.target) && event.target !== bell) {
        closePanel();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closePanel();
    });

    NotificationCentre.render();
  });

  window.NotificationCentre = NotificationCentre;
})();
