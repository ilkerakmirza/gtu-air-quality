// PM2.5 renk skalası
// Her 5 µg/m³'de yeni renk ailesi, her 2.5 µg/m³'de koyu → açık geçiş
const PM25_SCALE = [
    // ── YEŞİL (0–5) ──────────────────────────────────────────
    { max:  2.5, color: "#004d00", label: "0–2.5 µg/m³"   },  // koyu yeşil
    { max:  5,   color: "#00cc00", label: "2.5–5 µg/m³"   },  // açık yeşil
    // ── LİME (5–10) ──────────────────────────────────────────
    { max:  7.5, color: "#4a9900", label: "5–7.5 µg/m³"   },  // koyu lime
    { max: 10,   color: "#99ee00", label: "7.5–10 µg/m³"  },  // açık lime
    // ── SARI (10–15) ─────────────────────────────────────────
    { max: 12.5, color: "#b8b800", label: "10–12.5 µg/m³" },  // koyu sarı
    { max: 15,   color: "#ffff00", label: "12.5–15 µg/m³" },  // açık sarı
    // ── AMBER (15–20) ────────────────────────────────────────
    { max: 17.5, color: "#cc8800", label: "15–17.5 µg/m³" },  // koyu amber
    { max: 20,   color: "#ffcc00", label: "17.5–20 µg/m³" },  // açık amber
    // ── TURUNCU (20–25) ──────────────────────────────────────
    { max: 22.5, color: "#cc4400", label: "20–22.5 µg/m³" },  // koyu turuncu
    { max: 25,   color: "#ff8800", label: "22.5–25 µg/m³" },  // açık turuncu
    // ── KIRMIZI-TURUNCU (25–30) ──────────────────────────────
    { max: 27.5, color: "#bb1100", label: "25–27.5 µg/m³" },  // koyu
    { max: 30,   color: "#ff4400", label: "27.5–30 µg/m³" },  // açık
    // ── KIRMIZI (30–40) ──────────────────────────────────────
    { max: 35,   color: "#990000", label: "30–35 µg/m³"   },  // koyu kırmızı
    { max: 40,   color: "#ff0000", label: "35–40 µg/m³"   },  // açık kırmızı
    // ── MOR (40–55) ──────────────────────────────────────────
    { max: 47.5, color: "#660066", label: "40–47.5 µg/m³" },  // koyu mor
    { max: 55,   color: "#bb44bb", label: "47.5–55 µg/m³" },  // açık mor
    // ── BORDO (55+) ──────────────────────────────────────────
    { max: 75,   color: "#7e0023", label: "55–75 µg/m³"   },
    { max: Infinity, color: "#4a0015", label: ">75 µg/m³"  },
];

function pm25Color(value) {
    if (value == null || isNaN(value)) return "#aaaaaa";
    for (const band of PM25_SCALE) {
        if (value <= band.max) return band.color;
    }
    return "#4a0015";
}

function pm25Label(value) {
    if (value == null || isNaN(value)) return "Veri yok";
    for (const band of PM25_SCALE) {
        if (value <= band.max) return band.label;
    }
    return ">75 µg/m³";
}

function pm25Category(value) {
    if (value == null || isNaN(value)) return "unknown";
    if (value <= 15)  return "good";
    if (value <= 35)  return "moderate";
    if (value <= 55)  return "sensitive";
    if (value <= 150) return "unhealthy";
    return "hazardous";
}

// Normalise a PM2.5 value to 0-1 for Leaflet.heat intensity
function pm25Intensity(value, maxVal = 75) {
    if (value == null || isNaN(value)) return 0;
    return Math.min(value / maxVal, 1);
}

// Legend: her bantı göster
function buildLegend() {
    // Gradient için renk durakları
    const stops = PM25_SCALE.map(b => b.color).join(", ");
    const ticks = [
        { val: 0,    label: "0"   },
        { val: 5,    label: "5"   },
        { val: 10,   label: "10"  },
        { val: 15,   label: "15"  },
        { val: 20,   label: "20"  },
        { val: 25,   label: "25"  },
        { val: 30,   label: "30"  },
        { val: 40,   label: "40"  },
        { val: 55,   label: "55"  },
        { val: 75,   label: "75+" },
    ];
    const maxVal = 75;
    const ticksHtml = ticks.map(t => {
        const pct = Math.min(t.val / maxVal * 100, 100).toFixed(1);
        return `<span class="legend-tick" style="left:${pct}%">${t.label}</span>`;
    }).join("");

    return `
        <div class="legend-title">PM₂.₅ (µg/m³) — Her 2.5 µg/m³'de koyu/açık, her 5 µg/m³'de renk değişir</div>
        <div class="legend-gradient" style="background:linear-gradient(to right,${stops})"></div>
        <div class="legend-ticks">${ticksHtml}</div>
        <div class="legend-labels" style="display:flex;justify-content:space-between;font-size:9px;color:#8b949e;margin-top:14px">
            <span style="color:#00cc00">İyi</span>
            <span style="color:#ffff00">Orta</span>
            <span style="color:#ff8800">Hassas</span>
            <span style="color:#ff0000">Sağlıksız</span>
            <span style="color:#bb44bb">Tehlikeli</span>
        </div>`;
}
