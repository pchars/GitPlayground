(function () {
  const EYE_ICON =
    '<svg class="password-toggle-icon password-toggle-eye" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" ' +
    'aria-hidden="true" focusable="false">' +
    '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"></path>' +
    '<circle cx="12" cy="12" r="3"></circle>' +
    "</svg>";

  function ensureToggleMarkup(btn) {
    if (btn.querySelector(".password-toggle-icon-wrap")) {
      return;
    }
    btn.innerHTML =
      '<span class="password-toggle-icon-wrap" aria-hidden="true">' +
      EYE_ICON +
      '<span class="password-toggle-slash"></span>' +
      "</span>";
  }

  function setPasswordVisible(btn, visible) {
    btn.classList.toggle("is-visible", visible);
    btn.setAttribute("aria-label", visible ? "Скрыть пароль" : "Показать пароль");
    btn.setAttribute("aria-pressed", visible ? "true" : "false");
  }

  document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
    ensureToggleMarkup(btn);
    btn.addEventListener("click", () => {
      const wrap = btn.closest(".password-field-wrap");
      if (!wrap) {
        return;
      }
      const input = wrap.querySelector("input");
      if (!input) {
        return;
      }
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      setPasswordVisible(btn, show);
      input.focus();
    });
  });
})();
