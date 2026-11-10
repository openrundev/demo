// record.cjs <url> <outdir> <seconds> [width] [height]  -> records a webm of the autoplaying replay
const { chromium } = require('/opt/homebrew/lib/node_modules/@playwright/mcp/node_modules/playwright-core');
const exe = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const [url, outdir, seconds = '80', w = '1280', h = '860'] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch({ executablePath: exe });
  const ctx = await browser.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1, colorScheme: 'light', recordVideo: { dir: outdir, size: { width: +w, height: +h } } });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(+seconds * 1000);
  await ctx.close();
  console.log(await page.video().path());
  await browser.close();
})();
