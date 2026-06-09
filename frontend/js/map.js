// GTU Air Quality Map — Leaflet.js main logic
// Depends on: Leaflet, Leaflet.heat, Chart.js, colorscale.js, api.js, timeline.js

const GTU_CENTER = [40.806155, 29.360985];
const GTU_ZOOM   = 17;

// GTÜ kampüs haritası görseli için coğrafi sınırlar (SW → NE)
// 22TR-Kampüs Haritası Türkçe.jpg
const CAMPUS_BOUNDS = [[40.797, 29.348], [40.820, 29.378]];

let map, heatLayer, trackLayerGroup, purpleairMarker, envLayerGroup;
let miniChart = null;
let currentTracks = [];

// PurpleAir senkronizasyon — animasyon sırasında geçmiş verileri tutar
let _paHistory = [];   // [{recorded_at, pm2_5, pm10_0, temperature_c, humidity_pct}, ...]
let _paLiveMode = true; // true=canlı, false=animasyon geçmişi

// ---------------------------------------------------------------------------
// Initialise map
// ---------------------------------------------------------------------------

function initMap() {
    map = L.map("map", { center: GTU_CENTER, zoom: GTU_ZOOM });

    // Esri uydu tabanı
    const esriSatBase = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "© Esri, Maxar, Earthstar Geographics",
        maxZoom: 20,
    });
    // Esri bina/sokak isimleri overlay (uydu üstüne)
    const esriLabels = L.tileLayer(
        "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
        attribution: "",
        maxZoom: 20,
        pane: "overlayPane",
        opacity: 1,
    });
    // Hibrit: uydu + isimler (Google Maps hibrit gibi)
    const esriHybrid = L.layerGroup([esriSatBase, esriLabels]);

    // Esri sokak haritası (detaylı bina isimleri)
    const esriStreet = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", {
        attribution: "© Esri, HERE, Garmin, © OpenStreetMap contributors",
        maxZoom: 20,
    });
    // Esri topografik
    const esriTopo = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
        attribution: "© Esri, HERE, Garmin",
        maxZoom: 20,
    });

    // Kampüs haritası görsel overlay (22TR)
    const campusOverlay = L.imageOverlay(
        "images/campus_map_22TR.jpg",
        CAMPUS_BOUNDS,
        { opacity: 0.55, interactive: false }
    );

    // Varsayılan: Hibrit (uydu + bina isimleri)
    esriHybrid.addTo(map);

    L.control.layers(
        {
            "🛰️ Uydu + Bina İsimleri (Hibrit)": esriHybrid,
            "🗺️ Esri Sokak Haritası":            esriStreet,
            "🏔️ Esri Topografik":                esriTopo,
        },
        {
            "🗺️ Kampüs Planı (22TR)": campusOverlay,
        },
        { position: "topright" }
    ).addTo(map);

    // Layer groups
    trackLayerGroup = L.layerGroup().addTo(map);
    envLayerGroup   = L.layerGroup().addTo(map);

    // Heatmap layer (initially empty)
    heatLayer = L.heatLayer([], { radius: 25, blur: 15, maxZoom: 17, gradient: {
        0.0: "#00e400",
        0.2: "#ffff00",
        0.4: "#ff7e00",
        0.7: "#ff0000",
        1.0: "#8f3f97",
    }});

    // Legend
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
        const div = L.DomUtil.create("div", "map-legend");
        div.innerHTML = buildLegend();
        return div;
    };
    legend.addTo(map);

    // Timeline
    Timeline.init("timeline-slider", "timeline-presets", onTimelineChange);

    // Load initial data
    loadPurpleAir();
    loadSessions();
    loadHeatmap();
    loadEnvSummary();

    // Oynatıcıyı başlat (map hazır olduktan sonra)
    initPlayer();

    // Auto-refresh PurpleAir every 2 minutes + countdown
    const REFRESH_SEC = 120;
    let countdownSec = REFRESH_SEC;
    const countdownEl = document.getElementById("pa-countdown");

    function tickCountdown() {
        countdownSec--;
        if (countdownSec <= 0) {
            countdownSec = REFRESH_SEC;
            loadPurpleAir();
        }
        if (countdownEl) {
            countdownEl.textContent = `Sonraki güncelleme: ${countdownSec}s`;
        }
    }
    setInterval(tickCountdown, 1000);
}

