// Photos open in an overlay rather than navigating to the raw image file.
// Installed to the home screen there is no browser chrome, so a plain link to
// an image is a dead end - nothing to go back with short of quitting the app.
(function () {
  const overlay = document.createElement("div");
  overlay.className = "lightbox";
  overlay.hidden = true;
  overlay.innerHTML = `
    <button class="lightbox-close" type="button" aria-label="Close photo">&times;</button>
    <img class="lightbox-img" alt="">
  `;
  document.body.appendChild(overlay);

  const img = overlay.querySelector(".lightbox-img");
  let lastFocus = null;

  function open(src, alt) {
    lastFocus = document.activeElement;
    img.src = src;
    img.alt = alt || "";
    overlay.hidden = false;
    document.body.classList.add("lightbox-open");
    overlay.querySelector(".lightbox-close").focus();
  }

  function close() {
    overlay.hidden = true;
    img.removeAttribute("src");
    document.body.classList.remove("lightbox-open");
    if (lastFocus) lastFocus.focus();
  }

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-photo]");
    if (trigger) {
      e.preventDefault();
      open(trigger.dataset.photo, trigger.dataset.photoAlt);
      return;
    }
    // Tapping the backdrop or the close button dismisses it.
    if (!overlay.hidden && (e.target === overlay || e.target.closest(".lightbox-close"))) {
      close();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.hidden) close();
  });

  // The phone's back gesture should close the photo, not leave the page.
  window.addEventListener("popstate", () => {
    if (!overlay.hidden) close();
  });
})();
