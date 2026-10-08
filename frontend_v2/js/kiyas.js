// Kampüs–bölge karşılaştırması: kampüs PurpleAir (PM₂.₅) ile Tuzla istasyonunun AYNI saatlerdeki değerleri.
// Tuzla geçmişi: data/tuzla_saatlik.json (PM₂.₅: ÇŞB, scripts/csb_gecmis.py ile indirilir) + sunucu arşivi
// (6 Ekim 2026'dan beri İBB'den saatlik toplanan aynı Tuzla istasyonu; json'da olmayan saatleri tamamlar).
// Yalnızca iki tarafın da ölçüm yaptığı saatler karşılaştırılır; böylece eksik günler sonucu çarpıtmaz.
// Bağımlılıklar: who.js (WHO.history)

const Kiyas = (() => {
    const C_CAMPUS = "#6380f0", C_REGION = "#bf8418";   // doğrulayıcıdan geçen iki seri rengi (koyu zemin)
    let p = null;

    const hourFmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit",
                                                       day: "2-digit", hour: "2-digit", hourCycle: "h23" });
    function hourKey(d) {
        const o = {};
        for (const x of hourFmt.formatToParts(d)) o[x.type] = x.value;
        return `${o.year}-${o.month}-${o.day}T${o.hour}:00`;
    }
    const mean = a => a.reduce((s, x) => s + x, 0) / a.length;

    // { pairs: [{k, day, ym, c, r}], regionHours, updated }
    function data() {
        if (!p) {
            const since = new Date(Date.now() - 400 * 864e5).toISOString().slice(0, 10);
            p = Promise.all([
                WHO.history(),
                fetch("data/tuzla_saatlik.json", { cache: "no-cache" }).then(r => r.json()).catch(() => ({})),
                API.archiveCsv("ibb", since).catch(() => ""),
            ]).then(([rows, tz, csv]) => {
                const reg = new Map();
                for (const r of tz.veri || []) if (r.pm2_5 != null) reg.set(r.t, +r.pm2_5);
                // Sunucu arşivi: yalnızca Tuzla satırları; anahtar Türkiye saatine göre "YYYY-AA-GGTSS:00"
                const lines = (csv || "").trim().split(/\r?\n/);
                const hd = (lines.shift() || "").split(","), iDev = hd.indexOf("device"),
                      iT = hd.indexOf("recorded_at_TR"), iPm = hd.indexOf("pm2_5");
                let fromArchive = 0;
                if (iDev >= 0 && iT >= 0 && iPm >= 0) for (const ln of lines) {
                    const c = ln.split(",");
                    if (c[iDev] !== "Tuzla" || c[iPm] === "" || !c[iT]) continue;
                    const k = c[iT].slice(0, 13).replace(" ", "T") + ":00";
                    if (!reg.has(k)) { reg.set(k, +c[iPm]); fromArchive++; }
                }
                const pairs = [];
                for (const r of rows) {
                    if (r.pm2_5 == null) continue;
                    const t = new Date(r.recorded_at);
                    if (isNaN(t)) continue;
                    const k = hourKey(t), v = reg.get(k);
                    if (v == null) continue;
                    pairs.push({ k, day: k.slice(0, 10), ym: k.slice(0, 7), c: +r.pm2_5, r: v });
                }
                return { pairs, regionHours: reg.size, fromArchive, updated: tz.guncelleme };
            });
            p.catch(() => { p = null; });
        }
        return p;
    }

    function summary(pairs) {
        if (!pairs || !pairs.length) return null;
        const c = mean(pairs.map(x => x.c)), r = mean(pairs.map(x => x.r));
        return { n: pairs.length, c, r, diff: c - r, pct: (c - r) / r * 100,
                 cleaner: pairs.filter(x => x.c < x.r).length / pairs.length,
                 first: pairs[0].day, last: pairs[pairs.length - 1].day };
    }

    // Sade cümle: "%12 daha temiz" (±%5 içi "benzer")
    function verdict(s) {
        if (!s) return null;
        const a = Math.abs(s.pct).toFixed(0);
        if (s.pct <= -5) return { cls: "ok", icon: ico("trending-down"), txt: `Kampüs, Tuzla'dan ortalama %${a} daha temiz` };
        if (s.pct >= 5) return { cls: "bad", icon: ico("trending-up"), txt: `Kampüs, Tuzla'dan ortalama %${a} daha kirli` };
        return { cls: "", icon: ico("equal"), txt: "Kampüs ve Tuzla benzer seviyede" };
    }

    function daily(pairs) {
        const by = new Map();
        for (const x of pairs) (by.get(x.day) || by.set(x.day, []).get(x.day)).push(x);
        return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0]))
            .map(([day, xs]) => ({ day, n: xs.length, c: mean(xs.map(x => x.c)), r: mean(xs.map(x => x.r)) }));
    }

    return { data, summary, verdict, daily, C_CAMPUS, C_REGION };
})();
