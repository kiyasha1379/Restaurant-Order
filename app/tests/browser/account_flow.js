// Phase 8 browser check: register with the demo code, keep the cart, order, ordering again,
// addresses, profile, contact form, and the admin customers and messages pages.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/account_flow.js [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";
const ADMIN_PAGES = ["/admin/customers", "/admin/messages"];

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
  await page.screenshot({ path: `${OUT}/a8_${tag}_${name}.png`, fullPage: true });
}

(async () => {
  const browser = await chromium.launch();
  const stamp = String(Date.now()).slice(-7);
  for (const [label, viewport] of [["desktop", { width: 1366, height: 800 }], ["phone", { width: 390, height: 800 }]]) {
    for (const lang of ["fa", "en"]) {
      const tag = `${label}-${lang}`;
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const problems = [];
      watch(page, problems);
      const phone = `0912${label === "desktop" ? "1" : "2"}${lang === "fa" ? "1" : "2"}${stamp.slice(-5)}`;

      // A guest fills the cart first.
      await page.goto(`${BASE}/${lang}/menu`, { waitUntil: "networkidle" });
      await page.locator("[data-add-dish]").nth(0).click();
      await page.waitForTimeout(900);
      await page.locator("[data-add-dish]").nth(1).click();
      await page.waitForTimeout(900);
      const before = (await page.locator(".site-header__cart-count").innerText()).trim();

      // Register through the pages.
      await page.goto(`${BASE}/${lang}/login`, { waitUntil: "networkidle" });
      await shot(page, tag, "1_login");
      await page.click(".auth__switch a");
      await page.waitForURL("**/register**");
      await page.fill("#customer_name", lang === "fa" ? "مشتری آزمایشی" : "Test Customer");
      await page.fill("#phone", phone);
      await page.fill("#password", "browser-pass-1");
      await page.fill("#password_again", "browser-pass-1");
      await shot(page, tag, "2_register");
      await page.click(".auth__submit");
      await page.waitForURL("**/verify**");
      console.log(tag, "demo hint shown:", (await page.locator(".auth__demo").count()) === 1);
      await page.fill("#code", "00000");
      await page.click(".auth__submit");
      await page.waitForTimeout(500);
      console.log(tag, "wrong code error:", (await page.locator(".field__error").count()) === 1);
      await shot(page, tag, "3_verify");
      await page.fill("#code", "12345");
      await page.click(".auth__submit");
      await page.waitForURL("**/account");
      const after = (await page.locator(".site-header__cart-count").innerText()).trim();
      console.log(tag, "cart badge before/after sign-in:", before, after);
      await shot(page, tag, "4_overview");

      // Addresses: add one, then use it at checkout and save a second one there.
      await page.goto(`${BASE}/${lang}/account/addresses`, { waitUntil: "networkidle" });
      await page.fill("#label", lang === "fa" ? "خانه" : "Home");
      await page.fill("#text", lang === "fa" ? "تهران، خیابان آزادی، پلاک ۱۲، واحد ۳" : "Tehran, Azadi Street, number 12, unit 3");
      await page.click(".account-form .btn--primary");
      await page.waitForURL("**/addresses");
      await shot(page, tag, "5_addresses");

      await page.goto(`${BASE}/${lang}/checkout`, { waitUntil: "networkidle" });
      await page.locator("[data-fulfillment][value=delivery]").check({ force: true });
      await page.waitForTimeout(500);
      console.log(tag, "address chips:", await page.locator("[data-fill-address]").count());
      await page.fill("#delivery_address", lang === "fa" ? "تهران، میدان انقلاب، پلاک ۳" : "Tehran, Enghelab Square, number 3");
      await page.locator("#save_address").check({ force: true });
      await shot(page, tag, "6_checkout");
      await page.locator(".checkout__submit").click();
      await page.waitForURL("**/order/**");

      // History and ordering again.
      await page.goto(`${BASE}/${lang}/account/orders`, { waitUntil: "networkidle" });
      await shot(page, tag, "7_orders");
      await page.locator(".record__actions form button").first().click();
      await page.waitForURL("**/cart");
      await page.waitForTimeout(600);
      console.log(tag, "cart lines after ordering again:", await page.locator(".cart-line").count());

      await page.goto(`${BASE}/${lang}/account/addresses`, { waitUntil: "networkidle" });
      console.log(tag, "saved addresses:", await page.locator(".address").count());
      await page.goto(`${BASE}/${lang}/account/reservations`, { waitUntil: "networkidle" });
      await shot(page, tag, "8_reservations");
      await page.goto(`${BASE}/${lang}/account/profile`, { waitUntil: "networkidle" });
      await shot(page, tag, "9_profile");

      // Contact form.
      await page.goto(`${BASE}/${lang}/contact`, { waitUntil: "networkidle" });
      await page.fill("#body", lang === "fa" ? "سلام، ساعت کاری روز جمعه چیست؟" : "Hello, what are your opening hours on Friday?");
      await shot(page, tag, "10_contact");
      await page.click(".auth__submit");
      await page.waitForTimeout(600);
      console.log(tag, "contact sent notice:", (await page.locator(".notices__item--success").count()) === 1);

      // Sign out empties this browser's cart.
      await page.goto(`${BASE}/${lang}/account`, { waitUntil: "networkidle" });
      await page.click(".account-tabs__logout button");
      await page.waitForURL("**/");
      console.log(tag, "cart badge after sign-out:", (await page.locator(".site-header__cart-count").innerText()).trim());
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
      console.log(label, path, response.status());
      await shot(page, label, `admin${path.replace(/\W+/g, "_")}`);
    }
    await page.goto(`${BASE}/admin/customers`, { waitUntil: "networkidle" });
    const detail = await page.$$eval('a[href^="/admin/customers/"]', (links) => links.map((a) => a.getAttribute("href"))[0]);
    if (detail) {
      await page.goto(BASE + detail, { waitUntil: "networkidle" });
      await shot(page, label, "admin_customer_detail");
    }
    if (problems.length) console.log(label, "admin problems:", problems);
    await context.close();
  }
  await browser.close();
})();
