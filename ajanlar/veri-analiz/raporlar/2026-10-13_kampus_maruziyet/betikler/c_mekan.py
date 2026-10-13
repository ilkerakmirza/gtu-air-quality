"""3.2 Nerede kötü? — saha yürüyüşleri (27–30 Nisan 2026, 12 oturum) ile göreli mekânsal indeksler.

Kullanım: python3 -I c_mekan.py <ham klasörü> <rapor klasörü>
İndeksler (her nokta için):
  G    = PM₂.₅ / kendi oturumunun ortancası                         (ana göreli indeks)
  G_PA = (PM₂.₅ / aynı saatin PurpleAir ham ortalaması) / oturumdaki bu oranın ortancası   (zamana göre duyarlılık)
  K    = PM₂.₅ (Atmotube, ham) / aynı anın düzeltilmiş PurpleAir değeri (±3 dk, 2 dk kayıt)   (kişisel / çatı oranı)
Birim: 25 m ızgara hücresi ve bina (campus.geojson; içinde ya da sınırına ≤ 15 m). Gösterim: ≥ 2 oturum ve ≥ 10 nokta.
Güven aralığı: oturum düzeyinde (küme) bootstrap, 2000 yineleme, %2,5–97,5 yüzdelikleri; tohum 20261013.
Üretir: sekiller/sekil06_harita.png, sekil07_gorel_indeks.png; sayilar.json'a 'C.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
import ortak  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, xy, kampus_geojson, bina_etiketi, IRAKSAK, KATEGORIK, MUREKKEP,  # noqa: E402
                   IKINCIL, GRI, TABAN, CAMPUS_LAT, CAMPUS_LON, M_LAT, M_LON, uygulama_ile_esles)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

CS = 25.0          # ızgara (m)
MIN_OT, MIN_N = 2, 10
SICAK = 1.25
B = 2000
KAYNAK = ("Kaynak: Atmotube PRO saha yürüyüşleri (27–30 Nisan 2026, 12 oturum, ham PM₂.₅) ve PurpleAir PA-II (SUMER çatısı);"
          " bina poligonları campus.geojson.")
Q = "Q2 (saha noktaları) + docs/veri PurpleAir arşivi (27–30 Nisan, 2 dk)"


def boot_ci(g, col, rng):
    ses = g.oturum.unique()
    by = {s: g.loc[g.oturum == s, col].values for s in ses}
    if len(ses) < 2:
        return np.nan, np.nan
    st = [np.median(np.concatenate([by[s] for s in rng.choice(ses, size=len(ses), replace=True)])) for _ in range(B)]
    return float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5))


def ozet(g, rng):
    lo, hi = boot_ci(g, "G", rng)
    return pd.Series({"n": len(g), "oturum": g.oturum.nunique(), "G": g.G.median(), "G_lo": lo, "G_hi": hi,
                      "G_PA": g.G_PA.median(), "K": g.K.median(), "pm_med": g.pm2_5.median(),
                      "kimya_payi": float(g.kimya.mean())})


def en_yakin_bina(blds, x0, y0):
    lat, lon = CAMPUS_LAT + y0 / M_LAT, CAMPUS_LON + x0 / M_LON
    best = None
    for b in blds:
        d = 0.0 if ortak._icinde(b, lon, lat) else ortak._kenar_uzakligi(b, lon, lat)
        if best is None or d < best[0]:
            best = (d, b)
    return best


def poligonlar(fc, kat):
    for f in fc["features"]:
        if f["properties"].get("cat") != kat:
            continue
        g = f["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            yield f, np.array([xy(p[1], p[0]) for p in poly[0]])


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    from matplotlib.colors import LinearSegmentedColormap, LogNorm
    from matplotlib.patches import Polygon as MPoly, Rectangle
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    rng = np.random.default_rng(20261013)
    d, blds, pa = veri.saha(ham)
    n_tum = len(d)
    d = d[d.pm2_5.notna()].copy()
    d["G"] = d.pm2_5 / d.groupby("oturum").pm2_5.transform("median")
    d["rpa"] = d.pm2_5 / d.pa_ham_saat
    d["G_PA"] = d.rpa / d.groupby("oturum").rpa.transform("median")
    d["K"] = d.pm2_5 / d.pa_epa
    d["cx"] = np.floor(d.x / CS).astype(int)
    d["cy"] = np.floor(d.y / CS).astype(int)
    d["kimya"] = d.gk.fillna("").str.contains("Kimya")

    S.ekle("C.nokta_tum", int(n_tum), "nokta", "12 saha oturumunun konumlu noktaları (kampüs içi, 2 km kuralı)", Q)
    S.ekle("C.nokta_pm", int(len(d)), "nokta", "PM₂.₅ değeri olan noktalar", Q)
    S.ekle("C.kampus_disi", 0, "nokta", "kampüs sınırı (merkezden 2 km) dışında kalan nokta", Q)
    S.ekle("C.bina_ici", int(((d.gk.notna()) & (~d.yakin)).sum()), "nokta", "bir bina poligonunun içine düşen nokta", Q)
    S.ekle("C.bina_yakin", int(d.yakin.sum()), "nokta", "bina dışında ama sınırına ≤ 15 m olan nokta", Q)
    S.ekle("C.bina_disi", int(d.gk.isna().sum()), "nokta", "hiçbir binaya ≤ 15 m olmayan nokta (yol, açık alan)", Q)
    S.ekle("C.kimya_payi", round(float(d.kimya.mean() * 100), 1), "%", "noktaların 'Kimya ve Çevre Mühendisliği Bölümü' binasına (15 m kuralıyla) düşen payı", Q)
    S.ekle("C.kimya_oturum_85", int((d.groupby("oturum").kimya.mean() > 0.85).sum()), "oturum",
           "noktalarının %85'ten fazlası bu binada olan oturum sayısı", Q)
    rg = d.groupby("oturum").apply(lambda g: float(np.sqrt(((g.x - g.x.mean()) ** 2 + (g.y - g.y.mean()) ** 2).mean())),
                                   include_groups=False)
    S.ekle("C.donme_yaricapi_ortanca", round(float(rg.median()), 0), "m", "oturum başına dönme yarıçapı (noktaların ağırlık merkezine uzaklığının kareli ortalamasının kökü), 12 oturumun ortancası", Q)
    S.ekle("C.donme_yaricapi_aralik", f"{tr(rg.min(), 0)}–{tr(rg.max(), 0)}", "m", "aynı ölçünün en küçük ve en büyük değeri", Q)
    S.ekle("C.atmotube_cozunurluk_tamsayi_payi", round(float((d.pm2_5 == d.pm2_5.round()).mean() * 100), 1), "%",
           "Atmotube PM₂.₅ değerlerinin tam sayı olan payı (1 µg/m³ çözünürlük)", Q)

    # ── hücreler ──
    hucre = d.groupby(["cx", "cy"]).apply(lambda g: ozet(g, rng), include_groups=False)
    hucre = hucre[(hucre.n >= MIN_N) & (hucre.oturum >= MIN_OT)].copy()
    hucre["ad"] = ""
    hucre["uzak"] = np.nan
    for (cx, cy) in hucre.index:
        dist, b = en_yakin_bina(blds, (cx + 0.5) * CS, (cy + 0.5) * CS)
        hucre.loc[(cx, cy), "ad"] = bina_etiketi(b)
        hucre.loc[(cx, cy), "uzak"] = dist
    S.ekle("C.hucre_uygun", int(len(hucre)), "hücre", f"{int(CS)} m hücrelerden ≥ {MIN_OT} oturum ve ≥ {MIN_N} nokta içerenler", Q)
    S.ekle("C.hucre_uygun_nokta", int(hucre.n.sum()), "nokta", "bu hücrelerdeki nokta sayısı", Q)
    sicak = hucre[hucre.G >= SICAK].sort_values("G", ascending=False)
    S.ekle("C.sicak_hucre", int(len(sicak)), "hücre", f"G ortancası ≥ {SICAK} olan uygun hücre", Q)
    sicak_liste = []
    for i, ((cx, cy), r) in enumerate(sicak.iterrows(), 1):
        konum = r.ad if r.uzak == 0 else f"{r.ad} yakını ({tr(r.uzak, 0)} m)"
        sicak_liste.append((f"H{i}", konum, r))
        S.ekle(f"C.sicak_H{i}", {"konum": konum, "n": int(r.n), "oturum": int(r.oturum), "G": round(r.G, 2),
                                 "G_GA": [round(r.G_lo, 2), round(r.G_hi, 2)], "G_PA": round(r.G_PA, 2), "K": round(r.K, 2)},
               "oran", "sıcak hücre: ortanca G, oturum düzeyinde bootstrap %95 GA, G_PA ve K ortancaları", Q)

    # ── binalar ──
    bina = d[d.gk.notna()].groupby("gk").apply(lambda g: ozet(g, rng), include_groups=False)
    ad = {b["gk"]: bina_etiketi(b) for b in blds}
    bina["ad"] = [ad[k] for k in bina.index]
    bina_uy = bina[(bina.n >= MIN_N) & (bina.oturum >= MIN_OT)].sort_values("G", ascending=False)
    disari = d[d.gk.isna()]
    dz = ozet(disari, rng)
    S.ekle("C.bina_uygun", int(len(bina_uy)), "bina", "≥ 2 oturum ve ≥ 10 noktası olan bina", Q)
    S.ekle("C.bina_noktali", int(len(bina)), "bina", "en az bir noktası olan bina", Q)
    for k, r in bina_uy.iterrows():
        S.ekle(f"C.bina_{r.ad}", {"n": int(r.n), "oturum": int(r.oturum), "G": round(r.G, 2), "G_GA": [round(r.G_lo, 2), round(r.G_hi, 2)],
                                  "G_PA": round(r.G_PA, 2), "K": round(r.K, 2), "pm_ortanca": round(r.pm_med, 1)},
               "oran / µg/m³", "bina: nokta ve oturum sayısı, G ortancası ve bootstrap %95 GA, G_PA ve K ortancaları, ham PM₂.₅ ortancası", Q)
    S.ekle("C.bina_disi_ozet", {"n": int(dz.n), "oturum": int(dz.oturum), "G": round(dz.G, 2), "G_GA": [round(dz.G_lo, 2), round(dz.G_hi, 2)],
                                "G_PA": round(dz.G_PA, 2), "K": round(dz.K, 2)}, "oran", "hiçbir binaya ≤ 15 m olmayan noktalar", Q)
    S.ekle("C.K_kimya", round(float(d[d.kimya].K.median()), 2), "oran", "Kimya binası noktalarında K (Atmotube / düzeltilmiş PurpleAir) ortancası", Q)
    S.ekle("C.K_kimya_disi", round(float(d[~d.kimya].K.median()), 2), "oran", "Kimya binası dışındaki noktalarda K ortancası", Q)
    S.ekle("C.G_kimya_disi", round(float(d[~d.kimya].G.median()), 2), "oran", "Kimya binası dışındaki noktalarda G ortancası", Q)

    # Sıralama tutarlılığı: G ile G_PA (uygun hücreler + binalar)
    birlik = pd.concat([hucre[["G", "G_PA"]], bina_uy[["G", "G_PA"]]])
    rho = float(np.corrcoef(birlik.G.rank(), birlik.G_PA.rank())[0, 1])
    S.ekle("C.G_GPA_spearman", round(rho, 2), "", "uygun hücre ve binalarda G ile G_PA ortancaları arasında Spearman", Q)
    S.ekle("C.sicak_GPA_de_sicak", int((sicak.G_PA >= SICAK).sum()), "hücre", "sıcak hücrelerden G_PA ölçütüyle de ≥ 1,25 olanlar", Q)
    S.ekle("C.sicak_K_1_25", int((sicak.K >= SICAK).sum()), "hücre", "sıcak hücrelerden K ≥ 1,25 olanlar (çatı düzeyinin belirgin üstü)", Q)

    # Saha saatleri
    saat = d.tl.dt.hour + d.tl.dt.minute / 60
    d["bant"] = pd.cut(saat, [8, 11, 14, 18.5], labels=["sabah (08–11)", "öğle (11–14)", "akşamüstü (14–18)"], right=False)
    bt = d.groupby("bant", observed=True).agg(n=("G", "size"), G=("G", "median"), K=("K", "median"), pm=("pm2_5", "median"),
                                              pa=("pa_epa", "median"))
    for b_, r in bt.iterrows():
        S.ekle(f"C.bant_{b_.split()[0]}", {"n": int(r.n), "G": round(r.G, 2), "K": round(r.K, 2), "atmotube_ortanca": round(r.pm, 1),
                                          "purpleair_epa_ortanca": round(r.pa, 1)}, "oran / µg/m³",
               "saha saat bandı: nokta sayısı, G ve K ortancası, Atmotube ham ve eş zamanlı PurpleAir (EPA) ortancası", Q)

    # ── Şekil 6: harita ──
    fc = kampus_geojson()
    cmap = LinearSegmentedColormap.from_list("iraksak", [IRAKSAK[0], IRAKSAK[1], IRAKSAK[2]])
    norm = LogNorm(vmin=0.5, vmax=2.0)
    fig = plt.figure(figsize=(7.5, 4.6))
    axa = fig.add_axes([0.0, 0.30, 0.30, 0.62])
    axb = fig.add_axes([0.32, 0.30, 0.67, 0.62])
    cax = fig.add_axes([0.40, 0.215, 0.50, 0.025])
    axa.set_anchor("N")
    axb.set_anchor("N")
    ZX, ZY = (150, 620), (-745, -470)
    for ax, zoom in ((axa, False), (axb, True)):
        for _, pts in poligonlar(fc, "yol"):
            ax.add_patch(MPoly(pts, closed=True, fc="#f1f0ec", ec="none", zorder=1))
        for f, pts in poligonlar(fc, "bina"):
            ax.add_patch(MPoly(pts, closed=True, fc="#dcdad3", ec="#a9a79f", lw=0.4, zorder=2))
        for (cx, cy), r in hucre.iterrows():
            ax.add_patch(Rectangle((cx * CS, cy * CS), CS, CS, fc=cmap(norm(np.clip(r.G, 0.5, 2.0))), ec="white", lw=0.4,
                                   zorder=3))
        if zoom:
            for f, pts in poligonlar(fc, "bina"):   # bina sınırları hücrelerin üstünde, ince
                ax.add_patch(MPoly(pts, closed=True, fc="none", ec="#7d7b74", lw=0.5, zorder=4))
            for (cx, cy), r in sicak.iterrows():
                ax.add_patch(Rectangle((cx * CS, cy * CS), CS, CS, fc="none", ec=MUREKKEP, lw=1.3, zorder=5))
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    axa.set_xlim(-720, 960)
    axa.set_ylim(-920, 720)
    axa.add_patch(Rectangle((ZX[0], ZY[0]), ZX[1] - ZX[0], ZY[1] - ZY[0], fc="none", ec=MUREKKEP, lw=0.9, zorder=5))
    axa.set_title("(a) Kampüs: ölçüm kapsamı", loc="left", fontsize=10)
    axa.text(ZX[0] - 20, ZY[1] + 25, "(b)'deki alan", fontsize=7.5, ha="right", color=IKINCIL)
    axa.plot([-650, -450], [-860, -860], color=MUREKKEP, lw=1.5)
    axa.text(-550, -840, "200 m", ha="center", fontsize=7.5)
    axa.annotate("K", xy=(880, 680), xytext=(880, 560), ha="center", fontsize=8,
                 arrowprops=dict(arrowstyle="-|>", color=MUREKKEP, lw=0.8))
    axb.set_xlim(*ZX)
    axb.set_ylim(*ZY)
    axb.set_title("(b) Ölçüm yoğun alan: 25 m hücrelerde göreli indeks G", loc="left", fontsize=10)
    axb.plot([ZX[0] + 15, ZX[0] + 115], [ZY[0] + 15, ZY[0] + 15], color=MUREKKEP, lw=1.5)
    axb.text(ZX[0] + 65, ZY[0] + 22, "100 m", ha="center", fontsize=7.5)
    # bina etiketleri (yakınlaştırılmış panel)
    etiket = {"Kimya ve Çevre Mühendisliği Bölümü": ("Kimya ve Çevre\nMüh. Bölümü", (0, -62)), "Güzide Kafe": ("Güzide Kafe", (-48, -40)),
              "SUMER": ("SUMER\n(PurpleAir)", (8, -48)), "Kütüphane": ("Kütüphane", (-6, 30)), "BİM": ("BİM", (-6, -30)),
              "Yer ve Deniz Bilimleri Enstitüsü": ("Yer ve Deniz\nBil. Enst.", (88, -6))}
    for f, pts in poligonlar(fc, "bina"):
        n_ = (f["properties"].get("name") or "").strip()
        if n_ in etiket:
            t_, (dx, dy) = etiket.pop(n_)
            cxm, cym = pts[:, 0].mean(), pts[:, 1].mean()
            axb.annotate(t_, xy=(cxm, cym), xytext=(cxm + dx, cym + dy), fontsize=7.5, ha="center", va="center", color=MUREKKEP,
                         zorder=6, arrowprops=dict(arrowstyle="-", color=IKINCIL, lw=0.5, shrinkA=0, shrinkB=2))
    sicak_set = set(sicak.index)
    for kod, konum, r in sicak_liste:
        cx, cy = r.name
        if (cx, cy + 1) in sicak_set:     # üstünde başka sıcak hücre varsa etiket alta
            axb.text(cx * CS + CS / 2, cy * CS - 3, kod, ha="center", va="top", fontsize=7.5, fontweight="bold",
                     color=MUREKKEP, zorder=6)
        else:
            axb.text(cx * CS + CS / 2, cy * CS + CS + 3, kod, ha="center", va="bottom", fontsize=7.5, fontweight="bold",
                     color=MUREKKEP, zorder=6)
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal")
    tk = [0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0]
    cb.set_ticks(tk)
    cb.set_ticklabels([tr(t, 2).rstrip("0").rstrip(",") for t in tk])
    cb.ax.minorticks_off()
    cb.set_label("G (hücre ortancası) · kalın çerçeve: sıcak hücre, G ≥ 1,25", fontsize=8)
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha ölçümleri (27–30 Nisan 2026, 12 oturum, ham PM₂.₅); bina poligonları campus.geojson.\n"
                "G = nokta PM₂.₅ / kendi oturumunun ortancası. Yalnızca ≥ 2 oturum ve ≥ 10 ölçüm içeren 25 m hücreler çizilmiştir;\n"
                "tekil yürüyüş izi gösterilmez. Yerel metrik düzlem, kuzey yukarı.")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil06_harita.png"))
    plt.close(fig)

    # ── Şekil 7: göreli indeksler (orman grafiği) ──
    kisa = {"Kimya ve Çevre Mühendisliği Bölümü": "Kimya ve Çevre Müh. Böl."}
    satir = []
    for k, r in bina_uy.iterrows():
        satir.append((f"{kisa.get(r.ad, r.ad)} (bina)", r))
    satir.append(("Bina dışı (yol, açık alan)", dz))
    for kod, konum, r in sicak_liste:
        satir.append((f"{kod}: {konum}", r))
    fig, ax = plt.subplots(figsize=(7.5, 4.9))
    y = np.arange(len(satir))[::-1].astype(float)
    ara = len(bina_uy) + 1          # binalar + bina dışı | sıcak hücreler
    y[ara:] -= 0.6
    for yi, (et, r) in zip(y, satir):
        ax.plot([r.G_lo, r.G_hi], [yi + 0.14, yi + 0.14], color=KATEGORIK[0], lw=1.6, solid_capstyle="round", zorder=3)
        ax.plot(r.G, yi + 0.14, "o", color=KATEGORIK[0], ms=6.5, mec="white", mew=1.2, zorder=4)
        ax.plot(r.G_PA, yi, "s", color=KATEGORIK[1], ms=5.5, mec="white", mew=1.0, zorder=4)
        ax.plot(r.K, yi - 0.14, "D", color=KATEGORIK[2], ms=5.0, mec="white", mew=1.0, zorder=4)
        ax.text(5.0, yi, f"{int(r.n)} nokta · {int(r.oturum)} oturum", va="center", fontsize=7.5, color=IKINCIL)
    ax.set_yticks(y, [s_[0] for s_ in satir])
    ax.axhline((y[ara - 1] + y[ara]) / 2, color=TABAN, lw=0.8)
    ax.text(0.41, y[0] + 0.62, "Binalar ve bina dışı", fontsize=8, color=IKINCIL, va="bottom")
    ax.text(0.41, y[ara] + 0.62, "Sıcak hücreler (25 m, G ≥ 1,25)", fontsize=8, color=IKINCIL, va="bottom")
    ax.set_xscale("log")
    ax.set_xlim(0.4, 4.8)
    ax.set_xticks([0.5, 0.67, 1, 1.25, 2, 3, 4], ["0,5", "0,67", "1", "1,25", "2", "3", "4"])
    ax.minorticks_off()
    ax.axvline(1.0, color=GRI, lw=0.9, zorder=1)
    ax.axvline(SICAK, color=MUREKKEP, lw=0.8, zorder=1)
    ax.set_ylim(y.min() - 0.7, y.max() + 1.0)
    ax.set_xlabel("oran (logaritmik eksen; dikey çizgiler 1 ve 1,25)")
    ax.set_title("Göreli indeksler: binalar ve sıcak hücreler", loc="left")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=KATEGORIK[0], marker="o", lw=1.6, ms=6, label="G: oturum ortancasına göre (%95 GA)"),
         Line2D([], [], color=KATEGORIK[1], marker="s", lw=0, ms=5.5, label="G_PA: saatlik PurpleAir'e göre düzeltilmiş"),
         Line2D([], [], color=KATEGORIK[2], marker="D", lw=0, ms=5, label="K: Atmotube / düzeltilmiş PurpleAir")]
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.01, 0.20), ncol=2, frameon=False, fontsize=8)
    fig.subplots_adjust(left=0.30, right=0.80, top=0.93, bottom=0.30)
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha ölçümleri (27–30 Nisan 2026, 12 oturum, ham PM₂.₅); PurpleAir PA-II (SUMER çatısı) 2 dk ve saatlik.\n"
                "GA: oturum düzeyinde bootstrap (2000 yineleme). Bina: içinde ya da sınırına ≤ 15 m; yalnızca ≥ 2 oturum ve ≥ 10 nokta.")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil07_gorel_indeks.png"))
    plt.close(fig)

    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("C tamam:", len(S.d), "sayı")
    print(hucre.sort_values("G", ascending=False).round(2).head(8).to_string())
    print(bina_uy.round(2).to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
