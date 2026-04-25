(function () {
  function ensureToastStack() {
    var stack = document.querySelector("[data-toast-stack]");
    if (stack) return stack;
    stack = document.createElement("div");
    stack.className = "toast-stack";
    stack.setAttribute("data-toast-stack", "");
    stack.setAttribute("aria-live", "polite");
    document.body.appendChild(stack);
    return stack;
  }

  function renderAchievementToast(toast, payload) {
    toast.classList.add("achievement");
    var icon = payload.icon || "";
    var title = payload.title || "Новое достижение";
    var description = payload.description || "";
    toast.innerHTML =
      ""
      + '<div class="toast-achievement-layout">'
      + '<div class="toast-achievement-thumb-wrap">'
      + (icon ? '<img src="/static/' + icon + '" alt="' + title + '" class="toast-achievement-thumb">' : "")
      + "</div>"
      + '<div class="toast-achievement-content">'
      + '<div class="toast-achievement-title">'
      + title
      + "</div>"
      + '<div class="toast-achievement-desc">'
      + description
      + "</div>"
      + "</div>"
      + "</div>";
  }

  function scheduleHide(toast, index) {
    var hideDelayMs = 3200 + index * 250;
    window.setTimeout(function () {
      toast.classList.add("toast-hiding");
      window.setTimeout(function () {
        toast.remove();
        var stack = document.querySelector("[data-toast-stack]");
        if (stack && !stack.children.length) {
          stack.remove();
        }
      }, 280);
    }, hideDelayMs);
  }

  function initToastNode(toast, index) {
    if (toast.getAttribute("data-tags") && toast.getAttribute("data-tags").indexOf("achievement") !== -1) {
      try {
        var payload = JSON.parse(toast.textContent || "{}");
        renderAchievementToast(toast, payload);
      } catch (e) {
        // noop: fallback to plain toast text
      }
    }
    scheduleHide(toast, index);
  }

  window.gitplaygroundToast = function (payload) {
    var stack = ensureToastStack();
    var toast = document.createElement("div");
    var tags = payload && payload.tags ? payload.tags : "info";
    toast.className = "toast " + tags;
    toast.setAttribute("data-toast", "");
    toast.setAttribute("data-tags", tags);
    if (payload && payload.achievement) {
      renderAchievementToast(toast, payload.achievement);
    } else {
      toast.textContent = payload && payload.message ? payload.message : "";
    }
    stack.appendChild(toast);
    scheduleHide(toast, 0);
  };

  var toasts = document.querySelectorAll("[data-toast]");
  toasts.forEach(function (toast, index) {
    initToastNode(toast, index);
  });
})();