// ---------------------------------------------------------------------------
// PurpleAir fixed sensor
// ---------------------------------------------------------------------------

async function loadPurpleAir() {
    try {
        const res = await API.purpleairLatest();
        const d = res.data;
        updatePurpleairPanel(d);
        if (!d) return;

        const color = pm25Color(d.pm2_5);
        const icon = buildPulseIcon(color);

        const latlng = [d.lat || GTU_CENTER[0], d.lon || GTU_CENTER[1]];
        if (!purpleairMarker) {
            purpleairMarker = L.marker(latlng, { icon })
                .addTo(map)
                .bindTooltip(
                    `<b>🟣 PurpleAir PA-II</b><br>SUMER Lab — GTÜ Çatı<br>PM₂.₅: ${d.pm2_5?.toFixed(1) ?? "--"} µg/m³`,
                    { permanent: true, direction: "top", offset: [0, -14],
                      className: "pa-label" }
                )
                .on("click", () => openPurpleAirPopup(d));
        } else {
            purpleairMarker.setIcon(icon);
            // Etiketi PM2.5 ile güncelle
            purpleairMarker.setTooltipContent(
                `<b>🟣 PurpleAir PA-II</b><br>SUMER Lab — GTÜ Çatı<br>PM₂.₅: ${d.pm2_5?.toFixed(1) ?? "--"} µg/m³`
            );
            purpleairMarker.off("click").on("click", () => openPurpleAirPopup(d));
        }
    } catch (e) {
        console.error("[purpleair]", e);
        document.getElementById("pa-status").textContent = "Bağlantı hatası";
    }
}

function updatePurpleairPanel(d) {
    if (!d) {
        document.getElementById("pa-pm25").textContent   = "--";
        document.getElementById("pa-pm10").textContent   = "--";
        document.getElementById("pa-temp").textContent   = "--";
        document.getElementById("pa-humidity").textContent = "--";
        document.getElementById("pa-status").textContent = "Veri yok";
        document.getElementById("pa-time").textContent   = "";
        return;
    }
    document.getElementById("pa-pm25").textContent     = d.pm2_5 != null ? d.pm2_5.toFixed(1) : "--";
    document.getElementById("pa-pm10").textContent     = d.pm10_0 != null ? d.pm10_0.toFixed(1) : "--";
    document.getElementById("pa-temp").textContent     = d.temperature_c != null ? d.temperature_c.toFixed(1) + " °C" : "--";
    document.getElementById("pa-humidity").textContent = d.humidity_pct != null ? d.humidity_pct.toFixed(0) + "%" : "--";
    const cat = pm25Label(d.pm2_5);
    const catEl = document.getElementById("pa-status");
    catEl.textContent = cat;
    catEl.style.color = pm25Color(d.pm2_5);
    document.getElementById("pa-time").textContent = d.recorded_at
        ? "Son güncelleme: " + new Date(d.recorded_at).toLocaleString("tr-TR")
        : "";
}

async function openPurpleAirPopup(latest) {
    const { start, end } = Timeline.getRange();
    let chartHtml = "";
    try {
        const hist = await API.purpleairHistory(start || _daysAgo(1), end || _now(), "hourly");
        chartHtml = `<canvas id="pa-mini-chart" width="260" height="100"></canvas>`;
        // Chart rendered after popup opens
        setTimeout(() => renderMiniChart(hist.data), 50);
    } catch (_) {}

    const popup = L.popup({ maxWidth: 300 })
        .setLatLng(purpleairMarker.getLatLng())
        .setContent(`
            <div class="pa-popup">
              <h3>PurpleAir PA-II — GTÜ</h3>
              <table class="popup-table">
                <tr><td>PM₂.₅</td><td><b>${latest.pm2_5?.toFixed(1) ?? "--"} µg/m³</b></td></tr>
                <tr><td>PM₁₀</td><td>${latest.pm10_0?.toFixed(1) ?? "--"} µg/m³</td></tr>
                <tr><td>Sıcaklık</td><td>${latest.temperature_c?.toFixed(1) ?? "--"} °C</td></tr>
                <tr><td>Nem</td><td>${latest.humidity_pct?.toFixed(0) ?? "--"}%</td></tr>
              </table>
              <div style="margin-top:6px;font-size:11px;color:#666">${latest.recorded_at ? new Date(latest.recorded_at).toLocaleString("tr-TR") : ""}</div>
              ${chartHtml}
            </div>`)
        .openOn(map);
}

