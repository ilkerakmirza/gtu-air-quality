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
const FRAME = LONG ? { x: 0, y: 92, w: 1280, h: 628 } : { x: 90, y: 196, w: 360, h: 720 };
const STAGE = `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<link rel="stylesheet" href="/vendor/fonts/fonts.css">
<style>
*{box-sizing:border-box;margin:0}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:#0a101d;color:#e8ecf4;font-family:Inter,system-ui,sans-serif}
#cap{position:absolute;pointer-events:none;${LONG ? 'left:36px;right:300px;top:0;height:92px;display:flex;flex-direction:column;justify-content:center' : 'left:30px;right:30px;top:34px;height:150px'};transition:opacity .45s}
#cap h2{font-family:"Source Serif 4",serif;font-weight:600;font-size:${LONG ? 27 : 31}px;line-height:1.18;letter-spacing:-.005em}
#cap p{margin-top:${LONG ? 4 : 10}px;font-size:${LONG ? 14.5 : 16.5}px;line-height:1.45;color:#aeb8cc}
#cap h2 b{color:#7ea2ff;font-weight:600}
#app{position:absolute;left:${FRAME.x}px;top:${FRAME.y}px;width:${FRAME.w}px;height:${FRAME.h}px;border:0;background:#0a101d;
  ${LONG ? 'border-top:1px solid rgba(160,180,220,.14)' : 'border-radius:30px;box-shadow:0 0 0 7px #182235,0 0 0 8px rgba(160,180,220,.18),0 24px 60px rgba(0,0,0,.5)'}}
#brand{position:absolute;${LONG ? 'right:30px;top:0;height:92px' : 'left:0;right:0;bottom:8px;justify-content:center'};display:flex;align-items:center;gap:10px;font-size:12px;color:#8b96ab}
#brand img{width:${LONG ? 34 : 22}px;height:${LONG ? 34 : 22}px;border-radius:8px}
#brand b{font-family:"Source Serif 4",serif;font-size:${LONG ? 18 : 14}px;color:#e8ecf4;font-weight:600}
#brand b i{font-style:normal;color:#f5a623}
#draft{position:absolute;${LONG ? 'left:36px;bottom:10px' : 'right:16px;top:8px'};z-index:20;font-size:10.5px;font-weight:600;letter-spacing:.04em;color:#f5b840;
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
#card .qr{width:${LONG ? 190 : 210}px;height:${LONG ? 190 : 210}px;border-radius:14px;background:#fff;padding:10px;margin-top:26px}
#card .small{margin-top:16px;font-size:14px;color:#8b96ab}
</style></head><body>
<div id="cap"><h2></h2><p></p></div>
<div id="brand"><img src="${LOGO}" alt=""><span><b>GTÜ <i>Air</i>Lab</b>${LONG ? '<br>Kampüs Hava Kalitesi Laboratuvarı' : ''}</span></div>
${REAL ? '' : '<div id="draft">TASLAK · ÖRNEK VERİ</div>'}
<iframe id="app" name="app"></iframe>
<div id="sub"></div>
<div id="card"></div>
<script>
window.cap = (h, p) => { const c = document.getElementById('cap'); c.style.opacity = 0;
  setTimeout(() => { c.querySelector('h2').innerHTML = h; c.querySelector('p').innerHTML = p || ''; c.style.opacity = 1; }, 380); };
window.sub = html => { const e = document.getElementById('sub'); e.classList.remove('on');
  if (html) setTimeout(() => { e.innerHTML = html; e.classList.add('on'); }, 230); };
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
    addEventListener('pointerdown', e => {
      const d = document.createElement('div');
      d.style.cssText = `position:fixed;left:${e.clientX - 22}px;top:${e.clientY - 22}px;width:44px;height:44px;border-radius:50%;z-index:99999;pointer-events:none;
        border:3px solid rgba(255,255,255,.9);background:rgba(126,162,255,.28);transform:scale(.4);opacity:1;transition:transform .45s ease-out,opacity .55s ease-out`;
      document.body.appendChild(d); requestAnimationFrame(() => { d.style.transform = 'scale(1.25)'; d.style.opacity = '0'; });
      setTimeout(() => d.remove(), 700);
    }, true);
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
  const cap = (h, p) => page.evaluate(([h, p]) => window.cap(h, p), [h, p]);
  const card = html => page.evaluate(h => window.card(h), html);
  const sub = html => page.evaluate(h => window.sub(h), html);
  const click = async (sel, pause = 900) => { await F().click(sel); await wait(pause); };
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

  if (!LONG) {
    // ── Shorts (≈35 sn, 9:16) ──
    await card(`${LOGO_IMG}<h1 style="font-size:40px">Kampüste soluduğun<br>hava şu an nasıl?</h1><div class="rule"></div><div class="sub">GTÜ AirLab · canlı ölçüm</div>`);
    await wait(3600);
    await cap('Şu an kampüste', 'Ulusal Hava Kalitesi İndeksi (HKİ) ve PM₂.₅ · ölçüm zamanı ve kaynağıyla');
    await card(null); await wait(500);
    await sub('Kampüs sensörü <mark>2 dakikada bir</mark> ölçüyor'); await wait(2000);
    await sub('Yüz ve renk: <mark>hava kalitesi sınıfı</mark>'); await wait(1700);
    await sub('Herkes ve hassas gruplar için <mark>öneriler</mark>');
    await scroll('#ozet-body', 330, 2200); await wait(1600);
    await cap('Kampüs haritası', 'Sensörler, saha ölçümleri ve binalar tek ekranda');
    await F().evaluate(() => document.getElementById('ozet-body').scrollTop = 0);
    await sub('Sensörler ve saha ölçümleri <mark>harita üzerinde</mark>');
    await click('#tabbar [data-tab=map]', 1600);
    await F().evaluate(() => { map.flyTo([40.8105, 29.3575], 16.25, { duration: 2.2 }); }); await wait(2000);
    await sub('Sol alttaki <mark>yuvarlak düğmeye</mark> dokun'); await wait(1600);
    await cap('Ne kadar PM₂.₅ soludun?', 'Kişisel maruziyet asistanı · bilgilerin cihazından çıkmaz');
    await wait(700);
    await click('#exp-fab', 1300);
    await sub('Ne zaman, nerede, <mark>ne kadar</mark> kaldığını seç');
    await chat(780);
    await sub('Kampüste soluduğun <mark>PM₂.₅ miktarı</mark>'); await wait(400); await toChart(); await wait(2600);
    await sub('…ve <mark>neler yapabileceğin</mark>'); await scroll('#exp-body', 330, 1500); await wait(2200);
    await sub(null); await card(OUTRO); await wait(5200);
  } else {
    // ── Tanıtım (≈2,5 dk, 16:9) ──
    await card(`${LOGO_IMG}<h1>GTÜ <i>Air</i>Lab</h1><div class="sub">Kampüs Hava Kalitesi Laboratuvarı · Gebze Teknik Üniversitesi</div>
      <div class="rule"></div><div class="sub" style="margin-top:0">Kampüste soluduğumuz havayı ölçüyor, herkesle açıkça paylaşıyoruz.</div>`);
    await wait(6500);
    await card(`<h3>Neden ölçüyoruz?</h3><ul>
      <li><span class="n">1</span><span><b>PM₂.₅</b>, çapı 2,5 mikrometreden küçük parçacıklardır; solunum yollarının derinlerine ulaşabilir.</span></li>
      <li><span class="n">2</span><span>Dünya Sağlık Örgütü (WHO, 2021) kılavuzu: <b>24 saatlik ortalama 15 µg/m³</b>, yıllık ortalama 5 µg/m³.</span></li>
      <li><span class="n">3</span><span>Kampüsteki değeri bilmek; ders, çalışma ve açık hava etkinliklerini planlamaya yardımcı olabilir.</span></li></ul>`);
    await wait(10500);
    await card(`<h3>Ölçüm ağı</h3><ul>
      <li><span class="n">1</span><span><b>PurpleAir PA-II</b> · SÜMER Laboratuvarı çatısı; PM₁, PM₂.₅, PM₁₀, sıcaklık ve nem, 2 dakikada bir</span></li>
      <li><span class="n">2</span><span><b>Atmotube Pro (5 cihaz)</b> · taşınabilir, GPS'li saha ölçümleri; binaların karşılaştırılması</span></li>
      <li><span class="n">3</span><span><b>CO₂ sensörleri</b> · iç mekânlarda havalandırma göstergesi</span></li>
      <li><span class="n">4</span><span><b>Tuzla istasyonu</b> (İBB, ÇŞB) · kampüs ile bölgenin aynı saatte karşılaştırılması</span></li></ul>`);
    await wait(10000);
    await cap('Özet: kampüste şu an', 'Ulusal Hava Kalitesi İndeksi (HKİ), sınıfı ve ölçülü öneriler · veri kaynağı ve ölçüm zamanı her zaman görünür');
    await card(null); await wait(600);
    await sub('Kampüs sensörünün son ölçümü, <mark>ulusal hava kalitesi indeksiyle</mark>'); await wait(3300);
    await sub('Yüz ve renk sınıfı gösterir: <mark>İyi, Orta, Hassas…</mark>'); await wait(3200);
    await sub('Herkes ve hassas gruplar için <mark>ölçülü öneriler</mark>');
    await scroll('#ozet-body', 520, 3500); await wait(2500);
    await sub('Günlük ve aylık özet: <mark>WHO değerinin üstünde kaç gün?</mark>');
    await scroll('#ozet-body', 520, 3500); await wait(3000);
    await cap('Kampüs haritası', 'Binalar, sabit sensörler ve taşınabilir cihazlar; bina adına göre arama');
    await sub('Kuzey ve Güney kampüs, <mark>bina bina</mark>');
    await click('#ozet-close', 900);
    await F().evaluate(() => { map.flyTo([40.8105, 29.3575], 16.6, { duration: 2.5 }); }); await wait(4200);
    await sub('Sabit sensörler ve <mark>taşınabilir cihazlar</mark> aynı haritada');
    await F().evaluate(() => { map.flyTo([40.8114, 29.3563], 15.6, { duration: 2 }); }); await wait(3200);
    await cap('Sağlık: WHO karşılaştırması', 'Günlük ortalamalar WHO 2021 kılavuz değeriyle karşılaştırılır; kısa süreli saha ölçümleri 24 saatlik değerle karşılaştırılmaz');
    await sub('Her gün <mark>WHO 2021 kılavuz değeriyle</mark> karşılaştırılır');
    await click('#who-btn', 4500);
    await sub('Hangi günler sınırın üstünde, <mark>bir bakışta</mark>');
    await scroll('#who-body', 600, 4000); await wait(3500);
    await cap('Kişisel maruziyet asistanı', 'Kampüste geçirdiğiniz zamana göre solunan PM₂.₅ miktarının tahmini · girilen bilgiler cihazınızdan çıkmaz');
    await click('#who-close', 900);
    await sub('Haritadaki <mark>yuvarlak düğme</mark> asistanı açar');
    await click('#exp-fab', 1800);
    await sub('Saat, etkinlik, bina, havalandırma ve süre: <mark>birkaç dokunuş</mark>');
    await chat(1150);
    await sub('Sonuç: kampüste solunan <mark>tahmini PM₂.₅ miktarı</mark>');
    await wait(600); await toChart(); await wait(4200);
    await sub('…ve maruziyeti azaltmak için <mark>öneriler</mark>'); await scroll('#exp-body', 420, 2500); await wait(4000);
    await cap('Yöntem ve sınır değerler açık', 'HKİ kesim noktaları; WHO, Türkiye ve AB sınır değerleri; sınırlılıklar ve kaynaklar Hakkında bölümünde');
    await click('#exp-close', 700);
    await click('#info-btn', 1500);
    await sub('Her eşik ve hesap <mark>kaynağıyla birlikte</mark> yazılı');
    await F().evaluate(() => document.getElementById('inf-sinir').scrollIntoView({ behavior: 'smooth', block: 'start' })); await wait(4500);
    await scroll('#info-body', 380, 3000); await wait(2500);
    await cap('Araştırma görünümü', 'Sensör panelleri, saha ölçümleri ve karşılaştırma grafikleri · araştırmacılar için');
    await click('#info-close', 700);
    await sub('Tek düğmeyle <mark>araştırmacı görünümü</mark>');
    await click('#research-btn', 4500);
    await sub('Canlı sensörler ve <mark>saha ölçüm oturumları</mark>'); await wait(5000);
    await cap('Duyurular', 'Sensör kesintisi ya da yüksek kirlilik durumunda kendiliğinden bilgilendirme');
    await click('#research-btn', 800);
    await sub('Sensör kesintisinde ya da kirlilik artınca <mark>otomatik duyuru</mark>');
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
