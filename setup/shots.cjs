// Screenshots of the real apps on the demo server (run through record.sh)
const { chromium } = require('/opt/homebrew/lib/node_modules/@playwright/mcp/node_modules/playwright-core');
const path = require('path');
const OUT = path.join(__dirname, 'cap', 'shots');
const PORT = process.env.DEMO_HTTPS_PORT;
const B = 'https://localhost:' + PORT;
const PW = Object.fromEntries(['alice', 'bob', 'carol'].map((u) => [u, u + process.env.DEMO_PW_SUFFIX]));
const exe = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const only = process.argv.slice(2);

(async () => {
  const browser = await chromium.launch({ executablePath: exe });
  const ctxFor = async (user) => browser.newContext({
    viewport: { width: 1200, height: 750 }, deviceScaleFactor: 1, ignoreHTTPSErrors: true,
    extraHTTPHeaders: user ? { Authorization: 'Basic ' + Buffer.from(user + ':' + PW[user]).toString('base64') } : {},
  });
  const shot = async (name, user, url, fn, wait = 800) => {
    if (only.length && !only.includes(name)) return;
    const ctx = await ctxFor(user);
    const page = await ctx.newPage();
    try {
      const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch((e) => { console.log(name, 'goto:', e.message.split('\n')[0]); return null; });
      if (fn) await fn(page);
      await page.waitForTimeout(wait);
      await page.screenshot({ path: path.join(OUT, name + '.png') });
      console.log(name, resp && resp.status(), await page.title());
    } catch (e) { console.log(name, 'FAILED', e.message.split('\n')[0]); }
    await ctx.close();
  };
  // Streamlit needs its websocket: sign in through the login form for a session cookie
  await shot('dashboard', null, B + '/eng/dashboard/', async (p) => {
    await p.fill('#builtin-username', 'alice');
    await p.fill('#builtin-password', PW.alice);
    await p.press('#builtin-password', 'Enter');
    await p.getByText('Deploys per day').waitFor({ timeout: 30000 }).catch((e) => console.log('dash wait', e.message.split('\n')[0]));
  }, 3000);
  await shot('inventory', 'alice', B + '/eng/inventory/');
  await shot('oncall', 'alice', B + '/eng/oncall/');
  await shot('tasks-admin', 'alice', B + '/tasks/admin/');
  await shot('tasks-edit', 'alice', B + '/tasks/edit/');
  await shot('tasks-view', 'carol', B + '/tasks/view/');
  await shot('tasks-view-denied', 'carol', B + '/tasks/view/', async (p) => {
    const inp = p.locator('input[name=title]').first();
    await inp.fill('Sneak one in');
    await inp.press('Enter');
    await p.waitForTimeout(1200);
  });
  await shot('svc', 'bob', B + '/ops/svc/');
  await shot('svc-restart', 'bob', B + '/ops/svc/restart');
  await shot('svc-carol', 'carol', B + '/ops/svc/');
  await shot('handbook', 'carol', B + '/shared/handbook/');
  await shot('handbook-stage', 'carol', 'https://stage.localhost:' + PORT + '/shared/handbook/');
  await shot('docs', null, 'https://docs.localhost:' + PORT + '/', null, 2500);
  await shot('login', null, B + '/eng/dashboard/');
  await shot('forbidden', 'alice', B + '/ops/svc/');
  await browser.close();
})();
