// Uygulama kabuğu — telefon sekmeleri, duyurular, telefona kurulum (PWA)
// app.js'ten sonra yüklenir (global `map`'i kullanır).

const Shell = (() => {
    const MOBILE = window.matchMedia("(max-width: 760px)");
    const SEEN_KEY = "gtu.news.seen";
    const BANNER_KEY = "gtu.install.dismissed";
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
    function showTab(tab) {
        document.body.dataset.tab = tab;
        document.querySelectorAll("#tabbar [data-tab]").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
        if (tab === "news") markSeen();
    }

    function initTabs() {
        document.querySelectorAll("#tabbar [data-tab]").forEach(b =>
            b.addEventListener("click", () => showTab(b.dataset.tab)));

        // Panelden haritada bir yere gidildiğinde (cihaz satırı, bina sıralaması, ▶ oynat) haritaya geç.
        // Panel açıkken harita kapalı olduğundan bu hareketler hep panelden tetiklenir.
        if (typeof map !== "undefined" && map) {
            map.on("movestart", () => {
                if (MOBILE.matches && document.body.dataset.tab !== "map") showTab("map");
            });
        }
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

    function renderNews() {
        const list = $("news-list");
        if (!news.length) { list.innerHTML = `<div class="news-empty">Henüz duyuru yok.</div>`; return; }
        const seen = seenIds();
        list.innerHTML = news.map(n => `
            <article class="news-item">
              <div class="news-meta">
                ${n.etiket ? `<span class="news-tag">${esc(n.etiket)}</span>` : ""}
                <time>${fmtDate(n.tarih)}</time>
                ${seen.has(n.id) ? "" : `<span class="news-new">YENİ</span>`}
              </div>
              <h3>${esc(n.baslik)}</h3>
              ${n.metin ? `<p>${esc(n.metin).replace(/\n/g, "<br>")}</p>` : ""}
              ${n.link ? `<p><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.link_metni || "Bağlantıyı aç")} →</a></p>` : ""}
            </article>`).join("");
    }

    async function loadNews() {
        try {
            const res = await fetch(NEWS_URL, { cache: "no-cache" });
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            news = (Array.isArray(data) ? data : [])
                .filter(n => n && n.id && n.baslik)
                .sort((a, b) => String(b.tarih).localeCompare(String(a.tarih)));
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
        $("news-btn").addEventListener("click", () => {
            document.body.classList.toggle("news-open");
            if (newsVisible()) { renderNews(); markSeen(); }
        });
        $("news-close").addEventListener("click", () => {
            if (MOBILE.matches) showTab("map");
            document.body.classList.remove("news-open");
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
        initNews();
        initInstall();
    });

    return { showTab };
})();
