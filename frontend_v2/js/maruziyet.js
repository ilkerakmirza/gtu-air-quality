// Kişisel maruziyet hesabı (taslak) — kişi kampüste nerede, hangi saatlerde ve ne yaparak vakit geçirdiğini girer.
// Model (her satır için):  C = P(saat) × R(bina) × F(ortam)
//   P(saat): kampüs PurpleAir sensörünün ölçülen tüm günlerdeki saatlik ortalaması (Türkiye saati)
//   R(bina): binanın saha ölçüm ortalaması / tüm saha ölçümlerinin ortalaması (0,5–2 aralığında sınırlı)
//   F(ortam): iç/dış ortam oranı (iç mekân kaynakları dahil değil)
//   Solunan miktar = C × solunum hızı × süre
// Girilen bilgiler cihazdan çıkmaz; yalnızca kişi "bu cihazda hatırla" derse tarayıcıda saklanır.
// Yöntem, kabuller ve kaynakların tam kaydı: docs/maruziyet_yontemi.md — buradaki bir değer değişirse o belgeyi de güncelle.
// Bağımlılıklar: who.js (WHO.history, WHO.fieldPoints), campus.js (Campus.buildingStats), colorscale.js, icons.js

const Maruziyet = (() => {
    const STORE = "gtu.exp.rows";
    // F = dış kaynaklı PM₂.₅'in içeri geçen payı (sızma faktörü), iç kaynaklar hariç:
    //   doğal havalandırmalı binalar ort. ≈ 0,55 (Chen ve Zhao, 2011); konutlarda dış kaynak payı %29–75 (Salamalikis ve ark., 2025);
    //   pencereler açıkken / yazın daha yüksek (Hänninen ve ark., 2011); mekanik havalandırma + filtre ile üniversite binalarında
    //   I/O ≈ 0,12–0,28 (Afroz ve ark., 2025)
    const ENV = {
        out:    { ad: "Açık hava", f: 1.0 },
        vent:   { ad: "İç · açık pencere", f: 0.8 },
        closed: { ad: "İç · kapalı pencere", f: 0.5 },
        mech:   { ad: "İç · mekanik havalandırma", f: 0.25 },
    };
    // Solunum hızı (m³/saat): US EPA Exposure Factors Handbook (2011), Bölüm 6, Tablo 6-2, 21–31 yaş ortalaması
    // (m³/dk × 60: oturma/pasif 4,2E-03; hafif 1,2E-02; orta 2,6E-02; yoğun 5,0E-02)
    const ACT = {
        sit:   { ad: "Oturma (ders, ofis)", ir: 0.25 },
        light: { ad: "Hafif (ayakta, lab)", ir: 0.72 },
        walk:  { ad: "Tempolu yürüme", ir: 1.56 },
        sport: { ad: "Spor", ir: 3.0 },
    };
    const DEFAULT = [
        { yer: "", env: "closed", act: "sit", s: "09:00", e: "12:00" },
        { yer: "", env: "out", act: "walk", s: "12:00", e: "13:00" },
        { yer: "", env: "closed", act: "sit", s: "13:00", e: "17:00" },
    ];

    let rows = null, remember = false, model = null, busy = false;
    let mode = "chat", chat = null, chart = null;   // görünüm: "chat" (asistan) | "table" (tablo)
    const $ = id => document.getElementById(id);
    const f1 = v => v.toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const f0 = v => Math.round(v).toLocaleString("tr-TR");
    const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
    const hourOf = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Istanbul", hour: "2-digit", hourCycle: "h23" });
    const dayOf = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" });
    const dLabel = k => new Date(k + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
    const toMin = t => { const m = /^(\d\d):(\d\d)$/.exec(t || ""); return m ? +m[1] * 60 + +m[2] : null; };

    function lsGet() { try { return JSON.parse(localStorage.getItem(STORE)); } catch (_) { return null; } }
    function save() {
        try { remember ? localStorage.setItem(STORE, JSON.stringify(rows)) : localStorage.removeItem(STORE); } catch (_) {}
    }

    // ── Veri: saatlik profil ve bina oranları ─────────────────────────
    async function buildModel() {
        const [hist, field] = await Promise.all([WHO.history().catch(() => []), WHO.fieldPoints().catch(() => [])]);
        const byH = Array.from({ length: 24 }, () => []), days = new Set();
        for (const r of hist) {
            const t = new Date(r.recorded_at);
            if (r.pm2_5 == null || isNaN(t)) continue;
            byH[+hourOf.format(t)].push(+r.pm2_5);
            days.add(dayOf.format(t));
        }
        const all = byH.flat();
        const overall = all.length ? mean(all) : null;
        const P = byH.map(a => a.length >= 3 ? mean(a) : overall);
        const dk = [...days].sort();

        const vals = field.map(p => p.pm2_5).filter(v => v != null && !isNaN(v));
        const fieldMean = vals.length ? mean(vals) : null;
        const blds = (typeof Campus !== "undefined" && Campus.buildingStats(field)) || [];
        const B = blds.filter(b => b.avg != null)
            .map(b => ({ gk: b.gk, name: b.name, n: b.n, few: b.few, r: fieldMean ? Math.min(2, Math.max(0.5, b.avg / fieldMean)) : 1 }))
            .sort((a, b) => a.name.localeCompare(b.name, "tr"));
        return { P, overall, hours: all.length, first: dk[0], last: dk[dk.length - 1], B };
    }

    // Satırın saatlerine düşen ortalama P (dakika ağırlıklı)
    function pOver(s, e) {
        let sum = 0, w = 0;
        for (let m = s; m < e; ) {
            const h = Math.floor(m / 60) % 24, next = Math.min(e, (Math.floor(m / 60) + 1) * 60);
            sum += model.P[h] * (next - m); w += next - m; m = next;
        }
        return w ? sum / w : null;
    }

    function compute() {
        const res = [];
        for (const [i, r] of rows.entries()) {
            const s = toMin(r.s), e = toMin(r.e);
            if (s == null || e == null || e <= s) { res.push({ i, err: "Bitiş saati başlangıçtan sonra olmalı." }); continue; }
            const b = model.B.find(x => x.gk === r.yer);
            const p = pOver(s, e), R = b ? b.r : 1, F = ENV[r.env].f, ir = ACT[r.act].ir, h = (e - s) / 60;
            const c = p * R * F;
            res.push({ i, h, c, p, dose: c * ir * h, where: b ? b.name : "Kampüs geneli" });
        }
        const ok = res.filter(x => !x.err);
        const H = ok.reduce((a, x) => a + x.h, 0);
        return {
            res, H,
            twa: H ? ok.reduce((a, x) => a + x.c * x.h, 0) / H : null,
            dose: ok.reduce((a, x) => a + x.dose, 0),
            outTwa: H ? ok.reduce((a, x) => a + x.p * x.h, 0) / H : null,   // aynı saatler, açık hava, kampüs geneli
        };
    }

    // ── Görünüm ────────────────────────────────────────────────────────
    function opt(obj, sel) { return Object.entries(obj).map(([k, v]) => `<option value="${k}"${k === sel ? " selected" : ""}>${v.ad}</option>`).join(""); }

    function rowHtml(r, i) {
        const places = `<option value="">Kampüs geneli</option>` + model.B.map(b =>
            `<option value="${esc(b.gk)}"${b.gk === r.yer ? " selected" : ""}>${esc(b.name)}${b.few ? " (az ölçüm)" : ""}</option>`).join("");
        return `<div class="mx-row" data-i="${i}">
            <div class="mx-time"><input type="time" step="900" data-k="s" value="${esc(r.s)}" aria-label="Başlangıç">
              <span>–</span><input type="time" step="900" data-k="e" value="${esc(r.e)}" aria-label="Bitiş"></div>
            <select data-k="yer" aria-label="Yer">${places}</select>
            <select data-k="env" aria-label="Ortam">${opt(ENV, r.env)}</select>
            <select data-k="act" aria-label="Etkinlik">${opt(ACT, r.act)}</select>
            <button type="button" class="mx-del" data-del="${i}" title="Satırı sil" aria-label="Satırı sil">${ico("trash-2")}</button>
          </div>`;
    }

    function resultHtml() {
        if (model.overall == null) return `<div class="oz-card"><div class="wh-empty">Hesap için kampüs sensörü geçmişi yüklenemedi.</div></div>`;
        const k = compute(), ok = k.res.filter(x => !x.err);
        const errs = k.res.filter(x => x.err).map(x => `<div class="oz-line bad">${ico("triangle-alert")} ${x.i + 1}. satır: ${x.err}</div>`).join("");
        if (!ok.length) return errs || "";
        const c = pm25Color(k.twa), top = ok.reduce((a, b) => b.dose > a.dose ? b : a);
        const share = x => k.dose ? x.dose / k.dose * 100 : 0;
        const best = [...model.P.keys()].filter(h => h >= 7 && h <= 21).reduce((a, h) => model.P[h] < model.P[a] ? h : a, 7);
        // Öneri yalnızca açık hava etkinliğinin saatleri en düşük saatten belirgin (%10+) yüksekse
        const outdoorActive = ok.find(x => rows[x.i].env === "out" && ACT[rows[x.i].act].ir >= 1.5 && x.p > model.P[best] * 1.1);
        return errs + `<div class="oz-card oz-now" style="--c:${c}">
              <div class="wh-k">Kampüste ${f1(k.H)} saat · zaman ağırlıklı ortalama maruziyet (PM₂.₅)</div>
              <div class="oz-val"><b>${f1(k.twa)}</b><span>µg/m³</span></div>
              <div class="oz-src">Solunan PM₂.₅ ≈ <b>${f0(k.dose)} µg</b> · aynı saatlerde açık havada kampüs geneli: ${f1(k.outTwa)} µg/m³</div>
              <div class="mx-bars">${ok.map(x => `<div class="mx-bar">
                  <span>${esc(rows[x.i].s)}–${esc(rows[x.i].e)} · ${esc(x.where)} <small>${ENV[rows[x.i].env].ad.toLowerCase()}, ${f1(x.c)} µg/m³</small></span>
                  <i><em style="width:${share(x).toFixed(0)}%;background:${pm25Color(x.c)}"></em></i><b>%${share(x).toFixed(0)}</b></div>`).join("")}</div>
            </div>
            <div class="oz-line">${ico("info")} Solunan miktara en büyük katkı <b>${esc(top.where)}</b> (${esc(rows[top.i].s)}–${esc(rows[top.i].e)}, %${share(top).toFixed(0)}).
              ${outdoorActive ? ` ${esc(rows[outdoorActive.i].s)}–${esc(rows[outdoorActive.i].e)} arasındaki ${ACT[rows[outdoorActive.i].act].ad.toLowerCase()} etkinliğini
                kampüs profilinin en düşük olduğu saatlere (yaklaşık ${String(best).padStart(2, "0")}:00) almak maruziyeti azaltabilir.` : ""}</div>`;
    }

    function methodHtml() {
        const prof = model.first ? `${dLabel(model.first)} – ${dLabel(model.last)} arası ${model.hours.toLocaleString("tr-TR")} saatlik ölçüm` : "veri yok";
        return `<details class="who-table mx-method"><summary>Yöntem, varsayımlar ve sınırlılıklar</summary>
            <div class="who-info">
              <p><b>Hesap:</b> Her satır için derişim C = P × R × F; ortalama maruziyet = Σ(C × süre) / Σ süre;
                solunan miktar = Σ(C × solunum hızı × süre).</p>
              <p><b>P (saatlik profil):</b> Kampüs PurpleAir sensörünün ${prof} ile hesaplanan saatlik ortalamaları (ham, düzeltilmemiş değerler).</p>
              <p><b>R (bina):</b> Binanın saha ölçüm ortalamasının tüm saha ölçümleri ortalamasına oranı; kısa süreli ölçümlere dayandığı için
                0,5–2 aralığıyla sınırlanmıştır. Saha ölçümü olmayan yerler için kampüs geneli (R = 1) kullanılır.</p>
              <p><b>F (ortam):</b> Dışarıdan gelen PM₂.₅'in iç mekâna geçen payı: açık hava 1,0; açık pencere 0,8; kapalı pencere 0,5;
                mekanik havalandırma (filtreli) 0,25. Doğal havalandırmalı binalarda ortalama sızma faktörü yaklaşık 0,55'tir (Chen ve Zhao, 2011);
                güncel düşük maliyetli sensör çalışmalarında dış kaynak payı %29–75 bulunmuştur (Salamalikis ve ark., 2025). Sızma pencereler
                açıkken ve yaz aylarında artar (Hänninen ve ark., 2011); filtreli mekanik havalandırmalı üniversite binalarında iç/dış oranı
                0,12–0,28'dir (Afroz ve ark., 2025). İç kaynaklar (kalabalık sınıflarda tozun yeniden havalanması, yemek pişirme, yazıcı) dahil
                değildir; bu nedenle sınıflarda gerçek değer daha yüksek olabilir (Branco ve ark., 2024).</p>
              <p><b>Solunum hızı:</b> oturma 0,25; hafif 0,72; tempolu yürüme 1,56; spor 3,0 m³/saat. US EPA Exposure Factors Handbook,
                Bölüm 6, Tablo 6-2, 21–31 yaş ortalaması (bölüm 2011'den beri güncel; 2025'te erişilebilir sürümle yeniden yayımlandı).</p>
              <p><b>Sınırlılıklar:</b> Sonuç bir senaryo tahminidir, kişisel ölçüm değildir; tıbbi değerlendirme yerine geçmez. Birkaç saatlik
                ortalama, WHO'nun 24 saatlik kılavuz değeriyle doğrudan karşılaştırılamaz.</p>
              <p class="who-note">Kaynaklar: Afroz, R. ve ark. (2025). Impact of wildfire smoke PM2.5 on indoor air quality of public buildings
                on a university campus. <i>ACS ES&amp;T Air</i>, 2, 625–636. doi:10.1021/acsestair.4c00342 ·
                Branco, P. ve ark. (2024). A review of relevant parameters for assessing indoor air quality in educational facilities.
                <i>Environmental Research</i>, 261, 119713. doi:10.1016/j.envres.2024.119713 ·
                Chen, C., Zhao, B. (2011). Review of relationship between indoor and outdoor particles: I/O ratio, infiltration factor and
                penetration factor. <i>Atmospheric Environment</i>, 45, 275–288. doi:10.1016/j.atmosenv.2010.09.048 ·
                Hänninen, O. ve ark. (2011). Seasonal patterns of outdoor PM infiltration into indoor environments. <i>Air Quality, Atmosphere
                &amp; Health</i>, 4, 221–233. doi:10.1007/s11869-010-0076-5 ·
                Salamalikis, V. ve ark. (2025). Citizen-operated low-cost sensors for estimating outdoor particulate matter infiltration.
                <i>Air Quality, Atmosphere &amp; Health</i>, 18, 2609–2624. doi:10.1007/s11869-025-01787-4 ·
                U.S. EPA (2011). <i>Exposure Factors Handbook: 2011 Edition</i>, Bölüm 6. EPA/600/R-09/052F.</p>
            </div></details>`;
    }

    // ── Sohbet asistanı (kural tabanlı; yapay zekâ ya da dış servis yok) ──────────────
    // Adımlar: saat → etkinlik → yer → (iç mekânsa) havalandırma → süre → başka? → sonuç.
    // Her tamamlanan adım dizisi bir satıra (rows) dönüşür; sonuç tablo görünümüyle aynı hesaptan gelir.
    const CHOICES = [
        { k: "ders",  ico: "graduation-cap", ad: "Ders / ofis",            env: null,  act: "sit" },
        { k: "lab",   ico: "flask-conical",  ad: "Laboratuvar",            env: null,  act: "light" },
        { k: "yemek", ico: "coffee",         ad: "Yemekhane / kantin",     env: null,  act: "light" },
        { k: "yurume",ico: "footprints",     ad: "Açık havada yürüyüş",    env: "out", act: "walk" },
        { k: "otur",  ico: "trees",          ad: "Açık havada oturma",     env: "out", act: "sit" },
        { k: "spor",  ico: "dumbbell",       ad: "Spor (açık hava)",       env: "out", act: "sport" },
    ];
    const VENT = [
        { k: "closed", ad: "Pencereler kapalı" }, { k: "vent", ad: "Pencere açık" },
        { k: "mech", ad: "Mekanik havalandırma" }, { k: "closed", ad: "Bilmiyorum", alt: true },
    ];
    const DUR = [30, 60, 90, 120, 180, 240];
    const hm = m => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
    const durTxt = m => m < 60 ? `${m} dk` : m % 60 ? `${Math.floor(m / 60)},5 saat` : `${m / 60} saat`;

    // Asistanın yüzü o anki hava kalitesine (HKİ) göre değişir
    function face() {
        const cur = typeof Ozet !== "undefined" && Ozet.current && Ozet.current();
        return cur && cur.h ? { yuz: cur.h.yuz, renk: cur.h.renk, cur } : { yuz: "smile", renk: "var(--accent)", cur: null };
    }
    const avatar = () => { const f = face(); return `<span class="cb-av" style="--c:${f.renk}">${ico(f.yuz)}</span>`; };

    function chatStart() {
        const f = face();
        chat = { step: "saat", draft: {}, log: [], t: null, labels: [] };
        rows = [];
        bot(`Merhaba! Ben <b>AirLab asistanı</b>. Bugün kampüste geçirdiğin zamana göre ne kadar PM₂.₅'e maruz kaldığını birlikte tahmin edelim.`
            + (f.cur ? ` Şu an kampüste hava <b style="color:${f.renk}">${f.cur.h.ad}</b> (HKİ ${f.cur.h.i}).` : ""));
        bot("Kampüse saat kaçta geldin?");
    }
    const bot = html => chat.log.push({ who: "bot", html });
    const me = txt => chat.log.push({ who: "me", html: esc(txt) });

    function ask() {   // o anki adımın seçenekleri
        const d = chat.draft, opts = (list, f) => `<div class="cb-opts">${list.map(f).join("")}</div>`;
        switch (chat.step) {
            case "saat":
                return opts([8, 9, 10, 11, 13], h => `<button type="button" class="pd-chip" data-a="saat" data-v="${h * 60}">${hm(h * 60)}</button>`)
                    + `<div class="cb-row"><input type="time" step="900" id="cb-time" value="09:00" aria-label="Başka bir saat"><button type="button" class="sc-btn" data-a="saat-in">Bu saat</button></div>`;
            case "etkinlik":
                return opts(CHOICES, c => `<button type="button" class="cb-choice" data-a="etkinlik" data-v="${c.k}">${ico(c.ico)}<span>${c.ad}</span></button>`);
            case "yer":
                return `<div class="cb-row"><select id="cb-bld" aria-label="Bina"><option value="">Kampüs geneli / bilmiyorum</option>${model.B.map(b =>
                        `<option value="${esc(b.gk)}">${esc(b.name)}${b.few ? " (az ölçüm)" : ""}</option>`).join("")}</select>
                        <button type="button" class="sc-btn" data-a="yer">Seç</button></div>`;
            case "hava":
                return opts(VENT, v => `<button type="button" class="pd-chip${v.alt ? " alt" : ""}" data-a="hava" data-v="${v.k}">${v.ad}</button>`);
            case "sure":
                return opts(DUR, m => `<button type="button" class="pd-chip" data-a="sure" data-v="${m}">${durTxt(m)}</button>`);
            case "devam":
                return opts([["ekle", "Evet, ekleyeyim"], ["bitti", "Hayır, sonucu göster"]], ([k, t]) =>
                    `<button type="button" class="pd-chip${k === "bitti" ? " on" : ""}" data-a="devam" data-v="${k}">${t}</button>`);
            case "sonuc":
                return opts([["yeni", "rotate-ccw", "Baştan başla"], ["tablo", "table-2", "Tabloda düzenle"]], ([k, i, t]) =>
                    `<button type="button" class="pd-chip" data-a="son" data-v="${k}">${ico(i)} ${t}</button>`);
        }
        return "";
    }

    function answer(a, v, txt) {
        const d = chat.draft;
        if (a === "saat" || a === "saat-in") {
            const m = a === "saat" ? +v : toMin($("cb-time").value);
            if (m == null) return;
            chat.t = m; me(hm(m));
            bot(`Saat ${hm(m)}. O sırada ne yapıyordun?`);
            chat.step = "etkinlik";
        } else if (a === "etkinlik") {
            const c = CHOICES.find(x => x.k === v); d.c = c; me(c.ad);
            bot(c.env === "out" ? "Kampüsün neresindeydin? Bir binanın çevresindeysen onu seç." : "Hangi binadaydın?");
            chat.step = "yer";
        } else if (a === "yer") {
            const gk = $("cb-bld").value, b = model.B.find(x => x.gk === gk); d.yer = gk; me(b ? b.name : "Kampüs geneli");
            if (d.c.env === "out") { d.env = "out"; bot("Ne kadar sürdü?"); chat.step = "sure"; }
            else { bot("İçerisi nasıl havalandırılıyordu?"); chat.step = "hava"; }
        } else if (a === "hava") {
            d.env = v; me(txt);
            bot("Ne kadar sürdü?"); chat.step = "sure";
        } else if (a === "sure") {
            const m = +v, e = Math.min(chat.t + m, 23 * 60 + 45);
            me(durTxt(m));
            rows.push({ yer: d.yer || "", env: d.env, act: d.c.act, s: hm(chat.t), e: hm(e) });
            chat.labels.push(d.c.ad);
            chat.t = e; chat.draft = {};
            bot(`Not aldım: <b>${rows[rows.length - 1].s}–${rows[rows.length - 1].e}</b> · ${d.c.ad.toLowerCase()}. Sonra başka bir şey yaptın mı?`);
            chat.step = e >= 23 * 60 ? "sonuc-hazir" : "devam";
            if (chat.step === "sonuc-hazir") { result(); return; }
        } else if (a === "devam") {
            if (v === "ekle") { me("Evet"); bot(`Saat ${hm(chat.t)} sonrasında ne yaptın?`); chat.step = "etkinlik"; }
            else { me("Hayır, sonucu göster"); result(); return; }
        } else if (a === "son") {
            if (v === "yeni") { chatStart(); }
            else { mode = "table"; }
        }
        save(); render();
    }

    function result() {
        chat.step = "sonuc";
        const k = compute(), ok = k.res.filter(x => !x.err);
        if (!ok.length) { bot("Hesap için geçerli bir zaman dilimi bulamadım. Baştan başlayalım mı?"); save(); render(); return; }
        const top = ok.reduce((a, b) => b.dose > a.dose ? b : a), share = x => k.dose ? x.dose / k.dose * 100 : 0;
        const best = [...model.P.keys()].filter(h => h >= 7 && h <= 21).reduce((a, h) => model.P[h] < model.P[a] ? h : a, 7);
        const act = ok.find(x => rows[x.i].env === "out" && ACT[rows[x.i].act].ir >= 1.5 && x.p > model.P[best] * 1.1);
        const hiBld = ok.find(x => rows[x.i].env !== "out" && model.B.find(b => b.gk === rows[x.i].yer && b.r >= 1.2));
        const lab = x => `${rows[x.i].s}–${rows[x.i].e}`;
        bot(`Kampüste <b>${f1(k.H)} saat</b> geçirdin. Bu sürede ortalama maruziyetin yaklaşık <b>${f1(k.twa)} µg/m³</b>,
            soluduğun PM₂.₅ miktarı yaklaşık <b>${f0(k.dose)} µg</b>. Aynı saatleri açık havada geçirseydin ortalama ${f1(k.outTwa)} µg/m³ olurdu.`);
        bot(`<div class="cb-chart"><canvas id="cb-canvas" aria-label="Solunan PM₂.₅'in etkinliklere göre dağılımı"></canvas></div>
             <div class="who-cap">Çubuk uzunluğu: solunan PM₂.₅ (µg) · renk: o dilimdeki tahmini derişim</div>`);
        const tips = [`Solunan miktara en büyük katkı <b>${lab(top)}</b> dilimi (%${share(top).toFixed(0)}).`];
        if (act) tips.push(`${lab(act)} arasındaki ${ACT[rows[act.i].act].ad.toLowerCase()} etkinliğini kampüs profilinin en düşük olduğu saatlere (yaklaşık ${String(best).padStart(2, "0")}:00) almak maruziyeti azaltabilir.`);
        if (hiBld) tips.push(`${esc(hiBld.where)} çevresinde saha ölçümleri kampüs ortalamasının üzerinde; iç mekânın dış havanın daha temiz olduğu saatlerde havalandırılması düşünülebilir.`);
        const f = face();
        if (f.cur && f.cur.h.i > 100) tips.push(`Şu an hava kalitesi <b>${f.cur.h.ad}</b>; hassas grupların uzun süreli açık hava etkinliklerini azaltması önerilir.`);
        tips.push(`Bu bir tahmindir; kişisel ölçüm ya da tıbbi değerlendirme yerine geçmez. Ayrıntılar tablo görünümündeki "Yöntem" bölümünde.`);
        bot(`<b>Ne yapabilirsin?</b><ul class="cb-tips">${tips.map(t => `<li>${t}</li>`).join("")}</ul>`);
        chat.res = ok.map(x => ({ label: [lab(x), chat.labels[x.i] || ACT[rows[x.i].act].ad], dose: x.dose, c: x.c }));   // iki satırlı etiket
        save(); render();
    }

    function drawChart() {
        if (chart) { chart.destroy(); chart = null; }
        const cv = $("cb-canvas");
        if (!cv || !chat.res || typeof Chart === "undefined") return;
        const d = chat.res;
        chart = new Chart(cv, {
            type: "bar",
            data: { labels: d.map(x => x.label), datasets: [{ data: d.map(x => +x.dose.toFixed(1)), backgroundColor: d.map(x => pm25Color(x.c)), borderRadius: 4, maxBarThickness: 22 }] },
            options: {
                indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.raw} µg · derişim ${f1(d[c.dataIndex].c)} µg/m³` } } },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: "Solunan PM₂.₅ (µg)", color: "#a2adc2" }, ticks: { color: "#a2adc2" }, grid: { color: "rgba(160,180,220,0.1)" } },
                    y: { ticks: { color: "#e9edf5", font: { size: 11 } }, grid: { display: false } },
                },
            },
        });
        cv.parentElement.style.height = `${Math.max(100, d.length * 42 + 44)}px`;
    }

    function chatHtml() {
        return `<div class="cb">
            ${chat.log.map(m => m.who === "bot"
                ? `<div class="cb-msg bot">${avatar()}<div class="cb-bub">${m.html}</div></div>`
                : `<div class="cb-msg me"><div class="cb-bub">${m.html}</div></div>`).join("")}
            <div class="cb-ask">${ask()}</div>
          </div>`;
    }

    function bindChat() {
        $("exp-body").querySelectorAll(".cb-ask [data-a]").forEach(b => b.addEventListener("click", () => answer(b.dataset.a, b.dataset.v, b.textContent.trim())));
        drawChart();
        const last = $("exp-body").querySelector(".cb-ask");
        if (last) last.scrollIntoView({ block: "nearest" });
    }

    function render() {
        const body = $("exp-body");
        const tabs = `<div class="pd-chips mx-mode"><button type="button" class="pd-chip${mode === "chat" ? " on" : ""}" data-mode="chat">${ico("message-circle")} Asistan</button>
            <button type="button" class="pd-chip${mode === "table" ? " on" : ""}" data-mode="table">${ico("table-2")} Tablo</button></div>`;
        if (mode === "chat") {
            if (!chat) chatStart();
            body.innerHTML = tabs + chatHtml();
            body.querySelectorAll("[data-mode]").forEach(b => b.addEventListener("click", () => { mode = b.dataset.mode; render(); }));
            bindChat();
            return;
        }
        if (chart) { chart.destroy(); chart = null; }
        if (!rows.length) rows = DEFAULT.map(r => ({ ...r }));
        renderTable(tabs);
    }

    function renderTable(tabs) {
        const body = $("exp-body");
        body.innerHTML = tabs + `<p class="mx-intro">Kampüste hangi saatlerde, nerede ve ne yaparak vakit geçirdiğinizi girin. Kampüs ölçümlerine göre
              <b>taslak bir maruziyet tahmini</b> hesaplanır.</p>
            <div class="mx-rows">${rows.map(rowHtml).join("")}</div>
            <div class="mx-tools">
              <button type="button" class="sc-btn" id="mx-add">${ico("plus")} Satır ekle</button>
              <button type="button" class="sc-btn" id="mx-reset">Örneğe dön</button>
            </div>
            <label class="mx-remember"><input type="checkbox" id="mx-remember"${remember ? " checked" : ""}> Bu cihazda hatırla
              <small>Girdiğiniz bilgiler hiçbir yere gönderilmez; işaretlemezseniz sayfa kapanınca silinir.</small></label>
            <div id="mx-result">${resultHtml()}</div>
            ${methodHtml()}`;
        body.querySelectorAll("[data-mode]").forEach(b => b.addEventListener("click", () => { mode = b.dataset.mode; render(); }));
        bind();
    }
    function refreshResult() { $("mx-result").innerHTML = resultHtml(); save(); }

    function bind() {
        const body = $("exp-body");
        body.querySelectorAll(".mx-row [data-k]").forEach(el => el.addEventListener("change", () => {
            rows[+el.closest(".mx-row").dataset.i][el.dataset.k] = el.value;
            refreshResult();
        }));
        body.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => {
            rows.splice(+b.dataset.del, 1);
            if (!rows.length) rows = DEFAULT.map(r => ({ ...r }));
            save(); render();
        }));
        $("mx-add").addEventListener("click", () => {
            const last = rows[rows.length - 1];
            const s = last ? last.e : "09:00", em = Math.min(toMin(s) + 60, 23 * 60 + 45);
            rows.push({ yer: "", env: "closed", act: "sit", s, e: `${String(Math.floor(em / 60)).padStart(2, "0")}:${String(em % 60).padStart(2, "0")}` });
            save(); render();
        });
        $("mx-reset").addEventListener("click", () => { rows = DEFAULT.map(r => ({ ...r })); save(); render(); });
        $("mx-remember").addEventListener("change", ev => { remember = ev.target.checked; save(); });
    }

    async function load() {
        if (busy) return;
        if (!rows) {
            const stored = lsGet();
            remember = Array.isArray(stored) && stored.length > 0;
            rows = remember ? stored.filter(r => r && ENV[r.env] && ACT[r.act]) : DEFAULT.map(r => ({ ...r }));
            if (remember) mode = "table";   // kaydedilmiş satırlar asistan tarafından silinmesin
        }
        if (model) { render(); return; }
        busy = true;
        $("exp-body").innerHTML = `<div class="news-empty">Kampüs ölçümleri yükleniyor…</div>`;
        try {
            model = await buildModel();
            render();
        } catch (e) {
            console.warn("[maruziyet]", e);
            $("exp-body").innerHTML = `<div class="news-empty">Hesap için veriler yüklenemedi; bağlantınızı kontrol edip yeniden deneyin.</div>`;
        } finally { busy = false; }
    }

    return { load };
})();
