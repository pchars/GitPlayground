(function () {
  const button = document.getElementById("scroll-top-btn");
  if (!button) {
    return;
  }

  const showAfterPx = 280;

  function updateVisibility() {
    button.hidden = window.scrollY <= showAfterPx;
  }

  button.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", updateVisibility, { passive: true });
  updateVisibility();
})();
