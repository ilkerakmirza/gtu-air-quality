// Tanıtım videosu kaydı: node video_kaydet.js short|long
//   short → 1080×1920 (Instagram Reels, LinkedIn), long → 1920×1080 (YouTube)
// Uygulama bir "sahne" sayfasındaki iframe'de açılır; Playwright etkileşimleri yürütür,
// CDP ekran yayını kareleri 30 fps'ye oturtulup ffmpeg ile H.264 MP4'e yazılır (sessiz).
// Müzik: python fon_muzigi.py <süre> muzik.wav [tempo]; birleştirme için README.md.
// Gerekenler: Node + playwright (Chromium), ffmpeg; uygulama http://localhost:8765'te açık olmalı:
//   python -m http.server 8765 --directory frontend_v2
// Varsayılan: ÖRNEK veri + "TASLAK · ÖRNEK VERİ" etiketi. GERCEK=1 → canlı sunucu verisi, etiket yok.
// İsteğe bağlı karekod: bu klasöre qr.png (ör. python -c "import qrcode; qrcode.make('<adres>').save('qr.png')").
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const MODE = process.argv[2] || 'short';
const LONG = MODE === 'long';
const REAL = process.env.GERCEK === '1';
const OUT = path.join(process.env.CIKTI || path.join(__dirname, 'cikti'), `airlab-${MODE}.mp4`);
fs.mkdirSync(path.dirname(OUT), { recursive: true });
const ROOT = path.resolve(__dirname, '../../frontend_v2');
const QR_FILE = path.join(__dirname, 'qr.png');
const QR = fs.existsSync(QR_FILE) ? 'data:image/png;base64,' + fs.readFileSync(QR_FILE).toString('base64') : null;
const LOGO = 'data:image/png;base64,' + fs.readFileSync(path.join(ROOT, 'icons', 'icon-192.png')).toString('base64');

// ── Örnek veri (taslak; yayın sürümü gerçek veriyle kaydedilecek) ─────────────
let seed = 11; const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
const NOW = Date.now();
const hist = [];
for (let d = 75; d >= 0; d--) {
  const base = 5 + rnd() * 17;
  for (let h = 0; h < 24; h++) {
    const t = new Date(NOW - d * 864e5); t.setUTCHours(h, 0, 0, 0);
    if (t.getTime() > NOW) break;
    const trH = (h + 3) % 24;
    const peak = 1 + 0.45 * Math.exp(-((trH - 8.5) ** 2) / 4) + 0.55 * Math.exp(-((trH - 20) ** 2) / 6) - 0.25 * Math.exp(-((trH - 4) ** 2) / 5);
    const v = Math.max(1, base * peak + rnd() * 3 - 1.5);
    hist.push({ recorded_at: t.toUTCString(), pm2_5: +v.toFixed(1), pm10_0: +(v * 1.35 + rnd() * 4).toFixed(1), temperature_c: 17 + rnd() * 6, humidity_pct: 55 + rnd() * 15 });
  }
}
const fc = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'campus.geojson')));
const FIELD = []; let s2 = 3; const r2 = () => (s2 = (s2 * 9301 + 49297) % 233280) / 233280;
fc.features.filter(f => f.properties.cat === 'bina' && f.properties.name).forEach((f, i) => {
  if (i % 3) return;
  const c = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
  const lon = c.reduce((a, p) => a + p[0], 0) / c.length, lat = c.reduce((a, p) => a + p[1], 0) / c.length;
  const base = 6 + r2() * 20, n = i % 2 ? 12 : 45, days = [18, 11, 4].map(d => new Date(NOW - d * 864e5).toISOString());
  for (let k = 0; k < n; k++) {
    const t = new Date(new Date(days[k % 3]).getTime() + Math.floor(k / 3) * 10000);
    FIELD.push({ lat, lon, pm2_5: base + (k % 3 === 2 ? 5 : 0) + r2() * 4 - 2, recorded_at: t.toISOString(), session_id: 1 + (k % 3) });
  }
});
const sessions = [1, 2, 3].map(i => ({ id: i, session_name: `ATP-${i}_` + new Date(NOW - [18, 11, 4][i - 1] * 864e5).toISOString().slice(0, 10),
  reading_count: 120, started_at: new Date(NOW - [18, 11, 4][i - 1] * 864e5).toISOString() }));
