// Özet sekmesi — kampüsteki herkes için (öğrenci, akademik ve idari personel) sade bir bakış:
//   Günlük özet: şu anki hava, ne yapmalı, WHO kılavuz değerlerine göre bugün, sensörlerin durumu
//   Aylık özet: ay ortalaması, WHO aşım günleri, en temiz / en kirli binalar, önceki aya göre değişim
// Bağımlılıklar: api.js, colorscale.js, who.js (ortak veri), campus.js, app.js (getTuzla, trTime, timeAgo)

const Ozet = (() => {
    const PA_FRESH_MIN = 120;
    let month = null, busy = false, loadedAt = 0;
    let hist = [], field = null, now = {}, kiyas = null;

    const $ = id => document.getElementById(id);
    const f1 = v => v.toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
    const dayKey = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    const monthName = ym => new Date(ym + "-15T12:00:00").toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
    const dayLabel = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long" });
    const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

    // Sade dille ne yapmalı: HKİ sınıflarına göre (hassas gruplar: astım, kalp-akciğer hastalığı, yaşlılar, gebeler, çocuklar)
    const ADVICE = {
        "İyi":       { all: "Hava kalitesi iyi; açık hava etkinlikleri için uygun.",
                       sens: "Hassas gruplar için de risk düşük." },
        "Orta":      { all: "Hava kalitesi kabul edilebilir düzeyde.",
                       sens: "Kirliliğe karşı çok hassas kişiler uzun süreli ve yoğun açık hava etkinliklerini sınırlamayı düşünebilir." },
        "Hassas":    { all: "Genel nüfus için risk düşük.",
                       sens: "Hassas grupların uzun süreli ve yoğun açık hava etkinliklerini azaltması önerilir." },
        "Sağlıksız": { all: "Uzun süreli ve yoğun açık hava etkinliklerinin azaltılması önerilir.",
                       sens: "Hassas grupların açık hava etkinliklerinden kaçınması önerilir." },
        "Kötü":      { all: "Açık hava etkinliklerinin kısaltılması, mümkünse kapalı alanda kalınması önerilir.",
                       sens: "Hassas grupların dışarıda bulunmaması önerilir." },
        "Tehlikeli": { all: "Açık havada bulunmaktan kaçınılması ve pencerelerin kapalı tutulması önerilir.",
                       sens: "Hassas grupların iç mekânda kalması, şikâyet olursa sağlık birimine başvurması önerilir." },
    };

    // HKİ ölçeği: altı sınıf eşit genişlikte; değer kendi sınıfının içinde indeksine göre konumlanır
    function scaleHtml(h) {
        const pos = Math.min(99.5, (h.k + (h.i - h.ilo) / (h.ihi - h.ilo)) * 100 / HKI_PM25.length);
        return `<div class="oz-scale" role="img" aria-label="HKİ ölçeği: ${h.i}, ${h.ad}">
            <div class="oz-scale-bar">${HKI_PM25.map(b => `<i style="background:${b.renk}"></i>`).join("")}
              <em style="left:${pos.toFixed(1)}%"></em></div>
            <div class="oz-scale-lab">${HKI_PM25.map(b => `<span>${b.ad}</span>`).join("")}</div>
            <div class="oz-scale-tick">${HKI_PM25.slice(0, 5).map((b, k) => `<span style="left:${((k + 1) * 100 / HKI_PM25.length).toFixed(2)}%">${b.ihi}</span>`).join("")}</div>
          </div>`;
    }
    let current = null;   // sohbet asistanı ve diğer modüller için son kullanılan değer

    // ── Günlük özet ──────────────────────────────────────────────────
    async function fetchNow() {
        const out = {};
        const tasks = [
            API.purpleairLatest().then(r => { out.pa = r.data; }).catch(() => {}),
            (typeof getTuzla === "function" ? getTuzla() : Promise.resolve(null)).then(d => { out.tz = d; }).catch(() => {}),
            API.atmotubeLive().then(r => { out.atp = r.data || []; }).catch(() => {}),
            API.co2Live().then(r => { out.co2 = r.data || []; }).catch(() => {}),
        ];
        await Promise.all(tasks);
        return out;
    }

    function ageMin(iso) { const t = typeof trTime === "function" ? trTime(iso) : new Date(iso); return t ? (Date.now() - t) / 60000 : Infinity; }
    const ago = iso => typeof timeAgo === "function" ? timeAgo(typeof trTime === "function" ? trTime(iso) : iso) : "";

    function dailyHtml() {
        const pa = now.pa, tz = now.tz;
        const paFresh = pa && pa.pm2_5 != null && ageMin(pa.recorded_at) <= PA_FRESH_MIN;
        const tzFresh = tz && tz.pm2_5 != null && !tz.stale;
        const src = paFresh ? { v: pa.pm2_5, where: "Kampüs · PurpleAir (SUMER çatısı)", at: pa.recorded_at }
                  : tzFresh ? { v: tz.pm2_5, where: "Bölge · Tuzla istasyonu (6,4 km)", at: tz.recorded_at, note: "Kampüs sensörü şu an çevrimdışı; en yakın resmî istasyonun değeri gösteriliyor." }
                  : null;
        const today = new Date().toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" });
        let html = `<div class="oz-head"><span>Günlük özet</span><small>Bugün · ${today}</small></div>`;

        if (!src) {
            html += `<div class="oz-card"><div class="wh-empty">Şu an güncel ölçüm yok: kampüs sensörü ve bölge istasyonu veri göndermiyor.
                Sensör durumlarını aşağıda görebilirsiniz.</div></div>`;
        } else {
            const h = hki(src.v), a = ADVICE[h.ad] || ADVICE["Orta"];
            current = { ...src, h };
            document.dispatchEvent(new CustomEvent("airlab:hki", { detail: current }));
            html += `<div class="oz-card oz-now" style="--c:${h.renk}">
                <div class="oz-now-top">
                  <span class="oz-face" aria-hidden="true">${ico(h.yuz)}</span>
                  <div class="oz-hki"><b>${h.i}</b><span>HKİ</span></div>
                  <div class="oz-cat">${h.ad}</div>
                </div>
                <div class="oz-val2">PM₂.₅ <b>${f1(src.v)}</b> µg/m³ <span>(ince partikül)</span></div>
                <div class="oz-src">${ico("clock")} ${src.where} · ${ago(src.at)}</div>
                ${scaleHtml(h)}
                ${src.note ? `<div class="oz-note">${ico("info")}<span>${src.note}</span></div>` : ""}
                <div class="oz-adv"><div>${ico("users")}<span><b>Herkes için:</b> ${a.all}</span></div><div>${ico("heart-pulse")}<span><b>Hassas gruplar:</b> ${a.sens}</span></div></div>
                <div class="who-cap">HKİ: Ulusal Hava Kalitesi İndeksi (ÇŞB). Resmî HKİ 24 saatlik ortalamaya göre hesaplanır; burada son ölçüme göre gösterge değerdir.
                  <button type="button" class="oz-link" data-info="inf-sinir">Sınır değerler</button></div>
              </div>`;
        }

        // Bugünün kampüs ortalaması (WHO günlük değeri ile)
        const tk = dayKey.format(new Date());
        const todayRow = WHO.dailyMeans(hist, "pm2_5").find(d => d.k === tk);
        if (todayRow && todayRow.n >= 3) {
            const ok = todayRow.v <= WHO.G.pm2_5.day;
            html += `<div class="oz-line ${ok ? "ok" : "bad"}">${ico(ok ? "circle-check" : "triangle-alert")} Bugün şimdiye kadarki kampüs ortalaması <b>${f1(todayRow.v)}</b> µg/m³ —
                WHO günlük değeri ${WHO.G.pm2_5.day}'in ${ok ? "altında" : "üstünde"} <small>(${todayRow.n} saatlik ölçüm)</small></div>`;
        }
        if (paFresh && tzFresh) {
            const d = pa.pm2_5 - tz.pm2_5;
            html += `<div class="oz-line">${d < -0.5 ? ico("trending-down") + " Kampüs bölgeden daha temiz" : d > 0.5 ? ico("trending-up") + " Kampüs bölgeden daha kirli" : ico("equal") + " Kampüs ve bölge benzer"}
                <small>(kampüs ${f1(pa.pm2_5)} · Tuzla ${f1(tz.pm2_5)})</small></div>`;
        }

        // Sensör durumu
        const atpOn = (now.atp || []).filter(d => d.reading && ageMin(d.reading.recorded_at) < 60).length;
        const co2On = (now.co2 || []).filter(d => d.reading && d.reading.co2_ppm != null && ageMin(d.reading.recorded_at) < 60).length;
        const chip = (ok, name, txt) => `<span class="oz-chip ${ok ? "on" : "off"}"><i></i>${name}<small>${txt}</small></span>`;
        html += `<div class="oz-sub">Sensörler</div><div class="oz-chips">
            ${chip(paFresh, "PurpleAir", pa && pa.recorded_at ? (paFresh ? "canlı" : "son veri " + ago(pa.recorded_at)) : "veri yok")}
            ${chip(tzFresh, "Tuzla istasyonu", tz && tz.recorded_at ? (tzFresh ? "güncel" : "son veri " + ago(tz.recorded_at)) : "veri yok")}
            ${chip(atpOn > 0, "Atmotube", `${atpOn}/${(now.atp || []).length} çevrimiçi`)}
            ${chip(co2On > 0, "CO₂ (iç mekân)", (now.co2 || []).length ? `${co2On}/${now.co2.length} çevrimiçi` : "tanımlı değil")}
        </div>
        <button type="button" class="ic-btn oz-more oz-exp" id="oz-to-exp">${ico("message-circle")} AirLab asistanı: kampüste ne kadar PM₂.₅ soludum?</button>`;
        return html;
    }

    // ── Aylık özet ───────────────────────────────────────────────────
    function monthsAvailable(days) {
        const set = new Set(days.map(d => d.k.slice(0, 7)));
        (field || []).forEach(p => { const t = new Date(p.recorded_at); if (!isNaN(t)) set.add(dayKey.format(t).slice(0, 7)); });
        return [...set].sort();
    }

    function monthStats(days, ym) {
        const md = days.filter(d => d.k.startsWith(ym));
        const usable = md.filter(d => d.n >= WHO.MIN_H);
        return {
            days: md, usable,
            hours: md.reduce((s, d) => s + d.n, 0),
            mean: usable.length ? mean(usable.map(d => d.v)) : null,
            exceed: usable.filter(d => d.v > WHO.G.pm2_5.day).length,
            worst: usable.length ? usable.reduce((a, b) => b.v > a.v ? b : a) : null,
            best: usable.length ? usable.reduce((a, b) => b.v < a.v ? b : a) : null,
        };
    }

    // Bu ay kampüs ile Tuzla aynı saatlerde
    function regionLine() {
        if (!kiyas || !kiyas.regionHours) return "";
        const s = Kiyas.summary(kiyas.pairs.filter(x => x.ym === month));
        const v = Kiyas.verdict(s);
        if (!v) return "";
        return `<div class="oz-region">${v.icon} Aynı saatlerde ${v.txt.charAt(0).toLowerCase() + v.txt.slice(1)}
            <small>(kampüs ${f1(s.c)} · Tuzla ${f1(s.r)} · ${s.n} saat)</small></div>`;
    }

    function monthlyHtml() {
        const days = WHO.dailyMeans(hist, "pm2_5");
        const months = monthsAvailable(days);
        let html = `<div class="oz-head" style="margin-top:22px"><span>Aylık özet</span></div>`;
        if (!months.length) return html + `<div class="oz-card"><div class="wh-empty">Henüz ölçüm yok.</div></div>`;
        if (!month || !months.includes(month)) month = months[months.length - 1];
        const i = months.indexOf(month);
        html += `<div class="oz-month-nav">
            <button type="button" data-m="${months[i - 1] || ""}" ${i > 0 ? "" : "disabled"} aria-label="Önceki ay">${ico("chevron-left")}</button>
            <b>${monthName(month)}</b>
            <button type="button" data-m="${months[i + 1] || ""}" ${i < months.length - 1 ? "" : "disabled"} aria-label="Sonraki ay">${ico("chevron-right")}</button>
          </div>`;

        const s = monthStats(days, month);
        const prevYm = months.slice(0, i).reverse().find(m => monthStats(days, m).mean != null);
        const prev = prevYm ? monthStats(days, prevYm) : null;
        const g = WHO.G.pm2_5;

        if (s.mean != null) {
            const ok = s.mean <= g.year;
            let trend = "";
            if (prev && prev.mean != null) {
                const pct = (s.mean - prev.mean) / prev.mean * 100;
                trend = `<div class="oz-trend ${pct > 0 ? "up" : "down"}">${pct > 0 ? "▲" : "▼"} ${monthName(prevYm).split(" ")[0]} ayına göre %${Math.abs(pct).toFixed(0)} ${pct > 0 ? "daha kirli" : "daha temiz"}</div>`;
            }
            html += `<div class="oz-card">
                <div class="wh-k">Kampüs ortalaması · PM₂.₅ · PurpleAir</div>
                <div class="oz-val"><b style="color:${pm25Color(s.mean)}">${f1(s.mean)}</b><span>µg/m³ · ${pm25Label(s.mean)}</span></div>
                ${trend}${regionLine()}
                <div class="oz-tiles">
                  <div class="${s.exceed ? "bad" : "ok"}"><span>WHO günlük değeri (${g.day}) aşılan gün</span><b>${s.exceed} / ${s.usable.length}</b></div>
                  <div class="${ok ? "ok" : "bad"}"><span>WHO yıllık değerine (${g.year}) göre</span><b>${f1(s.mean / g.year)} kat</b></div>
                  ${s.usable.length >= 2 ? `<div><span>En kirli gün</span><b>${dayLabel(s.worst.k)}</b><small>${f1(s.worst.v)} µg/m³</small></div>
                  <div><span>En temiz gün</span><b>${dayLabel(s.best.k)}</b><small>${f1(s.best.v)} µg/m³</small></div>` : ""}
                </div>
                <div class="who-cap">${s.hours} saatlik ölçüm; ${s.usable.length} gün değerlendirmeye girdi (en az ${WHO.MIN_H} saat ölçülen günler).</div>
              </div>`;
        } else {
            html += `<div class="oz-card"><div class="wh-empty">Bu ay kampüs sensöründen yeterli ölçüm yok${s.hours ? ` (${s.hours} saat)` : ""}.
                ${field && field.length ? "Aşağıda bu ayın saha ölçümlerine göre binalar var." : ""}</div></div>`;
        }

        // Binalar: bu ayın saha ölçümleri
        if (field == null) {
            html += `<div class="who-cap" style="margin-top:10px">Bina verileri yükleniyor…</div>`;
        } else {
            const pts = field.filter(p => { const t = new Date(p.recorded_at); return !isNaN(t) && dayKey.format(t).startsWith(month); });
            const list = (Campus.buildingStats(pts) || []).filter(b => !b.few).sort((a, b) => b.avg - a.avg);
            if (list.length >= 2) {
                const row = b => `<button type="button" class="oz-bld" data-gk="${esc(b.gk)}">
                    <span>${b.icon} ${esc(b.name)}</span><b style="color:${pm25Color(b.avg)}">${f1(b.avg)}</b></button>`;
                const n = Math.min(3, Math.floor(list.length / 2));
                html += `<div class="oz-bld-grid">
                    <div><div class="oz-sub"><i class="dot" style="background:var(--red)"></i>En yüksek PM₂.₅</div>${list.slice(0, n).map(row).join("")}</div>
                    <div><div class="oz-sub"><i class="dot" style="background:var(--green)"></i>En düşük PM₂.₅</div>${list.slice(-n).reverse().map(row).join("")}</div>
                  </div>
                  <div class="who-cap">Saha ölçümlerinin bina ortalamaları (en az 30 ölçüm). Binaya dokununca haritada açılır.</div>`;
            } else {
                html += `<div class="who-cap" style="margin-top:10px">Bu ay bina karşılaştırması için yeterli saha ölçümü yok.</div>`;
            }
        }
        html += `<button type="button" class="ic-btn oz-more" id="oz-to-who">${ico("shield-check")} ${monthName(month)}: WHO kılavuz değerleriyle karşılaştırmalı değerlendirme</button>`;
        return html;
    }

    function render() {
        const body = $("ozet-body");
        body.innerHTML = dailyHtml() + monthlyHtml() + `<div class="oz-foot">
            <button type="button" data-info="inf-yon">Yöntem</button><button type="button" data-info="inf-sinir">Sınır değerler</button><button type="button" data-info="inf-kay">Veri kaynakları</button>
            <button type="button" data-info="inf-kvkk">Gizlilik (KVKK)</button><button type="button" data-info="inf-hak">Hakkında</button></div>`;
        body.querySelectorAll("[data-info]").forEach(b => b.addEventListener("click", () => {
            Shell.openPanel("info");
            setTimeout(() => document.getElementById(b.dataset.info)?.scrollIntoView({ block: "start" }), 60);
        }));
        body.querySelectorAll(".oz-month-nav [data-m]").forEach(b => b.addEventListener("click", () => {
            if (b.dataset.m) { month = b.dataset.m; render(); }
        }));
        body.querySelectorAll(".oz-bld").forEach(b => b.addEventListener("click", () => {
            document.body.classList.remove("ozet-open");
            const pts = (field || []).filter(p => { const t = new Date(p.recorded_at); return !isNaN(t) && dayKey.format(t).startsWith(month); });
            Campus.focusByKey(b.dataset.gk, pts);   // kart o ayın saha ölçümleriyle açılır
        }));
        $("oz-to-exp")?.addEventListener("click", () => Shell.openPanel("exp"));
        const toWho = $("oz-to-who");
        if (toWho) toWho.addEventListener("click", () => { WHO.setPeriod(month); Shell.openPanel("who"); });
    }

    async function load(force) {
        if (busy || (!force && Date.now() - loadedAt < 5 * 60e3)) return;
        busy = true;
        if (!loadedAt) $("ozet-body").innerHTML = `<div class="news-empty">Özet hazırlanıyor…</div>`;
        try {
            const [n, h] = await Promise.all([fetchNow(), WHO.history().catch(() => [])]);
            now = n; hist = h;
            render();
            loadedAt = Date.now();
            if (field == null) WHO.fieldPoints().then(f => { field = f; render(); }).catch(() => { field = []; render(); });
            if (kiyas == null && typeof Kiyas !== "undefined") Kiyas.data().then(k => { kiyas = k; render(); }).catch(() => {});
        } finally { busy = false; }
    }

    return { load, current: () => current };
})();
