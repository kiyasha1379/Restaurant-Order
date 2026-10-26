const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const jobs = [
    ['home-fa-d', '/fa/', 1440, 900], ['home-en-d', '/en/', 1440, 900],
    ['home-fa-m', '/fa/', 390, 844], ['menu-fa-d', '/fa/menu', 1440, 900],
    ['menu-en-m', '/en/menu', 390, 844],
  ];
  for (const [name, path, w, h] of jobs) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    page.on('requestfailed', r => errors.push('FAILED ' + r.url()));
    await page.goto('http://localhost:5055' + path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const videos = await page.evaluate(() => [...document.querySelectorAll('video')].map(v => (v.src ? 'src' : 'nosrc') + (v.paused ? ':paused' : ':playing')));
    console.log(name, 'overflow', overflow, 'videos', videos.join(','), 'errors', JSON.stringify(errors));
    await page.screenshot({ path: `/tmp/shots/${name}.png` });
    if (name === 'home-fa-d' || name === 'home-fa-m') {
      for (const id of ['modes', 'dishes', 'how', 'contact']) {
        await page.evaluate(i => document.getElementById(i).scrollIntoView(), id);
        await page.waitForTimeout(1300);
        await page.screenshot({ path: `/tmp/shots/${name}-${id}.png` });
      }
    }
    await ctx.close();
  }
  await browser.close();
})();
