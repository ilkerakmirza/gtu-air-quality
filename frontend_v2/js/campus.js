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
        sosyal:    { icon: "☕", label: "Sosyal tesis" },
        spor:      { icon: "⚽", label: "Spor / Açık alan" },
        ozel:      { icon: "🏛️", label: "İdari / Hizmet" },
        giris:     { icon: "🚪", label: "Giriş" },
        diger:     { icon: "🏢", label: "Diğer" },
    };
    const MIN_PTS = 3;          // bina ortalaması için gereken en az ölçüm
    const FEW = 30;             // bunun altındaki ortalamalar "az ölçüm" diye işaretlenir
    // Kart açılınca harita, kart sol/sağ panellerin altında kalmayacak şekilde kaysın
    const POPUP_OPTS = { maxWidth: 360, autoPanPaddingTopLeft: [270, 80], autoPanPaddingBottomRight: [350, 60] };
    const POPUP_OPTS_PHONE = { maxWidth: 300, autoPanPaddingTopLeft: [10, 70], autoPanPaddingBottomRight: [10, 130] };
    const isPhone = () => window.innerWidth <= 760;
    const popupOpts = () => isPhone() ? POPUP_OPTS_PHONE : POPUP_OPTS;
    const GENERIC = /^(bina \d+|küçük binalar)$/i;   // adı tanımlayıcı olmayan binalar: en düşük öncelik

    // Kademeli etiketler (Google Haritalar gibi): her binanın adı kendi yakınlık eşiğinden itibaren görünür.
    // Uzaktan yalnızca simge yapılar, yaklaştıkça bölümler, en yakında küçük birimler ve açık alanlar.
    // Çakışan etiketler yine öncelik sırasıyla gizlenir.
    const LABEL_ZOOM = 14;      // en erken etiket eşiği (kampüsün tamamı görünürken)
    const FULL_NAME_ZOOM = 18;  // bunun altında uzun adlar kısaltılır (Müh., Fak., Lab. …)
    const REGION_MAX_ZOOM = 16; // Kuzey/Güney Kampüs yazısı yalnızca uzaktan
    const KEY = /rektörlük|^kütüphane$|kongre|ana kapı|teknopark/i;       // her zaman uzaktan
    const LANDMARK = /fakülte|yurdu|yemekhane/i;
    const MINOR = /açık alan|saha|ön bahçe|tenis|kelebek ön|lojman|kırtasiye/i;
    function labelTier(e) {
        const name = e.feature.properties.name, a = e.areaM2;
        if (GENERIC.test(name) || MINOR.test(name)) return 4;          // ≥19
        if (KEY.test(name) || a > 3000 || (LANDMARK.test(name) && a > 1000)) return 1;   // ≥14
        if (a > 1500 || LANDMARK.test(name) || /salon/i.test(name)) return 2;          // ≥16
        if (a > 800 || e.unit === "bolum") return 3;                                   // ≥17 (açılış yakınlığı)
        if (a > 400 || e.unit === "sosyal" || e.unit === "giris") return 3.5;          // ≥18
        return 4;                                                                       // ≥19
    }
    const TIER_ZOOM = { 1: 14, 2: 16, 3: 17, 3.5: 18, 4: 19 };

    // Uzak planda kısaltmalar (tam ad yakında ve kartta)
    const ABBR = [[/Mühendisliği/g, "Müh."], [/Müh\. Bölümü/g, "Müh."], [/Fakültesi/g, "Fak."], [/Laboratuvarı/g, "Lab."],
                  [/Enstitüsü/g, "Enst."], [/Daire(si)? Başkanlığı/g, "D. Bşk."], [/^(Gebze Teknik Üniversitesi|GTÜ) /, ""],
                  [/Müh\., /g, "Müh. / "]];
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
    let selectedGk = null, selPopup = null;   // vurgulanan bina (kartı açık olan)

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
    // Aynısı, 1–2 ölçümlü binalar dahil (sıralama listesinin altındaki "1–2 ölçümlü binalar" bölümü için)
    function dispAll(e) {
        if (period === "all") return e.allStats || null;
        return (e.monthlyAll || []).find(m => m.ym === period) || null;
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
            e.full = e.feature.properties.name.trim();
            e.short = shortName(e.full);
            e.tier = labelTier(e);
            e.tip = L.tooltip({ permanent: true, direction: "center", pane: "tooltipPane",
                                className: `bld-label t${Math.floor(e.tier)}` })
                .setLatLng(ll.getCenter()).setContent(labelHtml(e)).addTo(labelLayer);
        }
        map.on("zoomend", syncLabels);
        map.on("moveend", cullLabels);
        // Cihaz işaretçisi eklenince (PurpleAir, ATP, CO₂) bölge yazısı çakışması yeniden değerlendirilsin
        let addT; map.on("layeradd", () => { clearTimeout(addT); addT = setTimeout(cullLabels, 150); });
        syncLabels();

        ready = true;
        renderLegend();
        colorByPoints(lastPoints);

        addHomeControl();
        fitCampus(false);
        initSearch();
        map.on("popupclose", ev => { if (ev.popup === selPopup) clearSelection(); });
    }

    // ── kampüsün tamamı ──────────────────────────────────────────────
    function campusBounds() {
        const b = L.latLngBounds([]);
        features.filter(e => e.cat === "sinir").forEach(e => b.extend(e.leafletLayer.getBounds()));
        return b.isValid() ? b : layer.getBounds();
    }
    // Paneller haritanın kenarlarını kapladığı için kampüs kalan boş alana sığdırılır
    function fitCampus(animate = true) {
        const pad = isPhone()
            ? { paddingTopLeft: [8, 64], paddingBottomRight: [8, 120] }
            : { paddingTopLeft: [350, 70], paddingBottomRight: [350, 40] };
        map.fitBounds(campusBounds(), { ...pad, animate });
    }
    function addHomeControl() {
        const Home = L.Control.extend({
            options: { position: "bottomright" },
            onAdd() {
                const div = L.DomUtil.create("div", "leaflet-bar leaflet-control leaflet-control-zoom home-control");
                const a = L.DomUtil.create("a", "", div);
                a.href = "#"; a.title = "Kampüsün tamamı"; a.setAttribute("role", "button");
                a.setAttribute("aria-label", "Kampüsün tamamını göster");
                a.textContent = "🏫";
                L.DomEvent.disableClickPropagation(div);
                L.DomEvent.on(a, "click", ev => { L.DomEvent.preventDefault(ev); map.closePopup(); fitCampus(); });
                return div;
            },
        });
        new Home().addTo(map);
    }

    // ── seçili binayı vurgula ────────────────────────────────────────
    // view/pts: kartı seçili saha ölçümleri yerine verilen noktalarla (ör. WHO/Özet listesinin dönemi) göstermek için
    function openBuilding(e, latlng, view = e, pts = lastPoints) {
        const name = e.feature.properties.name || "İsimsiz bina";
        const popup = L.popup(popupOpts()).setLatLng(latlng || e.leafletLayer.getBounds().getCenter())
            .setContent(popupHtml(view, name, pts));
        popup.openOn(map);            // önce eski kart kapanır (ve onun vurgusu kalkar)
        selPopup = popup;
        selectedGk = e.gk;
        map.getContainer().classList.add("has-sel");
        features.forEach(applyStyle);
        cullLabels();
    }
    function clearSelection() {
        selectedGk = null; selPopup = null;
        map.getContainer().classList.remove("has-sel");
        features.forEach(applyStyle);
        cullLabels();
    }
    function focusBuilding(e, view, pts) {
        map.fitBounds(e.leafletLayer.getBounds(), { maxZoom: 18, ...(isPhone()
            ? { paddingTopLeft: [20, 120], paddingBottomRight: [20, 140] }
            : { paddingTopLeft: [380, 120], paddingBottomRight: [380, 80] }) });
        map.once("moveend", () => openBuilding(e, null, view, pts));
    }

    // ── bina arama ───────────────────────────────────────────────────
    // Türkçe karakterden bağımsız: "kutuphane" → Kütüphane, "bilgisayar muh" → Bilgisayar Müh.
    const fold = t => t.toLocaleLowerCase("tr").replace(/[çğıöşüâî]/g, c => ({ ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", â: "a", î: "i" }[c]));
    function search(q) {
        const words = fold(q).split(/[\s.,/]+/).filter(Boolean);
        if (!words.length) return [];
        const seen = new Set(), out = [];
        for (const e of features) {
            if (e.cat !== "bina" || !e.full || seen.has(e.gk)) continue;
            const hay = fold(`${e.full} ${e.short} ${UNIT[e.unit].label}`);
            if (!words.every(w => hay.includes(w))) continue;
            seen.add(e.gk);
            const starts = fold(e.full).startsWith(words[0]) ? 0 : 1;
            out.push({ e, score: starts * 10 + e.tier });
        }
        return out.sort((a, b) => a.score - b.score || a.e.full.localeCompare(b.e.full, "tr")).slice(0, 8).map(r => r.e);
    }

    function initSearch() {
        const box = document.getElementById("search"), input = document.getElementById("search-input");
        const list = document.getElementById("search-results");
        if (!box || !input) return;
        let hits = [], active = 0;

        const close = () => { list.hidden = true; box.classList.remove("open"); input.blur(); };
        const render = () => {
            hits = search(input.value);
            active = 0;
            if (!input.value.trim()) { list.hidden = true; return; }
            list.innerHTML = hits.length ? hits.map((e, i) => {
                const s = choropleth ? disp(e) : null;
                return `<button type="button" class="sr-row${i === active ? " on" : ""}" data-i="${i}">
                    <span class="sr-ico">${UNIT[e.unit].icon}</span>
                    <span class="sr-txt"><b>${e.full}</b><small>${UNIT[e.unit].label} · ${REGION_LABEL[e.feature.properties.region] || ""}</small></span>
                    ${s ? `<span class="sr-pm" style="background:${pm25Color(s.avg)}">${f1tr(s.avg)}</span>` : ""}</button>`;
            }).join("") : `<div class="sr-empty">“${input.value.replace(/[<>&]/g, "")}” için bina bulunamadı</div>`;
            list.hidden = false;
        };
        const pick = i => {
            const e = hits[i];
            if (!e) return;
            input.value = e.full;
            close();
            focusBuilding(e);
        };

        input.addEventListener("input", render);
        input.addEventListener("focus", () => { if (input.value.trim()) render(); });
        input.addEventListener("keydown", ev => {
            if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
                if (!hits.length) return;
                ev.preventDefault();
                active = (active + (ev.key === "ArrowDown" ? 1 : hits.length - 1)) % hits.length;
                list.querySelectorAll(".sr-row").forEach((r, i) => r.classList.toggle("on", i === active));
            } else if (ev.key === "Enter") { ev.preventDefault(); pick(active); }
            else if (ev.key === "Escape") { input.value = ""; close(); }
        });
        list.addEventListener("click", ev => { const r = ev.target.closest(".sr-row"); if (r) pick(+r.dataset.i); });
        document.getElementById("search-open").addEventListener("click", () => {
            if (typeof Shell !== "undefined") Shell.showTab("map");   // telefonda sonuçlar haritanın üstünde açılsın
            box.classList.add("open"); input.focus();
        });
        document.getElementById("search-close").addEventListener("click", () => { input.value = ""; close(); });
        document.addEventListener("pointerdown", ev => { if (!box.contains(ev.target)) list.hidden = true; });
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
        const pm = s ? `<b class="bl-pm" style="background:${pm25Color(s.avg)}">${f1tr(s.avg)}</b>`
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
    // Kuzey/Güney Kampüs yazısı cihaz işaretçilerinin (PurpleAir, ATP, CO₂) ve PurpleAir etiketinin üstüne binmesin
    function cullRegions() {
        const marks = [...document.querySelectorAll(".pulse-marker, .mk-wrap, .leaflet-tooltip.pa-label")]
            .map(el => el.getBoundingClientRect()).filter(r => r.width && r.height);
        document.querySelectorAll(".leaflet-tooltip.region-label").forEach(el => {
            el.style.visibility = "";
            const r = el.getBoundingClientRect();
            if (marks.some(p => r.left < p.right + 4 && r.right > p.left - 4 && r.top < p.bottom + 2 && r.bottom > p.top - 2))
                el.style.visibility = "hidden";
        });
    }

    function cullLabels() {
        cullRegions();
        if (!labelLayer || !map.hasLayer(labelLayer)) return;
        const z = map.getZoom();
        const rank = e => (selectedGk && e.gk === selectedGk ? -1 : disp(e) ? 0 : 10) + e.tier;
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
            const sel = !!selectedGk && e.gk === selectedGk;
            el.classList.toggle("sel", sel);
            // birimi gizli ya da aynı binanın başka bloğu zaten etiketli
            if ((!sel && (z < minZoomOf(e) || hiddenUnits.has(e.unit))) || (e.gk && placedG.has(e.gk))) { el.style.display = "none"; continue; }
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
        l.on("click", ev => openBuilding(e, ev.latlng));
    }

    function unitLine(e) {
        const u = UNIT[e.unit], p = e.feature.properties;
        return `${u.label}${p.unit_guess ? " (adından)" : ""} · ${REGION_LABEL[p.region] || ""}`;
    }

    function tooltipHtml(e, name) {
        const s = disp(e);
        const head = `<b>${UNIT[e.unit].icon} ${name}</b><br><small>${unitLine(e)}</small>`;
        if (!s) return head;
        return `${head}<br>${periodLabel()} ort. PM₂.₅: <b style="color:${pm25Color(s.avg)}">${f1tr(s.avg)}</b> µg/m³ · ${s.n.toLocaleString("tr-TR")} ölçümün ortalaması`;
    }

    // Aylık kırılım: her ayın ortalaması, genelden farkı, en sorunlu ay
    function monthsHtml(e) {
        const ms = e.monthly || [];
        if (!ms.length || !e.stats) return "";
        const top = Math.max(...ms.map(m => m.avg));
        const worst = ms.length > 1 ? ms.reduce((a, b) => b.avg > a.avg ? b : a) : null;
        const sgn = d => { const r = Math.round(d * 10) / 10; return (r > 0 ? "+" : r < 0 ? "−" : "±") + f1tr(Math.abs(r)); };
        const rows = ms.map(m => {
            const d = m.avg - e.stats.avg;
            return `<div class="bpm-row${m === worst ? " worst" : ""}${m.ym === period ? " sel" : ""}">
                <span class="bpm-m">${monthLabel(m.ym)}</span>
                <span class="bpm-bar"><i style="width:${(m.avg / top * 100).toFixed(0)}%;background:${pm25Color(m.avg)}"></i></span>
                <b style="color:${pm25Color(m.avg)}">${f1tr(m.avg)}</b>
                <em>${ms.length > 1 ? sgn(d) : ""}</em>
                <small class="${m.n < FEW ? "few" : ""}">${m.n.toLocaleString("tr-TR")}</small></div>`;
        }).join("");
        const foot = worst
            ? `<div class="bpm-foot">⚠️ En sorunlu ay: <b>${monthLabel(worst.ym)}</b> — genel ortalamanın ${f1tr((worst.avg - e.stats.avg))} µg/m³ üstünde`
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

    // Ölçüm süresi, seçili saha ölçümlerinin genel ortalamasına göre konum ve son ölçüm günü.
    // Saha ölçümleri kısa süreli olduğundan WHO'nun 24 saatlik değeriyle değil, kendi içinde karşılaştırılır.
    function contextHtml(e, s, pts) {
        const lines = [];
        if (e.dur) lines.push(`⏱ Binada toplam ${fmtDur(e.dur.min)} ölçüm · ${e.dur.days} farklı gün`);
        const all = pts.filter(p => p.pm2_5 != null).map(p => p.pm2_5);
        if (all.length >= 30) {
            const ref = all.reduce((a, b) => a + b, 0) / all.length, pct = (s.avg - ref) / ref * 100;
            lines.push(Math.abs(pct) < 5 ? `≈ Kampüs saha ortalamasıyla benzer (${f1tr(ref)})`
                : `${pct > 0 ? "▲" : "▼"} Kampüs saha ortalamasından (${f1tr(ref)}) %${Math.abs(pct).toFixed(0)} ${pct > 0 ? "yüksek" : "düşük"}`);
        }
        if (e.visit) {
            const v = e.visit, pct = (v.avg - v.prevAvg) / v.prevAvg * 100;
            const dl = new Date(v.day + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "long" });
            lines.push(`📅 Son ölçüm (${dl}): ${f1tr(v.avg)} — binanın önceki ${v.prevDays} gündeki ortalamasından (${f1tr(v.prevAvg)}) `
                + (Math.abs(pct) < 5 ? "farksız" : `%${Math.abs(pct).toFixed(0)} ${pct > 0 ? "yüksek" : "düşük"}`));
        }
        return lines.length ? `<div class="bp-ctx">${lines.map(l => `<div>${l}</div>`).join("")}</div>` : "";
    }

    function popupHtml(e, name, pts = lastPoints) {
        const region = unitLine(e);
        const s = e.stats;
        let body;
        if (!s) {
            const vals = e.fewVals ? e.fewVals.map(v => `${f1tr(v)}`).join(" ve ") : "";
            body = `<div class="bp-empty">${!pts.length
                ? "Bina bazlı PM₂.₅ için Araştırma › Saha ölçümleri bölümünden ölçüm günü seçin."
                : vals ? `Seçili ölçümlerden bu binaya ${e.rawN} ölçüm düşüyor: ${vals} µg/m³. Ortalama için en az ${MIN_PTS} ölçüm gerekir.`
                : "Seçili ölçümlerden bu binaya düşen ölçüm yok."}</div>`;
        } else {
            const who = Object.entries(s.byPerson || {}).filter(([p]) => p !== "—").sort((a, b) => b[1].n - a[1].n)
                .map(([p, v]) => `<span class="bp-chip">${p} · ${v.n} · ${f1tr((v.sum / v.n))}</span>`).join("");
            body = `
              <div class="bp-grid">
                <div><span>Ortalama</span><b style="color:${pm25Color(s.avg)}">${f1tr(s.avg)}</b></div>
                <div><span>Medyan</span><b style="color:${pm25Color(s.med)}">${f1tr(s.med)}</b></div>
                <div><span>Maks.</span><b style="color:${pm25Color(s.max)}">${f1tr(s.max)}</b></div>
              </div>
              <div class="bp-cat">Genel ortalama · ${s.n.toLocaleString("tr-TR")} ölçüm (µg/m³, kısa süreli saha ölçümü)</div>
              ${contextHtml(e, s, pts)}
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
        const st = s
            ? { ...base, color: "#ffffff", weight: 1.4, opacity: 0.85, fillColor: pm25Color(s.avg), fillOpacity: 0.62, dashArray: null }
            : { ...base, dashArray: base.dashArray || null };
        if (selectedGk && e.cat === "bina") {
            if (e.gk === selectedGk) Object.assign(st, { color: "#ffffff", weight: 3.2, opacity: 1, fillOpacity: Math.max(st.fillOpacity, 0.5) });
            else Object.assign(st, { opacity: st.opacity * 0.35, fillOpacity: st.fillOpacity * 0.35 });
        }
        l.setStyle(st);
    }

    // Seçili ölçüm noktalarını binalara düşür, bina başına istatistik çıkar
    // Ölçüm noktalarını binalara düşür. Aynı adlı bloklar (ör. KYK Yurdu'nun 3 poligonu) tek bina sayılır.
    function groupPoints(points) {
        const buildings = features.filter(f => f.cat === "bina");
        const groups = new Map();
        buildings.forEach((b, i) => {
            const p = b.feature.properties;
            b.gk = p.name ? `${p.region}|${p.name}` : `#${i}`;
            if (!groups.has(b.gk)) groups.set(b.gk, { vals: [], by: {}, m: {}, d: {}, ts: [], members: [] });
            groups.get(b.gk).members.push(b);
        });
        for (const p of points) {
            if (p.pm2_5 == null || !p.lat || !p.lon) continue;
            const b = buildings.find(f => contains(f, p.lon, p.lat));
            if (!b) continue;
            const g = groups.get(b.gk);
            g.vals.push(p.pm2_5);
            const who = p._person || "—";
            (g.by[who] ||= { n: 0, sum: 0 }); g.by[who].n++; g.by[who].sum += p.pm2_5;
            const ym = monthOf(p);
            if (ym) (g.m[ym] ||= []).push(p.pm2_5);
            const t = p.recorded_at ? new Date(p.recorded_at) : null;
            if (t && !isNaN(t)) { g.ts.push(+t); (g.d[dayFmt.format(t)] ||= []).push(p.pm2_5); }
        }
        return groups;
    }

    // Binada geçen ölçüm süresi: ardışık ölçümler arası ≤5 dk boşluklar toplanır (yürüyüşte binada kalınan süre)
    const dayFmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    function durationOf(g) {
        const ts = [...g.ts].sort((a, b) => a - b);
        let ms = 0;
        for (let i = 1; i < ts.length; i++) { const gap = ts[i] - ts[i - 1]; if (gap <= 5 * 60e3) ms += gap; }
        return { min: Math.round(ms / 60e3), days: Object.keys(g.d).length };
    }
    // Son ölçüm günü ile binanın o güne kadarki (önceki günler) ortalaması
    function lastVisitOf(g) {
        const days = Object.keys(g.d).sort();
        if (days.length < 2) return null;
        const last = days[days.length - 1];
        const prev = days.slice(0, -1).flatMap(k => g.d[k]);
        if (g.d[last].length < MIN_PTS || prev.length < MIN_PTS) return null;
        const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
        return { day: last, avg: avg(g.d[last]), prevAvg: avg(prev), prevDays: days.length - 1 };
    }
    const fmtDur = m => m < 1 ? "1 dk'dan kısa" : m < 60 ? `~${m} dk` : `~${Math.floor(m / 60)} sa ${m % 60} dk`;

    // Haritayı değiştirmeden bina istatistikleri (WHO sekmesi için): en az MIN_PTS ölçümü olan binalar
    function buildingStats(points) {
        if (!ready) return null;
        const out = [];
        for (const [gk, g] of groupPoints(points || [])) {
            if (g.vals.length < MIN_PTS) continue;
            const e = g.members[0], p = e.feature.properties;
            out.push({ gk, name: p.name || "İsimsiz bina", icon: UNIT[e.unit].icon, unit: UNIT[e.unit].label,
                       region: REGION_LABEL[p.region] || "", ...statsOf(g.vals, g.by), few: g.vals.length < FEW,
                       dur: durationOf(g), durText: fmtDur(durationOf(g).min) });
        }
        return out;
    }
    // pts verilirse kart o noktalardan hesaplanır (Saha sekmesinde seçim yapılmamış olsa da dolu gelir)
    function focusByKey(gk, pts) {
        const e = features.find(f => f.cat === "bina" && f.gk === gk);
        if (!e) return;
        if (!pts) { focusBuilding(e); return; }
        const g = groupPoints(pts).get(gk);
        focusBuilding(e, g ? { ...e, ...groupSummary(g) } : e, pts);
    }

    // stats/monthly: en az MIN_PTS ölçüm (harita boyası, kart, sıralama). allStats/monthlyAll: 1 ölçüm bile olsa
    // (sıralamanın altındaki "1–2 ölçümlü binalar" listesi; hiçbir ölçüm listeden düşmesin diye).
    function groupSummary(g) {
        let stats = null, monthly = [];
        const allStats = g.vals.length ? statsOf(g.vals, g.by) : null;
        const monthlyAll = Object.entries(g.m).map(([ym, v]) => ({ ym, ...statsOf(v) }))
            .sort((x, y) => x.ym.localeCompare(y.ym));
        if (g.vals.length >= MIN_PTS) {
            stats = allStats;
            monthly = monthlyAll.filter(m => m.n >= MIN_PTS);
        }
        return { stats, monthly, allStats, monthlyAll, rawN: g.vals.length,
                 fewVals: g.vals.length && g.vals.length < MIN_PTS ? [...g.vals] : null,
                 dur: stats ? durationOf(g) : null, visit: stats ? lastVisitOf(g) : null };
    }

    function colorByPoints(points) {
        lastPoints = points || [];
        if (!ready) return;
        const groups = groupPoints(lastPoints);
        const mset = new Set();
        for (const g of groups.values()) {
            const sum = groupSummary(g);
            sum.monthlyAll.forEach(m => mset.add(m.ym));
            for (const b of g.members) Object.assign(b, sum);
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
        const fewN = new Set(features.filter(e => e.cat === "bina" && !disp(e) && dispAll(e)).map(e => e.gk)).size;
        const fewTxt = fewN ? `${fewN} binada 1–2 ölçüm var (boyanmadı)` : "";
        const note = document.getElementById("campus-note");
        if (note) note.textContent = !lastPoints.length
            ? "Sağ panelden ölçüm seçince binalar ortalama PM₂.₅ ile boyanır"
            : !choropleth ? "Bina ortalamaları için Saha ölçümleri panelinde «Bina ortalamaları» görünümünü seçin"
            : shown ? `${periodLabel()}: ${shown} bina boyandı (≥${MIN_PTS} ölçüm)${fewTxt ? "; " + fewTxt : ""}`
            : fewTxt ? `${periodLabel()}: ${fewTxt}` : "Bu dönemde bina içine düşen ölçüm yok";
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

    // Seçili döneme göre bina sıralaması (yüksekten düşüğe); tıklayınca binaya git.
    // Ölçümü olan her bina listelenir: en az MIN_PTS ölçümü olanlar sıralanır, 1–2 ölçümlüler altta ayrı durur
    // (tek ölçüm ortalama sayılmaz; yakında içilen bir sigara gibi tek bir yükselme sıralamanın başına geçmesin).
    function renderRanking() {
        const wrap = document.getElementById("bld-rank");
        if (!wrap) return;
        const seen = new Set();
        const all = features.filter(e => e.cat === "bina" && dispAll(e) && !seen.has(e.gk) && seen.add(e.gk))
            .sort((a, b) => dispAll(b).avg - dispAll(a).avg);
        const ranked = all.filter(e => dispAll(e).n >= MIN_PTS), few = all.filter(e => dispAll(e).n < MIN_PTS);
        if (!all.length) {
            wrap.innerHTML = `<div class="rk-empty">${lastPoints.length ? "Bu dönemde bina içine düşen ölçüm yok" : "Aşağıdaki listeden ölçüm günü seçin; binalar ortalama PM₂.₅'e göre sıralanır."}</div>`;
            return;
        }
        const nameOf = e => e.feature.properties.name || "İsimsiz bina";
        const rows = ranked.map((e, i) => {
            const s = dispAll(e);
            const ms = e.monthly || [];
            const worst = period === "all" && ms.length > 1 ? ms.reduce((a, b) => b.avg > a.avg ? b : a) : null;
            // Genelden fark yalnızca binanın başka aylarda da ölçümü varsa anlamlıdır (yoksa hep +0,0 çıkar)
            const diff = period !== "all" && e.stats && e.stats.n > s.n ? s.avg - e.stats.avg : null;
            const sub = worst ? `en kötü ay: ${monthLabel(worst.ym, true)} ${f1tr(worst.avg)}${worst.n < FEW ? ` (${worst.n} ölçüm)` : ""}`
                      : diff != null ? `genelden ${diff >= 0 ? "+" : "−"}${f1tr(Math.abs(diff))}` : "";
            return `<button class="rk-row" data-i="${features.indexOf(e)}">
                <span class="rk-no">${i + 1}</span>
                <span class="rk-name">${UNIT[e.unit].icon} ${nameOf(e)}<small>${s.n.toLocaleString("tr-TR")} ölçümün ortalaması${sub ? " · " + sub : ""}</small></span>
                <b class="rk-val" style="background:${pm25Color(s.avg)}">${f1tr(s.avg)}</b></button>`;
        });
        if (few.length) {
            rows.push(`<div class="rk-sub">1–2 ölçümlü binalar · sıralamaya ve harita boyasına girmez</div>`);
            few.forEach(e => {
                const s = dispAll(e);
                rows.push(`<button class="rk-row few" data-i="${features.indexOf(e)}">
                    <span class="rk-no">–</span>
                    <span class="rk-name">${UNIT[e.unit].icon} ${nameOf(e)}<small>${s.n} ölçüm${s.n > 1 ? "ün ortalaması" : ""}</small></span>
                    <b class="rk-val few" style="border-color:${pm25Color(s.avg)}">${f1tr(s.avg)}</b></button>`);
            });
        }
        wrap.innerHTML = rows.join("");
        wrap.querySelectorAll(".rk-row").forEach(btn => btn.addEventListener("click", () => {
            const e = features[+btn.dataset.i], l = e.leafletLayer;
            map.fitBounds(l.getBounds(), { maxZoom: 18, padding: [60, 60] });
            openBuilding(e);
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

    return { init, colorByPoints, setVisible, setChoropleth, setPeriod, getPeriod, monthOf, fitCampus, buildingStats, focusByKey };
})();
