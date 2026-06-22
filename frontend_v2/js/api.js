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
    purpleairLatest:  () => apiFetch("/api/purpleair/latest"),
    purpleairHistory: (start, end, interval = "hourly") =>
        apiFetch(`/api/purpleair/history?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&interval=${interval}`),
    sessions:         () => apiFetch("/api/sessions"),
    sessionReadings:  (id) => apiFetch(`/api/sessions/${id}/readings`),
    mapSummary:       () => apiFetch("/api/map/summary"),
    mapTracks:        (ids = []) => apiFetch(`/api/map/tracks${ids.length ? "?session_ids=" + ids.join(",") : ""}`),
    ibbLatest:        () => apiFetch("/api/ibb/latest"),
    csbLatest:        () => apiFetch("/api/csb/latest"),
    atmotubeLive:     () => apiFetch("/api/atmotube/live"),
    co2Live:          () => apiFetch("/api/co2/live"),
    atmotubeHistory:  (device, start, end) =>
        apiFetch(`/api/atmotube/history?device=${device}&start=${start}&end=${end}`),
    mapHeatmap:       (pollutant = "pm2_5", start, end) => {
        let q = `?pollutant=${pollutant}`;
        if (start) q += `&start=${encodeURIComponent(start)}`;
        if (end)   q += `&end=${encodeURIComponent(end)}`;
        return apiFetch(`/api/map/heatmap${q}`);
    },
};
