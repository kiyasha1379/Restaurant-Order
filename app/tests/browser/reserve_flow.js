// Phase 7 browser check: public reservation flow and the admin reservation pages.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/reserve_flow.js [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";
const ADMIN_PAGES = [
  "/admin/reservations", "/admin/reservations/new", "/admin/tables",
  "/admin/tables/new", "/admin/tables/1", "/admin/schedule",
];

function watch(page, problems) {
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(String(e)));
  page.on("requestfailed", (r) => problems.push("failed " + r.url()));
}

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

(async () => {
  const browser = await chromium.launch();
  for (const [label, viewport] of [["desktop", { width: 1366, height: 800 }], ["phone", { width: 390, height: 800 }]]) {
    for (const lang of ["fa", "en"]) {
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const problems = [];
      watch(page, problems);
      const tag = `${label}-${lang}`;
      await page.goto(`${BASE}/${lang}/reserve`, { waitUntil: "networkidle" });
      console.log(tag, "reserve overflow:", await overflow(page));
      await page.screenshot({ path: `${OUT}/r7_${tag}_1_start.png`, fullPage: true });

      // Quick day chips: pick the first enabled one.
      const chips = page.locator(".chip-row > button.chip[data-day]:not([disabled])");
      console.log(tag, "enabled day chips:", await chips.count());
      await chips.first().click();
      await page.waitForTimeout(600);

      // Other-date picker.
      await page.click("[data-date-trigger]");
      await page.waitForTimeout(300);
      const panelOpen = await page.locator("[data-date-panel]").isVisible();
      const dayButtons = await page.locator("[data-date-panel] .dp__day").count();
      const disabledDays = await page.locator("[data-date-panel] .dp__day--off").count();
      console.log(tag, "picker open:", panelOpen, "buttons:", dayButtons, "disabled:", disabledDays);
      await page.screenshot({ path: `${OUT}/r7_${tag}_2_picker.png`, fullPage: true });
      // Choose the last enabled day in the panel, then come back to the quick day.
      const enabledDay = page.locator("[data-date-panel] button.dp__day");
      if ((await enabledDay.count()) > 0) {
        await enabledDay.nth(Math.min(3, (await enabledDay.count()) - 1)).click();
        await page.waitForTimeout(700);
        console.log(tag, "other-day label:", (await page.locator("[data-date-label]").innerText()).trim());
      } else {
        console.log(tag, "no enabled day buttons found in the panel");
        await page.keyboard.press("Escape");
      }
      await chips.first().click();
      await page.waitForTimeout(700);

      // Time slot and table.
      const slots = page.locator("[data-reserve-slots] input:not([disabled])");
      console.log(tag, "free slots:", await slots.count());
      await page.locator("[data-reserve-slots] .time-chip__face").first().waitFor();
      const freeFaces = page.locator("[data-reserve-slots] .time-chip:has(input:not([disabled])) .time-chip__face");
      await freeFaces.nth(Math.min(2, (await freeFaces.count()) - 1)).click();
      await page.waitForTimeout(700);
      await page.click('[data-guests-step="1"]');
      await page.click('[data-guests-step="1"]');
      await page.waitForTimeout(700);
      const states = await page.$$eval("[data-plan-table]", (els) => els.map((e) => e.dataset.state));
      console.log(tag, "table states:", JSON.stringify(states));
      await page.screenshot({ path: `${OUT}/r7_${tag}_3_chosen.png`, fullPage: true });

      const freeTable = page.locator('[data-plan-table][data-state="free"]').first();
      await freeTable.click();
      await page.waitForTimeout(300);
      await page.fill("#customer_name", lang === "fa" ? "علی رضایی" : "Ali Rezaei");
      await page.fill("#customer_phone", "09123456789");
      console.log(tag, "summary:", (await page.locator(".reserve-summary").innerText()).replace(/\s+/g, " "));
      await page.screenshot({ path: `${OUT}/r7_${tag}_4_filled.png`, fullPage: true });
      await page.click("[data-reserve-submit]");
      await page.waitForURL("**/reservation/**", { timeout: 8000 });
      await page.waitForTimeout(500);
      console.log(tag, "confirmation url:", page.url(), "overflow:", await overflow(page));
      await page.screenshot({ path: `${OUT}/r7_${tag}_5_done.png`, fullPage: true });
      if (problems.length) console.log(tag, "problems:", problems);
      await context.close();
    }

    // Admin pages.
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const problems = [];
    watch(page, problems);
    await page.goto(`${BASE}/admin/login`);
    await page.fill('input[name="email"]', "admin@example.com");
    await page.fill('input[name="password"]', "demo-pass-1234");
    await page.click('button[type="submit"]');
    for (const path of ADMIN_PAGES) {
      const response = await page.goto(BASE + path, { waitUntil: "networkidle" });
      console.log(label, path, response.status(), "overflow:", await overflow(page));
      await page.screenshot({ path: `${OUT}/r7_${label}_admin_${path.replace(/\W+/g, "_")}.png`, fullPage: true });
    }
    await page.goto(`${BASE}/admin/reservations`, { waitUntil: "networkidle" });
    const first = page.locator('a[href^="/admin/reservations/"]').filter({ hasNot: page.locator("nothing") });
    const detailHref = await page.$$eval('a[href^="/admin/reservations/"]', (as) =>
      (as.map((a) => a.getAttribute("href")).find((h) => /\/admin\/reservations\/\d+$/.test(h)) || ""));
    if (detailHref) {
      const response = await page.goto(BASE + detailHref, { waitUntil: "networkidle" });
      console.log(label, detailHref, response.status(), "overflow:", await overflow(page));
      await page.screenshot({ path: `${OUT}/r7_${label}_admin_detail.png`, fullPage: true });
    } else {
      console.log(label, "no reservation detail link found");
    }
    if (problems.length) console.log(label, "admin problems:", problems);
    await context.close();
  }
  await browser.close();
})();
