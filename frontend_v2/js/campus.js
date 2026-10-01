// Kampüs bileşenleri katmanı — Serra'nın AtmotubePro-FieldLog haritasından alınan
// GeoJSON (binalar, yeşil alanlar, orman, yollar, otoparklar, bölge sınırları).
// Ayrıca seçili saha ölçümlerini binalara düşürüp bina bazında PM₂.₅ ortalaması verir.
// Bağımlılıklar: Leaflet, colorscale.js (pm25Color, pm25Label)

const Campus = (() => {
    // Bağlam katmanı renkleri — veri noktalarının (PM ölçeği) önüne geçmesin diye geri planda.
    // Bina/yeşil çifti dataviz doğrulayıcısından geçti (koyu zemin, CVD ΔE 20.1, normal ΔE 22.3).
    // Yol/otopark tonsuz altyapı: gri + kesik çizgi dokusuyla ayrışır.
    const BLUE = "#5b8def", GREEN = "#3aa36f", GRAY = "#c9ccd3";
    const STYLE = {
        bina:    { color: BLUE,  weight: 1.2, opacity: 0.9,  fillColor: BLUE,  fillOpacity: 0.26 },
        yesil:   { color: GREEN, weight: 0.8, opacity: 0.45, fillColor: GREEN, fillOpacity: 0.16 },
        orman:   { color: GREEN, weight: 1.4, opacity: 0.85, fillColor: GREEN, fillOpacity: 0.36, dashArray: "1 4" },
        yol:     { color: GRAY,  weight: 0,   opacity: 0,    fillColor: GRAY,  fillOpacity: 0.14 },
        otopark: { color: GRAY,  weight: 1,   opacity: 0.7,  fillColor: GRAY,  fillOpacity: 0.10, dashArray: "4 3" },
        sinir:   { color: "#ffffff", weight: 1.6, opacity: 0.55, fill: false, dashArray: "6 6" },
    };
    const CAT_LABEL = { bina: "Bina", yesil: "Yeşil alan", orman: "Orman", yol: "Yol", otopark: "Otopark", sinir: "Bölge sınırı" };
    const REGION_LABEL = { KD: "Kuzey-Doğu", KB: "Kuzey-Batı", GB: "Güney-Batı", SE: "Güney-Doğu",
                           NORTH: "Kuzey Kampüs", SOUTH: "Güney Kampüs" };
    // Birim türleri — Serra'nın haritasındaki sınıflama. Renk değil simge ile kodlanır:
    // bina dolgusu PM₂.₅ ölçeğine ayrıldığı için ikinci bir renk anlamı yüklenmez.
    const UNIT = {
        bolum:     { icon: "🎓", label: "Bölüm / Fakülte" },
        arastirma: { icon: "🔬", label: "Araştırma / Lab" },
        sosyal:    { icon: "☕", label: "Sosyal / Yemek / Yurt" },
        spor:      { icon: "⚽", label: "Spor / Açık alan" },
        ozel:      { icon: "🏛️", label: "İdari / Hizmet" },
        giris:     { icon: "🚪", label: "Giriş" },
        diger:     { icon: "🏢", label: "Diğer" },
    };
    const MIN_PTS = 3;          // bina ortalaması için gereken en az ölçüm
    const FEW = 30;             // bunun altındaki ortalamalar "az ölçüm" diye işaretlenir
    // Kart açılınca harita, kart sol/sağ panellerin altında kalmayacak şekilde kaysın
    const POPUP_OPTS = { maxWidth: 360, autoPanPaddingTopLeft: [270, 80], autoPanPaddingBottomRight: [350, 60] };
    const GENERIC = /^(bina \d+|küçük binalar)$/i;   // adı tanımlayıcı olmayan binalar: en düşük öncelik

    // Kademeli etiketler (Google Haritalar gibi): her binanın adı kendi yakınlık eşiğinden itibaren görünür.
    // Uzaktan yalnızca simge yapılar, yaklaştıkça bölümler, en yakında küçük birimler ve açık alanlar.
    // Çakışan etiketler yine öncelik sırasıyla gizlenir.
    const LABEL_ZOOM = 15;      // en erken etiket eşiği
    const FULL_NAME_ZOOM = 18;  // bunun altında uzun adlar kısaltılır (Müh., Fak., Lab. …)
    const REGION_MAX_ZOOM = 16; // Kuzey/Güney Kampüs yazısı yalnızca uzaktan
    const KEY = /rektörlük|^kütüphane$|kongre|ana kapı|teknopark/i;       // her zaman uzaktan
    const LANDMARK = /fakülte|yurdu|yemekhane/i;
    const MINOR = /açık alan|saha|ön bahçe|^tenis|kelebek ön|lojman|kırtasiye/i;
    function labelTier(e) {
        const name = e.feature.properties.name, a = e.areaM2;
        if (GENERIC.test(name) || MINOR.test(name)) return 4;          // ≥19
        if (KEY.test(name) || a > 3000 || (LANDMARK.test(name) && a > 1000)) return 1;   // ≥15
        if (a > 1500 || LANDMARK.test(name) || /salon/i.test(name)) return 2;          // ≥16
        if (a > 800 || e.unit === "bolum") return 3;                                   // ≥17 (açılış yakınlığı)
        if (a > 400 || e.unit === "sosyal" || e.unit === "giris") return 3.5;          // ≥18
        return 4;                                                                       // ≥19
    }
    const TIER_ZOOM = { 1: 15, 2: 16, 3: 17, 3.5: 18, 4: 19 };

    // Ad düzeltmeleri (kaynaktaki yazım hataları) ve kısaltmalar
    const TIDY = [[/Mühendsiliği/g, "Mühendisliği"], [/Laboratuvaru/g, "Laboratuvarı"], [/\s*,\s*/g, ", "], [/^tenis\s*(\d*)$/i, "Tenis Kortu $1"]];
    const ABBR = [[/Mühendisliği/g, "Müh."], [/Müh\. Bölümü/g, "Müh."], [/Fakültesi/g, "Fak."], [/Laboratuvarı/g, "Lab."],
                  [/Enstitüsü/g, "Enst."], [/Daire(si)? Başkanlığı/g, "D. Bşk."], [/^(Gebze Teknik Üniversitesi|GTÜ) /, ""],
                  [/, /g, " / "]];
    const tidyName = n => TIDY.reduce((t, [re, to]) => t.replace(re, to), n).trim();
    const shortName = n => ABBR.reduce((t, [re, to]) => t.replace(re, to), n).trim();

    let map, layer, labelLayer;
    let features = [];          // { feature, leafletLayer, cat, bbox, unit, tip }
    const hiddenCats = new Set();
    const hiddenUnits = new Set();
    let visible = true, choropleth = true;
    let period = "all";         // "all" = genel ortalama, "YYYY-MM" = o ayın ortalaması
    let months = [];            // binalara düşen ölçümlerin ayları (MIN_PTS'i geçen)
    let lastPoints = [];
    let ready = false;

    // ── dönem (ay) yardımcıları — Türkiye saatine göre ───────────────
    const ymFmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit" });
    function monthOf(p) {
        if (!p.recorded_at) return null;
        const d = new Date(p.recorded_at);
        return isNaN(d) ? null : ymFmt.format(d).slice(0, 7);
    }
    function monthLabel(ym, short) {
        const [y, m] = ym.split("-").map(Number);
        return new Date(Date.UTC(y, m - 1, 15)).toLocaleDateString("tr-TR",
            short ? { month: "short", timeZone: "UTC" } : { month: "long", year: "numeric", timeZone: "UTC" });
    }
    function periodLabel() { return period === "all" ? "Genel" : monthLabel(period); }
    function statsOf(vals, byPerson) {
        const v = [...vals].sort((x, y) => x - y);
        const avg = v.reduce((a, c) => a + c, 0) / v.length;
        return { n: v.length, avg, med: v[Math.floor(v.length / 2)], max: v[v.length - 1], byPerson };
    }
    // Seçili döneme göre gösterilecek istatistik
    function disp(e) {
        if (period === "all") return e.stats;
        return (e.monthly || []).find(m => m.ym === period) || null;
    }

    // ── geometri yardımcıları ────────────────────────────────────────
    function ringsOf(geom) {
        if (geom.type === "Polygon") return [geom.coordinates];
        if (geom.type === "MultiPolygon") return geom.coordinates;
        return [];
    }
    function bboxOf(geom) {
        let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
        for (const poly of ringsOf(geom)) for (const [x, y] of poly[0]) {
            if (x < a) a = x; if (y < b) b = y; if (x > c) c = x; if (y > d) d = y;
        }
        return [a, b, c, d];
    }
    function inRing(x, y, ring) {
        let inside = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            const [xi, yi] = ring[i], [xj, yj] = ring[j];
            if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
        }
        return inside;
    }
    // Yaklaşık alan (m²) — etiket önceliği için
    function areaM2(geom) {
        const k = 111320 * 111320 * Math.cos(40.8 * Math.PI / 180);
        let a = 0;
        for (const poly of ringsOf(geom)) {
            const r = poly[0];
            let s = 0;
            for (let i = 0; i < r.length - 1; i++) s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
            a += Math.abs(s) / 2;
        }
        return a * k;
    }
    function contains(f, lon, lat) {
        const [a, b, c, d] = f.bbox;
        if (lon < a || lon > c || lat < b || lat > d) return false;
        for (const poly of ringsOf(f.feature.geometry)) {
            if (inRing(lon, lat, poly[0]) && !poly.slice(1).some(h => inRing(lon, lat, h))) return true;
        }
        return false;
    }

    // ── kurulum ──────────────────────────────────────────────────────
    async function init(leafletMap) {
        map = leafletMap;
        // Ölçüm noktalarıyla AYNI canvas'a çizilir: ayrı bir SVG/canvas katmanı tüm haritayı
        // kaplayan nokta canvas'ının altında kalıp fare olaylarını hiç alamıyordu.
        // Sıra çizim sırasıyla korunur (aşağıda bringToBack ile kampüs en alta iner).
        const renderer = map.getRenderer(L.polygon([]));

        const res = await fetch("data/campus.geojson");
        const fc = await res.json();
        // Bölge sınırlarından yalnızca dış hatlar (Kuzey/Güney); çeyrekler bunların içinde kalıyor
        fc.features = fc.features.filter(f => f.properties.cat !== "sinir" ||
            ["NORTH", "SOUTH"].includes(f.properties.region));

        layer = L.geoJSON(fc, {
            renderer,
            style: f => STYLE[f.properties.cat] || STYLE.yol,
            onEachFeature: (f, l) => {
                const entry = { feature: f, leafletLayer: l, cat: f.properties.cat, bbox: bboxOf(f.geometry),
                                unit: f.properties.unit || "diger" };
                l.options.interactive = entry.cat === "bina";     // yol/yeşil fareyi binadan çalmasın
                features.push(entry);
                if (f.properties.cat === "bina") wireBuilding(entry);
                if (f.properties.cat === "sinir") {
                    l.bindTooltip(REGION_LABEL[f.properties.region] || "", {
                        permanent: true, direction: "center", className: "region-label",
                    });
                }
            },
        }).addTo(map);
        sendToBack();

        // Kalıcı bina/birim adları: birim simgesi + ad (+ ölçüm varsa ort. PM₂.₅)
        labelLayer = L.layerGroup();
        for (const e of features) {
            if (e.cat !== "bina" || !e.feature.properties.name) continue;
            const ll = e.leafletLayer.getBounds();
            e.area = (ll.getEast() - ll.getWest()) * (ll.getNorth() - ll.getSouth());
            e.areaM2 = areaM2(e.feature.geometry);
            e.full = tidyName(e.feature.properties.name);
            e.short = shortName(e.full);
            e.tier = labelTier(e);
            e.tip = L.tooltip({ permanent: true, direction: "center", pane: "tooltipPane",
                                className: `bld-label t${Math.floor(e.tier)}` })
                .setLatLng(ll.getCenter()).setContent(labelHtml(e)).addTo(labelLayer);
        }
        map.on("zoomend", syncLabels);
        map.on("moveend", cullLabels);
        syncLabels();

        ready = true;
        renderLegend();
        colorByPoints(lastPoints);
    }

    // Kampüsü canvas'ta en alta indir (önceden çizilmiş ölçüm noktaları üstte kalsın);
    // kendi içinde alttan üste: yol, otopark, yeşil, orman, sınır, bina
    const DRAW_ORDER = ["yol", "otopark", "yesil", "orman", "sinir", "bina"];
    function sendToBack() {
        [...features].sort((a, b) => DRAW_ORDER.indexOf(b.cat) - DRAW_ORDER.indexOf(a.cat))
            .forEach(e => e.leafletLayer.bringToBack());
    }

    function labelHtml(e) {
        const s = choropleth ? disp(e) : null;
        const near = map.getZoom() >= FULL_NAME_ZOOM;      // yakında tam ad ve ölçüm sayısı
        const pm = s ? `<b class="bl-pm" style="background:${pm25Color(s.avg)}">${s.avg.toFixed(1)}</b>`
                     + (near ? `<span class="bl-n">n=${s.n.toLocaleString("tr-TR")}</span>` : "") : "";
        const name = near ? e.full : e.short;
        // değer simgenin hemen yanında: ad alt satıra kaysa da değerden kopmaz
        return `<span class="bl-ico">${UNIT[e.unit].icon}</span>${pm}<span class="bl-name">${name}</span>`;
    }

    let fullNames = null;
    function syncLabels() {
        const z = map.getZoom();
        const want = visible && !hiddenCats.has("bina") && z >= LABEL_ZOOM;
        if (want && !map.hasLayer(labelLayer)) labelLayer.addTo(map);
        if (!want && map.hasLayer(labelLayer)) map.removeLayer(labelLayer);
        map.getContainer().classList.toggle("hide-regions", z > REGION_MAX_ZOOM);
        if (fullNames !== (z >= FULL_NAME_ZOOM)) {          // kısa ↔ tam ad geçişi
            fullNames = z >= FULL_NAME_ZOOM;
            for (const e of features) if (e.tip) e.tip.setContent(labelHtml(e));
        }
        cullLabels();
    }

    // Etiketin göründüğü en düşük yakınlık; ölçüm verisi olan binalar bir kademe erken görünür
    function minZoomOf(e) {
        const z = TIER_ZOOM[e.tier];
        return choropleth && disp(e) ? Math.min(z, 16) : z;
    }

    // Çakışan etiketleri gizle: önce ölçümlü binalar, sonra adı tanımlayıcı olanlar, sonra büyük olanlar
    function cullLabels() {
        if (!labelLayer || !map.hasLayer(labelLayer)) return;
        const z = map.getZoom();
        const rank = e => (disp(e) ? 0 : 10) + e.tier;
        const order = features.filter(e => e.tip).sort((a, b) => rank(a) - rank(b) || b.areaM2 - a.areaM2);
        // Arayüzün (üst çubuk, paneller, lejant) altında kalan yere etiket koyma
        const ui = (z <= REGION_MAX_ZOOM ? ".region-label, " : "") + ".leaflet-tooltip.pa-label, " + (window.innerWidth > 760
            ? ".topbar > *, #sidebar:not(.hidden) .panel, #sessions-dock .panel, .legend, .chart-handle, .player-dock.visible, .news-dock .panel"
            : ".topbar > *, .chart-handle, .player-dock.visible, .install-banner");
        const placed = [...document.querySelectorAll(ui)].map(el => el.getBoundingClientRect()).filter(r => r.width && r.height);
        const placedG = new Set();
        const view = map.getContainer().getBoundingClientRect();
        for (const e of order) {
            const el = e.tip.getElement();
            if (!el) continue;
            el.style.display = "";
            // birimi gizli ya da aynı binanın başka bloğu zaten etiketli
            if (z < minZoomOf(e) || hiddenUnits.has(e.unit) || (e.gk && placedG.has(e.gk))) { el.style.display = "none"; continue; }
            const r = el.getBoundingClientRect();
            // ekrana tam sığmayan (kenarda kesilen) etiketi gösterme
            if (r.left < view.left + 2 || r.right > view.right - 2 || r.top < view.top || r.bottom > view.bottom) {
                el.style.display = "none"; continue;
            }
            // etiketler arasında nefes payı bırak (Google Haritalar'daki gibi seyrek)
            const hit = placed.some(p => r.left < p.right + 8 && r.right > p.left - 8 && r.top < p.bottom + 4 && r.bottom > p.top - 4);
            if (hit) el.style.display = "none"; else { placed.push(r); if (e.gk) placedG.add(e.gk); }
        }
    }

    // ── bina etkileşimi ──────────────────────────────────────────────
    function wireBuilding(e) {
        const l = e.leafletLayer, name = e.feature.properties.name || "İsimsiz bina";
        l.bindTooltip(() => tooltipHtml(e, name), { sticky: true, className: "pa-label", direction: "top", offset: [0, -6] });
        l.on("mouseover", () => l.setStyle({ weight: 2.6, opacity: 1 }));
        l.on("mouseout",  () => applyStyle(e));
        l.on("click", ev => {
            L.popup(POPUP_OPTS).setLatLng(ev.latlng).setContent(popupHtml(e, name)).openOn(map);
        });
    }

    function unitLine(e) {
        const u = UNIT[e.unit], p = e.feature.properties;
        return `${u.label}${p.unit_guess ? " (adından)" : ""} · ${REGION_LABEL[p.region] || ""}`;
    }

    function tooltipHtml(e, name) {
        const s = disp(e);
        const head = `<b>${UNIT[e.unit].icon} ${name}</b><br><small>${unitLine(e)}</small>`;
        if (!s) return head;
        return `${head}<br>${periodLabel()} ort. PM₂.₅: <b style="color:${pm25Color(s.avg)}">${s.avg.toFixed(1)}</b> µg/m³ · ${s.n.toLocaleString("tr-TR")} ölçümün ortalaması`;
    }

    // Aylık kırılım: her ayın ortalaması, genelden farkı, en sorunlu ay
    function monthsHtml(e) {
        const ms = e.monthly || [];
        if (!ms.length || !e.stats) return "";
        const top = Math.max(...ms.map(m => m.avg));
        const worst = ms.length > 1 ? ms.reduce((a, b) => b.avg > a.avg ? b : a) : null;
        const sgn = d => { const r = Math.round(d * 10) / 10; return (r > 0 ? "+" : r < 0 ? "−" : "±") + Math.abs(r).toFixed(1); };
        const rows = ms.map(m => {
            const d = m.avg - e.stats.avg;
            return `<div class="bpm-row${m === worst ? " worst" : ""}${m.ym === period ? " sel" : ""}">
                <span class="bpm-m">${monthLabel(m.ym)}</span>
                <span class="bpm-bar"><i style="width:${(m.avg / top * 100).toFixed(0)}%;background:${pm25Color(m.avg)}"></i></span>
                <b style="color:${pm25Color(m.avg)}">${m.avg.toFixed(1)}</b>
                <em>${ms.length > 1 ? sgn(d) : ""}</em>
                <small class="${m.n < FEW ? "few" : ""}">${m.n.toLocaleString("tr-TR")}</small></div>`;
        }).join("");
        const foot = worst
            ? `<div class="bpm-foot">⚠️ En sorunlu ay: <b>${monthLabel(worst.ym)}</b> — genel ortalamanın ${(worst.avg - e.stats.avg).toFixed(1)} µg/m³ üstünde`
              + (worst.n < FEW ? `<div class="bpm-warn">Yalnızca ${worst.n} ölçüme dayanıyor; dikkatli yorumlayın.</div>` : "") + `</div>`
            : `<div class="bpm-foot">Ölçümler tek ayda (${monthLabel(ms[0].ym)})</div>`;
        return `<div class="bp-months"><div class="bpm-head"><span>Aylık ortalama</span><span>µg/m³ · genelden fark · ölçüm</span></div>${rows}${foot}</div>`;
    }

    function roomsHtml(e) {
        const rooms = e.feature.properties.rooms;
        if (!rooms || !rooms.length) return "";
        const byFloor = {};
        rooms.forEach(r => (byFloor[r.kat] ||= []).push(r.oda));
        const lvl = k => k === "Zemin" ? 0 : parseInt(k, 10) || 0;
        return `<div class="bp-rooms">${Object.entries(byFloor).sort((a, b) => lvl(a[0]) - lvl(b[0])).map(([k, list]) =>
            `<div><span>${k === "Zemin" ? "Zemin" : k + ". kat"}</span>${list.join(" · ")}</div>`).join("")}</div>`;
    }

    function popupHtml(e, name) {
        const region = unitLine(e);
        const s = e.stats;
        let body;
        if (!s) {
            body = `<div class="bp-empty">${lastPoints.length
                ? `Seçili ölçümlerden bu binaya düşen ${e.rawN ? e.rawN + " (yetersiz)" : "yok"}.`
                : "Bina bazlı PM₂.₅ için sağ panelden saha ölçümü seçin."}</div>`;
        } else {
            const who = Object.entries(s.byPerson).sort((a, b) => b[1].n - a[1].n)
                .map(([p, v]) => `<span class="bp-chip">${p} · ${v.n} · ${(v.sum / v.n).toFixed(1)}</span>`).join("");
            body = `
              <div class="bp-grid">
                <div><span>Ortalama</span><b style="color:${pm25Color(s.avg)}">${s.avg.toFixed(1)}</b></div>
                <div><span>Medyan</span><b style="color:${pm25Color(s.med)}">${s.med.toFixed(1)}</b></div>
                <div><span>Maks.</span><b style="color:${pm25Color(s.max)}">${s.max.toFixed(1)}</b></div>
              </div>
              <div class="bp-cat" style="color:${pm25Color(s.avg)}">Genel · ${pm25Label(s.avg)} · ${s.n.toLocaleString("tr-TR")} ölçümün ortalaması (µg/m³)</div>
              <div class="bp-who">${who}</div>${monthsHtml(e)}`;
        }
        return `<div class="bld-pop"><div class="bp-title">${UNIT[e.unit].icon} ${name}</div><div class="bp-sub">${region}</div>${roomsHtml(e)}${body}</div>`;
    }

    // ── stil / koroplet ──────────────────────────────────────────────
    function applyStyle(e) {
        const l = e.leafletLayer;
        const hidden = hiddenCats.has(e.cat);
        l.options.interactive = e.cat === "bina" && !hidden;   // gizli katman fareyi yakalamasın
        if (hidden) { l.setStyle({ opacity: 0, fillOpacity: 0 }); return; }
        const base = STYLE[e.cat] || STYLE.yol;
        const s = e.cat === "bina" && choropleth ? disp(e) : null;
        if (s) {
            const c = pm25Color(s.avg);
            l.setStyle({ ...base, color: "#ffffff", weight: 1.4, opacity: 0.85, fillColor: c, fillOpacity: 0.62, dashArray: null });
        } else {
            l.setStyle({ ...base, dashArray: base.dashArray || null });
        }
    }

    // Seçili ölçüm noktalarını binalara düşür, bina başına istatistik çıkar
    function colorByPoints(points) {
        lastPoints = points || [];
        if (!ready) return;
        // Aynı adlı bloklar (ör. KYK Yurdu'nun 3 poligonu) tek bina olarak hesaplanır
        const buildings = features.filter(f => f.cat === "bina");
        const groups = new Map();
        buildings.forEach((b, i) => {
            const p = b.feature.properties;
            b.gk = p.name ? `${p.region}|${p.name}` : `#${i}`;
            if (!groups.has(b.gk)) groups.set(b.gk, { vals: [], by: {}, m: {}, members: [] });
            groups.get(b.gk).members.push(b);
        });
        for (const p of lastPoints) {
            if (p.pm2_5 == null || !p.lat || !p.lon) continue;
            const b = buildings.find(f => contains(f, p.lon, p.lat));
            if (!b) continue;
            const g = groups.get(b.gk);
            g.vals.push(p.pm2_5);
            const who = p._person || "—";
            (g.by[who] ||= { n: 0, sum: 0 }); g.by[who].n++; g.by[who].sum += p.pm2_5;
            const ym = monthOf(p);
            if (ym) (g.m[ym] ||= []).push(p.pm2_5);
        }
        const mset = new Set();
        for (const g of groups.values()) {
            let stats = null, monthly = [];
            if (g.vals.length >= MIN_PTS) {
                stats = statsOf(g.vals, g.by);
                monthly = Object.entries(g.m).filter(([, v]) => v.length >= MIN_PTS)
                    .map(([ym, v]) => ({ ym, ...statsOf(v) })).sort((x, y) => x.ym.localeCompare(y.ym));
                monthly.forEach(m => mset.add(m.ym));
            }
            for (const b of g.members) { b.stats = stats; b.monthly = monthly; b.rawN = g.vals.length; }
        }
        months = [...mset].sort();
        if (period !== "all" && !months.includes(period)) period = "all";
        refresh();
    }

    // Etiket, boya, dönem çipleri, sıralama ve notu güncel duruma getir
    function refresh() {
        for (const b of features) if (b.tip) b.tip.setContent(labelHtml(b));
        features.forEach(applyStyle);
        cullLabels();
        renderPeriods();
        renderRanking();
        const shown = new Set(features.filter(e => e.cat === "bina" && disp(e)).map(e => e.gk)).size;
        const note = document.getElementById("campus-note");
        if (note) note.textContent = !lastPoints.length
            ? "Sağ panelden ölçüm seçince binalar ortalama PM₂.₅ ile boyanır"
            : !choropleth ? "Bina ortalamaları için sağ panelde 🏢 görünümünü seçin"
            : shown ? `${periodLabel()}: ${shown} bina boyandı (≥${MIN_PTS} ölçüm)` : "Bu dönemde bina içine düşen ölçüm yok";
    }

    // Dönem seçimi: Genel + ölçüm olan aylar
    function renderPeriods() {
        const wrap = document.getElementById("period-chips");
        if (!wrap) return;
        if (!months.length) { wrap.innerHTML = ""; return; }
        const chip = (p, txt) => `<button class="pd-chip${p === period ? " on" : ""}" data-p="${p}">${txt}</button>`;
        wrap.innerHTML = chip("all", "Genel") + months.map(m => chip(m, monthLabel(m))).join("");
        wrap.querySelectorAll(".pd-chip").forEach(b => b.addEventListener("click", () => setPeriod(b.dataset.p)));
    }

    // Seçili döneme göre bina sıralaması (yüksekten düşüğe); tıklayınca binaya git
    function renderRanking() {
        const wrap = document.getElementById("bld-rank");
        if (!wrap) return;
        const seen = new Set();
        const list = features.filter(e => e.cat === "bina" && disp(e) && !seen.has(e.gk) && seen.add(e.gk))
            .sort((a, b) => disp(b).avg - disp(a).avg);
        if (!list.length) {
            wrap.innerHTML = `<div class="rk-empty">${lastPoints.length ? "Bu dönemde bina içine düşen ölçüm yok" : "Ölçüm seçilmedi"}</div>`;
            return;
        }
        wrap.innerHTML = list.map((e, i) => {
            const s = disp(e), name = e.feature.properties.name || "İsimsiz bina";
            const ms = e.monthly || [];
            const worst = period === "all" && ms.length > 1 ? ms.reduce((a, b) => b.avg > a.avg ? b : a) : null;
            const diff = period !== "all" && e.stats ? s.avg - e.stats.avg : null;
            const sub = worst ? `en kötü ay: ${monthLabel(worst.ym, true)} ${worst.avg.toFixed(1)}${worst.n < FEW ? ` (${worst.n} ölçüm)` : ""}`
                      : diff != null ? `genelden ${diff >= 0 ? "+" : "−"}${Math.abs(diff).toFixed(1)}` : "";
            return `<button class="rk-row" data-i="${features.indexOf(e)}">
                <span class="rk-no">${i + 1}</span>
                <span class="rk-name">${UNIT[e.unit].icon} ${name}<small>${s.n.toLocaleString("tr-TR")} ölçümün ortalaması${sub ? " · " + sub : ""}</small></span>
                <b class="rk-val" style="background:${pm25Color(s.avg)}">${s.avg.toFixed(1)}</b></button>`;
        }).join("");
        wrap.querySelectorAll(".rk-row").forEach(btn => btn.addEventListener("click", () => {
            const e = features[+btn.dataset.i], l = e.leafletLayer;
            map.fitBounds(l.getBounds(), { maxZoom: 18, padding: [60, 60] });
            L.popup(POPUP_OPTS).setLatLng(l.getBounds().getCenter())
                .setContent(popupHtml(e, e.feature.properties.name || "İsimsiz bina")).openOn(map);
        }));
    }

    function setPeriod(p) {
        period = p;
        if (ready) refresh();
        document.dispatchEvent(new CustomEvent("campus:period", { detail: p }));
    }

    // ── katman paneli ────────────────────────────────────────────────
    function renderLegend() {
        const wrap = document.getElementById("campus-cats");
        if (!wrap) return;
        const counts = {};
        features.forEach(f => counts[f.cat] = (counts[f.cat] || 0) + 1);
        const order = ["bina", "yesil", "orman", "yol", "otopark", "sinir"].filter(c => counts[c]);
        wrap.innerHTML = order.map(c => {
            const s = STYLE[c];
            const sw = c === "sinir"
                ? `border:1.5px dashed #fff;background:transparent`
                : `background:${s.fillColor}${c === "yol" || c === "otopark" ? "66" : "aa"};border:1.5px ${s.dashArray ? "dashed" : "solid"} ${s.color === "#ffffff" ? "#fff" : s.fillColor}`;
            return `<button class="cat-chip${hiddenCats.has(c) ? " off" : ""}" data-cat="${c}" title="Göster/gizle">
                      <span class="cat-sw" style="${sw}"></span>${CAT_LABEL[c]}<em>${counts[c]}</em></button>`;
        }).join("");
        wrap.querySelectorAll(".cat-chip").forEach(btn => btn.addEventListener("click", () => {
            const c = btn.dataset.cat;
            hiddenCats.has(c) ? hiddenCats.delete(c) : hiddenCats.add(c);
            btn.classList.toggle("off");
            features.forEach(applyStyle);
            syncLabels();
        }));

        // Birim türü çipleri: hangi birimlerin adı haritada yazsın
        const uw = document.getElementById("campus-units");
        if (!uw) return;
        const uc = {};
        features.forEach(f => { if (f.tip) uc[f.unit] = (uc[f.unit] || 0) + 1; });
        uw.innerHTML = Object.keys(UNIT).filter(u => uc[u]).map(u =>
            `<button class="cat-chip${hiddenUnits.has(u) ? " off" : ""}" data-unit="${u}" title="Adları göster/gizle">
               <span class="unit-ico">${UNIT[u].icon}</span>${UNIT[u].label}<em>${uc[u]}</em></button>`).join("");
        uw.querySelectorAll(".cat-chip").forEach(btn => btn.addEventListener("click", () => {
            const u = btn.dataset.unit;
            hiddenUnits.has(u) ? hiddenUnits.delete(u) : hiddenUnits.add(u);
            btn.classList.toggle("off");
            cullLabels();
        }));
    }

    function setVisible(v) {
        visible = v;
        if (!ready) return;
        if (v && !map.hasLayer(layer)) { layer.addTo(map); sendToBack(); features.forEach(applyStyle); }
        if (!v && map.hasLayer(layer)) map.removeLayer(layer);
        syncLabels();
    }
    function setChoropleth(v) { choropleth = v; if (ready) refresh(); }
    function getPeriod() { return period; }

    return { init, colorByPoints, setVisible, setChoropleth, setPeriod, getPeriod, monthOf };
})();
