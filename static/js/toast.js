(function () {
  "use strict";

  var container = null;
  var counter = 0;

  function getContainer() {
    if (!container) {
      container = document.getElementById("toaster");
      if (!container) {
        container = document.createElement("div");
        container.id = "toaster";
        container.className = "toaster";
        document.body.appendChild(container);
      }
    }
    return container;
  }

  var ICONS = {
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

  function createToast(opts) {
    var id = "toast-" + ++counter;
    var type = opts.type || "info";
    var el = document.createElement("div");
    el.className = "toast toast--" + type;
    el.id = id;
    el.setAttribute("role", type === "error" ? "alert" : "status");

    // Push to notification centre (memory only, cleared on reload)
    if (window.NotificationCentre) {
      window.NotificationCentre.add(
        type,
        opts.title || "",
        opts.description || "",
      );
    }

    var icon = document.createElement("div");
    icon.className = "toast__icon";
    icon.innerHTML = ICONS[type] || ICONS.info;

    var body = document.createElement("div");
    body.className = "toast__body";

    if (opts.title) {
      var title = document.createElement("div");
      title.className = "toast__title";
      title.textContent = opts.title;
      body.appendChild(title);
    }
    if (opts.description) {
      var desc = document.createElement("div");
      desc.className = "toast__description";
      desc.textContent = opts.description;
      body.appendChild(desc);
    }
    if (opts.actionProps && opts.actionProps.label) {
      var action = document.createElement("div");
      action.className = "toast__action";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = opts.actionProps.label;
      btn.addEventListener("click", function () {
        if (typeof opts.actionProps.onClick === "function") {
          opts.actionProps.onClick(id);
        }
      });
      action.appendChild(btn);
      body.appendChild(action);
    }

    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast__close";
    close.setAttribute("aria-label", "Close");
    close.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    close.addEventListener("click", function () {
      toast.close(id);
    });

    el.appendChild(icon);
    el.appendChild(body);
    el.appendChild(close);
    getContainer().appendChild(el);

    if (type !== "loading" && opts.duration !== 0) {
      var duration = opts.duration || 3000;
      var timer = setTimeout(function () {
        toast.close(id);
      }, duration);
      el.addEventListener("mouseenter", function () {
        clearTimeout(timer);
      });
      el.addEventListener("mouseleave", function () {
        if (el.parentNode) {
          timer = setTimeout(function () {
            toast.close(id);
          }, duration);
        }
      });
    }

    return id;
  }

  var toast = {
    add: function (opts) {
      return createToast(opts || {});
    },

    close: function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      el.classList.add("toast--closing");
      setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 200);
    },

    success: function (title, description, opts) {
      return toast.add(
        Object.assign(
          { type: "success", title: title, description: description },
          opts,
        ),
      );
    },

    info: function (title, description, opts) {
      return toast.add(
        Object.assign(
          { type: "info", title: title, description: description },
          opts,
        ),
      );
    },

    warning: function (title, description, opts) {
      return toast.add(
        Object.assign(
          { type: "warning", title: title, description: description },
          opts,
        ),
      );
    },

    error: function (title, description, opts) {
      return toast.add(
        Object.assign(
          { type: "error", title: title, description: description },
          opts,
        ),
      );
    },

    loading: function (title, description, opts) {
      return toast.add(
        Object.assign(
          {
            type: "loading",
            title: title,
            description: description,
            duration: 0,
          },
          opts,
        ),
      );
    },

    promise: function (promise, messages) {
      var id = toast.loading(
        messages.loading.title,
        messages.loading.description,
      );
      promise
        .then(function (result) {
          toast.close(id);
          toast.success(messages.success.title, messages.success.description);
          return result;
        })
        .catch(function (err) {
          toast.close(id);
          toast.error(messages.error.title, messages.error.description);
          throw err;
        });
      return promise;
    },
  };

  window.toast = toast;

  document.addEventListener("DOMContentLoaded", function () {
    var el = document.getElementById("flashed-messages");
    if (!el) return;
    var flashed;
    try {
      flashed = JSON.parse(el.textContent);
    } catch (e) {
      return;
    }
    if (flashed && flashed.length) {
      flashed.forEach(function (item) {
        var category = item[0] || "info";
        var message = item[1];
        toast.add({ type: category, title: message });
      });
    }
  });
})();
