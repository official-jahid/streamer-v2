(function () {
  "use strict";

  var loadBtn = document.getElementById("aimbotLoad");
  var toggle = document.getElementById("aimbotToggle");

  function setSwitch(on) {
    if (toggle) toggle.setAttribute("aria-checked", on ? "true" : "false");
  }

  function runLoad() {
    return rg.post("/aimbot-load").then(function (res) {
      if (res.status === 200) {
        toast.success("Aimbot loaded");
        return true;
      }
      toast.error("Failed to load aimbot");
      return false;
    });
  }

  if (loadBtn) {
    loadBtn.addEventListener("click", function () {
      rg.loading(loadBtn, true);
      runLoad().finally(function () {
        rg.loading(loadBtn, false);
      });
    });
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      var wantOn = toggle.getAttribute("aria-checked") !== "true";
      rg.loading(toggle, true);
      setSwitch(wantOn);
      var prepare = wantOn ? runLoad() : Promise.resolve(true);
      prepare
        .then(function (ok) {
          if (!ok) {
            setSwitch(false);
            return;
          }
          return rg
            .post(wantOn ? "/aimbot-on" : "/aimbot-off")
            .then(function (res) {
              if (res.status === 200) {
                rg.setFeatureState("aimbot", wantOn);
                toast.success(wantOn ? "Aimbot enabled" : "Aimbot disabled");
              } else {
                setSwitch(!wantOn);
                toast.error(
                  wantOn ? "Failed to enable aimbot" : "Failed to disable aimbot",
                );
              }
            })
            .catch(function () {
              setSwitch(!wantOn);
              toast.error(
                wantOn ? "Failed to enable aimbot" : "Failed to disable aimbot",
              );
            });
        })
        .catch(function () {
          setSwitch(false);
        })
        .finally(function () {
          rg.loading(toggle, false);
        });
    });
  }

  // ------------------------------------------------------------
  // Aimbot Drag
  // ------------------------------------------------------------
  var dragLoadBtn = document.getElementById("dragLoad");
  var dragToggle = document.getElementById("dragToggle");

  function setDragSwitch(on) {
    if (dragToggle)
      dragToggle.setAttribute("aria-checked", on ? "true" : "false");
  }

  function runDragLoad() {
    return rg.post("/aimdrag-load").then(function (res) {
      if (res.status === 200) {
        toast.success("Aimbot drag loaded");
        return true;
      }
      toast.error("Failed to load aimbot drag");
      return false;
    });
  }

  if (dragLoadBtn) {
    dragLoadBtn.addEventListener("click", function () {
      rg.loading(dragLoadBtn, true);
      runDragLoad().finally(function () {
        rg.loading(dragLoadBtn, false);
      });
    });
  }

  if (dragToggle) {
    dragToggle.addEventListener("click", function () {
      var wantOn = dragToggle.getAttribute("aria-checked") !== "true";
      rg.loading(dragToggle, true);
      setDragSwitch(wantOn);
      var prepare = wantOn ? runDragLoad() : Promise.resolve(true);
      prepare
        .then(function (ok) {
          if (!ok) {
            setDragSwitch(false);
            return;
          }
          return rg
            .post(wantOn ? "/aimdrag-on" : "/aimdrag-off")
            .then(function (res) {
              if (res.status === 200) {
                rg.setFeatureState("aimdrag", wantOn);
                toast.success(
                  wantOn ? "Aimbot drag enabled" : "Aimbot drag disabled",
                );
              } else {
                setDragSwitch(!wantOn);
                toast.error(
                  wantOn
                    ? "Failed to enable aimbot drag"
                    : "Failed to disable aimbot drag",
                );
              }
            })
            .catch(function () {
              setDragSwitch(!wantOn);
              toast.error(
                wantOn
                  ? "Failed to enable aimbot drag"
                  : "Failed to disable aimbot drag",
              );
            });
        })
        .catch(function () {
          setDragSwitch(false);
        })
        .finally(function () {
          rg.loading(dragToggle, false);
        });
    });
  }
})();