const ago = m => new Date(NOW - m * 60000).toISOString();
const latest = { pm2_5: 14.6, pm10_0: 21.3, pm1_0: 9.2, temperature_c: 19.4, humidity_pct: 62, recorded_at: new Date(NOW - 3 * 60000).toUTCString() };
const ATP = [{ device: 'ATP-1', mac: 'a', reading: { pm2_5: 11.2, lat: 40.8098, lon: 29.3581, recorded_at: ago(4) } },
             { device: 'ATP-2', mac: 'b', reading: { pm2_5: 16.9, lat: 40.8131, lon: 29.3549, recorded_at: ago(6) } }];
const CO2 = [{ device: 'CO2-1', location: 'İç mekân sensörü', lat: 40.8075, lon: 29.3605, reading: { co2_ppm: 742, temperature_c: 23.1, humidity_pct: 44, recorded_at: ago(5) } }];

// ── Sahne sayfası ─────────────────────────────────────────────────────────
const W = LONG ? 1280 : 540, H = LONG ? 720 : 960, DPR = LONG ? 1.5 : 2;
const FRAME = LONG ? { x: 0, y: 92, w: 1280, h: 628 } : { x: 0, y: 214, w: 540, h: 746 };
const STAGE = `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<link rel="stylesheet" href="/vendor/fonts/fonts.css">
<style>
*{box-sizing:border-box;margin:0}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:#0a101d;color:#e8ecf4;font-family:Inter,system-ui,sans-serif}
#cap{position:absolute;pointer-events:none;${LONG ? 'left:36px;right:300px;top:0;height:92px;display:flex;flex-direction:column;justify-content:center' : 'left:22px;right:22px;top:58px;height:150px;display:block'};transition:opacity .45s}
#cap h2{font-family:"Source Serif 4",serif;font-weight:600;font-size:${LONG ? 27 : 23}px;line-height:1.2;letter-spacing:-.005em}
#cap p{margin-top:${LONG ? 4 : 5}px;font-size:${LONG ? 14.5 : 13.5}px;line-height:1.45;color:#aeb8cc}
#cap h2 b{color:#7ea2ff;font-weight:600}
#cap p:empty{display:none}
#cap .ex{margin-top:11px;font-size:18.5px;line-height:1.45;font-weight:650;color:#fff;transition:opacity .3s}
#cap .ex mark{background:#f5b840;color:#101521;padding:0 .22em;border-radius:5px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
#appwrap{position:absolute;left:${FRAME.x}px;top:${FRAME.y}px;width:${FRAME.w}px;height:${FRAME.h}px;overflow:hidden;border-top:1px solid rgba(160,180,220,.14)}
#app{position:absolute;inset:0;width:100%;height:100%;border:0;background:#0a101d;transition:transform .85s cubic-bezier(.4,0,.2,1)}
#brand{position:absolute;${LONG ? 'right:30px;top:0;height:92px' : 'left:22px;top:14px;height:30px'};display:flex;align-items:center;gap:10px;font-size:12px;color:#8b96ab}
#brand img{width:${LONG ? 34 : 26}px;height:${LONG ? 34 : 26}px;border-radius:8px}
#brand b{font-family:"Source Serif 4",serif;font-size:${LONG ? 18 : 13}px;color:#e8ecf4;font-weight:600}
#brand b i{font-style:normal;color:#f5a623}
#draft{position:absolute;${LONG ? 'left:36px;bottom:10px' : 'right:16px;top:19px;font-size:9.5px'};z-index:20;font-size:10.5px;font-weight:600;letter-spacing:.04em;color:#f5b840;
  padding:3px 8px;border:1px solid rgba(245,184,64,.45);border-radius:99px;background:rgba(10,16,29,.85)}
#sub{position:absolute;pointer-events:none;left:${LONG ? '445px' : '50%'};${LONG ? 'bottom:40px;max-width:820px;font-size:26px' : 'bottom:206px;max-width:470px;font-size:23px'};z-index:8;transform:translate(-50%,8px) scale(.97);
  width:max-content;text-align:center;font-weight:700;line-height:1.38;color:#fff;padding:${LONG ? '10px 22px' : '10px 16px'};border-radius:12px;
  background:rgba(8,12,22,.86);box-shadow:0 8px 28px rgba(0,0,0,.45);opacity:0;transition:opacity .28s,transform .28s}
#sub.on{opacity:1;transform:translate(-50%,0) scale(1)}
#sub mark{background:#f5b840;color:#101521;padding:0 .22em;border-radius:5px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
#card{position:absolute;inset:0;z-index:10;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;
  padding:0 ${LONG ? 160 : 40}px;background:#0a101d;opacity:0;pointer-events:none;transition:opacity .6s}
#card.on{opacity:1}
#card .logo{width:${LONG ? 96 : 104}px;height:${LONG ? 96 : 104}px;border-radius:24px;margin-bottom:22px}
#card h1{font-family:"Source Serif 4",serif;font-weight:600;font-size:${LONG ? 54 : 46}px;line-height:1.12}
#card h1 i{font-style:normal;color:#f5a623}
#card h3{font-family:"Source Serif 4",serif;font-weight:600;font-size:${LONG ? 38 : 36}px;line-height:1.2;margin-bottom:22px}
#card .sub{margin-top:14px;font-size:${LONG ? 19 : 18}px;line-height:1.5;color:#aeb8cc}
#card .rule{width:56px;height:3px;background:#5b8def;border-radius:2px;margin:22px auto}
#card ul{list-style:none;padding:0;text-align:left;max-width:${LONG ? 860 : 440}px}
#card li{display:flex;gap:16px;align-items:flex-start;padding:${LONG ? 11 : 12}px 0;border-bottom:1px solid rgba(160,180,220,.11);font-size:${LONG ? 19 : 17.5}px;line-height:1.45;color:#d7dce6}
#card li:last-child{border-bottom:0}
#card li b{color:#fff;font-weight:650}
#card li span.n{flex-shrink:0;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:14px;font-weight:700;color:#a9c0ff;background:rgba(91,141,239,.16);border:1px solid rgba(91,141,239,.45)}
#card .cmp{display:grid;gap:14px;width:100%;max-width:${LONG ? 980 : 470}px;grid-template-columns:${LONG ? '1fr 1fr' : '1fr'};text-align:left}
#card .cmp section{padding:16px 18px;border:1px solid rgba(160,180,220,.16);border-radius:14px;background:#0f1726}
#card .cmp h4{font-family:"Source Serif 4",serif;font-size:${LONG ? 23 : 21}px;font-weight:600;margin-bottom:2px}
#card .cmp .dev{font-size:13.5px;color:#8fa7d8;margin-bottom:10px}
#card .cmp dl{display:grid;grid-template-columns:82px 1fr;gap:6px 10px;font-size:${LONG ? 16 : 15}px;line-height:1.42;color:#d7dce6}
#card .cmp dt{color:#8b96ab;font-weight:600}
#card .note{margin-top:16px;max-width:${LONG ? 980 : 470}px;font-size:13.5px;line-height:1.5;color:#8b96ab;text-align:left}
#card h2.t{font-family:"Source Serif 4",serif;font-weight:600;font-size:${LONG ? 34 : 29}px;line-height:1.22;max-width:${LONG ? 900 : 470}px}
#card .qr{width:${LONG ? 190 : 210}px;height:${LONG ? 190 : 210}px;border-radius:14px;background:#fff;padding:10px;margin-top:26px}
#card .small{margin-top:16px;font-size:14px;color:#8b96ab}
</style></head><body>
<div id="cap"><h2></h2><p></p>${LONG ? '' : '<div class="ex"></div>'}</div>
<div id="brand"><img src="${LOGO}" alt=""><span><b>GTÜ <i>Air</i>Lab</b>${LONG ? '<br>Kampüs Hava Kalitesi Laboratuvarı' : ''}</span></div>
${REAL ? '' : '<div id="draft">TASLAK · ÖRNEK VERİ</div>'}
<div id="appwrap"><iframe id="app" name="app"></iframe></div>
<div id="sub"></div>
<div id="card"></div>
<script>
window.cap = (h, p) => { const c = document.getElementById('cap'); c.style.opacity = 0;
  setTimeout(() => { c.querySelector('h2').innerHTML = h; c.querySelector('p').innerHTML = p || ''; c.style.opacity = 1; }, 380); };
window.sub = ${LONG ? `html => { const e = document.getElementById('sub'); e.classList.remove('on');
  if (html) setTimeout(() => { e.innerHTML = html; e.classList.add('on'); }, 230); }` : `html => { const e = document.querySelector('#cap .ex'); e.style.opacity = 0;
  setTimeout(() => { e.innerHTML = html || ''; e.style.opacity = 1; }, 300); }`};
// "Kamera": uygulama görüntüsünde bir noktaya yakınlaş / geri çekil
window.zoomTo = (x, y, k) => { const a = document.getElementById('app');
  if (k) { a.style.transformOrigin = x + 'px ' + y + 'px'; a.style.transform = 'scale(' + k + ')'; } else a.style.transform = ''; };
window.card = html => { const c = document.getElementById('card'); if (html) { c.innerHTML = html; c.classList.add('on'); } else c.classList.remove('on'); };
</script></body></html>`;

