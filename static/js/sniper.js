(function () {
  "use strict";

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

  bindToggle(
    "scopeToggle",
    "scope",
    "/sniper-scope-on",
    "/sniper-scope-off",
    "Sniper scope enabled",
    "Sniper scope disabled",
    "Failed to enable sniper scope",
    "Failed to disable sniper scope",
  );

  bindToggle(
    "switchToggle",
    "switch",
    "/sniper-switch-on",
    "/sniper-switch-off",
    "Sniper switch enabled",
    "Sniper switch disabled",
    "Failed to enable sniper switch",
    "Failed to disable sniper switch",
  );
})();