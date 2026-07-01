(function () {
  const slider = document.querySelector("[data-learning-slider]");
  if (!slider) {
    return;
  }

  const track = slider.querySelector(".learning-slider-track");
  const slides = Array.from(slider.querySelectorAll(".learning-slide"));
  const prevBtn = slider.querySelector("[data-learning-prev]");
  const nextBtn = slider.querySelector("[data-learning-next]");
  const currentNode = slider.querySelector("[data-learning-current]");
  const dots = Array.from(slider.querySelectorAll("[data-learning-dot]"));
  if (!track || !slides.length) {
    return;
  }

  let index = slides.findIndex((slide) => slide.classList.contains("is-active"));
  if (index < 0) {
    index = 0;
  }

  function render(nextIndex) {
    index = (nextIndex + slides.length) % slides.length;
    track.style.transform = `translateX(-${index * 100}%)`;
    slides.forEach((slide, slideIndex) => {
      slide.classList.toggle("is-active", slideIndex === index);
    });
    dots.forEach((dot, dotIndex) => {
      dot.classList.toggle("is-active", dotIndex === index);
      dot.setAttribute("aria-selected", dotIndex === index ? "true" : "false");
    });
    if (currentNode) {
      currentNode.textContent = String(index + 1);
    }
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", () => render(index - 1));
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => render(index + 1));
  }
  dots.forEach((dot) => {
    dot.addEventListener("click", () => {
      const target = Number(dot.dataset.learningDot);
      if (!Number.isNaN(target)) {
        render(target);
      }
    });
  });

  let autoplay = window.setInterval(() => render(index + 1), 7000);
  slider.addEventListener("mouseenter", () => {
    window.clearInterval(autoplay);
  });
  slider.addEventListener("mouseleave", () => {
    autoplay = window.setInterval(() => render(index + 1), 7000);
  });

  render(index);
})();
