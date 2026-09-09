(function () {
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function showMode(mode) {
    var account = $("#loginFormAccount");
    var license = $("#loginFormLicense");
    var tabAccount = $('[data-login-tab="account"]');
    var tabLicense = $('[data-login-tab="license"]');
    if (!account || !license) return;
    var isAccount = mode !== "license";
    account.classList.toggle("hidden", !isAccount);
    license.classList.toggle("hidden", isAccount);
    if (tabAccount) {
      tabAccount.classList.toggle("rg-tab--active", isAccount);
      tabAccount.setAttribute("aria-selected", isAccount ? "true" : "false");
    }
    if (tabLicense) {
      tabLicense.classList.toggle("rg-tab--active", !isAccount);
      tabLicense.setAttribute("aria-selected", !isAccount ? "true" : "false");
    }
  }

  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest("[data-login-tab]");
    if (tab) {
      showMode(tab.getAttribute("data-login-tab"));
      return;
    }
    var eye = ev.target.closest("[data-toggle-password]");
    if (eye) {
      var input = document.getElementById(eye.getAttribute("data-toggle-password"));
      if (input) {
        input.type = input.type === "password" ? "text" : "password";
        eye.setAttribute("aria-pressed", input.type === "text" ? "true" : "false");
      }
      return;
    }
    var copy = ev.target.closest("[data-copy-hwid]");
    if (copy) {
      var code = $("#hwidValue");
      var text = code ? code.textContent.trim() : "";
      function done() {
        copy.textContent = "Copied";
        setTimeout(function () {
          copy.textContent = "Copy";
        }, 1200);
      }
      if (navigator.clipboard && text) {
        navigator.clipboard.writeText(text).then(done, done);
      } else if (text) {
        var ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
        } catch (e) {}
        document.body.removeChild(ta);
        done();
      }
      return;
    }
    var theme = ev.target.closest("[data-login-theme]");
    if (theme) {
      var root = document.documentElement;
      var next = root.classList.contains("dark") ? "light" : "dark";
      root.classList.remove("dark", "light");
      root.classList.add(next);
      fetch("/settings/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: next }),
      }).catch(function () {});
    }
  });

  document.addEventListener("submit", function (ev) {
    var form = ev.target.closest("[data-login-form]");
    if (!form) return;
    var btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.classList.add("rg-btn--loading");
      btn.disabled = true;
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var initial = "account";
    var bodyMode = document.body.getAttribute("data-login-mode");
    if (bodyMode === "license" || bodyMode === "account") initial = bodyMode;
    showMode(initial);
  });
})();
