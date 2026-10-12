// Mock of the Render API after the PurpleAir backfill.
// Hourly rows mimic backend AVG() output: PM2.5 fields everywhere, pm10_0/temperature_c only in hours that had
// old server rows (sparse before 6 Oct; full from 6 Oct). Values have REAL->double noise like Postgres AVG(real).
const NOW = Date.now();
let seed = 42;
const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const noisy = v => v == null ? null : Math.round((Math.fround(v) + 1e-9 * rnd()) * 100) / 100;   // backend now rounds to 2 decimals

const START = Date.UTC(2026, 3, 26, 21);         // 27 Apr 00:00 TR
const GAP = [Date.UTC(2026, 7, 10), Date.UTC(2026, 7, 15)];   // sensor gap 10-14 Aug
const SERVER_FULL_FROM = Date.UTC(2026, 9, 5, 21);   // 6 Oct TR: server has every hour with pm10/temp
const RICH_DAYS = new Set(["2026-06-15", "2026-07-20"]);   // old server online most of these days
const trDay = t => new Date(t + 3 * 3600e3).toISOString().slice(0, 10);
const trHour = t => new Date(t + 3 * 3600e3).getUTCHours();

function hourly() {
  const rows = [];
  for (let t = START; t < NOW - 3600e3 * 0.2; t += 3600e3) {
    if (t >= GAP[0] && t < GAP[1]) continue;
    const day = trDay(t), h = trHour(t);
    const base = 8 + 10 * Math.sin((t / 864e5) / 9) ** 2 + (h >= 19 || h <= 1 ? 8 : 0) + 6 * rnd();
    const cf1 = base * 1.4, atm = cf1 > 30 ? cf1 * 0.8 : cf1, hum = 45 + 30 * rnd();
    const disagree = rnd() < 0.003;      // rare A/B mismatch hour
    // did the old server have rows in this hour?
    const server = t >= SERVER_FULL_FROM || (RICH_DAYS.has(day) && h >= 3) || rnd() < 0.06;
    rows.push({
      recorded_at: new Date(t).toISOString().replace(".000Z", "+00:00"),
      pm2_5: noisy(atm), pm2_5_a: noisy(atm * 1.02), pm2_5_b: noisy(disagree ? atm * 3 + 10 : atm * 0.98),
      pm2_5_cf1_a: noisy(cf1 * 1.02), pm2_5_cf1_b: noisy(disagree ? cf1 * 3 + 10 : cf1 * 0.98),
      pm10_0: server ? noisy(atm * 1.3) : null,
      temperature_c: server ? noisy(18 + 10 * rnd()) : null,
      humidity_pct: noisy(hum),
    });
  }
  return rows;
}
const HOURLY = hourly();

// raw rows for one UTC day: 2-min import rows (cf1, no pm10/temp) interleaved with old server rows (no cf1, with pm10/temp)
function raw(startIso, endIso) {
  const s = Date.parse(startIso + (/[zZ+]/.test(startIso.slice(10)) ? "" : "Z")), e = Date.parse(endIso + (/[zZ+]/.test(endIso.slice(10)) ? "" : "Z"));
  const out = [];
  for (let t = s; t <= e; t += 120e3) {
    const x = 10 + 25 * rnd();
    out.push({ id: out.length, recorded_at: new Date(t).toISOString().replace(".000Z", "+00:00"), pm1_0: null,
      pm2_5: x, pm2_5_a: x, pm2_5_b: x, pm2_5_cf1_a: x * 1.45, pm2_5_cf1_b: x * 1.4, pm10_0: null, temperature_c: null,
      humidity_pct: 60, lat: 40.8038, lon: 29.4469 });
    if ((t / 120e3) % 5 === 2) {   // server row ~every 10 min, offset by 37 s
      const y = x * 1.1;
      out.push({ id: out.length, recorded_at: new Date(t + 37e3).toISOString().replace(".000Z", "+00:00"), pm1_0: y * 0.7,
        pm2_5: y, pm2_5_a: y, pm2_5_b: y, pm2_5_cf1_a: null, pm2_5_cf1_b: null, pm10_0: y * 1.3, temperature_c: 24.5,
        humidity_pct: 58, lat: 40.8038, lon: 29.4469 });
    }
  }
  return out.sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
}

