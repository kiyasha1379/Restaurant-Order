/**
 * <form data-confirm="Delete this address?"> asks the visitor before it is sent.
 */
export function startConfirmForms() {
  document.addEventListener("submit", (event) => {
    const message = event.target.dataset?.confirm;
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
}
