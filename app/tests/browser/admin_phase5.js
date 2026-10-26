// Phase 5 browser check: menu form with a photo upload, languages, users and roles pages.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/admin_phase5.js [outdir] [photo]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";
const PHOTO = process.argv[3] || "/tmp/dish_test.jpg";
const PAGES = [
  "/admin/menu", "/admin/menu/categories", "/admin/languages", "/admin/languages/texts",
  "/admin/users", "/admin/users/roles", "/admin/users/new", "/admin/users/roles/new", "/admin/users/roles/2",
];

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
    await page.fill('input[name="email"]', "admin@example.com");
    await page.fill('input[name="password"]', "demo-pass-1234");
    await page.click('button[type="submit"]');
    for (const path of PAGES) {
      const response = await page.goto(BASE + path);
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      console.log(label, path, response.status(), "overflow:", overflow);
      await page.screenshot({ path: `${OUT}/p5_${label}_${path.replace(/\W+/g, "_")}.png`, fullPage: true });
    }
    if (label === "desktop") {
      // Upload a photo to the first dish and check the thumbnail appears.
      await page.goto(`${BASE}/admin/menu`);
      const editLink = await page.locator('a[href^="/admin/menu/dishes/"]:not([href$="/new"])').first().getAttribute("href");
      await page.goto(BASE + editLink);
      await page.setInputFiles('input[type="file"]', PHOTO);
      await page.click('button[type="submit"].btn--primary');
      await page.waitForLoadState("networkidle");
      const image = page.locator('.photo__preview img').first();
      console.log("photo shown after save:", (await image.count()) > 0, page.url());
      await page.screenshot({ path: `${OUT}/p5_desktop_photo_saved.png`, fullPage: true });
    }
    if (problems.length) console.log(label, "problems:", problems);
    await context.close();
  }
  await browser.close();
})();
