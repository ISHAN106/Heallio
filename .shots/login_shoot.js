const puppeteer = require('puppeteer-core');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:5000';
const OUT = 'C:/Users/ishan/Desktop/Heallio/.shots';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox', '--hide-scrollbars'],
    defaultViewport: { width: 430, height: 932, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  });
  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 90000 });
  await sleep(22000); // DDC (web-server) build is slow to become interactive

  // Role choice -> Patient
  await page.mouse.click(215, 444);
  await sleep(4000);

  // Fill login (coords from the patient-auth screenshot, CSS px)
  await page.mouse.click(215, 534); await sleep(600);
  await page.keyboard.type('demo-ui1@example.com', { delay: 25 });
  await page.mouse.click(215, 624); await sleep(600);
  await page.keyboard.type('StrongPass1!', { delay: 25 });
  await sleep(400);
  await page.mouse.click(215, 702); // Sign In
  await sleep(12000);
  await page.screenshot({ path: `${OUT}/10_home.png` });
  console.log('home captured');

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
