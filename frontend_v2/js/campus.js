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
    const MIN_PTS = 3;          // bina ortalaması için gereken en az ölçüm
    const LABEL_ZOOM = 18;      // bina adları bu yakınlıktan itibaren kalıcı görünür

    let map, layer, labelLayer;
    let features = [];          // { feature, leafletLayer, cat, bbox }
    const hiddenCats = new Set();
    let visible = true, choropleth = true;
    let lastPoints = [];
    let ready = false;

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
        map.createPane("campus");
        map.getPane("campus").style.zIndex = 350;       // ölçüm noktalarının altında
        const renderer = L.svg({ pane: "campus" });

        const res = await fetch("data/campus.geojson");
        const fc = await res.json();
        // Bölge sınırlarından yalnızca dış hatlar (Kuzey/Güney); çeyrekler bunların içinde kalıyor
        fc.features = fc.features.filter(f => f.properties.cat !== "sinir" ||
            ["NORTH", "SOUTH"].includes(f.properties.region));

        layer = L.geoJSON(fc, {
            pane: "campus", renderer,
            style: f => STYLE[f.properties.cat] || STYLE.yol,
            onEachFeature: (f, l) => {
                const entry = { feature: f, leafletLayer: l, cat: f.properties.cat, bbox: bboxOf(f.geometry) };
                features.push(entry);
                if (f.properties.cat === "bina") wireBuilding(entry);
                if (f.properties.cat === "sinir") {
                    l.bindTooltip(REGION_LABEL[f.properties.region] || "", {
                        permanent: true, direction: "center", className: "region-label",
                    });
                }
            },
        }).addTo(map);

        // Kalıcı bina adları (yakın zoomda)
        labelLayer = L.layerGroup();
        for (const e of features) {
            if (e.cat !== "bina" || !e.feature.properties.name) continue;
            const c = e.leafletLayer.getBounds().getCenter();
            L.tooltip({ permanent: true, direction: "center", className: "bld-label", pane: "tooltipPane" })
                .setLatLng(c).setContent(e.feature.properties.name).addTo(labelLayer);
        }
        map.on("zoomend", syncLabels);
        syncLabels();

        ready = true;
        renderLegend();
        colorByPoints(lastPoints);
    }

    function syncLabels() {
        const want = visible && !hiddenCats.has("bina") && map.getZoom() >= LABEL_ZOOM;
        if (want && !map.hasLayer(labelLayer)) labelLayer.addTo(map);
        if (!want && map.hasLayer(labelLayer)) map.removeLayer(labelLayer);
    }

    // ── bina etkileşimi ──────────────────────────────────────────────
    function wireBuilding(e) {
        const l = e.leafletLayer, name = e.feature.properties.name || "İsimsiz bina";
        l.bindTooltip(() => tooltipHtml(e, name), { sticky: true, className: "pa-label", direction: "top", offset: [0, -6] });
        l.on("mouseover", () => { l.setStyle({ weight: 2.6, opacity: 1 }); l.bringToFront(); });
        l.on("mouseout",  () => applyStyle(e));
        l.on("click", ev => {
            L.popup({ maxWidth: 300 }).setLatLng(ev.latlng).setContent(popupHtml(e, name)).openOn(map);
        });
    }

    function tooltipHtml(e, name) {
        const s = e.stats;
        const region = REGION_LABEL[e.feature.properties.region] || "";
        if (!s) return `<b>🏢 ${name}</b><br><small>${region}</small>`;
        return `<b>🏢 ${name}</b><br>Ort. PM₂.₅: <b style="color:${pm25Color(s.avg)}">${s.avg.toFixed(1)}</b> µg/m³ · ${s.n} ölçüm`;
    }

    function popupHtml(e, name) {
        const region = REGION_LABEL[e.feature.properties.region] || "";
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
              <div class="bp-cat" style="color:${pm25Color(s.avg)}">${pm25Label(s.avg)} · ${s.n} ölçüm (µg/m³)</div>
              <div class="bp-who">${who}</div>`;
        }
        return `<div class="bld-pop"><div class="bp-title">🏢 ${name}</div><div class="bp-sub">${region}</div>${body}</div>`;
    }

    // ── stil / koroplet ──────────────────────────────────────────────
    function applyStyle(e) {
        const l = e.leafletLayer;
        const hidden = hiddenCats.has(e.cat);
        if (l._path) l._path.style.pointerEvents = hidden ? "none" : "";   // gizli katman fareyi yakalamasın
        if (hidden) { l.setStyle({ opacity: 0, fillOpacity: 0 }); return; }
        const base = STYLE[e.cat] || STYLE.yol;
        if (e.cat === "bina" && choropleth && e.stats) {
            const c = pm25Color(e.stats.avg);
            l.setStyle({ ...base, color: "#ffffff", weight: 1.4, opacity: 0.85, fillColor: c, fillOpacity: 0.62, dashArray: null });
        } else {
            l.setStyle({ ...base, dashArray: base.dashArray || null });
        }
    }

    // Seçili ölçüm noktalarını binalara düşür, bina başına istatistik çıkar
    function colorByPoints(points) {
        lastPoints = points || [];
        if (!ready) return;
        const buildings = features.filter(f => f.cat === "bina");
        for (const b of buildings) { b.stats = null; b.rawN = 0; b._vals = []; b._by = {}; }
        for (const p of lastPoints) {
            if (p.pm2_5 == null || !p.lat || !p.lon) continue;
            const b = buildings.find(f => contains(f, p.lon, p.lat));
            if (!b) continue;
            b._vals.push(p.pm2_5);
            const who = p._person || "—";
            (b._by[who] ||= { n: 0, sum: 0 }); b._by[who].n++; b._by[who].sum += p.pm2_5;
        }
        let colored = 0;
        for (const b of buildings) {
            b.rawN = b._vals.length;
            if (b._vals.length >= MIN_PTS) {
                const v = [...b._vals].sort((x, y) => x - y);
                const avg = v.reduce((a, c) => a + c, 0) / v.length;
                b.stats = { n: v.length, avg, med: v[Math.floor(v.length / 2)], max: v[v.length - 1], byPerson: b._by };
                colored++;
            }
            delete b._vals; delete b._by;
        }
        features.forEach(applyStyle);
        const note = document.getElementById("campus-note");
        if (note) note.textContent = !lastPoints.length
            ? "Ölçüm seçince binalar ortalama PM₂.₅ ile boyanır"
            : colored ? `${colored} bina ölçüme göre boyandı (≥${MIN_PTS} ölçüm)` : "Seçili ölçümler bina içine düşmüyor";
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
    }

    function setVisible(v) {
        visible = v;
        if (!ready) return;
        if (v && !map.hasLayer(layer)) { layer.addTo(map); features.forEach(applyStyle); }
        if (!v && map.hasLayer(layer)) map.removeLayer(layer);
        syncLabels();
    }
    function setChoropleth(v) { choropleth = v; if (ready) features.forEach(applyStyle); }

    return { init, colorByPoints, setVisible, setChoropleth };
})();