// ── Kayıt ─────────────────────────────────────────────────────────────────
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR, serviceWorkers: 'block', locale: 'tr-TR', timezoneId: 'Europe/Istanbul' });
  await ctx.addInitScript(() => {
    try { localStorage.setItem('gtu.install.dismissed', 'true'); localStorage.removeItem('gtu.view.research'); } catch (_) {}
    if (window.top === window) return;
    // Dokunma izi: tıklanan yerde kısa bir halka
    window.__tap = (x, y) => {
      const d = document.createElement('div');
      d.style.cssText = `position:fixed;left:${x - 22}px;top:${y - 22}px;width:44px;height:44px;border-radius:50%;z-index:99999;pointer-events:none;
        border:3px solid rgba(255,255,255,.9);background:rgba(126,162,255,.28);transform:scale(.4);opacity:1;transition:transform .45s ease-out,opacity .55s ease-out`;
      document.body.appendChild(d); requestAnimationFrame(() => { d.style.transform = 'scale(1.25)'; d.style.opacity = '0'; });
      setTimeout(() => d.remove(), 700);
    };
    addEventListener('pointerdown', e => { if (e.isTrusted) window.__tap(e.clientX, e.clientY); }, true);
  });
  if (!REAL) await ctx.route(/arcgisonline|cartocdn|ibb\.gov\.tr|openstreetmap/, r => r.abort());
  await ctx.route('http://localhost:8765/__stage.html', r => r.fulfill({ contentType: 'text/html; charset=utf-8', body: STAGE }));
  if (!REAL) await ctx.route('https://gtu-air-quality.onrender.com/**', r => {
    const u = r.request().url(); let body = { data: [] };
    if (u.includes('/purpleair/history')) body = { data: hist, count: hist.length };
    else if (u.includes('/purpleair/latest')) body = { data: latest };
    else if (u.includes('/purpleair/status')) body = { success: true, error: null };
    else if (u.includes('/api/map/tracks')) body = { tracks: [{ session_name: 'Saha', points: FIELD }] };
    else if (u.includes('/readings')) { const id = +u.match(/sessions\/(\d+)/)?.[1]; body = { data: FIELD.filter(x => x.session_id === id).map(x => ({ ...x, latitude: x.lat, longitude: x.lon })) }; }
    else if (u.includes('/api/sessions')) body = { data: sessions };
    else if (u.includes('/atmotube/live')) body = { data: ATP };
    else if (u.includes('/co2/live')) body = { data: CO2 };
    else if (u.includes('/csb/latest') || u.includes('/ibb/latest')) body = { data: { station_name: 'İstanbul - Tuzla', pm2_5: 18.2, pm10: 31, pm10_0: 31, lat: 40.843, lon: 29.30, distance_km: 6.4, recorded_at: ago(40), source: 'ibb' } };
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto('http://localhost:8765/__stage.html');
  await page.evaluate(() => { document.getElementById('app').src = '/index.html'; });
  await page.waitForTimeout(800);
  const app = page.frame({ name: 'app' });
  await page.waitForTimeout(6500);   // açılış ekranı ve veriler
  const F = () => page.frame({ name: 'app' });

  // ffmpeg: kareler sabit 30 fps'ye oturtulur
  const OW = Math.round(W * DPR), OH = Math.round(H * DPR);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', '30', '-i', '-',
    '-vf', `scale=${OW}:${OH}:flags=lanczos,format=yuv420p`, '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-movflags', '+faststart', OUT], { stdio: ['pipe', 'inherit', 'inherit'] });
  const cdp = await ctx.newCDPSession(page);
  let last = null, lastT = null, written = 0;
  const write = buf => new Promise(res => ff.stdin.write(buf) ? res() : ff.stdin.once('drain', res));
  let chain = Promise.resolve();
  const push = (buf, t) => {
    chain = chain.then(async () => {
      if (last) { const n = Math.max(0, Math.round((t - lastT) * 30)); for (let i = 0; i < n; i++) { await write(last); written++; } if (n) lastT += n / 30; }
      else lastT = t;
      last = buf;
    });
  };
  cdp.on('Page.screencastFrame', f => { push(Buffer.from(f.data, 'base64'), f.metadata.timestamp); cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {}); });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: OW, maxHeight: OH, everyNthFrame: 1 });
  // Yayın yalnızca ekran değişince kare yollar; sabit sahnelerde de zaman ilerlesin diye görünmez bir nokta yanıp söner
  await page.evaluate(() => { const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:0;top:0;width:1px;height:1px;z-index:99;background:#0a101d';
    document.body.appendChild(d); let k = 0; setInterval(() => { d.style.background = (k++ % 2) ? '#0a101d' : '#0b111e'; }, 33); });

  const wait = ms => page.waitForTimeout(ms);
  // Yeni sahne başlığı gelince önceki altyazı da kalkar
  const cap = (h, p) => page.evaluate(([h, p]) => { window.sub(null); window.cap(h, p); }, [h, p]);
  const card = html => page.evaluate(h => window.card(h), html);
  const sub = html => page.evaluate(h => window.sub(h), html);
  const click = async (sel, pause = 900) => { await F().click(sel); await wait(pause); };
  // Kamera öğeye yakınlaşır, dokunma izi görünür, öğe açılır, kamera geri çekilir
  const focusTap = async (sel, k = 1.9, hold = 900) => {
    const c = await F().evaluate(sel => { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, sel);
    await page.evaluate(([x, y, k]) => window.zoomTo(x, y, k), [c.x, c.y, k]); await wait(hold);
    await F().evaluate(([sel, x, y]) => { window.__tap(x, y); document.querySelector(sel).click(); }, [sel, c.x, c.y]); await wait(650);
    await page.evaluate(() => window.zoomTo()); await wait(900);
  };
  const scroll = async (sel, px, ms) => {
    const steps = Math.max(1, Math.round(ms / 40));
    for (let i = 0; i < steps; i++) { await F().evaluate(([s, d]) => { const e = document.querySelector(s); if (e) e.scrollTop += d; }, [sel, px / steps]); await wait(40); }
  };
  const toChart = () => F().evaluate(() => { const b = document.getElementById('exp-body'), c = document.querySelector('#exp-body .cb-chart');
    if (c) b.scrollTo({ top: b.scrollTop + c.getBoundingClientRect().top - b.getBoundingClientRect().top - 70, behavior: 'smooth' }); });
  const chat = async (pause) => {
    const a = (s) => click(`.cb-ask ${s}`, pause);
    await a('[data-a=saat][data-v="540"]');
    await a('[data-a=etkinlik][data-v=ders]');
    await F().selectOption('#cb-bld', { index: 1 }); await wait(pause * 0.6); await a('[data-a=yer]');
    await a('[data-a=hava][data-v=closed]');
    await a('[data-a=sure][data-v="180"]');
    await a('[data-a=devam][data-v=ekle]');
    await a('[data-a=etkinlik][data-v=yurume]');
    await a('[data-a=yer]');
    await a('[data-a=sure][data-v="60"]');
    await a('[data-a=devam][data-v=bitti]');
  };
  const LOGO_IMG = `<img class="logo" src="${LOGO}" alt="">`;
  const OUTRO = `${LOGO_IMG}<h1>GTÜ <i>Air</i>Lab</h1><div class="sub">Kampüs Hava Kalitesi Laboratuvarı<br>Gebze Teknik Üniversitesi</div>
    ${QR ? `<img class="qr" src="${QR}" alt="">` : ''}<div class="small">Tarayıcıda açın · telefonunuza uygulama olarak kurabilirsiniz</div>`;

  const CMP = `<h3>Sabit ve taşınabilir sensörler</h3><div class="cmp">
      <section><h4>Sabit sensör</h4><div class="dev">PurpleAir PA-II · SÜMER Laboratuvarı çatısı</div>
        <dl><dt>Ölçüm</dt><dd>Sürekli; 2 dakikalık zaman çözünürlüğü</dd><dt>Amaç</dt><dd>Kampüsün genel (dış ortam) hava kalitesi; zamansal değişim ve WHO kılavuz değeriyle karşılaştırma</dd></dl></section>
      <section><h4>Taşınabilir sensörler</h4><div class="dev">Atmotube Pro (5 cihaz) · GPS konumlu</div>
        <dl><dt>Ölçüm</dt><dd>Planlı saha yürüyüşleri; kısa süreli, konumlu</dd><dt>Amaç</dt><dd>Bina bazlı karakterizasyon; binalar arası farkların kampüs saha ortalamasına göre belirlenmesi</dd></dl></section></div>
    <div class="note">Her iki sensör türü de düşük maliyetli optik sensördür; değerler ham ölçümdür (nem düzeltmesi uygulanmamıştır).</div>`;
  if (!LONG) {
    // ── Kısa sürüm (≈60 sn, 9:16): açıklamalar üst bantta, uygulama görüntüsü kesintisiz ──
    await card(`${LOGO_IMG}<h1>GTÜ <i>Air</i>Lab</h1><div class="sub">Kampüs Hava Kalitesi Laboratuvarı<br>Gebze Teknik Üniversitesi</div>`);
    await wait(3200);
    // Ana ekran (Özet)
    await cap('Anlık hava kalitesi');
    await card(null); await wait(400);
    await sub('Sabit sensör: <mark>kampüsün genel hava kalitesi</mark>, Ulusal Hava Kalitesi İndeksi (HKİ) ile'); await wait(3600);
    await scroll('#ozet-body', 300, 1800);
    await sub('Genel nüfus ve hassas gruplar için <mark>öneriler</mark>; veri kaynağı ve ölçüm zamanı belirtilir'); await wait(2600);
    // Sensör türleri
    await card(CMP); await wait(1000);
    await F().evaluate(() => document.getElementById('ozet-body').scrollTop = 0);
    await click('#tabbar [data-tab=map]', 300);
    await wait(8300);
    // Ölçüm ağı
    await cap('Ölçüm ağı');
    await card(null); await wait(400);
    await F().evaluate(() => { map.flyTo([40.8100, 29.3578], 16.4, { duration: 2.4 }); });
    await sub('Sabit sensör (PurpleAir PA-II, SÜMER çatısı): <mark>kampüs genel hava kalitesi</mark>'); await wait(3200);
    await sub('Taşınabilir sensörler (Atmotube Pro, GPS): <mark>bina bazlı karakterizasyon</mark>'); await wait(3000);
    // Mekânsal sonuçlar
    await cap('Bina bazlı karakterizasyon');
    await click('#tabbar [data-tab=research]', 600);
    await click('#research-switch [data-sub=field]', 700);
    await sub('Saha ölçümlerinden <mark>bina ölçekli PM₂.₅ ortalamaları</mark> (µg/m³)');
    await click('#sel-all', 500);
    await focusTap('.vs-btn[data-view=avg]', 1.6, 800);
    await sub('Binalar <mark>kampüs saha ortalamasına</mark> göre sıralanır'); await wait(2400);
    await click('#map-cta', 900);
    await F().evaluate(() => { map.flyTo([40.8112, 29.3566], 16.3, { duration: 2.2 }); });
    await sub('Bina ortalamaları <mark>harita üzerinde</mark>'); await wait(2800);
    await sub('Kısa süreli ölçümler <mark>WHO 24 saatlik değeriyle karşılaştırılmaz</mark>'); await wait(3000);
    // WHO karşılaştırması
    await cap('WHO (2021) kılavuz değeriyle karşılaştırma');
    await click('#tabbar [data-tab=who]', 900);
    await sub('Kampüs genel hava kalitesi (sabit sensör) · 24 saatlik kılavuz değer <mark>15 µg/m³</mark>'); await wait(3000);
    await scroll('#who-body', 190, 1300);
    await sub('Kılavuz değeri aşan günler <mark>ayrı renkte</mark> gösterilir'); await wait(3000);
    await scroll('#who-body', 120, 1200);
    await sub('Yıllık kılavuz değer: <mark>5 µg/m³</mark>'); await wait(3000);
    // Kişisel maruziyet
    await cap('Kişisel maruziyet tahmini');
    await click('#tabbar [data-tab=map]', 700);
    await sub('Kampüste geçirilen zamana göre <mark>solunan PM₂.₅ miktarı</mark>');
    await focusTap('#exp-fab', 2.0, 1300);
    await sub('Girdiler: saat, etkinlik, bina, havalandırma ve süre · <mark>bilgiler cihazdan çıkmaz</mark>');
    await chat(430);
    await wait(300); await toChart();
    await sub('Solunan miktar = derişim × <mark>solunum hızı</mark> × süre'); await wait(3200);
    await sub('Solunum hızları: <mark>US EPA (2011)</mark>'); await wait(2400);
    await card(`${LOGO_IMG}<h1>GTÜ <i>Air</i>Lab</h1><div class="sub">Kampüs Hava Kalitesi Laboratuvarı<br>Gebze Teknik Üniversitesi</div>
      ${QR ? `<img class="qr" src="${QR}" alt="">` : ''}<div class="small">Yöntem, eşik değerler ve kaynaklar uygulamanın “Hakkında” bölümündedir.</div>`);
    await wait(5500);
  } else {
    // ── Tanıtım (≈2,5 dk, 16:9) ──
    await card(`${LOGO_IMG}<h1>GTÜ <i>Air</i>Lab</h1><div class="sub">Kampüs Hava Kalitesi Laboratuvarı · Gebze Teknik Üniversitesi</div>
      <div class="rule"></div><div class="sub" style="margin-top:0">Kampüs ölçekli ince partikül madde (PM₂.₅) izleme ve açık veri paylaşımı</div>`);
    await wait(6500);
    await card(`<h3>Neden ölçüyoruz?</h3><ul>
      <li><span class="n">1</span><span><b>PM₂.₅</b>, çapı 2,5 mikrometreden küçük parçacıklardır; solunum yollarının derinlerine ulaşabilir.</span></li>
      <li><span class="n">2</span><span>Dünya Sağlık Örgütü (WHO, 2021) kılavuzu: <b>24 saatlik ortalama 15 µg/m³</b>, yıllık ortalama 5 µg/m³.</span></li>
      <li><span class="n">3</span><span>Amaç: kampüs içindeki <b>zamansal ve mekânsal değişkenliği</b> ölçmek ve sonuçları yöntemiyle birlikte paylaşmak.</span></li></ul>`);
    await wait(10500);
    await card(CMP);
    await wait(10000);
    await cap('Anlık durum', 'Ulusal Hava Kalitesi İndeksi (HKİ) ile sınıflandırma · veri kaynağı ve ölçüm zamanı belirtilir');
    await card(null); await wait(600);
    await sub('Sabit hava kalitesi sensörünün son ölçümü, <mark>Ulusal Hava Kalitesi İndeksi</mark> ile'); await wait(3300);
    await sub('Altı sınıf: <mark>İyi, Orta, Hassas, Sağlıksız, Kötü, Tehlikeli</mark>'); await wait(3200);
    await sub('Genel nüfus ve hassas gruplar için <mark>öneriler</mark>');
    await scroll('#ozet-body', 520, 3500); await wait(2500);
    await sub('Aylık özet: <mark>kılavuz değeri aşan gün sayısı</mark>');
    await scroll('#ozet-body', 520, 3500); await wait(3000);
    await cap('Ölçüm ağı', 'Sabit sensör ve taşınabilir cihazların konumları; bina adına göre arama');
    await sub('Kuzey ve Güney kampüs, <mark>bina ölçeğinde</mark>');
    await click('#ozet-close', 900);
    await F().evaluate(() => { map.flyTo([40.8105, 29.3575], 16.6, { duration: 2.5 }); }); await wait(4200);
    await sub('Sabit sensör ve <mark>taşınabilir cihazlar</mark> aynı haritada');
    await F().evaluate(() => { map.flyTo([40.8114, 29.3563], 15.6, { duration: 2 }); }); await wait(3200);
    await cap('WHO (2021) kılavuz değeriyle karşılaştırma', 'Sabit sensörün günlük ortalamaları · kısa süreli saha ölçümleri 24 saatlik değerle karşılaştırılmaz');
    await sub('WHO 24 saatlik kılavuz değeri <mark>15 µg/m³</mark>, yıllık <mark>5 µg/m³</mark>');
    await click('#who-btn', 4500);
    await sub('Kılavuz değeri aşan günler <mark>ayrı renkte</mark> gösterilir');
    await scroll('#who-body', 600, 4000); await wait(3500);
    await cap('Kişisel maruziyet tahmini', 'Zaman, konum ve etkinlik bilgisinden solunan PM₂.₅ miktarı (µg) · girilen bilgiler cihazdan çıkmaz');
    await click('#who-close', 900);
    await sub('Haritadaki <mark>yuvarlak düğme</mark> maruziyet asistanını açar');
    await click('#exp-fab', 1800);
    await sub('Girdiler: saat, etkinlik, bina, <mark>havalandırma</mark> ve süre');
    await chat(1150);
    await sub('Solunan miktar = derişim × <mark>solunum hızı (US EPA, 2011)</mark> × süre');
    await wait(600); await toChart(); await wait(4200);
    await sub('Sonuçla birlikte <mark>varsayımlar ve sınırlılıklar</mark>'); await scroll('#exp-body', 420, 2500); await wait(4000);
    await cap('Yöntem ve sınır değerler', 'HKİ kesim noktaları; WHO (2021), Türkiye ve AB (2030) değerleri; sınırlılıklar ve kaynaklar');
    await click('#exp-close', 700);
    await click('#info-btn', 1500);
    await sub('Her eşik ve hesap <mark>kaynağıyla birlikte</mark> belirtilir');
    await F().evaluate(() => document.getElementById('inf-sinir').scrollIntoView({ behavior: 'smooth', block: 'start' })); await wait(4500);
    await scroll('#info-body', 380, 3000); await wait(2500);
    await cap('Araştırma görünümü', 'Sensör panelleri, saha ölçüm oturumları ve bina ortalamaları');
    await click('#info-close', 700);
    await sub('Teknik ayrıntılar <mark>Araştırma görünümünde</mark>');
    await click('#research-btn', 4500);
    await sub('Canlı sensörler ve <mark>saha ölçüm oturumları</mark>'); await wait(5000);
    await cap('Duyurular', 'Sensör kesintisi ve HKİ “Hassas” üzeri durumlarda otomatik bilgilendirme');
    await click('#research-btn', 800);
    await sub('Sensör kesintisi ve yüksek derişimde <mark>otomatik duyuru</mark>');
    await click('#news-btn', 6500);
    await sub(null);
    await card(`<h3>Gizlilik</h3><ul>
      <li><span class="n">1</span><span>Üyelik, çerez, reklam ya da izleme aracı <b>yoktur</b>.</span></li>
      <li><span class="n">2</span><span>Asistana girilen bilgiler <b>cihazınızdan çıkmaz</b>.</span></li>
      <li><span class="n">3</span><span>Saha ekibinin kimliği gösterilmez; kampüs dışındaki konumlar yayımlanmaz.</span></li></ul>`);
    await wait(8500);
    await card(OUTRO); await wait(7500);
  }

  await cdp.send('Page.stopScreencast');
  await chain;
  if (last) for (let i = 0; i < 15; i++) { await write(last); written++; }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log(MODE, 'kare:', written, 'süre:', (written / 30).toFixed(1), 'sn', '→', OUT);
  console.log(errs.join('\n') || 'JS hatası yok');
  await b.close();
})();
