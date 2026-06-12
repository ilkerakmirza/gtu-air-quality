// GTÜ Hava Kalitesi Platformu v2 — ana uygulama
// Bağımlılıklar: Leaflet, Leaflet.heat, Chart.js, colorscale.js, api.js

const GTU_CENTER = [40.806155, 29.360985];
const GTU_ZOOM = 17;
const CAMPUS_BOUNDS = [[40.797, 29.348], [40.820, 29.378]];

// Kişi grupları: oturum adı önekine göre renk + etiket
const PEOPLE = [
    { key: "Ayse",  name: "Ayşe",  color: "#34d27b", initial: "A" },
    { key: "Ilker", name: "İlker", color: "#6c8cff", initial: "İ" },
    { key: "Serra", name: "Serra", color: "#f5b840", initial: "S" },
];

let map, heatLayer, dotsLayer, trailLayer, paMarker, campusOverlay;
let allSessions = [];
let cmpChart = null;

// PurpleAir senkronizasyon durumu
let paHistory = [];     // animasyon sırasındaki geçmiş PA verisi
let paLive = true;

// ─────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
    initMap();
    initSidebar();
    initPlayerUI();
    initChartDrawer();

    document.getElementById("legend").innerHTML = buildLegend();

    // İlk yükleme: backend uyanana kadar dene
    await wakeBackend();
    document.getElementById("boot").classList.add("gone");

    loadPurpleAir();
    loadSessions();
    loadHeatmap();
    startCountdown();
});

async function wakeBackend() {
    const el = document.getElementById("boot-status");
    for (let i = 0; i < 12; i++) {
        try { await API.sessions(); return; }
        catch (_) {
            el.textContent = `Sunucu uyandırılıyor… (${(i+1)*10} sn)`;
            await new Promise(r => setTimeout(r, 10000));
        }
    }
    el.textContent = "Sunucuya ulaşılamadı — sayfayı yenileyin.";
}

// ─────────────────────────────────────────────────────────────────
// Harita
// ─────────────────────────────────────────────────────────────────

function initMap() {
    map = L.map("map", { center: GTU_CENTER, zoom: GTU_ZOOM, zoomControl: false });
    L.control.zoom({ position: "bottomleft" }).addTo(map);

    const sat = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { attribution: "© Esri, Maxar", maxZoom: 20 });
    const labels = L.tileLayer(
        "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 20 });
    L.layerGroup([sat, labels]).addTo(map);

    campusOverlay = L.imageOverlay("images/campus_map_22TR.jpg", CAMPUS_BOUNDS,
        { opacity: 0.55, interactive: false });

    dotsLayer  = L.layerGroup().addTo(map);
    trailLayer = L.layerGroup().addTo(map);
    heatLayer  = L.heatLayer([], { radius: 26, blur: 16, maxZoom: 17, gradient: {
        0.0: "#00cc00", 0.2: "#ffff00", 0.4: "#ff8800", 0.7: "#ff0000", 1.0: "#bb44bb",
    }});
}

// ─────────────────────────────────────────────────────────────────
// PurpleAir canlı panel
// ─────────────────────────────────────────────────────────────────

async function loadPurpleAir() {
    try {
        const res = await API.purpleairLatest();
        updatePAPanel(res.data);
        updatePAMarker(res.data);
    } catch (e) {
        document.getElementById("pa-cat").textContent = "Bağlantı hatası";
    }
}

function updatePAPanel(d) {
    const set = (id, v) => document.getElementById(id).textContent = v;
    if (!d) { set("pa-pm25", "--"); set("pa-cat", "Veri yok"); return; }

    set("pa-pm25", d.pm2_5 != null ? d.pm2_5.toFixed(1) : "--");
    document.getElementById("pa-pm25").style.color = pm25Color(d.pm2_5);

    const cat = document.getElementById("pa-cat");
    cat.textContent = pm25Label(d.pm2_5);
    cat.style.color = pm25Color(d.pm2_5);

    set("pa-pm10", d.pm10_0 != null ? d.pm10_0.toFixed(1) : "--");
    set("pa-temp", d.temperature_c != null ? d.temperature_c.toFixed(1) + "°" : "--");
    set("pa-hum",  d.humidity_pct != null ? d.humidity_pct.toFixed(0) + "%" : "--");
    set("pa-time", d.recorded_at ? new Date(d.recorded_at).toLocaleString("tr-TR") : "—");
}

