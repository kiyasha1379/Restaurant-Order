/**
 * Order tracking page: follows the order status live. It listens to the server-sent
 * event stream and, if streaming is blocked or breaks, polls the status every 5 seconds.
 */
import { config } from "./site-config.js";

const POLL_SECONDS = 5;

function showStatus(page, data) {
  page.dataset.status = data.status;
  page.querySelector("[data-status-label]").textContent = data.label;
  const steps = Array.from(page.querySelectorAll("[data-step]"));
  const currentIndex = steps.findIndex((step) => step.dataset.step === data.status);
  steps.forEach((step, index) => {
    step.classList.toggle("is-done", currentIndex > -1 && index < currentIndex);
    step.classList.toggle("is-current", index === currentIndex);
  });
  page.querySelector("[data-cancelled]").hidden = data.status !== "cancelled";
  // The pay-again panel only makes sense while the order waits for its payment.
  const payPanel = page.querySelector("[data-pay-panel]");
  if (payPanel) {
    payPanel.hidden = data.status !== "awaiting_payment";
  }
  page.querySelector("[data-live-note]").hidden = data.final;
}

export function startOrderTracker() {
  const page = document.querySelector("[data-order-tracker]");
  if (!page || page.querySelector("[data-live-note]").hidden) {
    return;
  }
  const token = page.dataset.token;
  const withToken = (template) => template.replace("TOKEN", encodeURIComponent(token));
  const language = encodeURIComponent(config.language);
  let pollTimer = null;

  async function poll() {
    try {
      const response = await fetch(`${withToken(config.urls.orderStatus)}?lang=${language}`);
      const data = await response.json();
      showStatus(page, data);
      if (data.final) {
        window.clearInterval(pollTimer);
      }
    } catch {
      // Try again on the next tick.
    }
  }

  function startPolling() {
    if (pollTimer === null) {
      poll();
      pollTimer = window.setInterval(poll, POLL_SECONDS * 1000);
    }
  }

  if (!("EventSource" in window)) {
    startPolling();
    return;
  }
  const source = new EventSource(`${withToken(config.urls.orderStream)}?lang=${language}`);
  source.addEventListener("status", (event) => {
    const data = JSON.parse(event.data);
    showStatus(page, data);
    if (data.final) {
      source.close();
    }
  });
  source.addEventListener("error", () => {
    // The server ends each stream after a while, and a proxy may block it; either way,
    // fall back to polling instead of leaving the page frozen.
    source.close();
    startPolling();
  });
}