function renderMiniChart(data) {
    const ctx = document.getElementById("pa-mini-chart");
    if (!ctx || !data?.length) return;
    if (miniChart) miniChart.destroy();
    miniChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.map(r => new Date(r.recorded_at).toLocaleDateString("tr-TR", { month: "short", day: "numeric" })),
            datasets: [{
                label: "PM₂.₅",
                data: data.map(r => r.pm2_5),
                borderColor: "#6c63ff",
                backgroundColor: "rgba(108,99,255,0.1)",
                tension: 0.3,
                pointRadius: 0,
                fill: true,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { maxTicksLimit: 5, font: { size: 9 } } },
                y: { ticks: { font: { size: 9 } } },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Atmotube tracks
// ---------------------------------------------------------------------------

async function loadSessions() {
    try {
        const res = await API.sessions();
        renderSessionList(res.data);
    } catch (e) {
        console.error("[sessions]", e);
    }
}

function renderSessionList(sessions) {
    const container = document.getElementById("session-list");
    if (!sessions?.length) {
        container.innerHTML = "<p class='no-data'>Henüz yüklenen oturum yok.</p>";
        return;
    }

    container.innerHTML = sessions.map(s => `
        <label class="session-item">
          <input type="checkbox" class="session-cb" value="${s.id}" checked>
          <span class="session-dot" style="background:${envColor(s.micro_environment)}"></span>
          <span class="session-name">${s.session_name}</span>
          <span class="session-meta">${s.reading_count ?? 0} ölçüm</span>
        </label>
    `).join("");

    container.querySelectorAll(".session-cb").forEach(cb => {
        cb.addEventListener("change", updateTracks);
    });

    updateTracks();
}

async function updateTracks() {
    const checked = [...document.querySelectorAll(".session-cb:checked")].map(cb => +cb.value);
    trackLayerGroup.clearLayers();
    if (!checked.length) return;

    try {
        const res = await API.mapTracks(checked);
        res.tracks.forEach(renderTrack);
        currentTracks = res.tracks;
    } catch (e) {
        console.error("[tracks]", e);
    }
}

function renderTrack(track) {
    if (!track.points?.length) return;
    const gpsPoints = track.points.filter(p => p.lat && p.lon);
    if (!gpsPoints.length) return;

    // Her ölçüm noktası için PM2.5 renginde dolu daire
    gpsPoints.forEach((pt, i) => {
        const color = pm25Color(pt.pm2_5);
        const isFirst = i === 0;
        L.circleMarker([pt.lat, pt.lon], {
            radius:      isFirst ? 9 : 7,
            color:       isFirst ? "#fff" : color,
            weight:      isFirst ? 2 : 1,
            fillColor:   isFirst ? envColor(track.micro_environment) : color,
            fillOpacity: 0.9,
            opacity:     0.95,
        })
        .bindPopup(`
            <b>${track.session_name}</b><br>
            PM₂.₅: <b>${pt.pm2_5 != null ? pt.pm2_5.toFixed(1) : "--"} µg/m³</b><br>
            <span style="color:${color}">${pm25Label(pt.pm2_5)}</span><br>
            <small>${pt.recorded_at ? new Date(pt.recorded_at).toLocaleString("tr-TR") : ""}</small>
        `)
        .addTo(trackLayerGroup);
    });
}

// ---------------------------------------------------------------------------
// Heatmap
// ---------------------------------------------------------------------------

async function loadHeatmap(start, end) {
    try {
        const res = await API.mapHeatmap("pm2_5", start, end);
        const pts = res.points.map(p => [p.lat, p.lon, pm25Intensity(p.value)]);
        heatLayer.setLatLngs(pts);
    } catch (e) {
        console.error("[heatmap]", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const heatToggle = document.getElementById("toggle-heatmap");
    if (heatToggle) {
        heatToggle.addEventListener("change", () => {
            if (heatToggle.checked) heatLayer.addTo(map);
            else map.removeLayer(heatLayer);
        });
    }
});

// ---------------------------------------------------------------------------
// Micro-environment summary markers
// ---------------------------------------------------------------------------

async function loadEnvSummary() {
    try {
        const res = await API.mapSummary();
        (res.micro_environments || []).forEach(env => {
            if (!env.lat || !env.lon) return;
            L.circleMarker([env.lat, env.lon], {
                radius: 10,
                color: "#fff",
                fillColor: pm25Color(env.avg_pm2_5),
                fillOpacity: 0.9,
                weight: 2,
            })
            .bindPopup(`<b>${env.micro_environment}</b><br>Ort. PM₂.₅: ${env.avg_pm2_5?.toFixed(1) ?? "--"} µg/m³`)
            .addTo(envLayerGroup);
        });
    } catch (_) {}
}

// ---------------------------------------------------------------------------
// Timeline change handler
// ---------------------------------------------------------------------------

function onTimelineChange(start, end) {
    loadHeatmap(start, end);
    loadPurpleAir();
}

// ---------------------------------------------------------------------------
// CSV Upload form
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = form.querySelector("button[type=submit]");
        btn.disabled = true;
        btn.textContent = "Yükleniyor…";

        const fd = new FormData(form);
        const result = document.getElementById("upload-result");

        try {
            const res = await API.uploadCSV(fd);
            result.className = "upload-result success";
            result.textContent = res.message + (res.warnings?.length ? " (" + res.warnings.join("; ") + ")" : "");
            form.reset();
            loadSessions(); // refresh session list and tracks
        } catch (err) {
            result.className = "upload-result error";
            result.textContent = "Hata: " + err.message;
        } finally {
            btn.disabled = false;
            btn.textContent = "Yükle";
        }
    });
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildPulseIcon(color) {
    return L.divIcon({
        className: "",
        html: `<div class="pulse-marker" style="--marker-color:${color}"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });
}

function envColor(env) {
    const map = {
        library:   "#4e79a7",
        classroom: "#f28e2b",
        canteen:   "#e15759",
        outdoor:   "#76b7b2",
        lab:       "#59a14f",
        corridor:  "#b07aa1",
    };
    return map[env] || "#aaaaaa";
}

function _daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString();
}

function _now() {
    return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Animasyon oynatıcı bağlantıları
// ---------------------------------------------------------------------------

function initPlayer() {
    Player.init(map, onPlayerStep);

    const panel      = document.getElementById("player-panel");
    const btnOpen    = document.getElementById("btn-open-player");
    const btnPlay    = document.getElementById("btn-play");
    const btnStop    = document.getElementById("btn-stop");
    const btnClose   = document.getElementById("btn-close-player");
    const selectEl   = document.getElementById("player-session-select");
    const progressEl = document.getElementById("player-progress");

    // Oturum listesini doldur
    API.sessions().then(res => {
        res.data.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.textContent = `${s.session_name} (${s.reading_count} ölçüm)`;
            selectEl.appendChild(opt);
        });
        // İlk oturumu seç
        if (res.data.length) selectEl.value = res.data[0].id;
    }).catch(() => {});

    // Panel aç
    btnOpen.addEventListener("click", () => {
        panel.style.display = "flex";
        btnOpen.style.background = "#238636";
        btnOpen.textContent = "▶ Animasyon Açık";
    });

    // Kapat
    btnClose.addEventListener("click", () => {
        Player.stop();
        panel.style.display = "none";
        btnPlay.textContent = "▶";
        btnPlay.classList.remove("active");
        btnOpen.style.background = "#1f6feb";
        btnOpen.textContent = "▶ Günü Oynat";
    });

    // Oynat / Durdur
    btnPlay.addEventListener("click", async () => {
        if (Player.isPlaying()) {
            Player.pause();
            btnPlay.textContent = "▶";
            btnPlay.classList.remove("active");
        } else {
            const sid = parseInt(selectEl.value);
            if (!sid) return;
            const count = await Player.loadSession(sid);
            if (!count) { alert("Bu oturumda GPS verisi bulunamadı."); return; }

            // PurpleAir geçmiş verisini o gün için çek
            _paHistory = [];
            _paLiveMode = false;
            try {
                const range = Player.getTimeRange();
                const dayStart = range.start.slice(0, 10) + "T00:00:00";
                const dayEnd   = range.end.slice(0, 10)   + "T23:59:59";
                const hist = await API.purpleairHistory(dayStart, dayEnd, "raw");
                _paHistory = (hist.data || []).map(r => ({
                    ts:   new Date(r.recorded_at).getTime(),
                    pm2_5: r.pm2_5, pm10_0: r.pm10_0,
                    temperature_c: r.temperature_c, humidity_pct: r.humidity_pct,
                    recorded_at: r.recorded_at,
                }));
                _setPABadge("hist");
                // Karşılaştırma grafiğini yükle
                loadCompareChart(sid, _paHistory);
            } catch(e) {
                console.warn("[pa-sync] geçmiş veri alınamadı:", e);
            }

            // Statik rotaları gizle — animasyon kendi çizer
            trackLayerGroup.clearLayers();
            Player.play();
            btnPlay.textContent = "⏸";
            btnPlay.classList.add("active");
        }
    });

    // Başa dön
    btnStop.addEventListener("click", () => {
        Player.stop();
        btnPlay.textContent = "▶";
        btnPlay.classList.remove("active");
        document.getElementById("player-time").textContent = "--:--";
        document.getElementById("player-loc").textContent  = "—";
        const pmEl = document.getElementById("player-pm");
        pmEl.style.color = "#e6edf3";
        pmEl.innerHTML = "-- <small>PM₂.₅ µg/m³</small>";
        document.getElementById("player-progress-bar").style.width = "0%";
        // Canlı moda dön
        _paHistory = [];
        _paLiveMode = true;
        _setPABadge("live");
        loadPurpleAir(); // anında canlı veriyi yenile
        // Statik rotaları geri getir
        updateTracks();
    });

    // Oturum değişince oynatıcıyı sıfırla
    selectEl.addEventListener("change", () => {
        Player.stop();
        btnPlay.textContent = "▶";
        btnPlay.classList.remove("active");
    });

    // Hız butonları
    document.querySelectorAll(".speed-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            Player.setSpeed(parseInt(btn.dataset.speed));
        });
    });

    // Progress bar tıklama ile atlama
    progressEl.addEventListener("click", (e) => {
        const rect = progressEl.getBoundingClientRect();
        const frac = (e.clientX - rect.left) / rect.width;
        Player.seekTo(Math.max(0, Math.min(1, frac)));
    });
}

function onPlayerStep(pt, idx, total) {
    // Zaman
    const dt = new Date(pt.recorded_at);
    document.getElementById("player-time").textContent =
        dt.toLocaleString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit",
                                      day: "2-digit", month: "short" });

    // Konum etiketi
    document.getElementById("player-loc").textContent =
        pt.activity || `${pt.lat?.toFixed(5)}, ${pt.lon?.toFixed(5)}`;

    // Atmotube PM2.5
    const pmEl = document.getElementById("player-pm");
    const val  = pt.pm2_5 != null ? pt.pm2_5.toFixed(1) : "--";
    pmEl.style.color = pm25Color(pt.pm2_5);
    pmEl.innerHTML   = `${val} <small>PM₂.₅ µg/m³</small>`;

    // Progress bar
    document.getElementById("player-progress-bar").style.width = `${(idx / total * 100).toFixed(1)}%`;

    // Grafik cursor
    updateChartCursor(idx);

    // ── PurpleAir senkronizasyonu ──────────────────────────────────────────
    if (_paHistory.length) {
        const ts = new Date(pt.recorded_at).getTime();
        // En yakın PurpleAir ölçümünü bul
        let best = _paHistory[0];
        let bestDiff = Math.abs(ts - best.ts);
        for (const r of _paHistory) {
            const diff = Math.abs(ts - r.ts);
            if (diff < bestDiff) { best = r; bestDiff = diff; }
        }
        // Sidebar panelini güncelle
        updatePurpleairPanel({
            pm2_5: best.pm2_5, pm10_0: best.pm10_0,
            temperature_c: best.temperature_c, humidity_pct: best.humidity_pct,
            recorded_at: best.recorded_at,
        });
        // Harita marker rengini de güncelle
        if (purpleairMarker) {
            purpleairMarker.setIcon(buildPulseIcon(pm25Color(best.pm2_5)));
            purpleairMarker.setTooltipContent(
                `<b>🟣 PurpleAir PA-II</b><br>SUMER Lab — GTÜ Çatı<br>PM₂.₅: ${best.pm2_5?.toFixed(1) ?? "--"} µg/m³<br><small style="color:#8b949e">${new Date(best.recorded_at).toLocaleString("tr-TR")}</small>`
            );
        }
        // Geri sayım sayacını gizle animasyon sırasında
        const cdEl = document.getElementById("pa-countdown");
        if (cdEl) cdEl.textContent = `📅 ${new Date(pt.recorded_at).toLocaleDateString("tr-TR", {day:"2-digit",month:"long",year:"numeric"})} — animasyon modu`;
    }

    // Animasyon bittiğinde
    if (idx === total - 1) {
        document.getElementById("btn-play").textContent = "▶";
        document.getElementById("btn-play").classList.remove("active");
        // Canlı moda dön
        _paLiveMode = true;
        _paHistory = [];
        _setPABadge("live");
        loadPurpleAir();
    }
}

// PurpleAir rozeti: "CANLI" ↔ "GEÇMİŞ VERİ"
function _setPABadge(mode) {
    const badge = document.querySelector(".live-badge");
    if (!badge) return;
    if (mode === "live") {
        badge.innerHTML = `<span class="live-dot"></span>CANLI`;
        badge.style.background = "rgba(0,200,100,0.12)";
        badge.style.borderColor = "rgba(0,200,100,0.3)";
        badge.style.color = "#3fb950";
    } else {
        badge.innerHTML = `<span class="live-dot" style="background:#f0a500;animation:none"></span>GEÇMİŞ VERİ`;
        badge.style.background = "rgba(240,165,0,0.12)";
        badge.style.borderColor = "rgba(240,165,0,0.4)";
        badge.style.color = "#f0a500";
    }
}

// ---------------------------------------------------------------------------
// Karşılaştırma Grafiği — Atmotube vs PurpleAir
// ---------------------------------------------------------------------------

let _compareChart = null;
let _compareAnnotationIdx = null;

function initCompareChart() {
    // Panel aç/kapat
    const panel   = document.getElementById("chart-panel");
    const toggle  = document.getElementById("chart-toggle");
    const arrow   = document.getElementById("chart-arrow");
    toggle.addEventListener("click", () => {
        const open = panel.classList.toggle("expanded");
        panel.classList.toggle("collapsed", !open);
        arrow.textContent = open ? "▼" : "▲";
        if (open && _compareChart) _compareChart.resize();
    });
}

async function loadCompareChart(sessionId, paHistoryData) {
    // Atmotube ölçümlerini al
    let atmoData = [];
    try {
        const res = await API.sessionReadings(sessionId);
        atmoData = (res.data || [])
            .filter(r => r.pm2_5 != null)
            .sort((a,b) => new Date(a.recorded_at) - new Date(b.recorded_at));
    } catch(e) { return; }
    if (!atmoData.length) return;

    const labels  = atmoData.map(r => new Date(r.recorded_at).toLocaleTimeString("tr-TR", {hour:"2-digit", minute:"2-digit"}));
    const atmoVals = atmoData.map(r => r.pm2_5);

    // PA verisini Atmotube zaman damgalarına hizala
    const paVals = atmoData.map(r => {
        if (!paHistoryData?.length) return null;
        const ts = new Date(r.recorded_at).getTime();
        let best = paHistoryData[0], bestDiff = Math.abs(ts - best.ts);
        for (const p of paHistoryData) {
            const d = Math.abs(ts - p.ts);
            if (d < bestDiff) { best = p; bestDiff = d; }
        }
        return bestDiff < 10 * 60 * 1000 ? best.pm2_5 : null; // max 10 dk fark
    });

    // Avantaj hesapla: hangisi ortalama daha düşük?
    const atmoMean = atmoVals.reduce((a,b)=>a+b,0)/atmoVals.length;
    const paFiltered = paVals.filter(v=>v!=null);
    const paMean = paFiltered.length ? paFiltered.reduce((a,b)=>a+b,0)/paFiltered.length : null;

    const badge = document.getElementById("chart-advantage-badge");
    if (paMean !== null) {
        const diff = Math.abs(atmoMean - paMean).toFixed(1);
        if (atmoMean > paMean) {
            badge.textContent = `Taşınabilir +${diff} µg/m³ fazla`;
            badge.style.background = "rgba(255,120,0,0.15)";
            badge.style.color = "#ff8800";
            badge.style.borderColor = "rgba(255,120,0,0.3)";
        } else {
            badge.textContent = `Sabit istasyon +${diff} µg/m³ fazla`;
            badge.style.background = "rgba(139,92,246,0.15)";
            badge.style.color = "#8b80f9";
            badge.style.borderColor = "rgba(139,92,246,0.3)";
        }
    }

    // Grafiği çiz
    const ctx = document.getElementById("compare-chart");
    if (_compareChart) { _compareChart.destroy(); _compareChart = null; }
    _compareChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Atmotube Pro (Taşınabilir)",
                    data: atmoVals,
                    borderColor: "#3fb950",
                    backgroundColor: "rgba(63,185,80,0.08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: "PurpleAir PA-II (Sabit — SUMER Lab)",
                    data: paVals,
                    borderColor: "#8b80f9",
                    backgroundColor: "rgba(139,128,249,0.08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.3,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    labels: { color: "#8b949e", font: { size: 10 }, boxWidth: 12 }
                },
                tooltip: {
                    backgroundColor: "#21262d",
                    titleColor: "#c9d1d9",
                    bodyColor: "#8b949e",
                    borderColor: "#30363d",
                    borderWidth: 1,
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) + " µg/m³" : "veri yok"}`,
                    }
                },
            },
            scales: {
                x: { ticks: { color:"#8b949e", font:{size:9}, maxTicksLimit: 10 },
                     grid: { color:"#21262d" } },
                y: { ticks: { color:"#8b949e", font:{size:9} },
                     grid: { color:"#21262d" },
                     title: { display:true, text:"PM₂.₅ (µg/m³)", color:"#8b949e", font:{size:9} } },
            },
        },
    });
    _compareAnnotationIdx = null;

    // Paneli otomatik aç
    const panel = document.getElementById("chart-panel");
    panel.classList.add("expanded");
    panel.classList.remove("collapsed");
    document.getElementById("chart-arrow").textContent = "▼";
}

// Animasyon adımında grafik üzerinde dikey çizgi kaydır
function updateChartCursor(idx) {
    if (!_compareChart) return;
    // Önceki annotation sil, yeni ekle (hafif highlight)
    const meta0 = _compareChart.getDatasetMeta(0);
    if (!meta0?.data?.[idx]) return;
    // Aktif noktayı büyüt
    _compareChart.data.datasets.forEach(ds => {
        ds.pointRadius = ds.data.map((_, i) => i === idx ? 5 : 0);
        ds.pointBackgroundColor = ds.data.map((_, i) =>
            i === idx ? (ds.borderColor) : "transparent");
    });
    _compareChart.update("none");
}

// Boot — initPlayer initMap'ten sonra çağrılmalı (map nesnesi hazır olsun)
document.addEventListener("DOMContentLoaded", () => { initMap(); initCompareChart(); });
