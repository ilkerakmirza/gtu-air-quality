// Backend API base URL
// Yerel: http://localhost:5000
// Railway deploy sonrası: window.API_BASE değişkenini map.html'de ayarlayın
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
    purpleairLatest:  () => apiFetch("/api/purpleair/latest"),
    purpleairHistory: (start, end, interval = "hourly") =>
        apiFetch(`/api/purpleair/history?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&interval=${interval}`),

    sessions:         () => apiFetch("/api/sessions"),
    sessionReadings:  (id) => apiFetch(`/api/sessions/${id}/readings`),

    mapSummary:       () => apiFetch("/api/map/summary"),
    mapTracks:        (sessionIds = []) => {
        const q = sessionIds.length ? `?session_ids=${sessionIds.join(",")}` : "";
        return apiFetch(`/api/map/tracks${q}`);
    },
    mapHeatmap:       (pollutant = "pm2_5", start, end) => {
        let q = `?pollutant=${pollutant}`;
        if (start) q += `&start=${encodeURIComponent(start)}`;
        if (end)   q += `&end=${encodeURIComponent(end)}`;
        return apiFetch(`/api/map/heatmap${q}`);
    },

    uploadCSV: (formData) => apiFetch("/api/upload", { method: "POST", body: formData }),
};
