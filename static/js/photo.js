// Show the chosen filename on the compact photo picker button.
document.addEventListener("change", (e) => {
  const input = e.target;
  if (input.type !== "file" || !input.closest(".photo-picker")) return;
  const label = input.closest(".photo-picker");
  const file = input.files && input.files[0];
  label.firstChild.textContent = file ? `📷 ${file.name.slice(0, 18)} ` : "📷 Photo ";
});