function updatePAMarker(d) {
    if (!d) return;
    const latlng = [d.lat || GTU_CENTER[0], d.lon || GTU_CENTER[1]];
    const html = `<b>🟣 PurpleAir PA-II</b><br>SUMER Lab — GTÜ Çatı<br>PM₂.₅: <b style="color:${pm25Color(d.pm2_5)}">${d.pm2_5?.toFixed(1) ?? "--"}</b> µg/m³`;
    const icon = L.divIcon({
        className: "",
        html: `<div class="pulse-marker" style="--marker-color:${pm25Color(d.pm2_5)}"></div>`,
        iconSize: [20, 20], iconAnchor: [10, 10],
    });
    if (!paMarker) {
        paMarker = L.marker(latlng, { icon, zIndexOffset: 500 }).addTo(map)
            .bindTooltip(html, { permanent: true, direction: "top", offset: [0, -14], className: "pa-label" });
    } else {
        paMarker.setIcon(icon);
        paMarker.setTooltipContent(html);
    }
}

function setPABadge(mode, dateLabel) {
    const b = document.getElementById("pa-badge");
    if (mode === "live") {
        b.innerHTML = `<span class="live-dot"></span>CANLI`;
        b.style.cssText = "";
    } else {
        b.innerHTML = `⏪ ${dateLabel || "GEÇMİŞ"}`;
        b.style.background = "rgba(245,184,64,0.12)";
        b.style.borderColor = "rgba(245,184,64,0.4)";
        b.style.color = "#f5b840";
    }
}

function startCountdown() {
    let s = 120;
    setInterval(() => {
        if (!paLive) return;
        s--;
        if (s <= 0) { s = 120; loadPurpleAir(); }
        document.getElementById("pa-countdown").textContent = `↻ ${s}s`;
    }, 1000);
}

// ─────────────────────────────────────────────────────────────────
// Oturumlar — kişiye göre gruplu liste
// ─────────────────────────────────────────────────────────────────

function personOf(sessionName) {
    for (const p of PEOPLE) if (sessionName.startsWith(p.key)) return p;
    return { key: "Other", name: "Diğer", color: "#8a93a6", initial: "•" };
}

