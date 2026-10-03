// Uygulama kabuğu — telefon sekmeleri, duyurular, telefona kurulum (PWA)
// app.js'ten sonra yüklenir (global `map`'i kullanır).

const Shell = (() => {
    const MOBILE = window.matchMedia("(max-width: 760px)");
    const SEEN_KEY = "gtu.news.seen";
    const BANNER_KEY = "gtu.install.dismissed";
    const RESEARCH_KEY = "gtu.view.research";   // masaüstü: Araştırma katmanları açık mı
    const SUB_KEY = "gtu.view.researchSub";     // telefon: Araştırma'da son açılan bölüm (live | field)
    const NEWS_URL = "data/duyurular.json";

    let news = [];
    let installEvt = null;   // Android/Chrome "uygulamayı yükle" olayı

    const $ = id => document.getElementById(id);

    function lsGet(k, fallback) {
        try { const v = localStorage.getItem(k); return v == null ? fallback : JSON.parse(v); } catch (_) { return fallback; }
    }
    function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} }

    function esc(s) {
        return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    // ── Sekmeler (yalnızca telefon düzeninde görünür) ──────────────
    // Araştırma sekmesi iki bölümden oluşur: Sensörler (live) ve Saha ölçümleri (field)
    const RESEARCH_TABS = ["live", "field"];
    function showTab(tab) {
        if (tab === "research") tab = lsGet(SUB_KEY, "live");
        if (RESEARCH_TABS.includes(tab)) lsSet(SUB_KEY, tab);
        document.body.dataset.tab = tab;
        const tabBtn = RESEARCH_TABS.includes(tab) ? "research" : tab;
        document.querySelectorAll("#tabbar [data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === tabBtn));
        document.querySelectorAll("#research-switch [data-sub]").forEach(b => {
            const on = b.dataset.sub === tab;
            b.classList.toggle("on", on); b.setAttribute("aria-selected", on);
        });
        if (tab === "news") markSeen();
        if (tab === "who" && typeof WHO !== "undefined") WHO.load();
        if (tab === "ozet" && typeof Ozet !== "undefined") Ozet.load();
        updateMapCta(false);
    }

    // Masaüstünde sağdaki paneller (Özet / WHO / Duyurular) aynı yerde açılır; biri açılınca diğerleri kapanır.
    // Telefonda aynı adlı sekmeye geçilir.
    const PANELS = ["ozet", "who", "news", "info"];
    function openPanel(name, toggle) {
        if (MOBILE.matches) { showTab(name); return; }
        const cls = name + "-open", was = document.body.classList.contains(cls);
        PANELS.forEach(n => document.body.classList.remove(n + "-open"));
        if (toggle && was) return;
        document.body.classList.add(cls);
        if (name === "who") WHO.load();
        if (name === "ozet") Ozet.load();
        if (name === "news") { renderNews(); markSeen(); }
    }
    function closePanel(name) {
        if (MOBILE.matches) showTab("map");
        document.body.classList.remove(name + "-open");
    }

    // Panelden haritaya dönüş düğmesi: Saha sekmesinde seçilen gün sayısını gösterir
    function updateMapCta(bump) {
        const n = document.querySelectorAll(".s-cb:checked").length;
        const avg = document.querySelector('.vs-btn.on[data-view="avg"]');
        $("map-cta-text").textContent = document.body.dataset.tab === "field" && n
            ? `${avg ? "Bina ortalamalarını" : "Ölçümleri"} haritada gör · ${n} gün`
            : "Haritaya dön";
        const btn = $("map-cta");
        if (bump) { btn.classList.remove("bump"); void btn.offsetWidth; btn.classList.add("bump"); }
    }

    function initTabs() {
        document.querySelectorAll("#tabbar [data-tab]").forEach(b =>
            b.addEventListener("click", () => showTab(b.dataset.tab)));
        document.querySelectorAll("#research-switch [data-sub]").forEach(b =>
            b.addEventListener("click", () => showTab(b.dataset.sub)));
        $("map-cta").addEventListener("click", () => showTab("map"));
        // seçim değişince düğme metni güncellensin ve dikkat çeksin
        document.addEventListener("change", ev => { if (ev.target.closest(".s-cb, .person-cb")) updateMapCta(true); });
        document.addEventListener("click", ev => {
            if (ev.target.closest("#sel-all, #sel-none, .vs-btn")) setTimeout(() => updateMapCta(true), 0);
        });

        // Panelden haritada bir yere gidildiğinde (cihaz satırı, bina, ▶ oynat) haritaya geç.
        // Yalnızca panelde bir şeye dokunulduktan kısa süre sonra başlayan hareketler sayılır;
        // açılıştaki "kampüsün tamamı" hareketi Özet sekmesini kapatmasın.
        let sheetTapAt = 0;
        document.addEventListener("click", ev => {
            if (ev.target.closest(".sidebar, .sessions-dock, .news-dock")) sheetTapAt = Date.now();
        }, true);
        if (typeof map !== "undefined" && map) {
            map.on("movestart", () => {
                if (MOBILE.matches && document.body.dataset.tab !== "map" && Date.now() - sheetTapAt < 8000) showTab("map");
            });
        }
    }

    // ── Basit / Araştırma görünümü (masaüstü) ─────────────────────
    // Varsayılan basit görünüm herkes içindir: harita, Özet, Sağlık, Duyurular.
    // Araştırma; sensör panellerini, saha ölçümlerini ve karşılaştırma grafiğini açar. Tercih cihazda saklanır.
    function setResearch(on) {
        document.body.classList.toggle("research", on);
        $("research-btn").setAttribute("aria-pressed", on);
        lsSet(RESEARCH_KEY, on);
    }
    function initResearch() {
        setResearch(lsGet(RESEARCH_KEY, false));
        $("research-btn").addEventListener("click", () => {
            const on = !document.body.classList.contains("research");
            setResearch(on);
            // Araştırma açılınca sağdaki okuma panelleri kapansın; saha paneli görünsün
            if (on) PANELS.forEach(n => document.body.classList.remove(n + "-open"));
        });
    }

    // ── Duyurular ──────────────────────────────────────────────────
    function seenIds() { return new Set(lsGet(SEEN_KEY, [])); }

    function markSeen() {
        if (!news.length) return;
        lsSet(SEEN_KEY, news.map(n => n.id));
        updateBadges();
    }

    function updateBadges() {
        const seen = seenIds();
        const unread = news.filter(n => !seen.has(n.id)).length;
        for (const id of ["news-badge", "tab-news-badge"]) {
            const el = $(id);
            el.hidden = unread === 0;
            el.textContent = unread > 9 ? "9+" : unread;
        }
    }

    function fmtDate(d) {
        const t = new Date(d + "T12:00:00");
        return isNaN(t) ? esc(d) : t.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
    }

    // Zengin duyurular: renkli başlık alanı + bölümler (özellik kartları, numaralı adımlar, not kutusu).
    // Alanların hepsi isteğe bağlı; sade duyurular eskisi gibi düz metin görünür. Biçim: CLAUDE.md
    const THEMES = {
        mor: ["#6c8cff", "#b07aff"], mavi: ["#3b82f6", "#22c3ee"], yesil: ["#22b46b", "#4cc9b0"],
        turuncu: ["#f59e0b", "#f4615e"], pembe: ["#ec4899", "#a855f7"],
    };
    const ACCENTS = ["#6c8cff", "#34d27b", "#f5b840", "#b07aff", "#5ec6c2", "#f4615e"];
    // **kalın** yazım ve satır sonları; geri kalan her şey kaçışlı metin
    const rich = t => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");

    function sectionHtml(b) {
        const title = b.baslik ? `<div class="nsec-title">${esc(b.baslik)}</div>` : "";
        if (b.tur === "ozellikler") {
            return title + `<div class="nf-grid">${(b.ogeler || []).map((o, i) => {
                const c = o.renk || ACCENTS[i % ACCENTS.length];
                return `<div class="nf-item" style="--c:${esc(c)}">
                    <span class="nf-ico">${esc(o.ikon || "•")}</span>
                    <span><b>${esc(o.baslik)}</b>${o.metin ? `<small>${rich(o.metin)}</small>` : ""}</span></div>`;
            }).join("")}</div>`;
        }
        if (b.tur === "adimlar") {
            const c = b.renk || ACCENTS[0];
            return `<div class="ns-card" style="--c:${esc(c)}">
                <div class="ns-head">${b.ikon ? `<span>${esc(b.ikon)}</span>` : ""}${esc(b.baslik || "")}
                    ${b.alt ? `<small>${esc(b.alt)}</small>` : ""}</div>
                <ol class="ns-steps">${(b.adimlar || []).map((a, i) =>
                    `<li><span class="ns-num">${i + 1}</span><span>${rich(a)}</span></li>`).join("")}</ol></div>`;
        }
        if (b.tur === "not") {
            return `<div class="news-note"><span>${esc(b.ikon || "💡")}</span><span>${rich(b.metin || "")}</span></div>`;
        }
        return title + (b.metin ? `<p>${rich(b.metin)}</p>` : "");
    }

    function newsHtml(n, isNew) {
        const meta = `${n.etiket ? `<span class="news-tag">${esc(n.etiket)}</span>` : ""}
            <time>${fmtDate(n.tarih)}</time>${isNew ? `<span class="news-new">YENİ</span>` : ""}`;
        const link = n.link ? `<a class="news-link" href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.link_metni || "Bağlantıyı aç")} →</a>` : "";
        if (!n.renk && !n.bolumler) {
            return `<article class="news-item">
              <div class="news-meta">${meta}</div>
              <h3>${esc(n.baslik)}</h3>
              ${n.metin ? `<p>${rich(n.metin)}</p>` : ""}${link}
            </article>`;
        }
        const [c1, c2] = THEMES[n.renk] || THEMES.mor;
        return `<article class="news-item rich" style="--c1:${c1};--c2:${c2}">
            <header class="news-hero">
              <div class="news-meta">${meta}</div>
              ${n.ikon ? `<div class="nh-ico">${esc(n.ikon)}</div>` : ""}
              <h3>${esc(n.baslik)}</h3>
              ${n.ozet ? `<p class="nh-sub">${rich(n.ozet)}</p>` : ""}
            </header>
            <div class="news-content">
              ${n.metin ? `<p class="news-lead">${rich(n.metin)}</p>` : ""}
              ${(n.bolumler || []).map(sectionHtml).join("")}
              ${link}
            </div>
          </article>`;
    }

    function renderNews() {
        const list = $("news-list");
        if (!news.length) { list.innerHTML = `<div class="news-empty">Henüz duyuru yok.</div>`; return; }
        const seen = seenIds();
        list.innerHTML = news.map(n => newsHtml(n, !seen.has(n.id))).join("");
    }

    async function loadNews() {
        try {
            const res = await fetch(NEWS_URL, { cache: "no-cache" });
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            news = (Array.isArray(data) ? data : [])
                .filter(n => n && n.id && n.baslik)
                .sort((a, b) => (b.sabit ? 1 : 0) - (a.sabit ? 1 : 0) || String(b.tarih).localeCompare(String(a.tarih)));
        } catch (e) {
            console.warn("[duyurular]", e);
            if (!news.length) $("news-list").innerHTML = `<div class="news-empty">Duyurular yüklenemedi.</div>`;
            return;
        }
        renderNews();
        updateBadges();
        if (newsVisible()) markSeen();
    }

    function newsVisible() {
        return MOBILE.matches ? document.body.dataset.tab === "news" : document.body.classList.contains("news-open");
    }

    function initNews() {
        $("ozet-btn").addEventListener("click", () => openPanel("ozet", true));
        $("ozet-close").addEventListener("click", () => closePanel("ozet"));
        $("who-btn").addEventListener("click", () => openPanel("who", true));
        $("who-close").addEventListener("click", () => closePanel("who"));
        $("news-btn").addEventListener("click", () => openPanel("news", true));
        $("info-btn").addEventListener("click", () => openPanel("info", true));
        $("info-close").addEventListener("click", () => closePanel("info"));
        // İçindekiler bağlantıları paneli kaydırsın (sayfa adresini değiştirmeden)
        document.querySelectorAll(".info-toc a").forEach(a => a.addEventListener("click", ev => {
            ev.preventDefault();
            document.querySelector(a.getAttribute("href"))?.scrollIntoView({ behavior: "smooth", block: "start" });
        }));
        $("news-close").addEventListener("click", () => {
            closePanel("news");
            renderNews();   // "YENİ" etiketlerini kaldır
        });
        loadNews();
        setInterval(loadNews, 10 * 60 * 1000);
        document.addEventListener("visibilitychange", () => { if (!document.hidden) loadNews(); });
    }

    // ── Telefona kurulum ───────────────────────────────────────────
    function isStandalone() {
        return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
    }
    function isIOS() {
        return /iPhone|iPad|iPod/.test(navigator.userAgent) ||
            (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    }

    function updateInstallUI() {
        const card = $("install-card"), text = $("install-text"), btn = $("install-btn");
        let mode = null;
        if (!isStandalone()) {
            if (installEvt) mode = "prompt";
            else if (isIOS()) mode = "ios";
        }
        card.hidden = !mode;
        btn.hidden = mode !== "prompt";
        if (mode === "prompt") {
            text.textContent = "Ana ekrana eklenir, kendi ikonuyla tam ekran açılır. Güncellemeler otomatik gelir.";
        } else if (mode === "ios") {
            text.innerHTML = "Safari'de alttaki <b>Paylaş</b> düğmesine (⬆️) dokunun, ardından <b>Ana Ekrana Ekle</b>'yi seçin.";
        }
        $("install-banner").hidden = !(mode && MOBILE.matches && !lsGet(BANNER_KEY, false));
    }

    function initInstall() {
        window.addEventListener("beforeinstallprompt", e => {
            e.preventDefault();
            installEvt = e;
            updateInstallUI();
        });
        window.addEventListener("appinstalled", () => { installEvt = null; updateInstallUI(); });

        $("install-btn").addEventListener("click", async () => {
            if (!installEvt) return;
            installEvt.prompt();
            await installEvt.userChoice.catch(() => {});
            installEvt = null;
            updateInstallUI();
        });
        $("install-banner-how").addEventListener("click", () => showTab("news"));
        $("install-banner-close").addEventListener("click", () => {
            lsSet(BANNER_KEY, true);
            $("install-banner").hidden = true;
        });
        updateInstallUI();

        if ("serviceWorker" in navigator) {
            navigator.serviceWorker.register("sw.js").catch(e => console.warn("[sw]", e));
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        initTabs();
        initResearch();
        initNews();
        initInstall();
        // Açılışta herkesin ilk gördüğü: Özet (telefonda sekme, masaüstünde sağ panel)
        openPanel("ozet");
    });

    return { showTab, openPanel };
})();
