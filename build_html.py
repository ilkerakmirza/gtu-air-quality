import os, sys

folder = os.path.expanduser('~/Desktop/BAP Proje Claude')

img_uri = "campus_map.jpg"

html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GTÜ BAP Projesi – Dinamik Proje Haritası</title>
<style>
:root{{
  --bg:#0a0e1a;--panel:#111827;--border:#1e3a5f;
  --blue:#3b82f6;--cyan:#06b6d4;--green:#10b981;
  --amber:#f59e0b;--purple:#8b5cf6;--red:#ef4444;
  --text:#e2e8f0;--muted:#64748b;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;overflow-x:hidden;}}

header{{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;gap:18px;position:relative;overflow:hidden;}}
header::after{{content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent,transparent 60px,rgba(59,130,246,.04) 60px,rgba(59,130,246,.04) 61px);pointer-events:none;}}
.logo-ring{{width:50px;height:50px;border-radius:50%;border:2px solid var(--cyan);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;box-shadow:0 0 18px rgba(6,182,212,.45);animation:pulse-ring 3s ease-in-out infinite;}}
@keyframes pulse-ring{{0%,100%{{box-shadow:0 0 10px rgba(6,182,212,.3)}}50%{{box-shadow:0 0 30px rgba(6,182,212,.7)}}}}
.header-text h1{{font-size:1rem;font-weight:700;color:#f0f9ff;line-height:1.35;}}
.header-text p{{font-size:.72rem;color:var(--cyan);margin-top:2px;}}
.header-meta{{margin-left:auto;display:flex;gap:22px;flex-shrink:0;}}
.meta-item .val{{font-size:1.25rem;font-weight:800;color:var(--cyan);text-align:center;}}
.meta-item .lbl{{font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;text-align:center;}}

.main{{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px;}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px;position:relative;overflow:hidden;}}
.card-title{{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:12px;display:flex;align-items:center;gap:7px;}}
.card-title span{{width:8px;height:8px;border-radius:50%;display:inline-block;}}

/* MAP */
.map-card{{grid-column:1;grid-row:1/3;}}
.map-wrapper{{position:relative;width:100%;border-radius:8px;overflow:hidden;border:1px solid var(--border);}}
.map-wrapper img{{width:100%;display:block;filter:brightness(.82) saturate(.85);}}
.map-overlay{{position:absolute;inset:0;}}
.mmarker{{position:absolute;transform:translate(-50%,-50%);cursor:pointer;z-index:10;}}
.mmarker-inner{{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;border:2px solid;background:rgba(0,0,0,.7);box-shadow:0 2px 12px rgba(0,0,0,.6);transition:transform .2s;position:relative;z-index:2;}}
.mmarker:hover .mmarker-inner{{transform:scale(1.3);}}
.pulse{{position:absolute;border-radius:50%;border:2px solid;top:50%;left:50%;transform:translate(-50%,-50%);animation:mPulse 2.3s ease-out infinite;pointer-events:none;z-index:1;}}
.pulse2{{animation-delay:.75s;}}
.pulse3{{animation-delay:1.4s;}}
@keyframes mPulse{{0%{{transform:translate(-50%,-50%) scale(.7);opacity:.9;}}100%{{transform:translate(-50%,-50%) scale(2.4);opacity:0;}}}}
.map-svg-lines{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;}}
.map-legend{{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;font-size:.61rem;color:var(--muted);}}
.leg{{display:flex;align-items:center;gap:5px;}}
.leg-dot{{width:10px;height:10px;border-radius:50%;}}

/* GANTT */
.wp-card{{grid-column:2;grid-row:1;}}
.gantt-row{{margin-bottom:12px;}}
.gantt-label{{font-size:.72rem;font-weight:600;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between;}}
.badge{{font-size:.58rem;padding:1px 7px;border-radius:99px;font-weight:700;}}
.gantt-track{{height:22px;background:#1e293b;border-radius:4px;position:relative;overflow:hidden;}}
.gantt-bar{{position:absolute;top:0;height:100%;border-radius:4px;display:flex;align-items:center;padding:0 8px;font-size:.6rem;font-weight:700;color:#fff;white-space:nowrap;animation:bar-grow .9s ease-out both;}}
@keyframes bar-grow{{from{{transform:scaleX(0);opacity:0}}to{{transform:scaleX(1);opacity:1}}}}
.wp1-bar{{left:0%;width:75%;background:linear-gradient(90deg,#1d4ed8,#3b82f6);animation-delay:.2s;}}
.wp2-bar{{left:16.7%;width:58.3%;background:linear-gradient(90deg,#065f46,#10b981);animation-delay:.5s;}}
.wp3-bar{{left:50%;width:50%;background:linear-gradient(90deg,#6d28d9,#8b5cf6);animation-delay:.8s;}}
.gantt-months{{display:flex;margin-top:6px;}}
.gantt-month{{flex:1;text-align:center;font-size:.57rem;color:var(--muted);border-left:1px solid #1e293b;padding-top:2px;}}
.milestones{{margin-top:12px;}}
.ms-item{{display:flex;align-items:flex-start;gap:9px;margin-bottom:8px;padding:7px 10px;border-radius:8px;border:1px solid #1e293b;animation:fade-slide .5s ease-out both;}}
@keyframes fade-slide{{from{{opacity:0;transform:translateX(20px)}}to{{opacity:1;transform:translateX(0)}}}}
.ms-dot{{width:9px;height:9px;border-radius:50%;margin-top:3px;flex-shrink:0;}}
.ms-title{{font-size:.7rem;font-weight:600;}}
.ms-desc{{font-size:.6rem;color:var(--muted);margin-top:2px;}}

/* PIPELINE */
.pipe-card{{grid-column:2;grid-row:2;}}
.pipeline{{display:flex;align-items:center;overflow-x:auto;padding-bottom:4px;gap:0;}}
.pipe-step{{background:#1e293b;border:1px solid var(--border);border-radius:8px;padding:9px 10px;min-width:92px;text-align:center;flex-shrink:0;animation:pop-in .5s cubic-bezier(.34,1.56,.64,1) both;}}
@keyframes pop-in{{from{{opacity:0;transform:scale(.5)}}to{{opacity:1;transform:scale(1)}}}}
.ps-icon{{font-size:1.25rem;}}
.ps-title{{font-size:.62rem;font-weight:700;margin-top:3px;}}
.ps-sub{{font-size:.52rem;color:var(--muted);margin-top:2px;}}
.pipe-arrow{{flex-shrink:0;color:var(--muted);font-size:.9rem;padding:0 2px;animation:arrow-blink 2s ease-in-out infinite;}}
@keyframes arrow-blink{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}

/* INFOGRAPHIC */
.info-card{{grid-column:1/3;}}
.gauges{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;}}
.gauge-box{{flex:1;min-width:130px;background:#0f172a;border:1px solid var(--border);border-radius:10px;padding:11px;text-align:center;}}
.gauge-title{{font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;}}
.gauge-val{{font-size:1.4rem;font-weight:800;margin-top:2px;}}
.gauge-unit{{font-size:.58rem;color:var(--muted);margin-top:1px;}}
.gauge-bar-wrap{{width:100%;height:7px;background:#1e293b;border-radius:4px;overflow:hidden;margin-top:5px;}}
.gauge-bar{{height:100%;border-radius:4px;width:0%;transition:width 1.4s ease-out;}}
.scenario-chart{{background:#0f172a;border:1px solid var(--border);border-radius:10px;padding:13px;margin-bottom:14px;}}
.chart-title{{font-size:.65rem;font-weight:700;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.07em;}}
.chart-area{{width:100%;height:120px;position:relative;}}
.chart-svg{{width:100%;height:100%;}}
.hypothesis{{background:linear-gradient(135deg,#0f172a,#1a2d4f);border:1px solid #2563eb;border-radius:10px;padding:13px;margin-bottom:16px;display:flex;gap:14px;align-items:center;}}
.hyp-icon{{font-size:2rem;flex-shrink:0;}}
.hyp-text{{font-size:.71rem;line-height:1.7;color:#cbd5e1;}}
.hyp-text strong{{color:#60a5fa;}}
.outcomes{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}}
.outcome-box{{background:#0f172a;border:1px solid var(--border);border-radius:8px;padding:10px;text-align:center;animation:fade-in .7s ease-out both;}}
@keyframes fade-in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
.oc-icon{{font-size:1.35rem;margin-bottom:5px;}}
.oc-title{{font-size:.67rem;font-weight:700;margin-bottom:3px;}}
.oc-desc{{font-size:.58rem;color:var(--muted);}}

/* METRICS */
.metrics-card{{grid-column:1/3;}}
.metrics-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}}
.metric-box{{background:#0f172a;border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;position:relative;overflow:hidden;animation:fade-in .6s ease-out both;}}
.metric-box::before{{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;}}
.m1::before{{background:var(--blue)}}.m2::before{{background:var(--green)}}.m3::before{{background:var(--amber)}}.m4::before{{background:var(--purple)}}
.metric-num{{font-size:1.9rem;font-weight:800;}}
.metric-lbl{{font-size:.62rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-top:3px;}}
.metric-sub{{font-size:.64rem;color:var(--muted);margin-top:5px;}}
.progress-ring{{width:58px;height:58px;margin:0 auto 7px;}}
.ring-bg{{fill:none;stroke:#1e293b;stroke-width:5;}}
.ring-fg{{fill:none;stroke-width:5;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%;transition:stroke-dashoffset 1.6s ease-out;}}
@keyframes val-blink{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
.live-dot{{width:6px;height:6px;border-radius:50%;background:#10b981;display:inline-block;animation:val-blink 1.2s ease-in-out infinite;}}

.ticker-wrap{{background:#0d1221;border-top:1px solid var(--border);padding:7px 14px;overflow:hidden;}}
.ticker-inner{{display:flex;gap:48px;white-space:nowrap;animation:scroll-left 40s linear infinite;}}
@keyframes scroll-left{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
.tick{{font-size:.63rem;color:var(--muted);}}
.tick strong{{color:var(--cyan);}}

@media(max-width:860px){{
  .main{{grid-template-columns:1fr;}}
  .map-card,.info-card,.metrics-card{{grid-column:1;}}
  .wp-card,.pipe-card{{grid-column:1;}}
  .map-card{{grid-row:auto;}}
  .metrics-grid{{grid-template-columns:repeat(2,1fr);}}
  .outcomes{{grid-template-columns:repeat(2,1fr);}}
}}
</style>
</head>
<body>

<header>
  <div class="logo-ring">🌬️</div>
  <div class="header-text">
    <h1>Kampüs Mikro-Ortamlarında Dinamik Kaynak Karakterizasyonu &amp; Karar Destek Modeli</h1>
    <p>GTÜ BAP Projesi &nbsp;·&nbsp; Dr. Öğr. Üyesi İlker AKMIRZA &nbsp;·&nbsp; Çevre Mühendisliği &nbsp;·&nbsp; Başlangıç: 01.09.2026</p>
  </div>
  <div class="header-meta">
    <div class="meta-item"><div class="val" id="hm1">0</div><div class="lbl">Ay Süre</div></div>
    <div class="meta-item"><div class="val" id="hm2">0K</div><div class="lbl">Bütçe TL</div></div>
    <div class="meta-item"><div class="val" id="hm3">0</div><div class="lbl">İş Paketi</div></div>
    <div class="meta-item"><div class="val" id="hm4">0</div><div class="lbl">Araştırmacı</div></div>
  </div>
</header>

<div class="main">

<!-- ══ KART 1: KAMPÜS HARİTASI ══ -->
<div class="card map-card" style="box-shadow:0 0 24px rgba(59,130,246,.15)">
  <div class="card-title"><span style="background:var(--cyan)"></span>GTÜ Kampüs Haritası — Ölçüm Noktaları</div>
  <div class="map-wrapper" id="mapWrap">
    <img src="{img_uri}" alt="GTÜ Kampüs Haritası"/>
    <!-- SVG akış çizgileri -->
    <svg class="map-svg-lines" id="flowSvg" viewBox="0 0 100 100" preserveAspectRatio="none"></svg>

    <!-- MARKER 1: Çevre Müh Binası (güneyde, merkez sağ) -->
    <div class="mmarker" style="left:70%;top:42%;" id="m1" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#10b981;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#10b981;"></div>
      <div class="mmarker-inner" style="border-color:#10b981;box-shadow:0 0 14px #10b98199;">🎓</div>
    </div>
    <!-- MARKER 2: Merkez Amfiler -->
    <div class="mmarker" style="left:54%;top:35%;" id="m2" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#10b981;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#10b981;"></div>
      <div class="mmarker-inner" style="border-color:#10b981;box-shadow:0 0 14px #10b98199;">🎓</div>
    </div>
    <!-- MARKER 3: Kimya/Lab Binası -->
    <div class="mmarker" style="left:76%;top:37%;" id="m3" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#3b82f6;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#3b82f6;"></div>
      <div class="mmarker-inner" style="border-color:#3b82f6;box-shadow:0 0 14px #3b82f699;">🔬</div>
    </div>
    <!-- MARKER 4: Kütüphane -->
    <div class="mmarker" style="left:59%;top:28%;" id="m4" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#a78bfa;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#a78bfa;"></div>
      <div class="mmarker-inner" style="border-color:#a78bfa;box-shadow:0 0 14px #a78bfa99;">📚</div>
    </div>
    <!-- MARKER 5: Spor Salonu -->
    <div class="mmarker" style="left:29%;top:53%;" id="m5" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#8b5cf6;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#8b5cf6;"></div>
      <div class="mmarker-inner" style="border-color:#8b5cf6;box-shadow:0 0 14px #8b5cf699;">🏊</div>
    </div>
    <!-- MARKER 6: Yemekhane -->
    <div class="mmarker" style="left:48%;top:50%;" id="m6" onclick="showTip(this)">
      <div class="pulse" style="width:46px;height:46px;border-color:#f59e0b;"></div>
      <div class="pulse pulse2" style="width:46px;height:46px;border-color:#f59e0b;"></div>
      <div class="mmarker-inner" style="border-color:#f59e0b;box-shadow:0 0 14px #f59e0b99;">🍽️</div>
    </div>
    <!-- MARKER 7: SUMER Lab – PurpleAir (büyük / sabit) -->
    <div class="mmarker" style="left:64%;top:57%;" id="m7" onclick="showTip(this)">
      <div class="pulse" style="width:54px;height:54px;border-color:#06b6d4;animation-duration:1.6s;"></div>
      <div class="pulse pulse2" style="width:54px;height:54px;border-color:#06b6d4;animation-duration:1.6s;"></div>
      <div class="pulse pulse3" style="width:54px;height:54px;border-color:#06b6d4;animation-duration:1.6s;"></div>
      <div class="mmarker-inner" style="border-color:#06b6d4;box-shadow:0 0 20px #06b6d4bb;background:rgba(6,182,212,.18);width:38px;height:38px;font-size:17px;">📡</div>
    </div>

    <!-- Tooltip -->
    <div id="mapTip" style="position:absolute;background:#1e293b;border:1px solid #3b82f6;border-radius:9px;padding:10px 14px;font-size:.68rem;z-index:200;min-width:200px;max-width:260px;display:none;pointer-events:none;box-shadow:0 6px 24px rgba(0,0,0,.8);"></div>

    <!-- Canlı ölçüm -->
    <div style="position:absolute;top:8px;right:8px;background:rgba(10,14,26,.88);border:1px solid #1e3a5f;border-radius:7px;padding:6px 10px;font-size:.6rem;">
      <div style="color:#64748b;margin-bottom:3px;text-transform:uppercase;letter-spacing:.05em;font-size:.55rem">Anlık Ölçüm</div>
      <div id="liveVal" style="color:#10b981;font-weight:700;font-size:.72rem;"></div>
    </div>

    <!-- Kampüs etiketi -->
    <div style="position:absolute;top:8px;left:8px;background:rgba(10,14,26,.8);border:1px solid #1e3a5f;border-radius:6px;padding:4px 8px;font-size:.6rem;color:#64748b;">
      Gebze Teknik Üniversitesi · Kampüs
    </div>
  </div>
  <div class="map-legend">
    <div class="leg"><div class="leg-dot" style="background:#f59e0b;box-shadow:0 0 5px #f59e0b"></div>Taşınabilir (Atmotube Pro 2)</div>
    <div class="leg"><div class="leg-dot" style="background:#06b6d4;box-shadow:0 0 5px #06b6d4"></div>Sabit (PurpleAir PA-II)</div>
    <div class="leg"><div class="leg-dot" style="background:#10b981"></div>Derslik</div>
    <div class="leg"><div class="leg-dot" style="background:#3b82f6"></div>Lab</div>
    <div class="leg"><div class="leg-dot" style="background:#8b5cf6"></div>Ortak Alan</div>
    <div class="leg"><div class="leg-dot" style="background:#a78bfa"></div>Kütüphane</div>
  </div>
</div>

<!-- ══ KART 2: GANTT ══ -->
<div class="card wp-card" style="box-shadow:0 0 20px rgba(59,130,246,.1)">
  <div class="card-title"><span style="background:var(--blue)"></span>İş Paketi Zaman Çizelgesi (12 Ay)</div>
  <div class="gantt-row">
    <div class="gantt-label"><span>📡 İP-1: Sensör Entegrasyonu &amp; Veri Toplama</span><span class="badge" style="background:#1d4ed8;color:#fff">Ay 1–9</span></div>
    <div class="gantt-track"><div class="gantt-bar wp1-bar">PM₂.₅ · CO₂ · UOB ölçümleri</div></div>
  </div>
  <div class="gantt-row">
    <div class="gantt-label"><span>🔍 İP-2: Kaynak Karakterizasyonu</span><span class="badge" style="background:#065f46;color:#fff">Ay 3–9</span></div>
    <div class="gantt-track"><div class="gantt-bar wp2-bar">I/O oranı · kümeleme analizi</div></div>
  </div>
  <div class="gantt-row">
    <div class="gantt-label"><span>🤖 İP-3: Makine Öğrenmesi Entegrasyonu</span><span class="badge" style="background:#6d28d9;color:#fff">Ay 7–12</span></div>
    <div class="gantt-track"><div class="gantt-bar wp3-bar">Regresyon · Karar Ağaçları · SVM</div></div>
  </div>
  <div class="gantt-months">
    <div class="gantt-month">1</div><div class="gantt-month">2</div><div class="gantt-month">3</div><div class="gantt-month">4</div><div class="gantt-month">5</div><div class="gantt-month">6</div><div class="gantt-month">7</div><div class="gantt-month">8</div><div class="gantt-month">9</div><div class="gantt-month">10</div><div class="gantt-month">11</div><div class="gantt-month">12</div>
  </div>
  <div class="milestones">
    <div class="ms-item" style="animation-delay:.1s"><div class="ms-dot" style="background:#3b82f6"></div><div><div class="ms-title">Ay 1–2: Sensör Kurulumu &amp; Pilot Ölçümler</div><div class="ms-desc">Atmotube Pro 2 (×6) · INKBIRD IAM-T1 · PurpleAir PA-II veri doğrulama</div></div></div>
    <div class="ms-item" style="animation-delay:.2s"><div class="ms-dot" style="background:#10b981"></div><div><div class="ms-title">Ay 3–6: Kapsamlı Saha Ölçümleri</div><div class="ms-desc">Derslik · Lab · Kütüphane · Spor · Kantin — mevsimsel &amp; zamansal değişkenlik</div></div></div>
    <div class="ms-item" style="animation-delay:.3s"><div class="ms-dot" style="background:#f59e0b"></div><div><div class="ms-title">Ay 5–8: Kirlilik Profilleri &amp; I/O Analizi</div><div class="ms-desc">İç/dış oranı · kümeleme · kaynak sınıflandırması (p &lt; 0.05)</div></div></div>
    <div class="ms-item" style="animation-delay:.4s"><div class="ms-dot" style="background:#8b5cf6"></div><div><div class="ms-title">Ay 9–12: ML Eğitimi &amp; Tahmin Mekanizması</div><div class="ms-desc">Regresyon · DT · SVM — Hedef: R² &gt; 0.90 · çapraz doğrulama</div></div></div>
  </div>
</div>

<!-- ══ KART 3: PIPELINE ══ -->
<div class="card pipe-card" style="box-shadow:0 0 20px rgba(139,92,246,.1)">
  <div class="card-title"><span style="background:var(--purple)"></span>Araştırma Veri Akış Şeması</div>
  <div class="pipeline">
    <div class="pipe-step" style="animation-delay:.0s;border-color:#1d4ed8"><div class="ps-icon">📡</div><div class="ps-title" style="color:#3b82f6">Sensör Ağı</div><div class="ps-sub">PM·CO₂·UOB<br>Dakikalık</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.12s;border-color:#065f46"><div class="ps-icon">🌐</div><div class="ps-title" style="color:#10b981">Dış Ortam</div><div class="ps-sub">PurpleAir<br>Arka plan PM₂.₅</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.24s;border-color:#92400e"><div class="ps-icon">⛅</div><div class="ps-title" style="color:#f59e0b">Meteoroloji</div><div class="ps-sub">Sıcaklık·Rüzgar<br>Nem·Yağış</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.36s;border-color:#1e3a5f"><div class="ps-icon">🗃️</div><div class="ps-title" style="color:#60a5fa">Ön İşleme</div><div class="ps-sub">Temizleme<br>Normalizasyon</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.48s;border-color:#374151"><div class="ps-icon">📊</div><div class="ps-title" style="color:#94a3b8">İstatistik</div><div class="ps-sub">I/O oranı<br>Kümeleme</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.60s;border-color:#6d28d9"><div class="ps-icon">🤖</div><div class="ps-title" style="color:#8b5cf6">ML Modeli</div><div class="ps-sub">Regresyon·DT<br>SVM·CV</div></div>
    <div class="pipe-arrow">→</div>
    <div class="pipe-step" style="animation-delay:.72s;border-color:#065f46"><div class="ps-icon">🎯</div><div class="ps-title" style="color:#10b981">Karar Destek</div><div class="ps-sub">Tahmin+strateji<br>R²&gt;0.90</div></div>
  </div>
</div>

<!-- ══ KART 4: GRAFİK ÖZET ══ -->
<div class="card info-card" style="box-shadow:0 0 20px rgba(6,182,212,.1)">
  <div class="card-title"><span style="background:var(--cyan)"></span>Proje Grafik Özeti — Kirletici Dinamikleri &amp; Araştırma Hipotezi</div>

  <div class="hypothesis">
    <div class="hyp-icon">💡</div>
    <div class="hyp-text">
      <strong>"GTÜ Kampüsü mikro-ortamlarında tespit edilen (CO₂, UOB, PM) hava kirleticilerinin mekansal ve zamansal dağılım verileri, makine öğrenmesi algoritmaları kullanılarak emisyon kaynakları tespit edilip gelecekteki lokal hava kalitesi güvenilir şekilde tahmin edilebilir mi?"</strong><br>
      Bu hipotez kampüs iç ortamlarında çok parametreli + zamansal izleme + ML entegrasyonu ile sınanacaktır.
    </div>
  </div>

  <div class="gauges">
    <div class="gauge-box"><div class="gauge-title" style="color:#ef4444">PM₂.₅</div><div class="gauge-val" style="color:#ef4444"><span id="gv1">--</span></div><div class="gauge-unit">µg/m³ · İç Ortam</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb1" style="background:linear-gradient(90deg,#7f1d1d,#ef4444)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">WHO: &lt;15 µg/m³/gün</div></div>
    <div class="gauge-box"><div class="gauge-title" style="color:#3b82f6">CO₂</div><div class="gauge-val" style="color:#3b82f6"><span id="gv2">--</span></div><div class="gauge-unit">ppm · İç Ortam</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb2" style="background:linear-gradient(90deg,#1d4ed8,#3b82f6)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">İdeal: &lt;1000 ppm</div></div>
    <div class="gauge-box"><div class="gauge-title" style="color:#f59e0b">Toplam UOB</div><div class="gauge-val" style="color:#f59e0b"><span id="gv3">--</span></div><div class="gauge-unit">ppb · İç Ortam</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb3" style="background:linear-gradient(90deg,#78350f,#f59e0b)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">Ref: &lt;500 ppb</div></div>
    <div class="gauge-box"><div class="gauge-title" style="color:#06b6d4">PM₂.₅ Dış</div><div class="gauge-val" style="color:#06b6d4"><span id="gv4">--</span></div><div class="gauge-unit">µg/m³ · PurpleAir</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb4" style="background:linear-gradient(90deg,#164e63,#06b6d4)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">D-100 etki bölgesi</div></div>
    <div class="gauge-box"><div class="gauge-title" style="color:#10b981">I/O Oranı</div><div class="gauge-val" style="color:#10b981"><span id="gv5">--</span></div><div class="gauge-unit">İç/Dış PM₂.₅</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb5" style="background:linear-gradient(90deg,#064e3b,#10b981)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">&gt;1 → iç kaynak baskın</div></div>
    <div class="gauge-box"><div class="gauge-title" style="color:#8b5cf6">Kullanıcı Yoğ.</div><div class="gauge-val" style="color:#8b5cf6"><span id="gv6">--</span></div><div class="gauge-unit">kişi/ortam</div><div class="gauge-bar-wrap"><div class="gauge-bar" id="gb6" style="background:linear-gradient(90deg,#4c1d95,#8b5cf6)"></div></div><div style="font-size:.56rem;color:var(--muted);margin-top:3px">CO₂ ile korelasyon</div></div>
  </div>

  <!-- Zaman serisi grafiği -->
  <div class="scenario-chart">
    <div class="chart-title">Simüle Günlük Kirletici Profili — Derslik Örneği (08:00–18:00)</div>
    <div class="chart-area">
      <svg class="chart-svg" id="lineChart" viewBox="0 0 700 115" preserveAspectRatio="none">
        <line x1="0" y1="30"  x2="700" y2="30"  stroke="#1e293b" stroke-width="1"/>
        <line x1="0" y1="62"  x2="700" y2="62"  stroke="#1e293b" stroke-width="1"/>
        <line x1="0" y1="94"  x2="700" y2="94"  stroke="#1e293b" stroke-width="1"/>
        <path id="co2Fill" opacity=".12" fill="#3b82f6"/>
        <path id="co2Path" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linejoin="round"/>
        <path id="pmPath"  fill="none" stroke="#ef4444" stroke-width="2"   stroke-linejoin="round"/>
        <path id="vocPath" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="5,3"/>
        <circle id="moveDot" r="5" fill="#06b6d4" opacity=".9"/>
        <text x="8" y="26"  fill="#3b82f6" font-size="8" font-weight="bold">CO₂</text>
        <text x="8" y="58"  fill="#ef4444" font-size="8" font-weight="bold">PM</text>
        <text x="8" y="90"  fill="#f59e0b" font-size="8" font-weight="bold">UOB</text>
        <text x="2"   y="113" fill="#475569" font-size="7">08:00</text>
        <text x="157" y="113" fill="#475569" font-size="7">10:30</text>
        <text x="312" y="113" fill="#475569" font-size="7">13:00</text>
        <text x="467" y="113" fill="#475569" font-size="7">15:30</text>
        <text x="622" y="113" fill="#475569" font-size="7">18:00</text>
      </svg>
    </div>
  </div>

  <!-- Çubuk grafiği -->
  <div class="scenario-chart">
    <div class="chart-title">Mikro-Ortam Bazlı Ortalama CO₂ Konsantrasyonu (ppm) — Temsili Beklenti</div>
    <div style="display:flex;gap:8px;align-items:flex-end;height:92px;padding:0 8px 0;position:relative;">
      <!-- yatay referans çizgisi 1000 ppm -->
      <div style="position:absolute;left:0;right:0;bottom:35px;height:1px;background:#ef444455;border-top:1px dashed #ef444466;z-index:0;"></div>
      <div style="position:absolute;right:4px;bottom:38px;font-size:.55rem;color:#ef4444;z-index:1;">1000 ppm eşik</div>
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1;">
        <span style="font-size:.61rem;color:#3b82f6;font-weight:700;">950</span>
        <div class="bar-col" data-h="62" style="width:80%;background:linear-gradient(180deg,#3b82f6,#1d4ed8);border-radius:3px 3px 0 0;height:0;transition:height 1.3s ease-out .2s;"></div>
        <span style="font-size:.54rem;color:var(--muted);text-align:center;">Derslik</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1;">
        <span style="font-size:.61rem;color:#ef4444;font-weight:700;">1280</span>
        <div class="bar-col" data-h="83" style="width:80%;background:linear-gradient(180deg,#ef4444,#991b1b);border-radius:3px 3px 0 0;height:0;transition:height 1.3s ease-out .35s;"></div>
        <span style="font-size:.54rem;color:var(--muted);text-align:center;">Kantin</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1;">
        <span style="font-size:.61rem;color:#10b981;font-weight:700;">720</span>
        <div class="bar-col" data-h="47" style="width:80%;background:linear-gradient(180deg,#10b981,#065f46);border-radius:3px 3px 0 0;height:0;transition:height 1.3s ease-out .5s;"></div>
        <span style="font-size:.54rem;color:var(--muted);text-align:center;">Kütüphane</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1;">
        <span style="font-size:.61rem;color:#f59e0b;font-weight:700;">1120</span>
        <div class="bar-col" data-h="73" style="width:80%;background:linear-gradient(180deg,#f59e0b,#78350f);border-radius:3px 3px 0 0;height:0;transition:height 1.3s ease-out .65s;"></div>
        <span style="font-size:.54rem;color:var(--muted);text-align:center;">Lab</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1;">
        <span style="font-size:.61rem;color:#8b5cf6;font-weight:700;">860</span>
        <div class="bar-col" data-h="56" style="width:80%;background:linear-gradient(180deg,#8b5cf6,#4c1d95);border-radius:3px 3px 0 0;height:0;transition:height 1.3s ease-out .8s;"></div>
        <span style="font-size:.54rem;color:var(--muted);text-align:center;">Spor</span>
      </div>
    </div>
  </div>

  <!-- Beklenen çıktılar -->
  <div class="outcomes">
    <div class="outcome-box" style="animation-delay:.1s"><div class="oc-icon">🗺️</div><div class="oc-title" style="color:#06b6d4">Kirlilik Haritası</div><div class="oc-desc">PM, CO₂, UOB'un kampüs genelinde mekânsal &amp; zamansal dağılım haritası</div></div>
    <div class="outcome-box" style="animation-delay:.2s"><div class="oc-icon">🔍</div><div class="oc-title" style="color:#10b981">Kaynak Profili</div><div class="oc-desc">Her mikro-ortam için baskın kirletici kaynak sınıflandırması (p &lt; 0.05)</div></div>
    <div class="outcome-box" style="animation-delay:.3s"><div class="oc-icon">🤖</div><div class="oc-title" style="color:#8b5cf6">ML Tahmin Modeli</div><div class="oc-desc">Kişisel maruziyet minimizasyonu için R² &gt; 0.90 hedefli tahmin mekanizması</div></div>
    <div class="outcome-box" style="animation-delay:.4s"><div class="oc-icon">📋</div><div class="oc-title" style="color:#f59e0b">Yönetim Stratejisi</div><div class="oc-desc">Havalandırma, temizlik planlaması &amp; kullanım yoğunluğu yönetimi</div></div>
    <div class="outcome-box" style="animation-delay:.5s"><div class="oc-icon">👥</div><div class="oc-title" style="color:#3b82f6">Kişisel Maruziyet</div><div class="oc-desc">Dezavantajlı gruplar dahil tüm kullanıcılar için minimum maruziyet planlaması</div></div>
    <div class="outcome-box" style="animation-delay:.6s"><div class="oc-icon">📄</div><div class="oc-title" style="color:#a78bfa">Bilimsel Yayın</div><div class="oc-desc">SCI-E düzeyinde uluslararası yayın hedefi + GTÜ iç raporları</div></div>
  </div>
</div>

<!-- ══ KART 5: METRİKLER ══ -->
<div class="card metrics-card">
  <div class="card-title"><span style="background:var(--green)"></span>Başarı Ölçütleri &amp; Proje Metrikleri</div>
  <div class="metrics-grid">
    <div class="metric-box m1" style="animation-delay:.1s">
      <svg class="progress-ring" viewBox="0 0 60 60"><circle class="ring-bg" cx="30" cy="30" r="24"/><circle class="ring-fg" id="r1" cx="30" cy="30" r="24" stroke="#3b82f6" stroke-dasharray="150.8" stroke-dashoffset="150.8"/></svg>
      <div class="metric-num" style="color:#3b82f6">30%</div>
      <div class="metric-lbl">Ölçüt 1 – Veri Toplama</div>
      <div class="metric-sub">≥%90 süre kapsama · 6 sensör · Güvenilir veri seti</div>
    </div>
    <div class="metric-box m2" style="animation-delay:.2s">
      <svg class="progress-ring" viewBox="0 0 60 60"><circle class="ring-bg" cx="30" cy="30" r="24"/><circle class="ring-fg" id="r2" cx="30" cy="30" r="24" stroke="#10b981" stroke-dasharray="150.8" stroke-dashoffset="150.8"/></svg>
      <div class="metric-num" style="color:#10b981">35%</div>
      <div class="metric-lbl">Ölçüt 2 – Kaynak Karakterizasyonu</div>
      <div class="metric-sub">p &lt; 0.05 anlamlılık · I/O oranı · kümeleme</div>
    </div>
    <div class="metric-box m3" style="animation-delay:.3s">
      <svg class="progress-ring" viewBox="0 0 60 60"><circle class="ring-bg" cx="30" cy="30" r="24"/><circle class="ring-fg" id="r3" cx="30" cy="30" r="24" stroke="#f59e0b" stroke-dasharray="150.8" stroke-dashoffset="150.8"/></svg>
      <div class="metric-num" style="color:#f59e0b">35%</div>
      <div class="metric-lbl">Ölçüt 3 – ML Modelleme</div>
      <div class="metric-sub">R² &gt; 0.90 · RMSE minimize · çapraz doğrulama</div>
    </div>
    <div class="metric-box m4" style="animation-delay:.4s">
      <div style="font-size:.63rem;color:var(--muted);margin-bottom:4px">Bütçe Dağılımı (125K TL)</div>
      <div style="background:#1e293b;border-radius:4px;height:10px;overflow:hidden;margin-bottom:5px">
        <div style="width:72%;height:100%;background:linear-gradient(90deg,#1d4ed8,#3b82f6);float:left;border-radius:4px 0 0 4px;"></div>
        <div style="width:28%;height:100%;background:linear-gradient(90deg,#065f46,#10b981);float:left;border-radius:0 4px 4px 0;"></div>
      </div>
      <div style="display:flex;gap:8px;font-size:.57rem;margin-bottom:10px"><span style="color:#3b82f6">■ Teçhizat 90K</span><span style="color:#10b981">■ Yolluk 35K</span></div>
      <div style="font-size:.6rem;color:var(--muted);margin-bottom:3px">Araştırma Ekibi</div>
      <div style="font-size:.6rem;line-height:1.9">
        <span style="color:#f59e0b">●</span> Dr. İlker AKMIRZA – Yürütücü<br>
        <span style="color:#10b981">●</span> Prof.Dr. P. Ergenekon – Çevre Müh.<br>
        <span style="color:#8b5cf6">●</span> Doç.Dr. Ö. Yücel – Kimya Müh.<br>
        <span style="color:#06b6d4">●</span> Arş.Gör. S. Saraçoğlu – Çevre Müh.
      </div>
    </div>
  </div>
</div>

</div><!-- end main -->

<div class="ticker-wrap">
  <div class="ticker-inner">
    <span class="tick">📅 Başlama: <strong>01.09.2026</strong></span>
    <span class="tick">🔬 Sensörler: <strong>Atmotube Pro 2 (×6) · INKBIRD IAM-T1 · PurpleAir PA-II</strong></span>
    <span class="tick">🏛️ GTÜ Çevre Müh. Bölümü · <strong>Gebze, Kocaeli</strong></span>
    <span class="tick">🎯 Kirleticiler: <strong>PM₂.₅ · PM₁₀ · CO₂ · Toplam UOB</strong></span>
    <span class="tick">📍 Mikro-Ortamlar: <strong>Derslik · Lab · Kütüphane · Kantin · Spor Salonu</strong></span>
    <span class="tick">📡 Arka Plan: <strong>SUMER Lab Çatısı – PurpleAir PA-II</strong></span>
    <span class="tick">🤖 ML: <strong>Doğrusal Regresyon · Karar Ağaçları · SVM</strong></span>
    <span class="tick">📊 Hedef: <strong>R² &gt; 0.90 · p &lt; 0.05 · ≥%90 veri kapsama</strong></span>
    <span class="tick">📅 Başlama: <strong>01.09.2026</strong></span>
    <span class="tick">🔬 Sensörler: <strong>Atmotube Pro 2 (×6) · INKBIRD IAM-T1 · PurpleAir PA-II</strong></span>
    <span class="tick">🏛️ GTÜ Çevre Müh. Bölümü · <strong>Gebze, Kocaeli</strong></span>
    <span class="tick">🎯 Kirleticiler: <strong>PM₂.₅ · PM₁₀ · CO₂ · Toplam UOB</strong></span>
    <span class="tick">📍 Mikro-Ortamlar: <strong>Derslik · Lab · Kütüphane · Kantin · Spor Salonu</strong></span>
    <span class="tick">📡 Arka Plan: <strong>SUMER Lab Çatısı – PurpleAir PA-II</strong></span>
    <span class="tick">🤖 ML: <strong>Doğrusal Regresyon · Karar Ağaçları · SVM</strong></span>
    <span class="tick">📊 Hedef: <strong>R² &gt; 0.90 · p &lt; 0.05 · ≥%90 veri kapsama</strong></span>
  </div>
</div>

<script>
// ── HEADER COUNTER ──
function countUp(id,end,suf,dur){{
  const el=document.getElementById(id);let s=0,step=16;
  const inc=end/(dur/step);
  const iv=setInterval(()=>{{s=Math.min(s+inc,end);el.textContent=Math.floor(s)+suf;if(s>=end)clearInterval(iv);}},step);
}}
setTimeout(()=>{{
  countUp('hm1',12,'',900);
  setTimeout(()=>{{document.getElementById('hm2').textContent='125K';}},400);
  setTimeout(()=>countUp('hm3',3,'',600),300);
  setTimeout(()=>countUp('hm4',4,'',600),500);
}},400);

// ── MARKER TOOLTIP ──
const MD={{
  m1:{{t:'🎓 Çevre Müh. Binası & Amfi',c:'#10b981',d:'Derslik mikro-ortamı. PM₂.₅, CO₂, UOB ölçümleri.<br>Kullanıcı yoğunluğu & ders saati değişkenliği izlenir.',p:'PM₂.₅ · CO₂ · UOB',s:'Atmotube Pro 2'}},
  m2:{{t:'🎓 Merkez Amfiler',c:'#10b981',d:'Büyük kapasiteli amfiler. Yüksek dolulukta CO₂ birikimi kritik.',p:'CO₂ · PM₂.₅',s:'Atmotube Pro 2'}},
  m3:{{t:'🔬 Kimya / Lab Binası',c:'#3b82f6',d:'Deneysel faaliyetler → UOB pik noktaları. Temizlik kimyasalları izlenir.',p:'UOB · PM₂.₅ · CO₂',s:'Atmotube Pro 2'}},
  m4:{{t:'📚 Kütüphane',c:'#a78bfa',d:'Sessiz çalışma ortamı. Sabah/öğleden sonra CO₂ değişkenliği.',p:'CO₂ · PM₂.₅ · UOB',s:'Atmotube Pro 2'}},
  m5:{{t:'🏊 Spor Salonu & Havuz',c:'#8b5cf6',d:'Havuz klorinasyonu UOB kaynağı. Nem oranı yüksek.',p:'UOB · PM · CO₂',s:'Atmotube Pro 2'}},
  m6:{{t:'🍽️ Kantin / Yemekhane',c:'#f59e0b',d:'Pik: öğle saatleri. Pişirme → PM & UOB artışı. En yüksek CO₂ beklenen alan.',p:'PM · UOB · CO₂',s:'Atmotube Pro 2'}},
  m7:{{t:'📡 SUMER Lab – PurpleAir PA-II',c:'#06b6d4',d:'<b style="color:#06b6d4">Sabit arka plan sensörü.</b> Dış ortam PM₂.₅ – 7/24 aktif.<br>I/O oranı hesabı referans noktası.',p:'PM₂.₅ dış ortam',s:'PurpleAir PA-II (Sabit)'}},
}};

function showTip(el){{
  const d=MD[el.id]; if(!d) return;
  const tip=document.getElementById('mapTip');
  const wr=document.getElementById('mapWrap').getBoundingClientRect();
  const er=el.getBoundingClientRect();
  const xp=Math.min(((er.left-wr.left)/wr.width)*100,55);
  const yp=Math.max(((er.top-wr.top+er.height)/wr.height)*100-5,2);
  tip.innerHTML=`<div style="font-weight:700;color:${{d.c}};margin-bottom:4px;font-size:.72rem">${{d.t}}</div><div style="color:#cbd5e1;margin-bottom:5px;font-size:.64rem;line-height:1.5">${{d.d}}</div><div style="background:#0f172a;border-radius:4px;padding:3px 7px;font-size:.6rem"><span style="color:#64748b">Parametreler: </span><b style="color:#f59e0b">${{d.p}}</b></div><div style="margin-top:4px;font-size:.58rem;color:${{d.s.includes('PurpleAir')?'#06b6d4':'#f59e0b'}}">● ${{d.s}}</div>`;
  tip.style.display='block';
  tip.style.left=xp+'%';
  tip.style.top=yp+'%';
  setTimeout(()=>{{tip.style.display='none';}},5000);
}}

// ── VERI AKIŞ ANİMASYONU ──
window.addEventListener('load',()=>{{
  const svg=document.getElementById('flowSvg');
  const wrap=document.getElementById('mapWrap');
  // marker positions in % (matching CSS left/top)
  const mpts=[
    {{x:.70,y:.42,c:'#10b981'}},
    {{x:.54,y:.35,c:'#10b981'}},
    {{x:.76,y:.37,c:'#3b82f6'}},
    {{x:.59,y:.28,c:'#a78bfa'}},
    {{x:.29,y:.53,c:'#8b5cf6'}},
    {{x:.48,y:.50,c:'#f59e0b'}},
  ];
  const sumer={{x:.64,y:.57}};

  // dashed lines
  mpts.forEach((p,i)=>{{
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',p.x*100); line.setAttribute('y1',p.y*100);
    line.setAttribute('x2',sumer.x*100); line.setAttribute('y2',sumer.y*100);
    line.setAttribute('stroke',p.c);
    line.setAttribute('stroke-width','0.5');
    line.setAttribute('stroke-dasharray','1.5 1.5');
    line.setAttribute('opacity','0.5');
    svg.appendChild(line);
  }});

  // particles
  mpts.forEach((p,i)=>{{
    const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('r','1.2');
    c.setAttribute('fill',p.c);
    svg.appendChild(c);
    const dur=2200+i*350;
    const delay=i*420;
    let start=null;
    function step(ts){{
      if(!start) start=ts+delay;
      const el=ts-start;
      if(el<0){{requestAnimationFrame(step);return;}}
      const t=(el%dur)/dur;
      const cx=p.x*100+(sumer.x-p.x)*100*t;
      const cy=p.y*100+(sumer.y-p.y)*100*t;
      const op=t<.1?t*10:t>.85?(1-t)*6.7:1;
      c.setAttribute('cx',cx.toFixed(2));
      c.setAttribute('cy',cy.toFixed(2));
      c.setAttribute('opacity',op.toFixed(2));
      c.setAttribute('r',(1.5*(1-t*.5)).toFixed(2));
      requestAnimationFrame(step);
    }}
    requestAnimationFrame(step);
  }});
}});

// ── CANLI ÖLÇÜM ──
const liveEl=document.getElementById('liveVal');
const locs2=['Derslik','Kantin','Lab','Kütüphane','Spor'];
const params2=[{{n:'PM₂.₅',u:'µg/m³',min:8,max:45}},{{n:'CO₂',u:'ppm',min:600,max:1400}},{{n:'UOB',u:'ppb',min:80,max:350}}];
let lI=0;
function upLive(){{
  const loc=locs2[Math.floor(Math.random()*locs2.length)];
  const p=params2[lI%3];lI++;
  const v=(p.min+Math.random()*(p.max-p.min)).toFixed(p.min>100?0:1);
  liveEl.innerHTML=`<span class="live-dot"></span> ${{loc}} · ${{p.n}}: ${{v}} ${{p.u}}`;
}}
upLive(); setInterval(upLive,2200);

// ── GAUGE ANİMASYON ──
const GC=[
  {{id:'gv1',gb:'gb1',min:5,max:60,v:22,wMax:60}},
  {{id:'gv2',gb:'gb2',min:500,max:1500,v:920,wMax:1500}},
  {{id:'gv3',gb:'gb3',min:50,max:400,v:180,wMax:400}},
  {{id:'gv4',gb:'gb4',min:5,max:50,v:18,wMax:50}},
  {{id:'gv5',gb:'gb5',min:.3,max:3,v:1.4,wMax:3}},
  {{id:'gv6',gb:'gb6',min:5,max:80,v:35,wMax:80}},
];
const gVals=GC.map(g=>g.v);
setTimeout(()=>{{
  GC.forEach((g,i)=>{{
    const el=document.getElementById(g.id);
    const bar=document.getElementById(g.gb);
    const v=gVals[i];
    el.textContent=v.toFixed(v<10?1:0);
    bar.style.width=Math.min(100,((v-g.min)/(g.wMax-g.min))*100)+'%';
  }});
}},600);
setInterval(()=>{{
  GC.forEach((g,i)=>{{
    gVals[i]+=(Math.random()-.48)*(g.max-g.min)*.05;
    gVals[i]=Math.max(g.min,Math.min(g.max,gVals[i]));
    document.getElementById(g.id).textContent=gVals[i].toFixed(gVals[i]<10?1:0);
    document.getElementById(g.gb).style.width=Math.min(100,((gVals[i]-g.min)/(g.wMax-g.min))*100)+'%';
  }});
}},1800);

// ── ÇİZGİ GRAFİĞİ ──
(function(){{
  const pts=50,W=700,H=110;
  const co2=[],pm=[],voc=[];
  for(let i=0;i<pts;i++){{
    const t=i/(pts-1);
    co2.push(400+600*Math.sin(t*Math.PI)+(Math.random()-.5)*60);
    pm.push(15+25*(Math.exp(-Math.pow((t-.15)/.1,2))+.6*Math.exp(-Math.pow((t-.75)/.12,2)))+Math.random()*5);
    voc.push(80+120*(Math.exp(-Math.pow((t-.05)/.08,2))+.9*Math.exp(-Math.pow((t-.55)/.09,2)))+Math.random()*20);
  }}
  function toPath(arr,mn,mx,top,bot){{
    return arr.map((v,i)=>{{
      const x=i/(arr.length-1)*W;
      const y=bot-((v-mn)/(mx-mn))*(bot-top);
      return (i===0?'M':'L')+x.toFixed(1)+','+y.toFixed(1);
    }}).join(' ');
  }}
  const co2p=toPath(co2,350,1100,5,32);
  const pmp =toPath(pm,0,60,36,63);
  const vocp=toPath(voc,0,280,67,95);
  document.getElementById('co2Path').setAttribute('d',co2p);
  document.getElementById('pmPath').setAttribute('d',pmp);
  document.getElementById('vocPath').setAttribute('d',vocp);
  document.getElementById('co2Fill').setAttribute('d',co2p+' L700,32 L0,32 Z');
  const co2el=document.getElementById('co2Path');
  const len=co2el.getTotalLength();
  co2el.style.strokeDasharray=len;co2el.style.strokeDashoffset=len;
  co2el.style.transition='stroke-dashoffset 2.8s ease-out';
  setTimeout(()=>{{co2el.style.strokeDashoffset='0';}},500);
  const pmEl=document.getElementById('pmPath');
  const plen=pmEl.getTotalLength();
  pmEl.style.strokeDasharray=plen;pmEl.style.strokeDashoffset=plen;
  pmEl.style.transition='stroke-dashoffset 2.8s ease-out .4s';
  setTimeout(()=>{{pmEl.style.strokeDashoffset='0';}},700);
  const dot=document.getElementById('moveDot');
  let dotT=0;
  function moveDot(){{
    dotT=(dotT+.0015)%1;
    const idx=Math.floor(dotT*(pts-1));
    const x=dotT*W;
    const v=co2[idx];
    const y=32-((v-350)/(1100-350))*27;
    dot.setAttribute('cx',x.toFixed(1));dot.setAttribute('cy',y.toFixed(1));
    requestAnimationFrame(moveDot);
  }}
  setTimeout(moveDot,3200);
}})();

// ── ÇUBUK GRAFİĞİ ──
setTimeout(()=>{{document.querySelectorAll('.bar-col').forEach(el=>{{el.style.height=el.dataset.h+'px';}});}},600);

// ── RING ANİMASYONLARI ──
window.addEventListener('load',()=>{{
  const C=2*Math.PI*24;
  [{{id:'r1',pct:.30}},{{id:'r2',pct:.35}},{{id:'r3',pct:.35}}].forEach(({{id,pct}})=>{{
    const el=document.getElementById(id);if(!el)return;
    setTimeout(()=>{{el.style.transition='stroke-dashoffset 1.6s ease-out';el.style.strokeDashoffset=C*(1-pct);}},700);
  }});
}});
</script>
</body>
</html>"""

out_path = os.path.join(folder, 'proje_animasyon.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

size = os.path.getsize(out_path)
print(f"OK — {size/1024:.0f} KB")
