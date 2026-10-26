const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto('http://localhost:5055/fa/menu', { waitUntil: 'networkidle' });
  const card = p.locator('.dish-card').first();
  await card.locator('.dish-card__flip').click();
  await p.waitForTimeout(900);
  console.log('flipped', await card.evaluate(e => e.classList.contains('is-flipped')), await card.locator('.dish-card__flip').getAttribute('aria-pressed'));
  await p.screenshot({ path: '/tmp/shots/flip.png' });
  let ev = 0; await p.exposeFunction('seen', () => { ev++; });
  await p.evaluate(() => document.addEventListener('cart:add', e => window.seen(e.detail.dishId)));
  await p.locator('[data-add-dish]').first().click(); await p.waitForTimeout(100);
  console.log('cart:add events', ev);
  await p.locator('[data-filter="pizza"]').click();
  const vis = await p.evaluate(() => [...document.querySelectorAll('.dish-grid__item')].filter(i => !i.hidden).length);
  console.log('visible after pizza', vis, p.url());
  await b.close();
})();
