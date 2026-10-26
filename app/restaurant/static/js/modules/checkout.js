/**
 * Checkout page: shows the address box only for delivery, and asks the server for the price
 * of the chosen way of receiving the order (the server is the only one that prices it).
 */
import { config, formatNumber, requestJson } from "./site-config.js";

export function startCheckout() {
  const page = document.querySelector("[data-checkout]");
  if (!page) {
    return;
  }
  const addressField = page.querySelector("[data-address-field]");
  const feeRow = page.querySelector("[data-quote-fee-row]");
  const feeValue = page.querySelector("[data-quote-fee]");
  const totalValue = page.querySelector("[data-quote-total]");

  async function refreshQuote(fulfillment) {
    addressField.hidden = fulfillment !== "delivery";
    try {
      const quote = await requestJson(`${config.urls.quote}?fulfillment=${fulfillment}`);
      feeRow.hidden = quote.delivery_fee === 0;
      feeValue.textContent = formatNumber(quote.delivery_fee);
      totalValue.textContent = formatNumber(quote.total);
    } catch {
      // The form still works: the server prices the order again when it is placed.
    }
  }

  page.querySelectorAll("[data-fulfillment]").forEach((radio) => {
    radio.addEventListener("change", () => refreshQuote(radio.value));
  });
  const selected = page.querySelector("[data-fulfillment]:checked");
  if (selected && selected.value === "delivery") {
    refreshQuote("delivery");
  }
}
