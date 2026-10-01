// WHO durumu — kampüs PurpleAir ölçümlerinin WHO 2021 hava kalitesi kılavuz değerleriyle karşılaştırması.
// Saatlik ortalamalar Türkiye gününe göre günlük ortalamaya çevrilir; bir gün en az 18 saat
// veri varsa (%75 kapsama) geçerli sayılır. Bağımlılıklar: api.js, colorscale.js, Chart.js

const WHO = (() => {
    // WHO Küresel Hava Kalitesi Kılavuzu (2021), µg/m³
    const G = {
        pm2_5: { name: "PM₂.₅", day: 15, year: 5, it: [{ k: "AH-4", v: 25 }, { k: "AH-3", v: 37.5 }, { k: "AH-2", v: 50 }, { k: "AH-1", v: 75 }] },
        pm10_0: { name: "PM₁₀", day: 45, year: 15, it: [{ k: "AH-4", v: 50 }, { k: "AH-3", v: 75 }, { k: "AH-2", v: 100 }, { k: "AH-1", v: 150 }] },
    };
    const DAYS = 30, MIN_HOURS = 18;
    const OK = "#34d27b", BAD = "#f4615e", BAR = "#6c8cff";
    let chart = null, loadedAt = 0, busy = false;

    const $ = id => document.getElementById(id);
    const dayKey = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    const dayLabel = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
    const f1 = v => v.toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const mean = a => a.reduce((s, x) => s + x, 0) / a.length;

    function summarize(rows, key) {
        const hourly = rows.filter(r => r[key] != null).map(r => ({ t: new Date(r.recorded_at), v: +r[key] }));
        const now = Date.now();
        const last24 = hourly.filter(h => now - h.t < 24 * 3600e3);
        const byDay = new Map();
        for (const h of hourly) {
            const k = dayKey.format(h.t);
            (byDay.get(k) || byDay.set(k, []).get(k)).push(h.v);
        }
        const days = [];
        for (let i = DAYS - 1; i >= 0; i--) {
            const k = dayKey.format(new Date(now - i * 86400e3));
            const vals = byDay.get(k) || [];
            days.push({ k, n: vals.length, v: vals.length >= MIN_HOURS ? mean(vals) : null });
        }
        const valid = days.filter(d => d.v != null);
        return {
            now: last24.length >= MIN_HOURS ? mean(last24.map(h => h.v)) : null, nowHours: last24.length,
            days, valid,
            exceed: valid.filter(d => d.v > G[key].day).length,
            period: valid.length ? mean(valid.map(d => d.v)) : null,
        };
    }

    // Değerin WHO değerine ve ara hedeflere göre yeri
    function standing(v, g) {
        if (v <= g.day) return { ok: true, txt: "WHO günlük kılavuz değerinin altında" };
        const passed = g.it.filter(t => v > t.v);
        const ratio = v / g.day;
        return { ok: false, txt: `WHO günlük değerinin ${f1(ratio)} katı` + (passed.length ? ` · ${passed[passed.length - 1].k} ara hedefi de aşıldı` : "") };
    }

    function meterHtml(v, g) {
        const max = Math.max(g.it[g.it.length - 1].v, v * 1.08);
        const pct = x => Math.min(100, x / max * 100).toFixed(1);
        const stops = [0, g.day, ...g.it.map(t => t.v), max].map(x => `${pm25Color(x * 15 / g.day)} ${pct(x)}%`).join(",");
        return `<div class="wm">
            <div class="wm-track" style="background:linear-gradient(90deg,${stops})"></div>
            <div class="wm-pin" style="left:${pct(v)}%"><span>${f1(v)}</span></div>
            <div class="wm-tick wm-who" style="left:${pct(g.day)}%"><i></i><span>WHO ${g.day}</span></div>
            ${g.it.slice(0, 3).map(t => `<div class="wm-tick" style="left:${pct(t.v)}%"><i></i><span>${t.v}</span></div>`).join("")}
        </div>`;
    }

    function heroHtml(s, g) {
        if (s.now == null) {
            return `<div class="who-hero"><div class="wh-k">Son 24 saat · ${g.name}</div>
                <div class="wh-empty">Son 24 saatte yeterli ölçüm yok (${s.nowHours} saat veri; en az ${MIN_HOURS} gerekli).<br>PurpleAir sensörü çevrimdışı olabilir.</div></div>`;
        }
        const st = standing(s.now, g);
        return `<div class="who-hero">
            <div class="wh-k">Son 24 saat ortalaması · ${g.name} · kampüs (PurpleAir)</div>
            <div class="wh-v"><b>${f1(s.now)}</b><span>µg/m³</span></div>
            <div class="wh-status ${st.ok ? "ok" : "bad"}">${st.ok ? "✅" : "⚠️"} ${st.txt}</div>
            ${meterHtml(s.now, g)}
        </div>`;
    }

    function tilesHtml(pm, pm10) {
        const tile = (k, v, sub, ok) => `<div class="wt ${ok == null ? "" : ok ? "ok" : "bad"}"><span>${k}</span><b>${v}</b><small>${sub}</small></div>`;
        const g = G.pm2_5, g10 = G.pm10_0;
        return `<div class="wt-grid">
            ${tile("Aşım günü (PM₂.₅)", pm.valid.length ? `${pm.exceed} / ${pm.valid.length}` : "—",
                   `son ${DAYS} günün geçerli günlerinde günlük ${g.day} µg/m³ aşıldı`, pm.valid.length ? pm.exceed <= 3 : null)}
            ${tile("Dönem ortalaması (PM₂.₅)", pm.period != null ? f1(pm.period) : "—",
                   pm.period != null ? `yıllık kılavuz ${g.year} µg/m³ · ${f1(pm.period / g.year)} katı` : "yeterli veri yok", pm.period != null ? pm.period <= g.year : null)}
            ${tile("Son 24 saat (PM₁₀)", pm10.now != null ? f1(pm10.now) : "—",
                   `WHO günlük ${g10.day} µg/m³`, pm10.now != null ? pm10.now <= g10.day : null)}
            ${tile("Aşım günü (PM₁₀)", pm10.valid.length ? `${pm10.exceed} / ${pm10.valid.length}` : "—",
                   `günlük ${g10.day} µg/m³ aşıldı`, pm10.valid.length ? pm10.exceed <= 3 : null)}
        </div>`;
    }

    // Eşik çizgisi (Chart.js eklentisi): WHO günlük değeri
    const guideLine = {
        id: "whoLine",
        afterDatasetsDraw(c) {
            const y = c.scales.y.getPixelForValue(G.pm2_5.day), { left, right } = c.chartArea, ctx = c.ctx;
            ctx.save();
            ctx.strokeStyle = "#e8ecf4"; ctx.lineWidth = 1.5; ctx.setLineDash([5, 4]);
            ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
            // etiket, çubukların üstünde okunsun diye koyu zeminli kutuda
            const txt = `WHO ${G.pm2_5.day}`;
            ctx.setLineDash([]); ctx.font = "700 10px Inter, sans-serif";
            const w = ctx.measureText(txt).width + 10;
            ctx.fillStyle = "#11151f"; ctx.fillRect(right - w, y - 17, w, 14);
            ctx.fillStyle = "#e8ecf4"; ctx.textAlign = "right"; ctx.fillText(txt, right - 5, y - 6);
            ctx.restore();
        },
    };

    function drawChart(pm) {
        const canvas = $("who-chart");
        if (!canvas || typeof Chart === "undefined") return;
        const g = G.pm2_5;
        const data = pm.days.map(d => d.v == null ? null : Math.round(d.v * 10) / 10);
        const max = Math.max(g.day * 1.6, ...data.filter(v => v != null)) * 1.1;
        if (chart) chart.destroy();
        chart = new Chart(canvas, {
            type: "bar",
            data: {
                labels: pm.days.map(d => dayLabel(d.k)),
                datasets: [{ data, backgroundColor: data.map(v => v > g.day ? BAD : BAR),
                             borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 14, categoryPercentage: 0.82 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: {
                        title: it => it[0].label,
                        label: it => {
                            const d = pm.days[it.dataIndex];
                            return d.v == null ? `Yetersiz veri (${d.n} saat)`
                                : `${f1(d.v)} µg/m³ ${d.v > g.day ? "⚠ WHO aşıldı" : "✓ WHO altında"} · ${d.n} saat veri`;
                        },
                    } },
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#9aa4b8", font: { size: 9.5 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                    y: { min: 0, suggestedMax: max, grid: { color: "rgba(255,255,255,0.06)" }, border: { display: false },
                         ticks: { color: "#9aa4b8", font: { size: 10 }, maxTicksLimit: 5 } },
                },
            },
            plugins: [guideLine],
        });
    }

    function tableHtml(pm, pm10) {
        const rows = pm.days.slice().reverse().map((d, i) => {
            const d10 = pm10.days[pm10.days.length - 1 - i];
            const cell = (v, lim) => v == null ? `<td class="na">—</td>` : `<td class="${v > lim ? "bad" : ""}">${f1(v)}${v > lim ? " ⚠" : ""}</td>`;
            return `<tr><td>${dayLabel(d.k)}</td>${cell(d.v, G.pm2_5.day)}${cell(d10.v, G.pm10_0.day)}<td class="na">${d.n}</td></tr>`;
        }).join("");
        return `<details class="who-table"><summary>Günlük değerler (tablo)</summary>
            <table><thead><tr><th>Gün</th><th>PM₂.₅</th><th>PM₁₀</th><th>Saat</th></tr></thead><tbody>${rows}</tbody></table></details>`;
    }

    const INFO = `<div class="who-info">
        <div class="nsec-title">WHO kılavuz değerleri (2021)</div>
        <table><thead><tr><th></th><th>24 saat</th><th>Yıllık</th></tr></thead><tbody>
          <tr><td>PM₂.₅</td><td><b>15</b> µg/m³</td><td><b>5</b> µg/m³</td></tr>
          <tr><td>PM₁₀</td><td><b>45</b> µg/m³</td><td><b>15</b> µg/m³</td></tr>
        </tbody></table>
        <p>24 saatlik değer yılda 3–4 günden fazla aşılmamalıdır. Kılavuz değere hemen ulaşılamayan yerler için
        kademeli <b>ara hedefler</b> (AH-1…AH-4) tanımlanmıştır; PM₂.₅ için günlük 75 → 50 → 37,5 → 25 µg/m³.</p>
        <p class="who-note">ℹ️ Değerler kampüs çatısındaki PurpleAir sensörünün ham (düzeltilmemiş) ölçümleridir; bu tür optik
        sensörler nemli havada PM₂.₅'i olduğundan yüksek gösterebilir. Yıllık kılavuzla karşılaştırma tam bir yıllık veri ister;
        buradaki dönem ortalaması gösterge niteliğindedir. Bir gün, en az ${MIN_HOURS} saat ölçüm varsa hesaba katılır.</p>
    </div>`;

    async function load(force) {
        if (busy || (!force && Date.now() - loadedAt < 10 * 60e3)) { if (chart) chart.resize(); return; }
        busy = true;
        const body = $("who-body");
        if (!loadedAt) body.innerHTML = `<div class="news-empty">Hesaplanıyor…</div>`;
        try {
            const end = new Date(), start = new Date(end - (DAYS + 1) * 86400e3);
            const res = await API.purpleairHistory(start.toISOString(), end.toISOString(), "hourly");
            const rows = res.data || [];
            const pm = summarize(rows, "pm2_5"), pm10 = summarize(rows, "pm10_0");
            body.innerHTML = heroHtml(pm, G.pm2_5)
                + `<div class="nsec-title">Son ${DAYS} gün · günlük PM₂.₅ ortalaması</div>
                   <div class="who-chart-wrap"><canvas id="who-chart" aria-label="Son ${DAYS} günün günlük PM2.5 ortalamaları ve WHO 15 µg/m³ çizgisi"></canvas></div>
                   <div class="who-legend"><span><i style="background:${BAR}"></i>WHO altında</span><span><i style="background:${BAD}"></i>WHO değerini aşan gün</span><span><i class="dash"></i>WHO günlük değer</span></div>`
                + tilesHtml(pm, pm10) + tableHtml(pm, pm10) + INFO;
            drawChart(pm);
            loadedAt = Date.now();
        } catch (e) {
            if (!loadedAt) body.innerHTML = `<div class="news-empty">Veri alınamadı (${e.message}). Biraz sonra tekrar deneyin.</div>`;
        } finally { busy = false; }
    }

    return { load };
})();
