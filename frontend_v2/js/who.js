// WHO durumu — kampüs PurpleAir ölçümlerinin WHO 2021 hava kalitesi kılavuz değerleriyle karşılaştırması.
// Saatlik ortalamalar Türkiye gününe göre günlük ortalamaya çevrilir. Ölçümler kesintili olduğu için
// (sunucu yalnızca açıkken kayıt alıyordu) günler kapsamlarına göre ayrılır:
//   tam gün ≥18 saat · gösterge gün ≥6 saat (karşılaştırmaya girer) · az veri <6 saat (yalnızca grafikte, soluk).
// Bağımlılıklar: api.js, colorscale.js, Chart.js

const WHO = (() => {
    // WHO Küresel Hava Kalitesi Kılavuzu (2021), µg/m³; AH = ara hedef
    const G = {
        pm2_5: { name: "PM₂.₅", day: 15, year: 5,
                 itDay:  [{ k: "AH-4", v: 25 }, { k: "AH-3", v: 37.5 }, { k: "AH-2", v: 50 }, { k: "AH-1", v: 75 }],
                 itYear: [{ k: "AH-4", v: 10 }, { k: "AH-3", v: 15 }, { k: "AH-2", v: 25 }, { k: "AH-1", v: 35 }] },
        pm10_0: { name: "PM₁₀", day: 45, year: 15,
                 itDay:  [{ k: "AH-4", v: 50 }, { k: "AH-3", v: 75 }, { k: "AH-2", v: 100 }, { k: "AH-1", v: 150 }],
                 itYear: [{ k: "AH-4", v: 20 }, { k: "AH-3", v: 30 }, { k: "AH-2", v: 50 }, { k: "AH-1", v: 70 }] },
    };
    const FULL_H = 18, MIN_H = 6, HISTORY_FROM = "2026-01-01T00:00:00Z";
    const BAD = "#f4615e", BAR = "#6c8cff", THIN = "#5d6678";
    let chart = null, loadedAt = 0, busy = false;
    let rows = [], period = null;
    let field = null;          // saha ölçüm noktaları (tüm oturumlar), bina karşılaştırması için

    const $ = id => document.getElementById(id);
    const dayKey = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    const dayLabel = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
    const longDay = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
    const monthName = ym => new Date(ym + "-15T12:00:00").toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
    const f1 = v => v.toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const mean = a => a.reduce((s, x) => s + x, 0) / a.length;

    // ── veri hazırlığı ───────────────────────────────────────────────
    function daysOf(key) {
        const by = new Map();
        for (const r of rows) {
            const t = new Date(r.recorded_at);
            if (r[key] == null || isNaN(t)) continue;      // bozuk kayıt sekmeyi düşürmesin
            const k = dayKey.format(t);
            (by.get(k) || by.set(k, []).get(k)).push(+r[key]);
        }
        return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0]))
            .map(([k, vals]) => ({ k, n: vals.length, v: mean(vals) }));
    }

    function pointInPeriod(p) {
        const t = new Date(p.recorded_at);
        if (isNaN(t)) return false;
        return inPeriod({ k: dayKey.format(t) });
    }

    function inPeriod(d) {
        if (period === "all") return true;
        if (period === "last30") return Date.now() - new Date(d.k + "T12:00:00") < 30 * 86400e3;
        return d.k.startsWith(period);
    }

    function stats(days, g) {
        const usable = days.filter(d => d.n >= MIN_H);
        return {
            days, usable,
            full: days.filter(d => d.n >= FULL_H).length,
            hours: days.reduce((s, d) => s + d.n, 0),
            exceed: usable.filter(d => d.v > g.day).length,
            mean: usable.length ? mean(usable.map(d => d.v)) : null,
            max: usable.length ? usable.reduce((a, b) => b.v > a.v ? b : a) : null,
        };
    }

    function last24(key) {
        const vals = rows.filter(r => r[key] != null && Date.now() - new Date(r.recorded_at) < 24 * 3600e3).map(r => +r[key]);
        return vals.length >= FULL_H ? mean(vals) : null;
    }

    // ── parçalar ─────────────────────────────────────────────────────
    function meterHtml(v, guide, its, label) {
        const max = Math.max(its[its.length - 1].v, v * 1.08);
        const pct = x => Math.min(100, x / max * 100).toFixed(1);
        const scale = 15 / guide;   // renkler PM₂.₅ günlük ölçeğinden
        const stops = [0, guide, ...its.map(t => t.v), max].map(x => `${pm25Color(x * scale)} ${pct(x)}%`).join(",");
        return `<div class="wm">
            <div class="wm-track" style="background:linear-gradient(90deg,${stops})"></div>
            <div class="wm-pin" style="left:${pct(v)}%"><span>${f1(v)}</span></div>
            <div class="wm-tick wm-who" style="left:${pct(guide)}%"><i></i><span>${label} ${guide}</span></div>
            ${its.slice(0, 3).map(t => `<div class="wm-tick" style="left:${pct(t.v)}%"><i></i><span>${t.v}</span></div>`).join("")}
        </div>`;
    }

    function chip(ok, txt) { return `<div class="wh-status ${ok ? "ok" : "bad"}">${ok ? "✅" : "⚠️"} ${txt}</div>`; }

    function heroHtml(now24, s) {
        const g = G.pm2_5;
        if (now24 != null) {
            const passed = g.itDay.filter(t => now24 > t.v);
            return `<div class="who-hero"><div class="wh-k">Son 24 saat ortalaması · ${g.name} · kampüs (PurpleAir)</div>
                <div class="wh-v"><b>${f1(now24)}</b><span>µg/m³</span></div>
                ${chip(now24 <= g.day, now24 <= g.day ? "WHO günlük kılavuz değerinin altında"
                    : `WHO günlük değerinin ${f1(now24 / g.day)} katı` + (passed.length ? ` · ${passed[passed.length - 1].k} de aşıldı` : ""))}
                ${meterHtml(now24, g.day, g.itDay, "WHO")}</div>`;
        }
        if (s.mean == null) {
            return `<div class="who-hero"><div class="wh-k">${periodLabel()} · ${g.name}</div>
                <div class="wh-empty">Bu dönemde değerlendirmeye yetecek ölçüm yok (en az ${MIN_H} saat ölçülen gün gerekiyor).</div></div>`;
        }
        return `<div class="who-hero"><div class="wh-k">${periodLabel()} · ölçülen günlerin ortalaması · ${g.name}</div>
            <div class="wh-v"><b>${f1(s.mean)}</b><span>µg/m³</span></div>
            ${chip(s.mean <= g.year, s.mean <= g.year ? "WHO yıllık kılavuz değerinin altında"
                : `WHO yıllık kılavuz değerinin (${g.year}) ${f1(s.mean / g.year)} katı`)}
            <div class="wh-sub">Günlük ${g.day} µg/m³ değeri <b>${s.exceed} / ${s.usable.length}</b> günde aşıldı${s.max ? ` · en yüksek gün: ${dayLabel(s.max.k)} (${f1(s.max.v)})` : ""}</div>
            ${meterHtml(s.mean, g.year, g.itYear, "WHO yıllık")}</div>`;
    }

    function tilesHtml(s, s10) {
        const tile = (k, v, sub, ok) => `<div class="wt ${ok == null ? "" : ok ? "ok" : "bad"}"><span>${k}</span><b>${v}</b><small>${sub}</small></div>`;
        const g = G.pm2_5, g10 = G.pm10_0;
        return `<div class="wt-grid">
            ${tile("Aşım günü (PM₂.₅)", s.usable.length ? `${s.exceed} / ${s.usable.length}` : "—",
                   `günlük ${g.day} µg/m³ aşılan gün · WHO: yılda en çok 3–4`, s.usable.length ? s.exceed <= 3 : null)}
            ${tile("Dönem ortalaması (PM₂.₅)", s.mean != null ? f1(s.mean) : "—",
                   `yıllık kılavuz ${g.year} µg/m³` + (s.mean != null ? ` · ${f1(s.mean / g.year)} katı` : ""), s.mean != null ? s.mean <= g.year : null)}
            ${tile("Dönem ortalaması (PM₁₀)", s10.mean != null ? f1(s10.mean) : "—",
                   `yıllık kılavuz ${g10.year} µg/m³` + (s10.mean != null ? ` · ${s10.exceed} günde günlük ${g10.day} aşıldı` : ""), s10.mean != null ? s10.mean <= g10.year : null)}
            ${tile("Ölçüm kapsamı", `${s.hours} saat`, `${s.days.length} günde ölçüm var · ${s.usable.length} gün ≥${MIN_H} saat · ${s.full} gün tam (≥${FULL_H} saat)`, null)}
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
            const txt = `WHO ${G.pm2_5.day}`;   // etiket çubukların üstünde okunsun diye koyu zeminli kutuda
            ctx.setLineDash([]); ctx.font = "700 10px Inter, sans-serif";
            const w = ctx.measureText(txt).width + 10;
            ctx.fillStyle = "#11151f"; ctx.fillRect(right - w, y - 17, w, 14);
            ctx.fillStyle = "#e8ecf4"; ctx.textAlign = "right"; ctx.fillText(txt, right - 5, y - 6);
            ctx.restore();
        },
    };

    function drawChart(days) {
        const canvas = $("who-chart");
        if (!canvas || typeof Chart === "undefined" || !days.length) return;
        const g = G.pm2_5;
        const data = days.map(d => Math.round(d.v * 10) / 10);
        const colors = days.map(d => d.n < MIN_H ? THIN : d.v > g.day ? BAD : BAR);
        if (chart) chart.destroy();
        chart = new Chart(canvas, {
            type: "bar",
            data: { labels: days.map(d => dayLabel(d.k)),
                    datasets: [{ data, backgroundColor: colors.map((c, i) => days[i].n < MIN_H ? c + "88" : c),
                                 borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 14, categoryPercentage: 0.82 }] },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: {
                        label: it => {
                            const d = days[it.dataIndex];
                            if (d.n < MIN_H) return `${f1(d.v)} µg/m³ · yalnızca ${d.n} saat ölçüm (değerlendirmeye girmez)`;
                            return `${f1(d.v)} µg/m³ ${d.v > g.day ? "⚠ WHO aşıldı" : "✓ WHO altında"} · ${d.n} saat ölçüm`;
                        },
                    } },
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#9aa4b8", font: { size: 9.5 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                    y: { min: 0, suggestedMax: Math.max(g.day * 1.6, ...data) * 1.1, grid: { color: "rgba(255,255,255,0.06)" },
                         border: { display: false }, ticks: { color: "#9aa4b8", font: { size: 10 }, maxTicksLimit: 5 } },
                },
            },
            plugins: [guideLine],
        });
    }

    // Aylık özet: eski ölçümlerin ay ay WHO ile karşılaştırması
    function monthlyHtml(all, all10) {
        const months = [...new Set(all.map(d => d.k.slice(0, 7)))].sort().reverse();
        if (!months.length) return "";
        const row = ym => {
            const s = stats(all.filter(d => d.k.startsWith(ym)), G.pm2_5);
            const s10 = stats(all10.filter(d => d.k.startsWith(ym)), G.pm10_0);
            const m = s.mean, bad = m != null && m > G.pm2_5.year;
            return `<tr class="${ym === period ? "sel" : ""}" data-p="${ym}"><td>${monthName(ym)}</td><td>${s.hours}</td>
                <td class="${bad ? "bad" : ""}">${m != null ? f1(m) : "—"}</td>
                <td class="${s.exceed ? "bad" : ""}">${s.usable.length ? `${s.exceed}/${s.usable.length}` : "—"}</td>
                <td>${s10.mean != null ? f1(s10.mean) : "—"}</td></tr>`;
        };
        return `<div class="nsec-title">Aylık özet · eski ölçümler</div>
            <table class="who-month"><thead><tr><th>Ay</th><th>Saat</th><th>PM₂.₅ ort.</th><th>Aşım günü</th><th>PM₁₀ ort.</th></tr></thead>
            <tbody>${months.map(row).join("")}</tbody></table>
            <div class="who-cap">Satıra dokunarak o ayı seçin. Aşım günü: günlük 15 µg/m³'ü aşan gün / en az ${MIN_H} saat ölçülen gün.</div>`;
    }

    function tableHtml(days, days10) {
        if (!days.length) return "";
        const pm10 = new Map(days10.map(d => [d.k, d]));
        const cell = (d, lim) => !d ? `<td class="na">—</td>`
            : d.n < MIN_H ? `<td class="na">${f1(d.v)}</td>`
            : `<td class="${d.v > lim ? "bad" : ""}">${f1(d.v)}${d.v > lim ? " ⚠" : ""}</td>`;
        const rowsHtml = days.slice().reverse().map(d =>
            `<tr><td>${dayLabel(d.k)}</td>${cell(d, G.pm2_5.day)}${cell(pm10.get(d.k), G.pm10_0.day)}<td class="na">${d.n}</td></tr>`).join("");
        return `<details class="who-table"><summary>Günlük değerler (tablo)</summary>
            <table><thead><tr><th>Gün</th><th>PM₂.₅</th><th>PM₁₀</th><th>Saat</th></tr></thead><tbody>${rowsHtml}</tbody></table>
            <div class="who-cap">Gri değerler ${MIN_H} saatten az ölçüme dayanır, değerlendirmeye girmez.</div></details>`;
    }

    // Bina bazında: saha ölçümlerinin bina ortalamaları ve WHO günlük değeri
    function buildingsHtml() {
        const head = `<div class="nsec-title">Bina bazında · saha ölçümleri (Atmotube)</div>`;
        if (field == null) return head + `<div class="who-cap">Saha ölçümleri yükleniyor…</div>`;
        const list = typeof Campus !== "undefined" ? Campus.buildingStats(field.filter(pointInPeriod)) : null;
        if (list == null) return head + `<div class="who-cap">Kampüs haritası yükleniyor…</div>`;
        if (!list.length) return head + `<div class="who-cap">${periodLabel()} döneminde bina içine düşen saha ölçümü yok.</div>`;
        const g = G.pm2_5;
        list.sort((a, b) => b.avg - a.avg);
        const over = list.filter(b => b.avg > g.day).length;
        const max = Math.max(g.day * 1.6, list[0].avg) * 1.05;
        const pct = v => (v / max * 100).toFixed(1);
        const rowHtml = b => `
            <button type="button" class="wb-row${b.few ? " few" : ""}" data-gk="${b.gk.replace(/"/g, "&quot;")}" title="Haritada göster">
              <span class="wb-name">${b.icon} ${b.name}<small>${b.n.toLocaleString("tr-TR")} ölçüm${b.few ? " · az ölçüm" : ""} · ${b.region}</small></span>
              <span class="wb-bar"><i style="width:${pct(b.avg)}%;background:${b.avg > g.day ? BAD : BAR}"></i><em style="left:${pct(g.day)}%"></em></span>
              <span class="wb-val ${b.avg > g.day ? "bad" : ""}">${f1(b.avg)}${b.avg > g.day ? " ⚠" : ""}</span>
            </button>`;
        const TOP = 10;
        const rowsHtml = list.slice(0, TOP).map(rowHtml).join("") + (list.length > TOP
            ? `<details class="wb-more"><summary>Tüm binaları göster (${list.length})</summary>${list.slice(TOP).map(rowHtml).join("")}</details>` : "");
        return head + `<div class="wh-sub" style="margin:0 0 8px">${periodLabel()}: ölçüm yapılan <b>${list.length}</b> binadan
              <b>${over}</b> tanesinde ortalama PM₂.₅, WHO günlük değeri olan ${g.day} µg/m³'ün üzerinde.</div>
            <div class="wb-list">${rowsHtml}</div>
            <div class="who-legend"><span><i style="background:${BAR}"></i>WHO altında</span><span><i style="background:${BAD}"></i>WHO üstünde</span>
              <span><i class="tick"></i>WHO ${g.day}</span><span>Soluk: 30'dan az ölçüm</span></div>
            <div class="who-cap">Saha ölçümleri yürürken alınan kısa süreli değerlerdir; WHO değeri ise 24 saatlik ortalama içindir.
              Bu karşılaştırma binaların birbirine göre durumunu gösterir, gösterge niteliğindedir. Binaya dokununca haritada açılır.</div>`;
    }

    const INFO = `<div class="who-info">
        <div class="nsec-title">WHO kılavuz değerleri (2021)</div>
        <table><thead><tr><th></th><th>24 saat</th><th>Yıllık</th></tr></thead><tbody>
          <tr><td>PM₂.₅</td><td><b>15</b> µg/m³</td><td><b>5</b> µg/m³</td></tr>
          <tr><td>PM₁₀</td><td><b>45</b> µg/m³</td><td><b>15</b> µg/m³</td></tr>
        </tbody></table>
        <p>24 saatlik değer yılda 3–4 günden fazla aşılmamalıdır. Kılavuz değere hemen ulaşılamayan yerler için kademeli
        <b>ara hedefler</b> (AH-1…AH-4) tanımlanmıştır: PM₂.₅ günlük 75 → 50 → 37,5 → 25, yıllık 35 → 25 → 15 → 10 µg/m³.</p>
        <p class="who-note">ℹ️ Değerler kampüs çatısındaki PurpleAir sensörünün ham (düzeltilmemiş) ölçümleridir; bu tür optik sensörler
        nemli havada PM₂.₅'i olduğundan yüksek gösterebilir. Ölçümler kesintilidir: günlük değer, o gün ölçülen saatlerin ortalamasıdır ve
        günün tamamını temsil etmeyebilir. Yıllık kılavuzla karşılaştırma tam bir yıllık veri ister; dönem ortalamaları gösterge niteliğindedir.</p>
    </div>`;

    // ── dönem seçimi ─────────────────────────────────────────────────
    function periodLabel() {
        return period === "all" ? "Tüm ölçümler" : period === "last30" ? "Son 30 gün" : monthName(period);
    }

    function fieldDays() {
        return (field || []).map(p => new Date(p.recorded_at)).filter(t => !isNaN(t)).map(t => ({ k: dayKey.format(t) }));
    }

    function periodChips(all) {
        const every = all.concat(fieldDays());
        const months = [...new Set(every.map(d => d.k.slice(0, 7)))].sort().reverse();
        const has30 = every.some(d => Date.now() - new Date(d.k + "T12:00:00") < 30 * 86400e3);
        const opts = [...(has30 ? [["last30", "Son 30 gün"]] : []), ["all", "Tüm ölçümler"],
                      ...months.map(m => [m, new Date(m + "-15T12:00:00").toLocaleDateString("tr-TR", { month: "long" })])];
        return `<div class="pd-chips who-periods">${opts.map(([p, t]) =>
            `<button type="button" class="pd-chip${p === period ? " on" : ""}" data-p="${p}">${t}</button>`).join("")}</div>`;
    }

    function staleBanner(all) {
        if (!all.length) return "";
        const last = all[all.length - 1].k;
        const ageDays = Math.floor((Date.now() - new Date(last + "T12:00:00")) / 86400e3);
        if (ageDays < 2) return "";
        return `<div class="who-banner">🔌 PurpleAir sensöründen <b>${longDay(last)}</b>'dan beri veri gelmiyor.
            Aşağıdaki değerlendirme o tarihe kadarki ölçümlere dayanıyor.</div>`;
    }

    function render() {
        const all = daysOf("pm2_5"), all10 = daysOf("pm10_0");
        if (!period) {
            const recent = all.filter(d => d.n >= MIN_H && Date.now() - new Date(d.k + "T12:00:00") < 30 * 86400e3);
            period = recent.length ? "last30" : "all";
        }
        const days = all.filter(inPeriod), days10 = all10.filter(inPeriod);
        const s = stats(days, G.pm2_5), s10 = stats(days10, G.pm10_0);
        const now24 = last24("pm2_5");
        $("who-body").innerHTML = staleBanner(all) + periodChips(all) + heroHtml(now24, s)
            + (days.length ? `<div class="nsec-title">${periodLabel()} · günlük PM₂.₅ ortalaması</div>
                <div class="who-chart-wrap"><canvas id="who-chart" aria-label="Günlük PM2.5 ortalamaları ve WHO 15 µg/m³ çizgisi"></canvas></div>
                <div class="who-legend"><span><i style="background:${BAR}"></i>WHO altında</span><span><i style="background:${BAD}"></i>WHO değerini aşan gün</span>
                <span><i style="background:${THIN}88"></i>${MIN_H} saatten az ölçüm</span><span><i class="dash"></i>WHO günlük değer</span></div>`
                : `<div class="news-empty" style="margin-top:12px">Bu dönemde ölçüm yok.</div>`)
            + tilesHtml(s, s10) + buildingsHtml() + monthlyHtml(all, all10) + tableHtml(days, days10) + INFO;
        $("who-body").querySelectorAll("[data-p]").forEach(el =>
            el.addEventListener("click", () => { period = el.dataset.p; render(); }));
        $("who-body").querySelectorAll(".wb-row").forEach(el => el.addEventListener("click", () => {
            document.body.classList.remove("who-open");         // masaüstünde panel haritayı kapatmasın
            Campus.focusByKey(el.dataset.gk);                    // telefonda harita sekmesine kendiliğinden geçer
        }));
        drawChart(days);
    }

    async function load(force) {
        if (busy || (!force && Date.now() - loadedAt < 10 * 60e3)) { if (chart) chart.resize(); return; }
        busy = true;
        if (!loadedAt) $("who-body").innerHTML = `<div class="news-empty">Hesaplanıyor…</div>`;
        try {
            const res = await API.purpleairHistory(HISTORY_FROM, new Date().toISOString(), "hourly");
            rows = res.data || [];
            render();
            loadedAt = Date.now();
            if (field == null) loadField();
        } catch (e) {
            if (!loadedAt) $("who-body").innerHTML = `<div class="news-empty">Veri alınamadı (${e.message}). Biraz sonra tekrar deneyin.</div>`;
        } finally { busy = false; }
    }

    async function loadField() {
        try {
            const res = await API.mapTracks();
            field = (res.tracks || []).flatMap(t => t.points || []).filter(p => p.lat && p.lon && p.pm2_5 != null);
        } catch (_) { field = []; }
        render();
    }

    return { load };
})();
