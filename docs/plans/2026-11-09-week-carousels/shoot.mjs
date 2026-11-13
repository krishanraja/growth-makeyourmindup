// node shoot.mjs mon : screenshots mon/cards/card-N.html to card-N.png at 1080 x 1350
import { chromium } from 'playwright';
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url));
const day = process.argv[2]; const dir = path.join(here, day, 'cards');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.html')).sort()) {
  await page.goto('file://' + path.join(dir, f));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(dir, f.replace('.html', '.png')) });
  console.log(day, f);
}
await browser.close();
