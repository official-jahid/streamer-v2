(function () {
  "use strict";

  function bindLoad(id, url, successMsg, errorMsg) {
    var el = document.getElementById(id);
    if (!el) return;

    el.addEventListener("click", function () {
      rg.loading(el, true);
      rg.post(url)
        .then(function (res) {
          if (res.status === 200) {
            toast.success(successMsg);
          } else {
            toast.error(errorMsg);
          }
        })
        .catch(function () {
          toast.error(errorMsg);
        })
        .finally(function () {
          rg.loading(el, false);
        });
    });
  }

  function bindToggle(toggleId, feature, onUrl, offUrl, onMsg, offMsg, onErr, offErr) {
    var el = document.getElementById(toggleId);
    if (!el) return;

    el.addEventListener("click", function () {
      var wantOn = el.getAttribute("aria-checked") !== "true";
      rg.loading(el, true);
      el.setAttribute("aria-checked", wantOn ? "true" : "false");
      rg
        .post(wantOn ? onUrl : offUrl)
        .then(function (res) {
          if (res.status === 200) {
            rg.setFeatureState(feature, wantOn);
            toast.success(wantOn ? onMsg : offMsg);
          } else {
            el.setAttribute("aria-checked", wantOn ? "false" : "true");
            toast.error(wantOn ? onErr : offErr);
          }
        })
        .catch(function () {
          el.setAttribute("aria-checked", wantOn ? "false" : "true");
          toast.error(wantOn ? onErr : offErr);
        })
        .finally(function () {
          rg.loading(el, false);
        });
    });
  }

  bindLoad(
    "chamsmenu",
    "/chams-menu",
    "Chams menu loaded",
    "Failed to load chams menu",
  );
  bindLoad("chams3d", "/chams-3D", "Chams 3D loaded", "Failed to load chams 3D");

  bindToggle(
    "m82bToggle",
    "m82b",
    "/m82b-esp-on",
    "/m82b-esp-off",
    "M82B ESP enabled",
    "M82B ESP disabled",
    "Failed to enable M82B ESP",
    "Failed to disable M82B ESP",
  );
})();