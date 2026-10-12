const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright");
const mock = require("./mock.js");
const OUT = process.env.OUT_DIR || require("os").tmpdir();   // ekran görüntüleri repoya değil, buraya yazılır
async function go(name, viewport, phone) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport, isMobile: phone, hasTouch: phone, serviceWorkers: "block", locale: "tr-TR", timezoneId: "Europe/Istanbul" });
  await ctx.route("https://gtu-air-quality.onrender.com/**", r => r.fulfill(mock.handle(r.request().url())));
  await ctx.route(/arcgisonline|ibb\.gov|tile|basemaps|cartocdn/, r => r.abort());
  const p = await ctx.newPage(); await p.goto("http://localhost:8791/index.html"); await p.waitForTimeout(2500);
  const open = async t => { if (phone) await p.click(`#tabbar [data-tab="${t}"]`); else await p.evaluate(t => Shell.openPanel(t), t); await p.waitForTimeout(2500); };
  // Özet: walk months, shoot trend card each
  await open("ozet");
  for (let i = 0; i < 6; i++) {
    const el = await p.$("#ozet-body .oz-trend");
    if (el) { const card = await el.evaluateHandle(e => e.closest(".oz-card")); await card.asElement().screenshot({ path: `${OUT}/${name}-trend${i}.png` }); }
    const prev = await p.$('#ozet-body .oz-month-nav button[aria-label="Önceki ay"]:not([disabled])'); if (!prev) break; await prev.click(); await p.waitForTimeout(300);
  }
  await open("who");
  for (const per of ["all", "2026-10", "2026-09"]) {
    const c = await p.$(`#who-body .who-periods [data-p="${per}"]`); if (!c) continue; await c.click(); await p.waitForTimeout(500);
    await (await p.$("#who-body .wt-grid")).screenshot({ path: `${OUT}/${name}-tiles-${per}.png` });
  }
  const tabs = await p.$$("#who-body table.who-month"); const mt = tabs[tabs.length - 1];
  const sec = await mt.evaluateHandle(e => e.parentElement); await mt.scrollIntoViewIfNeeded();
  await mt.screenshot({ path: `${OUT}/${name}-month.png` });
  const cap = await mt.evaluateHandle(e => e.nextElementSibling); await cap.asElement().screenshot({ path: `${OUT}/${name}-monthcap.png` });
  await p.evaluate(() => document.querySelectorAll("#who-body details").forEach(d => d.open = true));
  const det = await p.$("#who-body details.who-table"); if (det) { await det.scrollIntoViewIfNeeded(); await det.screenshot({ path: `${OUT}/${name}-daily.png` }); }
  const ov = await p.evaluate(() => { const o = []; document.querySelectorAll("#who-body *, #ozet-body *").forEach(e => { if (e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== "visible" ) o.push(e.className + ":" + e.scrollWidth + ">" + e.clientWidth); }); return o.slice(0, 10).concat(["doc " + document.documentElement.scrollWidth + "/" + innerWidth]); });
  console.log(name, "overflow", JSON.stringify(ov));
  // Hakkında › Sınırlılıklar
  await p.evaluate(() => { try { Shell.openPanel("info"); } catch (e) {} });
  await p.waitForTimeout(1500);
  const li = await p.evaluateHandle(() => [...document.querySelectorAll("li")].find(l => l.textContent.includes("PurpleAir'in kendi veri arşivinden")));
  if (li.asElement()) { await li.asElement().evaluate(e => { let d = e.closest("details"); while (d) { d.open = true; d = d.parentElement.closest("details"); } e.scrollIntoView(); }); await p.waitForTimeout(400); await li.asElement().screenshot({ path: `${OUT}/${name}-sinirlilik.png` }).catch(e => console.log("li shot", e.message)); }
  else console.log("no li");
  // playback
  if (phone) await p.click('#tabbar [data-tab="research"]'); else await p.click("#research-btn");
  await p.waitForTimeout(1200);
  await p.evaluate(() => startPlayback(7)); await p.waitForTimeout(4000);
  await p.screenshot({ path: `${OUT}/${name}-playback.png` });
  await b.close();
}
(async () => { await go("d", { width: 1280, height: 800 }, false); await go("m", { width: 390, height: 844 }, true); })();