function dateLabelOf(s) {
    // start_time'dan gün etiketi üret
    if (!s.start_time) return s.session_name;
    const d = new Date(s.start_time.replace(" ", "T"));
    return d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

async function loadSessions() {
    try {
        const res = await API.sessions();
        allSessions = res.data || [];
        renderSessionGroups();
        updateChips();
        refreshDots();
    } catch (e) {
        document.getElementById("session-list").innerHTML =
            `<div style="color:var(--red);font-size:12px">Oturumlar yüklenemedi</div>`;
    }
}

function renderSessionGroups() {
    const wrap = document.getElementById("session-list");
    const groups = new Map();
    for (const s of allSessions) {
        const p = personOf(s.session_name);
        if (!groups.has(p.key)) groups.set(p.key, { person: p, sessions: [] });
        groups.get(p.key).sessions.push(s);
    }

    wrap.innerHTML = [...groups.values()].map(({ person, sessions }) => `
      <div class="person-group open" data-person="${person.key}">
        <div class="person-head">
          <div class="person-avatar" style="background:${person.color}">${person.initial}</div>
          <span class="person-name">${person.name}</span>
          <span class="person-count">${sessions.length} gün · ${sessions.reduce((a,s)=>a+(s.reading_count||0),0)} ölçüm</span>
          <span class="person-arrow">▶</span>
        </div>
        <div class="person-sessions">
          ${sessions.map(s => `
            <div class="session-item">
              <input type="checkbox" class="s-cb" value="${s.id}" checked>
              <span class="session-date">${dateLabelOf(s)}</span>
              <span class="session-n">${s.reading_count ?? 0}</span>
              <button class="session-play" data-sid="${s.id}" title="Bu günü oynat">▶</button>
            </div>`).join("")}
        </div>
      </div>`).join("");

    wrap.querySelectorAll(".person-head").forEach(h =>
        h.addEventListener("click", () => h.parentElement.classList.toggle("open")));
    wrap.querySelectorAll(".s-cb").forEach(cb =>
        cb.addEventListener("change", refreshDots));
    wrap.querySelectorAll(".session-play").forEach(btn =>
        btn.addEventListener("click", (e) => { e.stopPropagation(); startPlayback(+btn.dataset.sid); }));
}

function updateChips() {
    const total = allSessions.reduce((a, s) => a + (s.reading_count || 0), 0);
    document.querySelector("#chip-readings b").textContent = total.toLocaleString("tr-TR");
    document.querySelector("#chip-sessions b").textContent = allSessions.length;
}

// ─────────────────────────────────────────────────────────────────
// Ölçüm noktaları + istatistik
// ─────────────────────────────────────────────────────────────────

async function refreshDots() {
    const ids = [...document.querySelectorAll(".s-cb:checked")].map(cb => +cb.value);
    dotsLayer.clearLayers();
    setStats([]);
    if (!ids.length) return;

    try {
        const res = await API.mapTracks(ids);
        const allPts = [];
        for (const track of res.tracks || []) {
            const person = personOf(track.session_name);
            for (const pt of (track.points || []).filter(p => p.lat && p.lon)) {
                allPts.push(pt);
                if (!document.getElementById("tg-dots").checked) continue;
                L.circleMarker([pt.lat, pt.lon], {
                    radius: 6.5,
                    color: "rgba(255,255,255,0.55)", weight: 1,
                    fillColor: pm25Color(pt.pm2_5), fillOpacity: 0.88,
                }).bindPopup(`
                    <div style="font-family:Inter;min-width:170px">
                      <div style="display:flex;align-items:center;gap:7px;margin-bottom:6px">
                        <span style="width:20px;height:20px;border-radius:6px;background:${person.color};display:grid;place-items:center;font-size:10px;font-weight:800;color:#0b0e14">${person.initial}</span>
                        <b style="font-size:12.5px">${track.session_name}</b>
                      </div>
                      <div style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:${pm25Color(pt.pm2_5)}">${pt.pm2_5?.toFixed(1) ?? "--"} <span style="font-size:10px;color:#9aa4b8">µg/m³</span></div>
                      <div style="font-size:11px;color:${pm25Color(pt.pm2_5)};font-weight:600">${pm25Label(pt.pm2_5)}</div>
                      <div style="font-size:10.5px;color:#9aa4b8;margin-top:4px">${pt.recorded_at ? new Date(pt.recorded_at).toLocaleString("tr-TR") : ""}</div>
                    </div>`)
                  .addTo(dotsLayer);
            }
        }
        setStats(allPts);
    } catch (e) { console.error("[tracks]", e); }
}

function setStats(pts) {
    const vals = pts.map(p => p.pm2_5).filter(v => v != null);
    const set = (id, v) => document.getElementById(id).textContent = v;
    if (!vals.length) { set("st-count","—"); set("st-avg","—"); set("st-max","—"); return; }
    const avg = vals.reduce((a,b)=>a+b,0)/vals.length;
    const max = Math.max(...vals);
    set("st-count", vals.length.toLocaleString("tr-TR"));
    set("st-avg", avg.toFixed(1));
    document.getElementById("st-avg").style.color = pm25Color(avg);
    set("st-max", max.toFixed(1));
    document.getElementById("st-max").style.color = pm25Color(max);
}

// ─────────────────────────────────────────────────────────────────
// Heatmap + katman anahtarları
// ─────────────────────────────────────────────────────────────────

async function loadHeatmap() {
    try {
        const res = await API.mapHeatmap("pm2_5");
        heatLayer.setLatLngs((res.points || []).map(p => [p.lat, p.lon, pm25Intensity(p.value)]));
    } catch (_) {}
}

function initSidebar() {
    document.getElementById("tg-heat").addEventListener("change", e =>
        e.target.checked ? heatLayer.addTo(map) : map.removeLayer(heatLayer));
    document.getElementById("tg-campus").addEventListener("change", e =>
        e.target.checked ? campusOverlay.addTo(map) : map.removeLayer(campusOverlay));
    document.getElementById("tg-dots").addEventListener("change", refreshDots);

    const sb = document.getElementById("sidebar");
    document.getElementById("sidebar-toggle").addEventListener("click", () => sb.classList.remove("hidden"));
}

// ─────────────────────────────────────────────────────────────────
// Gün animasyonu (oynatıcı)
// ─────────────────────────────────────────────────────────────────

const Player = {
    pts: [], idx: 0, timer: null, speed: 4, marker: null, session: null,

    load(points, session) {
        this.stop();
        this.pts = points;
        this.session = session;
        this.idx = 0;
    },
    play() {
        if (!this.pts.length || this.timer) return;
        this.timer = setInterval(() => this.step(), 1000 / this.speed);
        document.getElementById("pl-play").textContent = "⏸";
    },
    pause() {
        clearInterval(this.timer); this.timer = null;
        document.getElementById("pl-play").textContent = "▶";
    },
    stop() {
        this.pause();
        this.idx = 0;
        trailLayer.clearLayers();
        if (this.marker) { map.removeLayer(this.marker); this.marker = null; }
    },
    setSpeed(s) { this.speed = s; if (this.timer) { this.pause(); this.play(); } },
    seek(frac) {
        if (!this.pts.length) return;
        this.idx = Math.max(0, Math.min(Math.floor(frac * this.pts.length), this.pts.length - 1));
        this.render(this.pts[this.idx]);
        onStep(this.pts[this.idx], this.idx, this.pts.length);
    },
    step() {
        if (this.idx >= this.pts.length) { this.finish(); return; }
        const pt = this.pts[this.idx];
        this.render(pt);
        onStep(pt, this.idx, this.pts.length);
        this.idx++;
    },
    finish() {
        this.pause();
        paLive = true; paHistory = [];
        setPABadge("live");
        loadPurpleAir();
    },
    render(pt) {
        const color = pm25Color(pt.pm2_5);
        if (this.idx > 0) {
            const prev = this.pts[this.idx - 1];
            L.circleMarker([prev.lat, prev.lon], {
                radius: 5.5, color: pm25Color(prev.pm2_5), weight: 1,
                fillColor: pm25Color(prev.pm2_5), fillOpacity: 0.82,
            }).addTo(trailLayer);
        }
        const icon = L.divIcon({
            className: "",
            html: `<div class="player-dot" style="background:${color};box-shadow:0 0 0 5px ${color}44,0 0 16px ${color}99"></div>`,
            iconSize: [16, 16], iconAnchor: [8, 8],
        });
        if (!this.marker) this.marker = L.marker([pt.lat, pt.lon], { icon, zIndexOffset: 1000 }).addTo(map);
        else { this.marker.setLatLng([pt.lat, pt.lon]); this.marker.setIcon(icon); }
    },
};

async function startPlayback(sessionId) {
    const session = allSessions.find(s => s.id === sessionId);
    if (!session) return;

    const res = await API.sessionReadings(sessionId);
    const pts = (res.data || [])
        .filter(r => r.lat && r.lon && r.pm2_5 != null)
        .sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));
    if (!pts.length) { alert("Bu oturumda GPS verisi yok."); return; }

    Player.load(pts, session);

    // Dock'u göster ve etiketle
    const dock = document.getElementById("player-dock");
    dock.classList.add("visible");
    const person = personOf(session.session_name);
    const tag = document.getElementById("pl-tag");
    tag.textContent = `${person.name} — ${dateLabelOf(session)}`;
    tag.style.background = person.color + "22";
    tag.style.color = person.color;

    // O günün PurpleAir geçmişini çek
    paHistory = []; paLive = false;
    const day = pts[0].recorded_at.slice(0, 10);
    setPABadge("hist", new Date(day).toLocaleDateString("tr-TR", { day: "numeric", month: "short" }));
    try {
        const hist = await API.purpleairHistory(day + "T00:00:00", day + "T23:59:59", "raw");
        paHistory = (hist.data || []).map(r => ({ ...r, ts: new Date(r.recorded_at).getTime() }));
    } catch (_) {}

    // Karşılaştırma grafiği
    loadCompareChart(pts, paHistory, person);

    // Statik noktaları gizle, animasyonu başlat
    dotsLayer.clearLayers();
    map.flyTo([pts[0].lat, pts[0].lon], 17, { duration: 1 });
    Player.play();
}

