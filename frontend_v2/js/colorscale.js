// Ekranda gösterilen sayılar Türkçe biçimde: tek ondalık, virgül (12,3). Boş değerde null döner (?? "--" ile kullanılır).
function f1tr(v) {
    return v == null || isNaN(v) ? null : (+v).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

// ─────────────────────────────────────────────────────────────────
// PurpleAir PM₂.₅ düzeltmesi: US EPA genişletilmiş ABD geneli düzeltmesi (AirNow Yangın ve Duman Haritası'nın uyguladığı biçim).
// Kaynaklar ve gerekçe: docs/purpleair_epa_duzeltmesi.md. Kısaca: optik sensör ham değeri referans cihazlara göre yaklaşık
// %40 yüksek okur ve nemden etkilenir (Barkjohn vd. 2021). Girdi: x = PurpleAir cf_atm PM₂.₅ (A ve B kanal ortalaması, µg/m³),
// rh = PurpleAir'in kendi nem ölçümü (%). Formül cf_1 verisiyle geliştirildi; EPA haritada cf_atm'ye uygular (iki değer
// ~25–28 µg/m³'e kadar aynı, yüksek derişimde cf_atm ≈ 2/3 × cf_1; 0,786 = 0,524 × 1,5). Ara bölgelerde ağırlıklı geçiş vardır.
// ─────────────────────────────────────────────────────────────────
function epaPM25(x, rh) {
    if (x == null || isNaN(x)) return null;
    x = +x;
    if (rh == null || isNaN(rh) || rh < 0 || rh > 100) rh = 50;   // EPA: nem eksik ya da 0–100 dışındaysa %50 alınır
    let y;
    if (x < 30)       y = 0.524 * x - 0.0862 * rh + 5.75;
    else if (x < 50)  { const w = x / 20 - 1.5;  y = (0.786 * w + 0.524 * (1 - w)) * x - 0.0862 * rh + 5.75; }
    else if (x < 210) y = 0.786 * x - 0.0862 * rh + 5.75;
    else if (x < 260) { const w = x / 50 - 4.2;  y = (0.69 * w + 0.786 * (1 - w)) * x - 0.0862 * rh * (1 - w)
                                                    + 2.966 * w + 5.75 * (1 - w) + 8.84e-4 * x * x * w; }
    else              y = 2.966 + 0.69 * x + 8.84e-4 * x * x;
    return Math.max(0, y);   // derişim negatif olamaz (çok temiz ve nemli havada formül 0'ın altına inebilir; uygulama kuralı)
}

// EPA kalite kontrolü: A ve B kanalları hem ≥ 5 µg/m³ hem ≥ %70 (göreli fark, iki kanalın ortalamasına göre) ayrışırsa ölçüm
// geçersizdir. Dönüş: true = uyumlu, false = geçersiz, null = kanal verisi yok (değerlendirilemedi).
function paChannelsAgree(a, b) {
    if (a == null || b == null || isNaN(a) || isNaN(b)) return null;
    const d = Math.abs(a - b), m = (+a + +b) / 2;
    return !(d >= 5 && m > 0 && d / m >= 0.70);
}

// PurpleAir kaydını düzeltilmiş değere çevirir (api.js tek yerden çağırır). Ham değer pm2_5_raw'da kalır;
// kanallar uyuşmuyorsa pm2_5 = null olur ve o kayıt hesaplara girmez.
function paCorrect(r) {
    if (!r || r._epa) return r;
    const raw = r.pm2_5 != null && !isNaN(r.pm2_5) ? +r.pm2_5 : null;
    const ok = paChannelsAgree(r.pm2_5_a, r.pm2_5_b);
    r.pm2_5_raw = raw;
    r.qa_ab = ok;
    r.pm2_5 = raw == null || ok === false ? null : epaPM25(raw, r.humidity_pct);
    r._epa = true;
    return r;
}

// Cihaz (seri) renkleri: her grafikte aynı cihaz aynı renk. Üçü birlikte veri görselleştirme doğrulayıcısından geçti
// (koyu zemin #0f1726, tüm ikililer: renk körlüğü ΔE ≥ 14,5, normal görüş ΔE ≥ 19,3, kontrast ≥ 3:1).
const DEVICE_COLOR = { purpleair: "#6380f0", tuzla: "#bf8418", atmotube: "#2fa79a" };

// PM₂.₅ rengi = HKİ sınıf rengi (uygulamanın her yerinde tek renk sistemi; sınıf adı ile renk hiç çelişmez)
function pm25Color(v) {
    const h = hki(v);
    return h ? h.renk : "#8a93a6";
}

// Ulusal Hava Kalitesi İndeksi (HKİ), PM₂.₅: ÇŞB'nin EPA indeksinden uyarladığı ulusal tablo
// (İBB Çevre Koruma ve Kontrol Dairesi yayımı). Kesim noktaları 24 saatlik ortalamalar için tanımlıdır.
// I = (I_üst − I_alt) / (C_üst − C_alt) × (C − C_alt) + I_alt   (C, 0,1 µg/m³'e kesilir)
const HKI_PM25 = [
    { ilo: 0,   ihi: 50,  clo: 0,     chi: 12.0,  ad: "İyi",       renk: "#00cc00", yuz: "laugh" },
    { ilo: 51,  ihi: 100, clo: 12.1,  chi: 35.4,  ad: "Orta",      renk: "#ffcc00", yuz: "smile" },
    { ilo: 101, ihi: 150, clo: 35.5,  chi: 55.4,  ad: "Hassas",    renk: "#ff8800", yuz: "meh" },
    { ilo: 151, ihi: 200, clo: 55.5,  chi: 150.4, ad: "Sağlıksız", renk: "#ff0000", yuz: "frown" },
    { ilo: 201, ihi: 300, clo: 150.5, chi: 250.4, ad: "Kötü",      renk: "#bb44bb", yuz: "annoyed" },
    { ilo: 301, ihi: 500, clo: 250.5, chi: 500.4, ad: "Tehlikeli", renk: "#7e0023", yuz: "angry" },
];
function hki(v) {
    if (v == null || isNaN(v)) return null;
    const c = Math.max(0, Math.floor(+v * 10) / 10);
    const k = HKI_PM25.findIndex(b => c <= b.chi), b = HKI_PM25[k < 0 ? HKI_PM25.length - 1 : k];
    const i = k < 0 ? 500 : Math.round((b.ihi - b.ilo) / (b.chi - b.clo) * (c - b.clo) + b.ilo);
    return { ...b, i, k: k < 0 ? HKI_PM25.length - 1 : k };
}

function pm25Label(v) {
    const h = hki(v);
    return h ? h.ad : "Veri yok";
}

function pm25Intensity(v, maxVal = 75) {
    if (v == null || isNaN(v)) return 0;
    return Math.min(v / maxVal, 1);
}

// ─────────────────────────────────────────────────────────────────
// CO₂ renk skalası (ppm) — havalandırma göstergesi eşikleri (yaygın uygulama; kaynakları docs/hesaplama_ve_kaynaklar.md §8)
// Dış ortam ~420 ppm. WHO COVID havalandırma rehberi <800 ppm hedefler;
// dünyada en yaygın iç mekân sınırı 1000 ppm. 1000+ bilişsel düşüş,
// 1500+ uyuşukluk/baş ağrısı, 5000 ppm 8 saatlik mesleki maruziyet sınırı (OSHA).
// ─────────────────────────────────────────────────────────────────
const CO2_SCALE = [
    { max:  600,     color: "#00cc00", label: "<600 — mükemmel (dış ortam ~420)" },
    { max:  800,     color: "#99ee00", label: "600–800 — iyi"                     },
    { max: 1000,     color: "#ffff00", label: "800–1000 — yeterli havalandırma"  },
    { max: 1500,     color: "#ffaa00", label: "1000–1500 — zayıf (iyileştir)"    },
    { max: 2000,     color: "#ff6600", label: "1500–2000 — kötü (uyuşukluk)"     },
    { max: 5000,     color: "#ee0000", label: "2000–5000 — çok kötü"             },
    { max: Infinity, color: "#990099", label: ">5000 — tehlikeli (mesleki sınır)" },
];

function co2Color(v) {
    if (v == null || isNaN(v)) return "#8a93a6";
    for (const b of CO2_SCALE) if (v <= b.max) return b.color;
    return "#990099";
}

function co2Label(v) {
    if (v == null || isNaN(v)) return "Veri yok";
    if (v <= 600)  return "Mükemmel havalandırma";
    if (v <= 800)  return "İyi havalandırma";
    if (v <= 1000) return "Yeterli havalandırma";
    if (v <= 1500) return "Havalandırma zayıf — iyileştir";
    if (v <= 2000) return "Yetersiz — uyuşukluk/baş ağrısı";
    return "Tehlikeli — acil havalandır";
}

// Lejant için kompakt CO₂ şeridi (chip'lerdeki sayı = bandın üst sınırı, ppm)
function buildCO2Legend() {
    const chips = [
        ["#00cc00", "600"], ["#99ee00", "800"], ["#ffff00", "1000"],
        ["#ffaa00", "1500"], ["#ff6600", "2000"], ["#ee0000", "5000"], ["#990099", "5000+"],
    ].map(([c, t], i) =>
        `<span style="background:${c};color:${i >= 5 ? "#fff" : "#0b0e14"}">${t}</span>`).join("");
    return `
      <div class="legend-title" style="margin-top:9px">CO₂ (ppm) — havalandırma göstergesi</div>
      <div class="legend-co2">${chips}</div>`;
}

// Harita lejandı: tek ölçek = HKİ'nin 6 sınıfı (renk, ad, PM₂.₅ aralığı). Haritadaki her PM₂.₅ rengi bu tablodan gelir.
function buildLegend() {
    const rng = b => b.chi > 500 ? `${f1tr(b.clo)}+` : `${b.clo === 0 ? "0" : f1tr(b.clo)}–${f1tr(b.chi)}`;
    const rows = HKI_PM25.map(b =>
        `<span><i style="background:${b.renk}"></i><b>${b.ad}</b><em>${rng(b)}</em></span>`).join("");
    return `
      <div class="legend-title">PM₂.₅ (µg/m³) · HKİ sınıfları</div>
      <div class="legend-hki6">${rows}</div>
      <div class="legend-note">Ulusal Hava Kalitesi İndeksi (ÇŞB). PurpleAir değerleri US EPA düzeltmelidir.</div>`;
}
