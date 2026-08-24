(function () {
  const boxes = [...document.querySelectorAll('input[name="codes"]')];
  if (!boxes.length) return;

  const count = document.getElementById("select-count");
  const printBtn = document.getElementById("print-btn");
  const resetBtn = document.getElementById("reset-btn");
  const resetCodes = document.getElementById("reset-codes");

  function selected() {
    return boxes.filter((b) => b.checked);
  }

  function sync() {
    const n = selected().length;
    count.textContent = n ? `${n} selected` : "";
    printBtn.disabled = n === 0;
    resetBtn.disabled = n === 0;

    // Mirror the selection into the "mark as not printed" form.
    resetCodes.innerHTML = "";
    for (const box of selected()) {
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "codes";
      hidden.value = box.value;
      resetCodes.appendChild(hidden);
    }
  }

  document.querySelectorAll("[data-select]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.select;
      for (const box of boxes) {
        if (mode === "all") box.checked = true;
        else if (mode === "none") box.checked = false;
        else if (mode === "unprinted") box.checked = box.dataset.printed === "0";
      }
      sync();
    });
  });

  boxes.forEach((b) => b.addEventListener("change", sync));

  // Default to whatever still needs a label - the common case.
  const unprinted = boxes.filter((b) => b.dataset.printed === "0");
  if (unprinted.length) unprinted.forEach((b) => (b.checked = true));
  sync();

  // The sheet opens in a new tab; refresh this list so printed badges update.
  document.querySelector('form[target="_blank"]').addEventListener("submit", () => {
    setTimeout(() => window.location.reload(), 2500);
  });
})();
