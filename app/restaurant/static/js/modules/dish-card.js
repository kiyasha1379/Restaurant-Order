/**
 * Round cards: a tap on the card flips it to its details (aria-pressed follows),
 * and the add button announces the dish through a "cart:add" event. cart.js listens for it,
 * so this file never talks to the server.
 */
export const CART_ADD_EVENT = "cart:add";

function toggleFlip(card, button) {
  const flipped = card.classList.toggle("is-flipped");
  button.setAttribute("aria-pressed", String(flipped));
}

function popAddButton(button) {
  button.classList.remove("is-popped");
  void button.offsetWidth; // restart the animation
  button.classList.add("is-popped");
}

export function startDishCards() {
  document.addEventListener("click", (event) => {
    const flipButton = event.target.closest(".dish-card__flip");
    if (flipButton) {
      const card = flipButton.closest("[data-dish-card]");
      if (card && !event.target.closest("a")) {
        toggleFlip(card, flipButton);
      }
      return;
    }
    const addButton = event.target.closest("[data-add-dish]");
    if (addButton) {
      popAddButton(addButton);
      document.dispatchEvent(
        new CustomEvent(CART_ADD_EVENT, {
          detail: { dishId: Number(addButton.dataset.addDish), button: addButton },
        }),
      );
    }
  });
}
