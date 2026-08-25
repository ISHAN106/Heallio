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

  // Pass 1: role choice -> tap Patient -> patient auth
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await sleep(9000);
  await page.screenshot({ path: `${OUT}/01_role_choice.png` });
  console.log('shot 1: role choice');
  await page.mouse.click(215, 444); // Patient card
  await sleep(2500);
  await page.screenshot({ path: `${OUT}/02_patient_auth.png` });
  console.log('shot 2: patient auth');

  // Pass 2: reload to role choice -> tap Doctor -> doctor auth
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await sleep(6000);
  await page.mouse.click(215, 678); // Doctor card
  await sleep(2500);
  await page.screenshot({ path: `${OUT}/03_doctor_auth.png` });
  console.log('shot 3: doctor auth');

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
