// Builder check: builds a sandwich, a pizza and a drink in a real browser and screenshots them.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/builder_screens.js [outdir]
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://127.0.0.1:5055";
const OUT = process.argv[2] || "/tmp/shots";

async function pick(page, name) {
  const exact = new RegExp(`^${name}$`);
  await page.locator("label.pick").filter({ has: page.locator(".pick__name", { hasText: exact }) }).first().click();
}

async function totalText(page) {
  return (await page.locator("[data-total-price]").textContent()).trim();
}

(async () => {
  const browser = await chromium.launch();
  for (const [label, viewport] of [["desktop", { width: 1366, height: 900 }], ["phone", { width: 390, height: 800 }]]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const problems = [];
    page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
    page.on("pageerror", (e) => problems.push(String(e)));
    page.on("requestfailed", (r) => problems.push("failed " + r.url()));
    for (const kind of ["pizza", "sandwich", "drink"]) {
      await page.goto(`${BASE}/fa/build/${kind}`);
      await page.waitForTimeout(500);
      if (kind === "pizza") {
        await pick(page, "پپرونی");
        await pick(page, "قارچ");
        await pick(page, "پستو");
      } else if (kind === "sandwich") {
        await pick(page, "کوبیده");
        await pick(page, "کاهو");
        await pick(page, "گوجه");
        await pick(page, "مایونز");
        await pick(page, "پنیر پیتزا");
      } else {
        await pick(page, "اسموتی میوه");
        await pick(page, "بزرگ \\(۵۰۰ میلی‌لیتر\\)");
        await pick(page, "انبه");
        await pick(page, "توت‌فرنگی");
        await pick(page, "خامه");
      }
      await page.waitForTimeout(700);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      console.log(label, kind, "total:", await totalText(page), "overflow:", overflow);
      await page.screenshot({ path: `${OUT}/build_${label}_${kind}.png`, fullPage: label === "desktop" });
    }
    if (problems.length) console.log(label, "problems:", problems);
    await context.close();
  }
  await browser.close();
})();
