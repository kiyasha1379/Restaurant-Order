// Phase 10 browser check: change the settings and the site appearance in the admin panel and
// see the result on the public site (pause bar, accent colour, logo, poster, section order, texts).
// Usage: NODE_PATH=$(npm root -g) node tests/browser/site_flow.js [outdir]
// Needs /tmp/logo.png and /tmp/poster.png (any pictures). Restores the demo state at the end.
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

async function shot(page, tag, name, full = true) {
  console.log(tag, name, "overflow:", await overflow(page));
  await page.screenshot({ path: `${OUT}/p10_${tag}_${name}.png`, fullPage: full });
}

async function signIn(page) {
  await page.goto(`${BASE}/admin/login`);
  await page.fill('input[name="email"]', "admin@example.com");
  await page.fill('input[name="password"]', "demo-pass-1234");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/admin/dashboard");
}

async function save(page) {
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle" }), page.locator("form .btn--primary").last().click()]);
}

async function sectionIds(page) {
  return page.$$eval("section[data-section]", (nodes) => nodes.map((n) => n.id));
}

(async () => {
  const browser = await chromium.launch();
  for (const [label, viewport] of [["desktop", { width: 1366, height: 800 }], ["phone", { width: 390, height: 800 }]]) {
    const adminContext = await browser.newContext({ viewport });
    const admin = await adminContext.newPage();
    const problems = [];
    watch(admin, problems);
    await signIn(admin);

    // Settings: pause ordering with a custom message and switch online payment off.
    await admin.goto(`${BASE}/admin/settings`, { waitUntil: "networkidle" });
    await shot(admin, label, "1_settings");
    await admin.locator("#ordering_paused").check({ force: true });
    await admin.fill("#pause_message_fa", "امشب فقط حضوری سفارش می‌گیریم");
    await admin.fill("#pause_message_en", "Tonight we take walk-in orders only");
    await admin.locator("#online_payment").uncheck({ force: true });
    await save(admin);
    console.log(label, "settings saved notice:", (await admin.locator(".notices__item--success, .flash--success, [role=status]").count()) > 0);

    // General: brand name, accent colour and logo.
    await admin.goto(`${BASE}/admin/site`, { waitUntil: "networkidle" });
    await admin.fill("#brand_name", label === "desktop" ? "رستوران نمونه" : "Sample Kitchen");
    await admin.locator("#use_default_color").uncheck({ force: true });
    await admin.locator("#accent_color").evaluate((el) => { el.value = "#2f7d6b"; el.dispatchEvent(new Event("input", { bubbles: true })); });
    await admin.setInputFiles("#logo", "/tmp/logo.png");
    await shot(admin, label, "2_site_general");
    await save(admin);
    await shot(admin, label, "3_site_general_saved");

    // Backgrounds: new poster for the menu page and a lighter dim for the hero.
    await admin.goto(`${BASE}/admin/site/backgrounds`, { waitUntil: "networkidle" });
    await shot(admin, label, "4_backgrounds");
    await admin.setInputFiles("#poster-menu-page", "/tmp/poster.png");
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#bg-menu-page .btn--primary").click()]);
    await admin.fill("#dim-home-hero", "20");
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#bg-home-hero .btn--primary").click()]);
    console.log(label, "poster stored:", (await admin.locator("#bg-menu-page .bg-edit__poster").getAttribute("src")).includes("uploads/backgrounds/"));

    // Home: move "how" up one step, hide "reserve", change the headline.
    await admin.goto(`${BASE}/admin/site/home`, { waitUntil: "networkidle" });
    await admin.locator('button[value="how:up"]').click();
    await admin.waitForLoadState("networkidle");
    await admin.locator('input[name=visible][value=reserve]').uncheck({ force: true });
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#sections .btn--primary").click()]);
    await admin.locator('textarea[name="home.headline.fa"]').fill("سرآشپز امشب برای شماست");
    await admin.locator('textarea[name="home.headline.en"]').fill("The chef cooks for you tonight");
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#texts .btn--primary").click()]);
    await shot(admin, label, "5_home");
    if (problems.length) console.log(label, "admin problems:", problems);

    // The public site shows all of it.
    for (const lang of ["fa", "en"]) {
      const tag = `${label}-${lang}`;
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      const publicProblems = [];
      watch(page, publicProblems);
      await page.goto(`${BASE}/${lang}/`, { waitUntil: "networkidle" });
      console.log(tag, "pause bar:", (await page.locator(".pause-bar").innerText()).replace(/\s+/g, " "));
      console.log(tag, "logo shown:", (await page.locator(".brand-logo").count()) > 0);
      console.log(tag, "accent:", await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--color-accent").trim()));
      console.log(tag, "section order:", (await sectionIds(page)).join(","));
      console.log(tag, "headline:", (await page.locator(".hero__title").innerText()).trim());
      await shot(page, tag, "6_home", false);
      await page.goto(`${BASE}/${lang}/menu`, { waitUntil: "networkidle" });
      await page.locator("[data-add-dish]").first().click();
      await page.waitForTimeout(700);
      console.log(tag, "toast while paused:", (await page.locator(".toast--error").first().innerText()).trim());
      console.log(tag, "cart count:", (await page.locator(".site-header__cart-count").innerText()).trim());
      await shot(page, tag, "7_menu_paused", false);
      await page.goto(`${BASE}/${lang}/reserve`, { waitUntil: "networkidle" });
      await shot(page, tag, "8_reserve", false);
      const real = publicProblems.filter((text) => !text.includes("409"));  // the refused add is expected
      if (real.length) console.log(tag, "public problems:", real);
      await context.close();
    }

    // Put the demo back the way it was.
    await admin.goto(`${BASE}/admin/settings`, { waitUntil: "networkidle" });
    await admin.locator("#ordering_paused").uncheck({ force: true });
    await admin.fill("#pause_message_fa", "");
    await admin.fill("#pause_message_en", "");
    await admin.locator("#online_payment").check({ force: true });
    await save(admin);
    await admin.goto(`${BASE}/admin/site`, { waitUntil: "networkidle" });
    await admin.fill("#brand_name", "Restaurant");
    await admin.locator("#use_default_color").check({ force: true });
    await admin.locator("#remove_logo").check({ force: true });
    await save(admin);
    await admin.goto(`${BASE}/admin/site/backgrounds`, { waitUntil: "networkidle" });
    await admin.locator("#rmposter-menu-page").check({ force: true });
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#bg-menu-page .btn--primary").click()]);
    await admin.fill("#dim-home-hero", "40");
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#bg-home-hero .btn--primary").click()]);
    await admin.goto(`${BASE}/admin/site/home`, { waitUntil: "networkidle" });
    await admin.locator('button[value="how:down"]').click();
    await admin.waitForLoadState("networkidle");
    await admin.locator('input[name=visible][value=reserve]').check({ force: true });
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#sections .btn--primary").click()]);
    await admin.locator('textarea[name="home.headline.fa"]').fill("");
    await admin.locator('textarea[name="home.headline.en"]').fill("");
    await Promise.all([admin.waitForNavigation({ waitUntil: "networkidle" }), admin.locator("#texts .btn--primary").click()]);
    await adminContext.close();
  }
  await browser.close();
})();
