/**
 * Menu category chips: switch category instantly without reloading.
 * Without JavaScript the chips are plain links (?category=slug) that do the same on the server.
 */
export function startCategoryFilter() {
  const chips = document.querySelector("[data-category-filter]");
  const grid = document.querySelector("[data-dish-grid]");
  if (!chips || !grid) {
    return;
  }

  function select(slug) {
    chips.querySelectorAll("[data-filter]").forEach((chip) => {
      if (chip.dataset.filter === slug) {
        chip.setAttribute("aria-current", "true");
      } else {
        chip.removeAttribute("aria-current");
      }
    });
    grid.querySelectorAll(".dish-grid__item").forEach((item) => {
      item.hidden = slug !== "" && item.dataset.category !== slug;
    });
  }

  chips.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-filter]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    select(chip.dataset.filter);
    const url = new URL(window.location.href);
    if (chip.dataset.filter) {
      url.searchParams.set("category", chip.dataset.filter);
    } else {
      url.searchParams.delete("category");
    }
    window.history.replaceState(null, "", url);
  });
}
