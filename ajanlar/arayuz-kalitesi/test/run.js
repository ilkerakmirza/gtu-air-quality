const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright");
const mock = require("./mock.js");
const OUT = process.env.OUT_DIR || require("os").tmpdir();   // ekran görüntüleri repoya değil, buraya yazılır
const BAD = /\bNaN\b|undefined|\bnull\b|Infinity/;

async function scan(page, sel, tag, log) {
  const txt = await page.evaluate(s => { const el = document.querySelector(s); return el ? el.innerText : "(yok: " + s + ")"; }, sel);
  const hits = txt.split("\n").filter(l => BAD.test(l));
  log.push(`[${tag}] ${sel}: ${hits.length ? "BAD TEXT -> " + hits.join(" | ") : "ok"}`);
  return txt;
}

async function run(name, viewport, phone) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport, serviceWorkers: "block", locale: "tr-TR", timezoneId: "Europe/Istanbul",
                                         isMobile: phone, hasTouch: phone });
  const log = [], reqs = [];
  await ctx.route("https://gtu-air-quality.onrender.com/**", async r => {
    const res = mock.handle(r.request().url());
    reqs.push(`${r.request().url().replace("https://gtu-air-quality.onrender.com", "")} -> ${res.body.length} B`);
    await r.fulfill(res);
  });
  await ctx.route(/havakalitesi\.ibb\.gov\.tr/, r => r.abort());
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error" || m.type() === "warning") log.push(`console.${m.type()}: ${m.text()}`); });
  page.on("pageerror", e => log.push(`PAGEERROR: ${e.message}`));
  await page.goto("http://localhost:8791/index.html", { waitUntil: "load" });
  await page.waitForTimeout(2500);

  const texts = {};
  // Özet
  if (phone) await page.click('#tabbar [data-tab="ozet"]'); else await page.evaluate(() => Shell.openPanel("ozet"));
  await page.waitForTimeout(2500);
  texts.ozet = await scan(page, "#ozet-body", name, log);
  await page.screenshot({ path: `${OUT}/${name}-ozet.png`, fullPage: false });
  // walk all months in Özet
  for (let i = 0; i < 8; i++) {
    const prev = await page.$('#ozet-body .oz-month-nav button[aria-label="Önceki ay"]:not([disabled])');
    if (!prev) break;
    await prev.click(); await page.waitForTimeout(200);
    const t = await scan(page, "#ozet-body", name + " ozet-month" + i, log);
    texts["ozet_m" + i] = t.split("Aylık özet")[1]?.slice(0, 600);
  }

  // Sağlık (WHO)
  if (phone) await page.click('#tabbar [data-tab="who"]'); else await page.evaluate(() => Shell.openPanel("who"));
  await page.waitForTimeout(3000);
  await page.evaluate(() => document.querySelectorAll("#who-body details").forEach(d => d.open = true));
  texts.who = await scan(page, "#who-body", name, log);
  await page.screenshot({ path: `${OUT}/${name}-who.png`, fullPage: false });
  const chips = await page.$$eval("#who-body .who-periods [data-p]", b => b.map(x => x.dataset.p));
  texts.who_periods = {};
  for (const p of chips) {
    await page.click(`#who-body .who-periods [data-p="${p}"]`); await page.waitForTimeout(400);
    await page.evaluate(() => document.querySelectorAll("#who-body details").forEach(d => d.open = true));
    const t = await scan(page, "#who-body", `${name} who:${p}`, log);
    const tiles = await page.$$eval("#who-body .wt", els => els.map(e => e.innerText.replace(/\n/g, " ")));
    texts.who_periods[p] = tiles;
  }
  texts.who_month_table = await page.$$eval("#who-body table.who-month", ts => ts.map(t => t.innerText));

  // Araştırma
  if (phone) await page.click('#tabbar [data-tab="research"]'); else await page.click("#research-btn");
  await page.waitForTimeout(1500);
  texts.sidebar = await scan(page, ".sidebar", name, log);
  await page.screenshot({ path: `${OUT}/${name}-research.png`, fullPage: false });
  // Playback of the 28 Apr session (raw PurpleAir day)
  await page.evaluate(() => startPlayback(7));
  await page.waitForTimeout(4000);
  texts.player = await scan(page, "#player-dock", name + " playback", log);
  texts.paPanelDuringPlayback = await page.evaluate(() => ["pa-pm25", "pa-cat", "pa-raw", "pa-pm10", "pa-temp", "pa-hum", "pa-time"]
    .map(id => id + "=" + document.getElementById(id)?.textContent).join(" | "));
  // sample the PA panel across several steps to see flicker
  const samples = [];
  for (let i = 0; i < 12; i++) {
    samples.push(await page.evaluate(() => ["pl-time", "pl-pa", "pa-pm10", "pa-temp"].map(id => document.getElementById(id)?.textContent).join(" ")));
    await page.waitForTimeout(350);
  }
  texts.playbackSamples = samples;
  texts.cmpChart = await page.evaluate(() => cmpChart ? cmpChart.data.datasets.map(d => `${d.label}: n=${d.data.length}, nulls=${d.data.filter(v => v == null).length}, NaN=${d.data.filter(v => v != null && isNaN(v)).length}`) : "no chart");
  await page.screenshot({ path: `${OUT}/${name}-playback.png`, fullPage: false });

  // Maruziyet (exp)
  await page.evaluate(() => Shell.openPanel("exp"));
  await page.waitForTimeout(2000);
  texts.exp = (await scan(page, "#exp-body", name, log)).slice(0, 400);

  // Duyurular (statusNotices)
  await page.evaluate(() => Shell.openPanel("news"));
  await page.waitForTimeout(1500);
  await scan(page, "#news-dock", name, log);

  await browser.close();
  return { name, log, reqs, texts };
}

(async () => {
  const res = [];
  res.push(await run("desktop", { width: 1280, height: 800 }, false));
  res.push(await run("phone", { width: 390, height: 844 }, true));
  require("fs").writeFileSync(`${OUT}/result.json`, JSON.stringify(res, null, 1));
  for (const r of res) {
    console.log("=====", r.name);
    console.log(r.log.join("\n"));
    console.log("-- requests:\n" + [...new Set(r.reqs)].join("\n"));
  }
})();