function nearestPA(ts) {
    if (!paHistory.length) return null;
    let best = paHistory[0], bd = Math.abs(ts - best.ts);
    for (const r of paHistory) {
        const d = Math.abs(ts - r.ts);
        if (d < bd) { best = r; bd = d; }
    }
    return bd < 10 * 60 * 1000 ? best : null;
}

function onStep(pt, idx, total) {
    const dt = new Date(pt.recorded_at);
    document.getElementById("pl-time").textContent =
        dt.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
    document.getElementById("pl-loc").textContent =
        pt.activity || `${pt.lat.toFixed(5)}, ${pt.lon.toFixed(5)}`;

    const pmEl = document.getElementById("pl-pm");
    pmEl.style.color = pm25Color(pt.pm2_5);
    pmEl.innerHTML = `${pt.pm2_5.toFixed(1)}<small>ATMOTUBE PM₂.₅ µg/m³</small>`;

    document.getElementById("pl-fill").style.width = `${(idx / (total - 1) * 100).toFixed(1)}%`;

    // PurpleAir senkronizasyonu
    const pa = nearestPA(dt.getTime());
    const paEl = document.getElementById("pl-pa");
    if (pa) {
        paEl.textContent = pa.pm2_5?.toFixed(1) ?? "--";
        paEl.style.color = pm25Color(pa.pm2_5);
        updatePAPanel(pa);
        updatePAMarker({ ...pa, lat: GTU_CENTER[0], lon: GTU_CENTER[1] });
    } else {
        paEl.textContent = "--";
    }

    updateChartCursor(idx);

    if (idx === total - 1) Player.finish();
}

