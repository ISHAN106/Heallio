const puppeteer = require('puppeteer-core');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:5000';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
    defaultViewport: { width: 430, height: 932, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
  });
  const page = await browser.newPage();
  page.on('console', (m) => console.log('CONSOLE:', m.text()));
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message));
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await sleep(9000);
  await page.mouse.click(215, 444); await sleep(2500);       // Patient
  await page.mouse.click(215, 534); await sleep(300);
  await page.keyboard.type('demo-ui1@example.com', { delay: 15 });
  await page.mouse.click(215, 624); await sleep(300);
  await page.keyboard.type('StrongPass1!', { delay: 15 });
  await page.mouse.click(215, 702); // Sign In
  await sleep(10000);
  await page.screenshot({ path: 'C:/Users/ishan/Desktop/Heallio/.shots/dbg_home.png' });
  // Dump any visible text the framework rendered (Flutter a11y off -> may be empty)
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
