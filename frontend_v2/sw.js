// GTÜ AirLab — service worker (telefona kurulan uygulama için)
// Uygulama dosyaları: önce ağ → her açılışta en güncel sürüm; ağ yoksa son kopya.
// Sürümlü CDN kütüphaneleri: önce önbellek.
// API ve harita karoları önbelleğe alınmaz (veri her zaman canlı).
const CACHE = "gtu-hava-v1";
const SHELL = [
    "./", "index.html", "manifest.webmanifest",
    "js/colorscale.js", "js/api.js", "js/campus.js", "js/app.js", "js/who.js", "js/ozet.js", "js/shell.js",
    "data/campus.geojson", "data/duyurular.json",
    "icons/icon.svg", "icons/icon-192.png",
];
const CDN = /^(unpkg\.com|cdn\.jsdelivr\.net|fonts\.googleapis\.com|fonts\.gstatic\.com)$/;

self.addEventListener("install", e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
    e.waitUntil(caches.keys()
        .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
        .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
    const req = e.request;
    if (req.method !== "GET") return;
    const url = new URL(req.url);
    if (url.origin === self.location.origin) e.respondWith(networkFirst(req));
    else if (CDN.test(url.hostname)) e.respondWith(cacheFirst(req));
});

async function networkFirst(req) {
    const cache = await caches.open(CACHE);
    try {
        const res = await fetch(req);
        if (res.ok) cache.put(req, res.clone());
        return res;
    } catch (err) {
        const hit = await cache.match(req, { ignoreSearch: true })
            || (req.mode === "navigate" && await cache.match("index.html"));
        if (hit) return hit;
        throw err;
    }
}

async function cacheFirst(req) {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    if (hit) return hit;
    const res = await fetch(req);
    if (res.ok || res.type === "opaque") cache.put(req, res.clone());
    return res;
}
