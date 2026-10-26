// Phase 9 browser check: pay online through the test gateway (fail, retry, succeed, cancel,
// pay on arrival instead) and the admin views of payments.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/pay_flow.js [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";

function watch(page, problems) {
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(String(e)));
  page.on("requestfailed", (r) => problems.push("failed " + r.url()));
}

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

async function shot(page, tag, name) {
  console.log(tag, name, "overflow:", await overflow(page));
  await page.screenshot({ path: `${OUT}/p9_${tag}_${name}.png`, fullPage: true });
}

async function order(page, lang, tag, label) {
  await page.goto(`${BASE}/${lang}/menu`, { waitUntil: "networkidle" });
  await page.locator("[data-add-dish]").nth(0).click();
  await page.waitForTimeout(800);
  await page.goto(`${BASE}/${lang}/checkout`, { waitUntil: "networkidle" });
  await page.fill("#customer_name", lang === "fa" ? "علی رضایی" : "Ali Rezaei");
  await page.fill("#customer_phone", "09123456789");
  await page.locator("[data-fulfillment][value=takeaway]").check({ force: true });
  console.log(tag, label, "online option present:", (await page.locator('input[name=payment_method][value=online]').count()) === 1);
  await page.locator('input[name=payment_method][value=online]').check({ force: true });
  await shot(page, tag, `${label}_1_checkout`);
  await page.locator(".checkout__submit").click();
  await page.waitForURL("**/pay/mock/**");
}

(async () => {
  const browser = await chromium.launch();
  for (const [label, viewport] of [["desktop", { width: 1366, height: 800 }], ["phone", { width: 390, height: 800 }]]) {
    for (const lang of ["fa", "en"]) {
      const tag = `${label}-${lang}`;
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const problems = [];
      watch(page, problems);

      // 1. Fail, retry, then succeed.
      await order(page, lang, tag, "a");
      await page.waitForLoadState("networkidle");
      await shot(page, tag, "a_2_gateway");
      console.log(tag, "gateway has card fields:", (await page.locator("input").count()) > 0);
      await page.click('[data-outcome="failure"]');
      await page.waitForURL("**/order/**");
      await page.waitForTimeout(600);
      console.log(tag, "pay panel visible:", await page.locator("[data-pay-panel]").isVisible());
      await shot(page, tag, "a_3_failed");
      await page.locator("[data-pay-panel] .btn--primary").click();
      await page.waitForURL("**/pay/mock/**");
      await page.click('[data-outcome="success"]');
      await page.waitForURL("**/order/**");
      await page.waitForTimeout(600);
      console.log(tag, "pay panel after success:", await page.locator("[data-pay-panel]").count());
      console.log(tag, "status:", (await page.locator("[data-status-label]").innerText()).trim());
      await shot(page, tag, "a_4_paid");

      // 2. Cancel at the gateway, then choose to pay on arrival.
      await order(page, lang, tag, "b");
      await page.click('[data-outcome="cancel"]');
      await page.waitForURL("**/order/**");
      await page.locator("[data-pay-panel] .btn--ghost").click();
      await page.waitForURL("**/order/**");
      await page.waitForTimeout(600);
      console.log(tag, "after pay-on-arrival status:", (await page.locator("[data-status-label]").innerText()).trim());
      await shot(page, tag, "b_2_cash");

      // 3. Leave a waiting order for the admin to see.
      await order(page, lang, tag, "c");
      await page.click('[data-outcome="failure"]');
      await page.waitForURL("**/order/**");
      if (problems.length) console.log(tag, "problems:", problems);
      await context.close();
    }

    // Admin views.
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const problems = [];
    watch(page, problems);
    await page.goto(`${BASE}/admin/login`);
    await page.fill('input[name="email"]', "admin@example.com");
    await page.fill('input[name="password"]', "demo-pass-1234");
    await page.click('button[type="submit"]');
    for (const path of ["/admin/orders", "/admin/orders/history?status=awaiting_payment", "/admin/dashboard"]) {
      const response = await page.goto(BASE + path, { waitUntil: "networkidle" });
      console.log(label, path, response.status());
      await shot(page, label, `admin${path.replace(/\W+/g, "_")}`);
    }
    const link = await page.$$eval('a[href^="/admin/orders/"]', (as) =>
      as.map((a) => a.getAttribute("href")).find((h) => /\/admin\/orders\/\d+$/.test(h)));
    if (link) {
      await page.goto(BASE + link, { waitUntil: "networkidle" });
      await shot(page, label, "admin_order_detail");
    }
    if (problems.length) console.log(label, "admin problems:", problems);
    await context.close();
  }
  await browser.close();
})();
