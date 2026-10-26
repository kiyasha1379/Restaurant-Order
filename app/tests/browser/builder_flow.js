// Builder flow: build a sandwich, add it to the cart, order it, then look at it in the panel
// and open the builder admin pages.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/builder_flow.js [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";
const STAFF_EMAIL = process.env.STAFF_EMAIL || "admin@example.com";
const STAFF_PASSWORD = process.env.STAFF_PASSWORD || "demo-pass-1234";

async function pick(page, name) {
  const exact = new RegExp(`^${name}$`);
  await page.locator("label.pick").filter({ has: page.locator(".pick__name", { hasText: exact }) }).first().click();
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();
  const problems = [];
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(String(e)));
  page.on("requestfailed", (r) => problems.push("failed " + r.url()));

  await page.goto(`${BASE}/fa/build/sandwich`);
  await page.waitForTimeout(500);
  for (const name of ["کوبیده", "کاهو", "گوجه", "مایونز", "پنیر پیتزا"]) await pick(page, name);
  // Move the first layer (lettuce or the like) down once to change the order.
  await page.locator(".layers button[aria-label], .layer-list button").first().click().catch(() => {});
  await page.locator("[data-add]").click();
  await page.waitForTimeout(900);
  console.log("cart badge", (await page.locator("[data-cart-count]").first().innerText()).trim());
  await page.locator("[data-cart-link]").click();
  await page.waitForTimeout(600);
  console.log("cart url", page.url());
  await page.screenshot({ path: `${OUT}/flow_cart.png` });
  await page.goto(`${BASE}/fa/checkout`);
  await page.fill("#customer_name", "علی رضایی");
  await page.fill("#customer_phone", "۰۹۱۲۳۴۵۶۷۸۹");
  await page.screenshot({ path: `${OUT}/flow_checkout.png` });
  await page.locator(".checkout__submit").click();
  await page.waitForURL("**/order/**");
  console.log("order url", page.url());
  const orderText = await page.locator("main").innerText();
  console.log("order shows options:", ["کوبیده", "کاهو", "گوجه", "مایونز"].every((w) => orderText.includes(w)));
  await page.screenshot({ path: `${OUT}/flow_order.png`, fullPage: true });

  // The panel
  await page.goto(`${BASE}/admin/login`);
  await page.fill("input[name=email]", STAFF_EMAIL);
  await page.fill("input[name=password]", STAFF_PASSWORD);
  await page.locator("button[type=submit]").click();
  await page.waitForURL("**/admin/**");
  console.log("after login:", page.url());
  await page.goto(`${BASE}/admin/orders`);
  const hrefs = await page.locator("a").evaluateAll((links) => links.map((a) => a.getAttribute("href")));
  const ids = hrefs.map((h) => /^\/admin\/orders\/(\d+)$/.exec(h || "")).filter(Boolean).map((m) => Number(m[1]));
  await page.goto(`${BASE}/admin/orders/${Math.max(...ids)}`);
  await page.waitForTimeout(500);
  console.log("detail url:", page.url());
  const detail = await page.locator("body").innerText();
  console.log("admin detail has layers:", ["کوبیده", "کاهو", "گوجه", "مایونز"].every((w) => detail.includes(w)));
  await page.screenshot({ path: `${OUT}/flow_admin_order.png`, fullPage: true });

  for (const [name, url] of [["builders", "/admin/builders"]]) {
    await page.goto(BASE + url);
    await page.screenshot({ path: `${OUT}/flow_admin_${name}.png`, fullPage: true });
  }
  await page.locator("a[href^='/admin/builders/']").filter({ hasText: /ویرایش/ }).first().click();
  await page.screenshot({ path: `${OUT}/flow_admin_builder.png`, fullPage: true });
  await page.locator("a[href*='/admin/builders/steps/']").filter({ hasText: /ویرایش/ }).first().click();
  await page.screenshot({ path: `${OUT}/flow_admin_step.png`, fullPage: true });
  await page.locator("a[href*='/admin/builders/options/']").filter({ hasText: /ویرایش/ }).first().click();
  await page.screenshot({ path: `${OUT}/flow_admin_option.png`, fullPage: true });
  console.log(problems.length ? ["problems:", problems] : "no problems");
  await browser.close();
})();
