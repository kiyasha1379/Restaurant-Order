# Browser checks (manual)

Scripts that drive a real Chromium through Playwright against a running dev server
(`flask run -p 5055`, after `flask db upgrade` and `flask seed-demo`):

- `screenshots.js` opens the home and menu pages in both languages on desktop and phone,
  reports horizontal overflow, failed requests, console errors and which videos play,
  and saves screenshots to `/tmp/shots`.
- `menu_interaction.js` flips a dish card, clicks the add button (a `cart:add` event must fire)
  and switches the category chips.

Run: `npm i -g playwright` once, then `NODE_PATH=$(npm root -g) node tests/browser/screenshots.js`.

Phase 4 scripts (run the server with `APP_CONFIG=demo flask run -p 5055`):

- `order_flow.js` adds dishes, changes quantities, checks out as a delivery order and follows the order page.
- `order_flow_phone.js` does the same on a 390 px phone (cart bar, checkout errors, no horizontal scroll).
- `order_live_status.js <token>` opens an order page, runs `flask advance-order 1` and checks the status changes without a reload. Start the browser with `delete window.EventSource` to test the polling fallback.
