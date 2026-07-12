(function () {
  const slider = document.querySelector("[data-learning-slider]");
  if (!slider) {
    return;
  }

  const track = slider.querySelector(".learning-slider-track");
  const slides = Array.from(slider.querySelectorAll(".learning-slide"));
  const flowSteps = Array.from(slider.querySelectorAll("[data-flow-step]"));
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
    flowSteps.forEach((step, stepIndex) => {
      step.classList.toggle("is-active", stepIndex === index);
      step.classList.toggle("is-complete", stepIndex < index);
      step.setAttribute("aria-selected", stepIndex === index ? "true" : "false");
    });
  }

  flowSteps.forEach((step) => {
    step.addEventListener("click", () => {
      const target = Number(step.dataset.flowStep);
      if (!Number.isNaN(target)) {
        render(target);
      }
    });
  });

  function startAutoplay() {
    window.clearInterval(autoplay);
    autoplay = window.setInterval(() => render(index + 1), 4000);
  }

  let autoplay = 0;
  startAutoplay();
  slider.addEventListener("mouseenter", () => {
    window.clearInterval(autoplay);
  });
  slider.addEventListener("mouseleave", startAutoplay);

  render(index);
})();
