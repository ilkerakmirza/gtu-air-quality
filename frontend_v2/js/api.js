// Backend API — Render production
const API_BASE = "https://gtu-air-quality.onrender.com";

async function apiFetch(path, options = {}) {
    const res = await fetch(API_BASE + path, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
}

const API = {
    // PurpleAir değerleri burada, tek yerden US EPA düzeltmesinden geçer (colorscale.js → paCorrect):
    // pm2_5 = düzeltilmiş değer (kanallar uyuşmuyorsa null), pm2_5_raw = sensörün ham cf_atm değeri
    purpleairLatest:  () => apiFetch("/api/purpleair/latest").then(r => { if (r && r.data) paCorrect(r.data); return r; }),
    purpleairHistory: (start, end, interval = "hourly") =>
        apiFetch(`/api/purpleair/history?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&interval=${interval}`)
            .then(r => { (r && r.data || []).forEach(paCorrect); return r; }),
    sessions:         () => apiFetch("/api/sessions"),
    sessionReadings:  (id) => apiFetch(`/api/sessions/${id}/readings`),
    mapSummary:       () => apiFetch("/api/map/summary"),
    mapTracks:        (ids = []) => apiFetch(`/api/map/tracks${ids.length ? "?session_ids=" + ids.join(",") : ""}`),
    ibbLatest:        () => apiFetch("/api/ibb/latest"),
    csbLatest:        () => apiFetch("/api/csb/latest"),
    purpleairStatus:  () => apiFetch("/api/purpleair/status"),
    atmotubeLive:     () => apiFetch("/api/atmotube/live"),
    co2Live:          () => apiFetch("/api/co2/live"),
    atmotubeHistory:  (device, start, end) =>
        apiFetch(`/api/atmotube/history?device=${device}&start=${start}&end=${end}`),
    // Sunucu arşivi (CSV, zamanlar Türkiye saati): ör. source=ibb → Tuzla istasyonunun saatlik değerleri
    archiveCsv:       (source, start) =>
        fetch(`${API_BASE}/api/export.csv?source=${encodeURIComponent(source)}&start=${encodeURIComponent(start)}`)
            .then(r => r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))),
    mapHeatmap:       (pollutant = "pm2_5", start, end) => {
        let q = `?pollutant=${pollutant}`;
        if (start) q += `&start=${encodeURIComponent(start)}`;
        if (end)   q += `&end=${encodeURIComponent(end)}`;
        return apiFetch(`/api/map/heatmap${q}`);
    },
};
