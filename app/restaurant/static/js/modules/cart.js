/**
 * The cart in the browser: adds dishes (listening to "cart:add"), draws the cart panel,
 * updates the header badge and the phone cart bar, and flies a dot from the add button
 * to the badge. All prices come from the server; this file only shows them.
 */
import {
  config,
  fillText,
  formatNumber,
  prefersReducedMotion,
  requestJson,
  showToast,
} from "./site-config.js";

const FLY_SECONDS = 0.7;

const panel = document.querySelector("[data-cart-panel]");
const badges = document.querySelectorAll("[data-cart-count]");
const bar = document.querySelector("[data-cart-bar]");

function popBadge() {
  const headerBadge = document.querySelector(".site-header__cart-count");
  if (headerBadge) {
    headerBadge.classList.remove("is-popped");
    void headerBadge.offsetWidth; // restart the animation
    headerBadge.classList.add("is-popped");
  }
}

function makeQuantityButton(label, symbol, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "cart-line__button";
  button.setAttribute("aria-label", label);
  button.textContent = symbol;
  button.addEventListener("click", onClick);
  return button;
}

function makeLine(line) {
  const item = document.createElement("li");
  item.className = "cart-line";

  const info = document.createElement("div");
  info.className = "cart-line__info";
  const name = document.createElement("div");
  name.className = "cart-line__name";
  name.textContent = line.name;
  const price = document.createElement("div");
  price.className = "cart-line__price";
  price.textContent = `${formatNumber(line.unit_price)} ${config.texts["price.currency"]}`;
  info.append(name);
  if (line.summary) {
    const summary = document.createElement("div");
    summary.className = "cart-line__summary";
    summary.textContent = line.summary;
    info.append(summary);
  }
  info.append(price);

  const controls = document.createElement("div");
  controls.className = "cart-line__controls";
  const quantity = document.createElement("span");
  quantity.className = "cart-line__quantity";
  quantity.textContent = formatNumber(line.quantity);
  const less = makeQuantityButton(
    fillText(config.texts["cart.decrease"], { name: line.name }),
    "−",
    () => changeQuantity(line.line_id, line.quantity - 1),
  );
  const more = makeQuantityButton(
    fillText(config.texts["cart.increase"], { name: line.name }),
    "+",
    () => changeQuantity(line.line_id, line.quantity + 1),
  );
  controls.append(less, quantity, more);

  item.append(info, controls);
  return item;
}

function renderPanel(cart) {
  if (!panel) {
    return;
  }
  const isEmpty = cart.lines.length === 0;
  panel.querySelector("[data-cart-lines]").replaceChildren(...cart.lines.map(makeLine));
  panel.querySelector("[data-cart-empty]").hidden = !isEmpty;
  panel.querySelector("[data-cart-summary]").hidden = isEmpty;
  panel.querySelector("[data-cart-checkout]").hidden = isEmpty;
  panel.querySelector("[data-cart-total]").textContent = formatNumber(cart.subtotal);
}

function renderBadgesAndBar(cart) {
  badges.forEach((badge) => {
    badge.textContent = formatNumber(cart.count);
  });
  if (bar) {
    bar.hidden = cart.count === 0;
    const countText = config.texts[cart.count === 1 ? "cart.item_count_one" : "cart.item_count"];
    bar.querySelector("[data-cart-bar-label]").textContent =
      `${config.texts["cart.view"]} · ${fillText(countText, { count: formatNumber(cart.count) })}`;
    bar.querySelector("[data-cart-bar-total]").textContent = formatNumber(cart.subtotal);
  }
}

function render(cart) {
  renderPanel(cart);
  renderBadgesAndBar(cart);
  if (cart.removed_unavailable) {
    showToast(config.texts["cart.removed_unavailable"], true);
  }
}

async function changeQuantity(lineId, quantity) {
  try {
    render(await requestJson(config.urls.cartUpdate, { line_id: lineId, quantity }));
  } catch (error) {
    showToast(error.message, true);
  }
}

/** A dot that travels from the pressed button to the cart badge in the header. */
function flyToCart(fromElement) {
  const target = document.querySelector(".site-header__cart-count");
  if (!fromElement || !target || prefersReducedMotion() || !window.gsap) {
    return Promise.resolve();
  }
  const from = fromElement.getBoundingClientRect();
  const to = target.getBoundingClientRect();
  const dot = document.createElement("span");
  dot.className = "fly-dot";
  document.body.append(dot);
  return new Promise((resolve) => {
    window.gsap.fromTo(
      dot,
      { x: from.left + from.width / 2 - 9, y: from.top + from.height / 2 - 9, scale: 1.2 },
      {
        x: to.left + to.width / 2 - 9,
        y: to.top + to.height / 2 - 9,
        scale: 0.5,
        duration: FLY_SECONDS,
        ease: "power2.inOut",
        onComplete: () => {
          dot.remove();
          resolve();
        },
      },
    );
  });
}

async function addDish(dishId, button) {
  try {
    const [cart] = await Promise.all([
      requestJson(config.urls.cartAdd, { dish_id: dishId, quantity: 1 }),
      flyToCart(button),
    ]);
    render(cart);
    popBadge();
    const name = button && button.closest("[data-dish-card]")?.querySelector(".dish-card__name");
    if (name) {
      showToast(fillText(config.texts["cart.added"], { name: name.textContent.trim() }));
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

/** Add a custom build (see builder.js). Returns true when the cart accepted it. */
export async function addCustomBuild(payload, button, name) {
  try {
    const [cart] = await Promise.all([requestJson(config.urls.cartAddCustom, payload), flyToCart(button)]);
    render(cart);
    popBadge();
    showToast(fillText(config.texts["cart.added"], { name }));
    return true;
  } catch (error) {
    showToast(error.message, true);
    return false;
  }
}

export async function startCart() {
  if (!config.urls.cart) {
    return;
  }
  document.addEventListener("cart:add", (event) => {
    addDish(event.detail.dishId, event.detail.button);
  });
  if (panel || bar) {
    try {
      render(await requestJson(config.urls.cart));
    } catch (error) {
      showToast(error.message, true);
    }
  }
}
