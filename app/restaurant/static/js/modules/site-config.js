/**
 * Shared helpers for the page scripts: the config the server wrote into the page,
 * number formatting in the page language, JSON requests with the CSRF token, and toasts.
 */
const configElement = document.getElementById("site-config");
export const config = configElement ? JSON.parse(configElement.textContent) : { urls: {}, texts: {} };

const csrfMeta = document.querySelector('meta[name="csrf-token"]');
const csrfToken = csrfMeta ? csrfMeta.content : "";
const numberFormat = new Intl.NumberFormat(config.locale || "en-US");

export function formatNumber(value) {
  return numberFormat.format(value);
}

/** Fill `{name}` placeholders of a server text. */
export function fillText(template, values) {
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in values ? values[key] : match));
}

function withLanguage(url) {
  const address = new URL(url, window.location.origin);
  address.searchParams.set("lang", config.language);
  return address.toString();
}

/** Send or fetch JSON. Resolves with the parsed body; rejects with the server's message. */
export async function requestJson(url, body) {
  const options = { headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.headers["X-CSRFToken"] = csrfToken;
    options.body = JSON.stringify(body);
  }
  const response = await fetch(withLanguage(url), options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || config.texts["cart.error"]);
  }
  return data;
}

const TOAST_SECONDS = 2.6;

export function showToast(message, isError = false) {
  const region = document.querySelector("[data-toasts]");
  if (!region) {
    return;
  }
  const toast = document.createElement("p");
  toast.className = isError ? "toast toast--error" : "toast";
  toast.textContent = message;
  region.append(toast);
  window.setTimeout(() => toast.remove(), TOAST_SECONDS * 1000);
}

export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
