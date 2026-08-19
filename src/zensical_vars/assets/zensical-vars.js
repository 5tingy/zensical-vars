/*!
 * zensical-vars — live, reader-editable values in code blocks and prose.
 *
 * Every reference is rendered server-side with its default value, so this
 * script only ever upgrades a page that already reads correctly.
 */
(function () {
  "use strict";

  var DEFAULT_STORAGE_KEY = "zensical-vars";

  function selector(attribute, value) {
    var quoted =
      window.CSS && CSS.escape ? CSS.escape(value) : value.replace(/["\\]/g, "\\$&");
    return "[" + attribute + '="' + quoted + '"]';
  }

  function readStore(key) {
    try {
      return JSON.parse(window.localStorage.getItem(key) || "{}") || {};
    } catch (error) {
      return {};
    }
  }

  function writeStore(key, values) {
    try {
      window.localStorage.setItem(key, JSON.stringify(values));
    } catch (error) {
      /* private browsing, quota, or storage disabled — values stay per-page */
    }
  }

  /* Rewrite every reference to `name`, falling back to the built-in default
     whenever the field is left empty. */
  function paint(name, value) {
    var nodes = document.querySelectorAll(selector("data-zv-var", name));
    Array.prototype.forEach.call(nodes, function (node) {
      var fallback = node.getAttribute("data-zv-default") || "";
      var next = value == null || value === "" ? fallback : value;
      if (node.textContent !== next) {
        node.textContent = next;
      }
      node.classList.toggle("zv-var--custom", next !== fallback);
    });
  }

  function controlsFor(name) {
    return document.querySelectorAll(selector("data-zv-input", name));
  }

  function isCustomised(panel) {
    var controls = panel.querySelectorAll("[data-zv-input]");
    return Array.prototype.some.call(controls, function (control) {
      var fallback = control.getAttribute("data-zv-default") || "";
      /* Text fields show their default as placeholder text, so an empty one is
         still showing the default — not a change the reader has made. */
      return control.value !== "" && control.value !== fallback;
    });
  }

  function bind(panel) {
    if (panel.hasAttribute("data-zv-bound")) {
      return;
    }
    panel.setAttribute("data-zv-bound", "");

    var storageKey = panel.getAttribute("data-zv-storage") || DEFAULT_STORAGE_KEY;
    var persist = panel.getAttribute("data-zv-persist") === "true";
    var stored = persist ? readStore(storageKey) : {};
    var reset = panel.querySelector("[data-zv-reset]");

    function refreshReset() {
      if (reset) {
        reset.disabled = !isCustomised(panel);
      }
    }

    function commit(name, value, fallback) {
      Array.prototype.forEach.call(controlsFor(name), function (control) {
        if (control.value !== value) {
          control.value = value;
        }
      });
      paint(name, value);
      if (persist) {
        var values = readStore(storageKey);
        if (value === "" || value === fallback) {
          delete values[name];
        } else {
          values[name] = value;
        }
        writeStore(storageKey, values);
      }
      refreshReset();
    }

    Array.prototype.forEach.call(
      panel.querySelectorAll("[data-zv-input]"),
      function (control) {
        var name = control.getAttribute("data-zv-input");
        var fallback = control.getAttribute("data-zv-default") || "";

        if (persist && Object.prototype.hasOwnProperty.call(stored, name)) {
          control.value = stored[name];
        }
        paint(name, control.value);

        control.addEventListener("input", function () {
          commit(name, control.value, fallback);
        });
        control.addEventListener("change", function () {
          commit(name, control.value, fallback);
        });
      }
    );

    if (reset) {
      reset.addEventListener("click", function () {
        Array.prototype.forEach.call(
          panel.querySelectorAll("[data-zv-input]"),
          function (control) {
            var fallback = control.getAttribute("data-zv-default") || "";
            control.value = control.tagName === "SELECT" ? fallback : "";
            commit(control.getAttribute("data-zv-input"), control.value, fallback);
          }
        );
        var first = panel.querySelector("[data-zv-input]");
        if (first) {
          first.focus();
        }
      });
    }

    refreshReset();
  }

  function start() {
    var panels = document.querySelectorAll("[data-zv-form]");
    if (!panels.length) {
      return;
    }
    Array.prototype.forEach.call(panels, bind);
  }

  /* Zensical notifies subscribers on every navigation, so this also runs on
     pages loaded without a full refresh. */
  if (typeof document$ !== "undefined" && document$ && document$.subscribe) {
    document$.subscribe(start);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