function initPlayerUI() {
    document.getElementById("pl-play").addEventListener("click", () =>
        Player.timer ? Player.pause() : Player.play());
    document.getElementById("pl-restart").addEventListener("click", () => {
        Player.stop(); Player.play();
    });
    document.getElementById("pl-close").addEventListener("click", () => {
        Player.stop();
        document.getElementById("player-dock").classList.remove("visible");
        paLive = true; paHistory = [];
        setPABadge("live");
        loadPurpleAir();
        refreshDots();
    });
    document.querySelectorAll(".speed-btn").forEach(b =>
        b.addEventListener("click", () => {
            document.querySelectorAll(".speed-btn").forEach(x => x.classList.remove("active"));
            b.classList.add("active");
            Player.setSpeed(+b.dataset.speed);
        }));
    const prog = document.getElementById("pl-progress");
    prog.addEventListener("click", (e) => {
        const r = prog.getBoundingClientRect();
        Player.seek((e.clientX - r.left) / r.width);
    });
}

// ─────────────────────────────────────────────────────────────────
// Karşılaştırma grafiği
// ─────────────────────────────────────────────────────────────────

function initChartDrawer() {
    const drawer = document.getElementById("chart-drawer");
    document.getElementById("chart-handle").addEventListener("click", () => {
        drawer.classList.toggle("collapsed");
        if (!drawer.classList.contains("collapsed") && cmpChart) cmpChart.resize();
    });
}

