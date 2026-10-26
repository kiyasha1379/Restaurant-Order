const { chromium } = require('playwright');
const { execSync } = require('child_process');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const token = process.argv[2];
  await p.goto('http://localhost:5055/fa/order/' + token, { waitUntil: 'networkidle' });
  console.log('before', await p.locator('[data-status-label]').innerText());
  execSync('cd /home/claude/Restaurant/app && source /home/claude/venv/bin/activate && FLASK_APP=wsgi.py flask advance-order 1', { shell: '/bin/bash', stdio: 'inherit' });
  await p.waitForTimeout(4500);
  console.log('after advance (no reload)', await p.locator('[data-status-label]').innerText());
  console.log('overflow', await p.evaluate(() => document.documentElement.scrollWidth - innerWidth));
  await p.screenshot({ path: '/tmp/shots/order-m.png' });
  await b.close();
})();
