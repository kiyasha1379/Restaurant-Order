// Phase 11 accessibility pass: run axe-core (WCAG A/AA rules) on the main public and admin pages.
// Usage: AXE_PATH=/path/to/axe.min.js NODE_PATH=$(npm root -g) node tests/browser/a11y_check.js
const fs = require("fs");
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const AXE = fs.readFileSync(process.env.AXE_PATH, "utf8");
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const PUBLIC = ["/", "/menu", "/builder", "/reserve", "/cart", "/checkout", "/login", "/register", "/contact"];
const ADMIN = ["/admin/dashboard", "/admin/orders", "/admin/menu", "/admin/reservations", "/admin/customers",
  "/admin/builders", "/admin/languages", "/admin/settings", "/admin/site", "/admin/site/backgrounds",
  "/admin/site/home", "/admin/users"];

async function scan(page, label) {
  await page.waitForTimeout(700);
  await page.evaluate(AXE);
  const result = await page.evaluate((tags) => axe.run(document, { runOnly: { type: "tag", values: tags } }), TAGS);
  for (const v of result.violations) {
    const nodes = v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ");
    console.log(`${label} [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length}) -> ${nodes}`);
  }
  return result.violations.length;
}

(async () => {
  const browser = await chromium.launch();
  let total = 0;
  for (const lang of ["fa", "en"]) {
    const context = await browser.newContext({ viewport: { width: 1366, height: 800 } });
    const page = await context.newPage();
    // Put one dish in the cart so the cart and checkout pages have content.
    await page.goto(`${BASE}/${lang}/menu`, { waitUntil: "networkidle" });
    await page.locator("[data-add-dish]").first().click();
    await page.waitForTimeout(800);
    for (const path of PUBLIC) {
      await page.goto(`${BASE}/${lang}${path === "/" ? "/" : path}`, { waitUntil: "networkidle" });
      total += await scan(page, `${lang}${path}`);
    }
    await context.close();
  }
  const context = await browser.newContext({ viewport: { width: 1366, height: 800 } });
  const page = await context.newPage();
  await page.goto(`${BASE}/admin/login`);
  await page.fill('input[name="email"]', "admin@example.com");
  await page.fill('input[name="password"]', "demo-pass-1234");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/dashboard");
  for (const path of ADMIN) {
    await page.goto(BASE + path, { waitUntil: "networkidle" });
    total += await scan(page, path);
  }
  console.log("violations:", total);
  await browser.close();
})();
