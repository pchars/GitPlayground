(function () {
  document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
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
      btn.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль");
      btn.textContent = show ? "Скрыть" : "Показать";
      input.focus();
    });
  });
})();
