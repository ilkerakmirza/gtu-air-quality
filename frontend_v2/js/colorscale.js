// PM2.5 renk skalası — her 5 µg/m³'de yeni renk ailesi, her 2.5'te koyu/açık
const PM25_SCALE = [
    { max:  2.5, color: "#004d00", label: "0–2.5 µg/m³"   },
    { max:  5,   color: "#00cc00", label: "2.5–5 µg/m³"   },
    { max:  7.5, color: "#4a9900", label: "5–7.5 µg/m³"   },
    { max: 10,   color: "#99ee00", label: "7.5–10 µg/m³"  },
    { max: 12.5, color: "#b8b800", label: "10–12.5 µg/m³" },
    { max: 15,   color: "#ffff00", label: "12.5–15 µg/m³" },
    { max: 17.5, color: "#cc8800", label: "15–17.5 µg/m³" },
    { max: 20,   color: "#ffcc00", label: "17.5–20 µg/m³" },
    { max: 22.5, color: "#cc4400", label: "20–22.5 µg/m³" },
    { max: 25,   color: "#ff8800", label: "22.5–25 µg/m³" },
    { max: 27.5, color: "#bb1100", label: "25–27.5 µg/m³" },
    { max: 30,   color: "#ff4400", label: "27.5–30 µg/m³" },
    { max: 35,   color: "#990000", label: "30–35 µg/m³"   },
    { max: 40,   color: "#ff0000", label: "35–40 µg/m³"   },
    { max: 47.5, color: "#660066", label: "40–47.5 µg/m³" },
    { max: 55,   color: "#bb44bb", label: "47.5–55 µg/m³" },
    { max: 75,   color: "#7e0023", label: "55–75 µg/m³"   },
    { max: Infinity, color: "#4a0015", label: ">75 µg/m³"  },
];

function pm25Color(v) {
    if (v == null || isNaN(v)) return "#8a93a6";
    for (const b of PM25_SCALE) if (v <= b.max) return b.color;
    return "#4a0015";
}

function pm25Label(v) {
    if (v == null || isNaN(v)) return "Veri yok";
    if (v <= 15)  return "İyi";
    if (v <= 25)  return "Orta";
    if (v <= 35)  return "Hassas gruplar için sağlıksız";
    if (v <= 55)  return "Sağlıksız";
    return "Tehlikeli";
}

function pm25Intensity(v, maxVal = 75) {
    if (v == null || isNaN(v)) return 0;
    return Math.min(v / maxVal, 1);
}

// ─────────────────────────────────────────────────────────────────
// CO₂ renk skalası (ppm) — kapalı alan hava kalitesi eşikleri
// Dış ortam ~420 ppm. 1000 üstü havalandırma yetersiz; 2000 üstü baş ağrısı/uyuşukluk.
// ─────────────────────────────────────────────────────────────────
const CO2_SCALE = [
    { max:  600,     color: "#00cc00", label: "<600 (çok iyi)"      },
    { max:  800,     color: "#99ee00", label: "600–800 (iyi)"       },
    { max: 1000,     color: "#ffff00", label: "800–1000 (kabul)"    },
    { max: 1400,     color: "#ffcc00", label: "1000–1400 (orta)"    },
    { max: 2000,     color: "#ff8800", label: "1400–2000 (kötü)"    },
    { max: 5000,     color: "#ff0000", label: "2000–5000 (çok kötü)" },
    { max: Infinity, color: "#bb44bb", label: ">5000 (tehlikeli)"   },
];

function co2Color(v) {
    if (v == null || isNaN(v)) return "#8a93a6";
    for (const b of CO2_SCALE) if (v <= b.max) return b.color;
    return "#bb44bb";
}

function co2Label(v) {
    if (v == null || isNaN(v)) return "Veri yok";
    if (v <= 800)  return "İyi havalandırma";
    if (v <= 1000) return "Kabul edilebilir";
    if (v <= 1400) return "Havalandırma zayıf";
    if (v <= 2000) return "Havalandırma yetersiz";
    return "Tehlikeli — havalandır";
}

function buildLegend() {
    const cells = PM25_SCALE.slice(0, 17).map(b => `<span style="background:${b.color}"></span>`).join("");
    const ticks = [0,5,10,15,20,25,30,40,55,75].map(t =>
        `<span style="left:${Math.min(t/75*100,100).toFixed(1)}%">${t}</span>`).join("");
    return `
      <div class="legend-title">PM₂.₅ <span style="text-transform:none">(µg/m³)</span> — her 2.5'te ton, her 5'te renk değişir</div>
      <div class="legend-bar">${cells}</div>
      <div class="legend-ticks">${ticks}</div>
      <div class="legend-cats">
        <span style="color:#00cc00">İyi</span>
        <span style="color:#ffff00">Orta</span>
        <span style="color:#ff8800">Hassas</span>
        <span style="color:#ff0000">Sağlıksız</span>
        <span style="color:#bb44bb">Tehlikeli</span>
      </div>`;
}