function loadCompareChart(atmoPts, paHist, person) {
    const labels = atmoPts.map(r =>
        new Date(r.recorded_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }));
    const atmoVals = atmoPts.map(r => r.pm2_5);
    const paVals = atmoPts.map(r => {
        const pa = nearestPAIn(paHist, new Date(r.recorded_at).getTime());
        return pa ? pa.pm2_5 : null;
    });

    // Avantaj rozeti
    const am = atmoVals.reduce((a,b)=>a+b,0)/atmoVals.length;
    const pf = paVals.filter(v=>v!=null);
    const badge = document.getElementById("adv-badge");
    if (pf.length) {
        const pm = pf.reduce((a,b)=>a+b,0)/pf.length;
        const diff = Math.abs(am - pm).toFixed(1);
        if (am > pm) {
            badge.textContent = `Taşınabilir +${diff} µg/m³ yüksek ölçüyor`;
            badge.style.cssText = "background:rgba(52,210,123,0.13);color:#34d27b;border-color:rgba(52,210,123,0.3)";
        } else {
            badge.textContent = `Sabit istasyon +${diff} µg/m³ yüksek ölçüyor`;
            badge.style.cssText = "background:rgba(176,122,255,0.13);color:#b07aff;border-color:rgba(176,122,255,0.3)";
        }
    } else badge.textContent = "";

    if (cmpChart) cmpChart.destroy();
    cmpChart = new Chart(document.getElementById("cmp-chart"), {
        type: "line",
        data: { labels, datasets: [
            {
                label: `Atmotube Pro — ${person.name}`,
                data: atmoVals,
                borderColor: person.color,
                backgroundColor: person.color + "14",
                borderWidth: 2, pointRadius: 0, tension: 0.35, fill: true,
            },
            {
                label: "PurpleAir PA-II (Sabit)",
                data: paVals,
                borderColor: "#b07aff",
                backgroundColor: "rgba(176,122,255,0.07)",
                borderWidth: 2, pointRadius: 0, tension: 0.35, fill: true,
                spanGaps: true,
            },
        ]},
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: "#9aa4b8", font: { size: 11, family: "Inter" }, boxWidth: 14 } },
                tooltip: {
                    backgroundColor: "#181e2c", titleColor: "#e8ecf4", bodyColor: "#9aa4b8",
                    borderColor: "rgba(255,255,255,0.12)", borderWidth: 1,
                    callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y != null ? c.parsed.y.toFixed(1) + " µg/m³" : "—"}` },
                },
            },
            scales: {
                x: { ticks: { color: "#5d6678", font: { size: 9.5 }, maxTicksLimit: 12 }, grid: { color: "rgba(255,255,255,0.04)" } },
                y: { ticks: { color: "#5d6678", font: { size: 9.5 } }, grid: { color: "rgba(255,255,255,0.05)" },
                     title: { display: true, text: "PM₂.₅ (µg/m³)", color: "#5d6678", font: { size: 10 } } },
            },
        },
    });

    document.getElementById("chart-drawer").classList.remove("collapsed");
}

function nearestPAIn(hist, ts) {
    if (!hist?.length) return null;
    let best = hist[0], bd = Math.abs(ts - best.ts);
    for (const r of hist) {
        const d = Math.abs(ts - r.ts);
        if (d < bd) { best = r; bd = d; }
    }
    return bd < 10 * 60 * 1000 ? best : null;
}

function updateChartCursor(idx) {
    if (!cmpChart) return;
    cmpChart.data.datasets.forEach(ds => {
        ds.pointRadius = ds.data.map((_, i) => i === idx ? 5 : 0);
        ds.pointBackgroundColor = ds.borderColor;
    });
    cmpChart.update("none");
}
