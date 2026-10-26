/* Admin panel behaviour: the phone drawer and confirm-before-submit forms. */

const shell = document.querySelector("[data-admin-shell]");

function setDrawer(open) {
  if (!shell) return;
  shell.toggleAttribute("data-open", open);
  const burger = document.querySelector("[data-admin-burger]");
  if (burger) burger.setAttribute("aria-expanded", String(open));
}

document.querySelector("[data-admin-burger]")?.addEventListener("click", () => {
  setDrawer(!shell.hasAttribute("data-open"));
});
document.querySelector("[data-admin-scrim]")?.addEventListener("click", () => setDrawer(false));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setDrawer(false);
});

// <form data-confirm="Delete this item?"> asks before it is sent.
document.addEventListener("submit", (event) => {
  const message = event.target.dataset?.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
