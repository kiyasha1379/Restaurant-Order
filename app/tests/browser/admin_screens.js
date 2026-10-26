// Signs in to the admin panel and screenshots its pages on desktop and phone.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/admin_screens.js [email] [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const EMAIL = process.argv[2] || "admin@example.com";
const OUT = process.argv[3] || "/tmp/shots";
const PASSWORD = "demo-pass-1234";
const PAGES = ["/admin/dashboard", "/admin/orders", "/admin/orders/history", "/admin/orders/1"];

(async () => {
  const browser = await chromium.launch();
  for (const [label, viewport] of [["desktop", { width: 1366, height: 800 }], ["phone", { width: 390, height: 800 }]]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const problems = [];
    page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
    page.on("pageerror", (e) => problems.push(String(e)));
    page.on("requestfailed", (r) => problems.push("failed " + r.url()));
    await page.goto(`${BASE}/admin/login`);
    await page.screenshot({ path: `${OUT}/admin_login_${label}.png` });
    await page.fill('input[name="email"]', EMAIL);
    await page.fill('input[name="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    for (const path of PAGES) {
      await page.goto(BASE + path);
      await page.waitForTimeout(400);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      console.log(label, path, "overflow:", overflow);
      await page.screenshot({ path: `${OUT}/admin_${label}_${path.replace(/\W+/g, "_")}.png`, fullPage: true });
    }
    if (problems.length) console.log(label, "problems:", problems);
    await context.close();
  }
  await browser.close();
})();
