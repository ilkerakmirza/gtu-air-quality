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
    const EXCEED_SHARE = 0.01;   // WHO: yılda 3–4 aşım günü ≈ 99. yüzdelik → ölçülen günlerin en çok %1'i
    const FULL_H = 18, MIN_H = 6, HISTORY_FROM = "2026-01-01T00:00:00Z";
    const BAD = "#f4615e", BAR = "#6c8cff", THIN = "#5d6678";
    let chart = null, kchart = null, loadedAt = 0, busy = false;
    let rows = [], period = null;
    let field = null;          // saha ölçüm noktaları (tüm oturumlar), bina karşılaştırması için

    const $ = id => document.getElementById(id);
    const dayKey = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    const dayLabel = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
    const longDay = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
    const monthName = ym => new Date(ym + "-15T12:00:00").toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
    const f1 = v => v.toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const mean = a => a.reduce((s, x) => s + x, 0) / a.length;

    // ── ortak veri (WHO ve Özet sekmeleri aynı istekleri paylaşır, 10 dk önbellek) ──
    const cache = {};
    function shared(name, fetcher) {
        const c = cache[name];
        if (c && Date.now() - c.at < 10 * 60e3) return c.p;
        const p = fetcher();
        cache[name] = { at: Date.now(), p };
        p.catch(() => { delete cache[name]; });
        return p;
    }
    const history = () => shared("hist", () =>
        API.purpleairHistory(HISTORY_FROM, new Date().toISOString(), "hourly").then(r => r.data || []));
    const fieldPoints = () => shared("field", () =>
        API.mapTracks().then(r => (r.tracks || []).flatMap(t => t.points || []).filter(p => p.lat && p.lon && p.pm2_5 != null)));

    // ── veri hazırlığı ───────────────────────────────────────────────
    // Saatlik kayıtları Türkiye gününe göre günlük ortalamaya çevir
    function dailyMeans(src, key) {
        const by = new Map();
        for (const r of src) {
            const t = new Date(r.recorded_at);
            if (r[key] == null || isNaN(t)) continue;      // bozuk kayıt sekmeyi düşürmesin
            const k = dayKey.format(t);
            (by.get(k) || by.set(k, []).get(k)).push(+r[key]);
        }
        return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0]))
            .map(([k, vals]) => ({ k, n: vals.length, v: mean(vals) }));
    }
    const daysOf = key => dailyMeans(rows, key);

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
            ${its.slice(0, 3).map(t => `<div class="wm-tick" style="left:${pct(t.v)}%"><i></i><span>${String(t.v).replace(".", ",")}</span></div>`).join("")}
        </div>`;
    }

    function chip(ok, txt) { return `<div class="wh-status ${ok ? "ok" : "bad"}">${ico(ok ? "circle-check" : "triangle-alert")} ${txt}</div>`; }

    function heroHtml(now24, s) {
        const g = G.pm2_5;
        if (now24 != null) {
            const passed = g.itDay.filter(t => now24 > t.v);
            return `<div class="who-hero"><div class="wh-k">Son 24 saat ortalaması · ${g.name} · kampüs (PurpleAir, US EPA düzeltmeli)</div>
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
                   `günlük ${g.day} µg/m³ aşılan gün` + (s.usable.length ? ` (%${Math.round(s.exceed / s.usable.length * 100)})` : "")
                   + ` · WHO: yılda en çok 3–4 gün (≈ %1)`,
                   // WHO ölçütü bir yıllık veri içindir (99. yüzdelik ≈ günlerin %1'i); kısa dönemde mutlak sayı değil oran karşılaştırılır
                   s.usable.length ? s.exceed / s.usable.length <= EXCEED_SHARE : null)}
            ${tile("Dönem ortalaması (PM₂.₅)", s.mean != null ? f1(s.mean) : "—",
                   `yıllık kılavuz ${g.year} µg/m³` + (s.mean != null ? ` · ${f1(s.mean / g.year)} katı` : ""), s.mean != null ? s.mean <= g.year : null)}
            ${tile("Dönem ortalaması (PM₁₀)", s10.mean != null ? f1(s10.mean) : "—",
                   `yıllık kılavuz ${g10.year} µg/m³` + (s10.mean != null ? ` · ${s10.exceed} günde günlük ${g10.day} aşıldı` : "") + " · ham sensör değeri", s10.mean != null ? s10.mean <= g10.year : null)}
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
            // Etiket çizim alanının sağ dışında (layout.padding.right): hiçbir çubuğun üstüne binmez
            ctx.setLineDash([]); ctx.font = "700 10px Inter, sans-serif";
            ctx.fillStyle = "#e8ecf4"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
            ctx.fillText("WHO", right + 5, y - 6); ctx.fillText(String(G.pm2_5.day), right + 5, y + 6);
            ctx.restore();
        },
    };

    // Takvim ekseni: dönemdeki her gün bir sütun; ölçüm olmayan gün boş kalır (veri kesintisi saklanmaz).
    // k: gün alanının adı ("k" günlük ortalamalar, "day" kampüs–Tuzla eşleşmeleri)
    function calendarDays(days, k = "k") {
        if (!days.length) return [];
        const today = dayKey.format(new Date());
        let from = days[0][k], to = days[days.length - 1][k];
        if (period === "last30") { from = dayKey.format(new Date(Date.now() - 29 * 864e5)); to = today; }
        else if (/^\d{4}-\d{2}$/.test(period || "")) {
            from = period + "-01";
            const end = new Date(Date.UTC(+period.slice(0, 4), +period.slice(5, 7), 0)).toISOString().slice(0, 10);
            to = end < today ? end : today;
        }
        const by = new Map(days.map(d => [d[k], d])), out = [];
        for (let t = new Date(from + "T12:00:00Z"); ; t = new Date(t.getTime() + 864e5)) {
            const key = t.toISOString().slice(0, 10);
            if (key > to) break;
            out.push(by.get(key) || { [k]: key, empty: true });
        }
        return out;
    }

    function drawChart(days) {
        const canvas = $("who-chart");
        if (!canvas || typeof Chart === "undefined" || !days.length) return;
        const g = G.pm2_5;
        const measured = days;
        days = calendarDays(measured);
        const data = days.map(d => d.empty ? null : Math.round(d.v * 10) / 10);
        const colors = days.map(d => d.empty ? THIN : d.n < MIN_H ? THIN : d.v > g.day ? BAD : BAR);
        if (chart) chart.destroy();
        chart = new Chart(canvas, {
            type: "bar",
            data: { labels: days.map(d => dayLabel(d.k)),
                    datasets: [{ data, backgroundColor: colors.map((c, i) => days[i].n < MIN_H ? c + "88" : c),
                                 borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 14, categoryPercentage: 0.82 }] },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false, layout: { padding: { right: 30 } },
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
                    y: { min: 0, suggestedMax: Math.max(g.day * 1.6, ...data.filter(v => v != null)) * 1.1, grid: { color: "rgba(255,255,255,0.06)" },
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

    // Kampüs ve bölge: aynı saatlerde kampüs PurpleAir ile Tuzla istasyonu (PM₂.₅)
    async function fillKiyas() {
        const box = $("who-kiyas");
        if (!box || typeof Kiyas === "undefined") return;
        const head = `<div class="nsec-title">Kampüs ve bölge · aynı saatler · PM₂.₅</div>`;
        let d;
        try { d = await Kiyas.data(); } catch (_) { box.innerHTML = head + `<div class="who-cap">Tuzla verisi yüklenemedi.</div>`; return; }
        if (!$("who-kiyas")) return;
        if (!d.regionHours) {
            box.innerHTML = head + `<div class="who-cap">Tuzla istasyonunun PM₂.₅ geçmişi henüz yüklenmedi (resmî ÇŞB verisi yalnızca
                Türkiye'den indirilebiliyor). Yüklendiğinde bu bölüm kendiliğinden dolacak.</div>`;
            return;
        }
        const pairs = d.pairs.filter(x => inPeriod({ k: x.day }));
        const s = Kiyas.summary(pairs);
        if (!s) { box.innerHTML = head + `<div class="who-cap">${periodLabel()} döneminde kampüs ve Tuzla'nın aynı anda ölçtüğü saat yok.</div>`; return; }
        const v = Kiyas.verdict(s);
        const months = [...new Set(d.pairs.map(x => x.ym))].sort().reverse();
        const mrow = ym => {
            const m = Kiyas.summary(d.pairs.filter(x => x.ym === ym));
            return `<tr><td>${monthName(ym)}</td><td>${m.n}</td><td>${f1(m.c)}</td><td>${f1(m.r)}</td>
                <td class="${m.pct >= 5 ? "bad" : ""}">${m.pct > 0 ? "+" : "−"}%${Math.abs(m.pct).toFixed(0)}</td></tr>`;
        };
        box.innerHTML = head + `
            <div class="oz-line ${v.cls}">${v.icon} ${v.txt} <small>(${s.n} ortak saat · kampüsün daha temiz olduğu saat oranı: %${(s.cleaner * 100).toFixed(0)})</small></div>
            <div class="kx-pair">
              <div><i style="background:${Kiyas.C_CAMPUS}"></i><span>Kampüs (PurpleAir)</span><b>${f1(s.c)}</b></div>
              <div><i style="background:${Kiyas.C_REGION}"></i><span>Tuzla istasyonu</span><b>${f1(s.r)}</b></div>
            </div>
            <div class="who-chart-wrap"><canvas id="who-kiyas-chart" aria-label="Günlük ortalamalar: kampüs ve Tuzla"></canvas></div>
            <div class="who-legend"><span><i style="background:${Kiyas.C_CAMPUS}"></i>Kampüs</span><span><i style="background:${Kiyas.C_REGION}"></i>Tuzla</span><span><i class="dash"></i>WHO günlük değer</span></div>
            <table class="who-month" style="margin-top:10px"><thead><tr><th>Ay</th><th>Saat</th><th>Kampüs</th><th>Tuzla</th><th>Fark</th></tr></thead>
              <tbody>${months.map(mrow).join("")}</tbody></table>
            <div class="who-cap">Aynı ölçekte karşılaştırma: Tuzla ~6,4 km uzaktaki resmî istasyondur, değeri olduğu gibi kullanılır
              (geçmiş ÇŞB'den; 6 Ekim 2026'dan beri aynı istasyonun İBB'deki saatlik değeri). Kampüs değeri, PurpleAir'i resmî cihaz
              ölçeğine çeken US EPA düzeltmesinden geçmiştir (Hakkında › Yöntem). Yalnızca iki tarafın da ölçüm yaptığı saatler
              karşılaştırılır (µg/m³); boş günlerde ortak ölçüm yok.</div>`;
        const days = calendarDays(Kiyas.daily(pairs), "day");
        if (kchart) kchart.destroy();
        kchart = new Chart($("who-kiyas-chart"), {
            type: "bar",
            data: { labels: days.map(x => dayLabel(x.day)), datasets: [
                { label: "Kampüs", data: days.map(x => x.empty ? null : +x.c.toFixed(1)), backgroundColor: Kiyas.C_CAMPUS, borderRadius: 4, maxBarThickness: 10 },
                { label: "Tuzla", data: days.map(x => x.empty ? null : +x.r.toFixed(1)), backgroundColor: Kiyas.C_REGION, borderRadius: 4, maxBarThickness: 10 },
            ] },
            options: {
                responsive: true, maintainAspectRatio: false, animation: false, layout: { padding: { right: 30 } },
                datasets: { bar: { categoryPercentage: 0.8, barPercentage: 0.9 } },
                plugins: { legend: { display: false }, tooltip: { callbacks: {
                    afterBody: it => days[it[0].dataIndex].empty ? "" : `${days[it[0].dataIndex].n} ortak saat` } } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#9aa4b8", font: { size: 9.5 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } },
                    y: { min: 0, suggestedMax: G.pm2_5.day * 1.6, grid: { color: "rgba(255,255,255,0.06)" }, border: { display: false },
                         ticks: { color: "#9aa4b8", font: { size: 10 }, maxTicksLimit: 5 } },
                },
            },
            plugins: [guideLine],
        });
    }

    // Bina bazında: saha ölçümlerinin bina ortalamaları ve WHO günlük değeri
    // Binalar: saha ölçümleri kısa süreli (yürüyüş) olduğundan WHO'nun 24 saatlik değeriyle karşılaştırılmaz;
    // her bina aynı dönemdeki tüm saha ölçümlerinin ortalamasıyla (kampüs saha ortalaması) karşılaştırılır.
    function buildingsHtml() {
        const head = `<div class="nsec-title">Binalar · saha ölçümleri · kampüs ortalamasına göre</div>`;
        if (field == null) return head + `<div class="who-cap">Saha ölçümleri yükleniyor…</div>`;
        const pts = field.filter(pointInPeriod);
        const list = typeof Campus !== "undefined" ? Campus.buildingStats(pts) : null;
        if (list == null) return head + `<div class="who-cap">Kampüs haritası yükleniyor…</div>`;
        if (!list.length) return head + `<div class="who-cap">${periodLabel()} döneminde bina içine düşen saha ölçümü yok.</div>`;
        const ref = mean(pts.map(p => +p.pm2_5));
        list.sort((a, b) => b.avg - a.avg);
        const over = list.filter(b => b.avg > ref).length;
        const max = Math.max(ref * 1.6, list[0].avg) * 1.05;
        const pct = v => (v / max * 100).toFixed(1);
        const diff = b => { const d = (b.avg - ref) / ref * 100; return Math.abs(d) < 5 ? "≈" : `${d > 0 ? "+" : "−"}%${Math.abs(d).toFixed(0)}`; };
        const rowHtml = b => `
            <button type="button" class="wb-row${b.few ? " few" : ""}" data-gk="${b.gk.replace(/"/g, "&quot;")}" title="Haritada göster">
              <span class="wb-name">${b.icon} ${b.name}<small>${b.n.toLocaleString("tr-TR")} ölçüm · ${b.durText} · ${b.dur.days} gün${b.few ? " · az ölçüm" : ""}</small></span>
              <span class="wb-bar"><i style="width:${pct(b.avg)}%;background:${b.avg > ref ? BAD : BAR}"></i><em style="left:${pct(ref)}%"></em></span>
              <span class="wb-val ${b.avg > ref ? "bad" : ""}">${f1(b.avg)}<small>${diff(b)}</small></span>
            </button>`;
        const TOP = 10;
        const rowsHtml = list.slice(0, TOP).map(rowHtml).join("") + (list.length > TOP
            ? `<details class="wb-more"><summary>Tüm binaları göster (${list.length})</summary>${list.slice(TOP).map(rowHtml).join("")}</details>` : "");
        return head + `<div class="wh-sub" style="margin:0 0 8px">${periodLabel()}: ölçüm yapılan <b>${list.length}</b> binadan
              <b>${over}</b> tanesinde ortalama PM₂.₅, kampüs saha ortalamasının (<b>${f1(ref)}</b> µg/m³) üstünde.</div>
            <div class="wb-list">${rowsHtml}</div>
            <div class="who-legend"><span><i style="background:${BAR}"></i>Kampüs ortalamasının altında</span><span><i style="background:${BAD}"></i>Üstünde</span>
              <span><i class="tick"></i>Kampüs saha ortalaması</span><span>Soluk: 30'dan az ölçüm</span></div>
            <div class="who-cap">Saha ölçümleri yürürken alınan kısa süreli değerlerdir; WHO kılavuz değeri ise 24 saatlik ortalama için
              tanımlandığından binalar WHO ile değil, aynı dönemdeki tüm saha ölçümlerinin ortalamasıyla karşılaştırılır. Süre, binada
              ölçüm yapılan toplam süredir. Binaya dokununca haritada açılır.</div>`;
    }

    const INFO = `<div class="who-info">
        <div class="nsec-title">WHO kılavuz değerleri (2021)</div>
        <table><thead><tr><th></th><th>24 saat</th><th>Yıllık</th></tr></thead><tbody>
          <tr><td>PM₂.₅</td><td><b>15</b> µg/m³</td><td><b>5</b> µg/m³</td></tr>
          <tr><td>PM₁₀</td><td><b>45</b> µg/m³</td><td><b>15</b> µg/m³</td></tr>
        </tbody></table>
        <p>24 saatlik değer yılda 3–4 günden fazla aşılmamalıdır. Kılavuz değere hemen ulaşılamayan yerler için kademeli
        <b>ara hedefler</b> (AH-1…AH-4) tanımlanmıştır: PM₂.₅ günlük 75 → 50 → 37,5 → 25, yıllık 35 → 25 → 15 → 10 µg/m³.</p>
        <p class="who-note">PM₂.₅ değerleri kampüs çatısındaki PurpleAir sensörünün <b>US EPA düzeltmesinden</b> geçmiş değerleridir
        (optik sensörün ham değeri referans cihazlara göre yüksek okur ve nemden etkilenir; yöntem: Hakkında › Yöntem). PM₁₀ için
        yerleşik bir düzeltme olmadığından PM₁₀ ham sensör değeridir. Ölçümler kesintilidir: günlük değer, o gün ölçülen saatlerin ortalamasıdır ve
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
        return `<div class="who-banner">${ico("plug")}PurpleAir sensöründen <b>${longDay(last)}</b>'dan beri veri gelmiyor.
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
                <span><i style="background:${THIN}88"></i>${MIN_H} saatten az ölçüm</span><span><i class="dash"></i>WHO günlük değer</span><span>Boş gün: ölçüm yok</span></div>`
                : `<div class="news-empty" style="margin-top:12px">Bu dönemde ölçüm yok.</div>`)
            + tilesHtml(s, s10) + `<div id="who-kiyas"></div>` + buildingsHtml() + monthlyHtml(all, all10) + tableHtml(days, days10) + INFO;
        $("who-body").querySelectorAll("[data-p]").forEach(el =>
            el.addEventListener("click", () => { period = el.dataset.p; render(); }));
        $("who-body").querySelectorAll(".wb-row").forEach(el => el.addEventListener("click", () => {
            document.body.classList.remove("who-open");         // masaüstünde panel haritayı kapatmasın
            Campus.focusByKey(el.dataset.gk, field.filter(pointInPeriod));   // kart listedeki dönemin verisiyle açılır
        }));
        drawChart(days);
        fillKiyas();
    }

    async function load(force) {
        if (busy || (!force && Date.now() - loadedAt < 10 * 60e3)) { if (chart) chart.resize(); return; }
        busy = true;
        if (!loadedAt) $("who-body").innerHTML = `<div class="news-empty">Hesaplanıyor…</div>`;
        try {
            rows = await history();
            render();
            loadedAt = Date.now();
            if (field == null) loadField();
        } catch (e) {
            if (!loadedAt) $("who-body").innerHTML = `<div class="news-empty">Veri alınamadı (${e.message}). Biraz sonra tekrar deneyin.</div>`;
        } finally { busy = false; }
    }

    async function loadField() {
        try { field = await fieldPoints(); } catch (_) { field = []; }
        render();
    }

    // Özet sekmesinden belirli bir ayla açmak için
    function setPeriod(p) { period = p; if (loadedAt) render(); }

    return { load, setPeriod, history, fieldPoints, dailyMeans, G, MIN_H, FULL_H };
})();
