/* Live order board: listens for change events and swaps in the fresh columns.
 *
 * Server-sent events carry the signal. If the browser or a proxy blocks streaming,
 * the board polls every 5 seconds instead (technical plan, section 7).
 */

const POLL_MILLISECONDS = 5000;
const board = document.querySelector("[data-board]");

if (board) {
  const fragmentUrl = board.dataset.fragmentUrl;
  const streamUrl = board.dataset.streamUrl;
  let knownIds = collectIds();
  let busy = false;

  function collectIds() {
    return new Set([...board.querySelectorAll("[data-order-id]")].map((card) => card.dataset.orderId));
  }

  async function refresh() {
    if (busy) return;
    busy = true;
    try {
      const response = await fetch(fragmentUrl, { headers: { "X-Requested-With": "fetch" } });
      if (!response.ok) return;
      board.innerHTML = await response.text();
      for (const card of board.querySelectorAll("[data-order-id]")) {
        if (!knownIds.has(card.dataset.orderId)) card.classList.add("order-card--new");
      }
      knownIds = collectIds();
    } finally {
      busy = false;
    }
  }

  function startPolling() {
    window.setInterval(() => {
      if (!document.hidden) refresh();
    }, POLL_MILLISECONDS);
  }

  if ("EventSource" in window) {
    const source = new EventSource(streamUrl);
    let opened = false;
    source.addEventListener("board", refresh);
    // After a reconnect, changes made in the gap are fetched once.
    source.addEventListener("open", () => {
      if (opened) refresh();
      opened = true;
    });
    source.addEventListener("error", () => {
      if (source.readyState === EventSource.CLOSED) startPolling();
    });
  } else {
    startPolling();
  }
}
