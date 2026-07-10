(function initMobileNav() {
  const header = document.querySelector(".header.has-collapsible-nav");
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("header-nav");
  if (!header || !toggle || !nav) {
    return;
  }

  const mq = window.matchMedia("(max-width: 768px)");

  function setOpen(open) {
    header.classList.toggle("is-nav-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function closeNav() {
    setOpen(false);
  }

  toggle.addEventListener("click", () => {
    setOpen(!header.classList.contains("is-nav-open"));
  });

  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      closeNav();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeNav();
    }
  });

  mq.addEventListener("change", (event) => {
    if (!event.matches) {
      closeNav();
    }
  });
})();