function daily(startIso, endIso) {
  const by = new Map();
  for (const r of HOURLY) {
    if (r.recorded_at < startIso || r.recorded_at > endIso) continue;
    const k = r.recorded_at.slice(0, 10);
    (by.get(k) || by.set(k, []).get(k)).push(r);
  }
  const avg = (rs, f) => { const v = rs.map(r => r[f]).filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  return [...by].map(([k, rs]) => { const o = { recorded_at: k + "T00:00:00+00:00" };
    for (const f of ["pm2_5", "pm2_5_a", "pm2_5_b", "pm2_5_cf1_a", "pm2_5_cf1_b", "pm10_0", "temperature_c", "humidity_pct"]) o[f] = avg(rs, f);
    return o; });
}

const LATEST = { id: 999, recorded_at: new Date(NOW - 4 * 60e3).toISOString().replace(/\.\d+Z/, "+00:00"),
  pm1_0: 9.1, pm2_5: 14.2, pm2_5_a: 14.5, pm2_5_b: 13.9, pm2_5_cf1_a: 19.8, pm2_5_cf1_b: 19.0, pm10_0: 18.7,
  temperature_c: 23.4, humidity_pct: 61, lat: 40.8038, lon: 29.4469, aqi_category: "Moderate" };

// one field session on 28 Apr 10:00–11:40 TR (07:00–08:40 UTC)
const SESSION = { id: 7, session_name: "Other-2026-04-28", micro_environment: "outdoor", sensor_number: 1, reading_count: 100,
  start_time: "2026-04-28 10:00:00", end_time: "2026-04-28 11:40:00" };
const SESSION_PTS = Array.from({ length: 100 }, (_, i) => ({
  recorded_at: new Date(Date.UTC(2026, 3, 28, 7, i)).toISOString().replace(".000Z", "+00:00"),
  lat: 40.8062 + 0.0003 * Math.sin(i / 8), lon: 29.3610 + 0.0004 * Math.cos(i / 8), pm2_5: 8 + 20 * rnd(), pm10: null, activity: null }));

function tzLatest() {
  const t = new Date(NOW - 75 * 60e3 + 3 * 3600e3);
  const s = t.toISOString().slice(0, 13).replace("T", " ") + ":00";
  return { station_name: "Tuzla", pm2_5: 16.4, lat: 40.82, lon: 29.29, distance_km: 6.4, recorded_at: s, source: "live" };
}

function ibbCsv() {
  const lines = ["device,recorded_at_TR,pm2_5,pm10"];
  for (const r of HOURLY.filter(r => r.recorded_at >= "2026-10-06")) {
    const t = new Date(Date.parse(r.recorded_at) + 3 * 3600e3).toISOString();
    lines.push(`Tuzla,${t.slice(0, 10)} ${t.slice(11, 16)},${(r.pm2_5 * 1.1).toFixed(1)},`);
  }
  return lines.join("\n");
}

function handle(url) {
  const u = new URL(url), p = u.pathname, q = k => u.searchParams.get(k);
  const json = o => ({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
  if (p === "/api/purpleair/latest") return json({ data: LATEST });
  if (p === "/api/purpleair/history") {
    const iv = q("interval") || "raw", s = q("start"), e = q("end");
    let rows;
    if (iv === "hourly") rows = HOURLY.filter(r => Date.parse(r.recorded_at) >= Date.parse(s) && Date.parse(r.recorded_at) <= Date.parse(e));
    else if (iv === "daily") rows = daily(s, e);
    else rows = raw(s, e);
    return json({ data: rows, count: rows.length });
  }
  if (p === "/api/purpleair/status") return json({ success: true });
  if (p === "/api/sessions") return json({ data: [SESSION] });
  if (p === "/api/sessions/7/readings") return json({ data: SESSION_PTS });
  if (p === "/api/map/tracks") return json({ tracks: [{ session_id: 7, session_name: "saha-1", micro_environment: "outdoor", points: SESSION_PTS }] });
  if (p === "/api/map/summary") return json({ purpleair: LATEST, sessions_count: 1, micro_environments: [] });
  if (p === "/api/map/heatmap") return json({ points: [], pollutant: "pm2_5" });
  if (p === "/api/csb/latest" || p === "/api/ibb/latest") return json({ data: tzLatest() });
  if (p === "/api/atmotube/live") return json({ data: [] });
  if (p === "/api/co2/live") return json({ data: [] });
  if (p === "/api/export.csv") return { status: 200, contentType: "text/csv", body: ibbCsv() };
  if (p === "/health") return json({ ok: true });
  return { status: 404, contentType: "application/json", body: JSON.stringify({ error: "mock: " + p }) };
}

module.exports = { handle, HOURLY };
