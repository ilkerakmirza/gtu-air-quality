"""3.5 Senaryolar — kampüste geçen zaman dış ortamda geçseydi (uygulamanın maruziyet modeli, maruziyet_yontemi.md).

Kullanım: python3 -I f_senaryo.py <ham klasörü> <rapor klasörü>
Model (her satır): C = P̄ × R × F;  D = C × IR × t;  TWA = Σ(C·t)/Σt.  R = 1 (kampüs geneli).
P̄: o günün saatlik düzeltilmiş PurpleAir değerlerinden dakika ağırlıklı ortalama (uygulamadaki pOver ile aynı; ayrıca
uygulamanın tüm günler profili P[h] ile de hesaplanır).
Gerçekçi senaryo = uygulamanın varsayılan satırları (maruziyet.js → DEFAULT):
  09:00–12:00 iç, kapalı pencere (F 0,5), oturma (IR 0,25) · 12:00–13:00 açık hava (F 1), tempolu yürüme (IR 1,56)
  · 13:00–17:00 iç, kapalı pencere, oturma.  Tamamen dış ortam: aynı saat ve etkinlikler, F = 1.
Günler: tam gün (≥ 18 saat), hafta içi, 06:00–19:00 arasındaki 13 saatin hepsi ölçülmüş; 1 Mayıs – 12 Ekim.
Üretir: sekiller/sekil14_senaryo.png; sayilar.json'a 'F.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, virgul_eksen, F, F_ARALIK, IR, IR_P95, KATEGORIK, GRI, MUREKKEP,  # noqa: E402
                   IKINCIL, DEVICE_COLOR, uygulama_ile_esles)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

Q = "Q1 (PurpleAir saatlik, paCorrect) + maruziyet.js (ENV, ACT, DEFAULT)"
GERCEKCI = [("09:00", "12:00", "closed", "sit"), ("12:00", "13:00", "out", "walk"), ("13:00", "17:00", "closed", "sit")]


def dk(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def p_ort(P, s, e):
    """maruziyet.js → pOver: satırın saatlerine düşen profil değeri (dakika ağırlıklı)."""
    top = w = 0.0
    m = s
    while m < e:
        h = m // 60
        nxt = min(e, (h + 1) * 60)
        top += P[h % 24] * (nxt - m)
        w += nxt - m
        m = nxt
    return top / w


def hesap(P, satirlar, f_ust=None, ir_ust=None):
    """(TWA, D, satır dozları). f_ust/ir_ust: ortam/etkinlik → değer sözlükleri (duyarlılık için)."""
    fd = dict(F, **(f_ust or {}))
    ird = dict(IR, **(ir_ust or {}))
    top_ct = top_t = D = 0.0
    dozlar = []
    for s, e, env, act in satirlar:
        t = (dk(e) - dk(s)) / 60
        c = p_ort(P, dk(s), dk(e)) * 1.0 * fd[env]
        d_ = c * ird[act] * t
        top_ct += c * t
        top_t += t
        D += d_
        dozlar.append(d_)
    return top_ct / top_t, D, dozlar


def disari(satirlar):
    return [(s, e, "out", a) for s, e, _, a in satirlar]


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    df = veri.pa_saatlik(ham)
    v = df.dropna(subset=["pm"])
    gun = veri.gunluk(df)
    tam = set(gun[gun.tam].index)
    P_gun = {k: dict(zip(g.saat, g.pm)) for k, g in v.groupby("gun")}
    uygun = []
    for k in sorted(P_gun):
        hg = pd.Timestamp(k).weekday()
        if k in tam and hg < 5 and all(h in P_gun[k] for h in range(6, 19)):
            uygun.append(k)
    S.ekle("F.gun", len(uygun), "gün", "senaryo günleri: tam gün, hafta içi, 06:00–19:00 saatlerinin hepsi ölçülmüş", Q)
    rows = []
    for k in uygun:
        P = P_gun[k]
        tr_, dr_, doz_r = hesap(P, GERCEKCI)
        to_, do_, _ = hesap(P, disari(GERCEKCI))
        rows.append({"gun": k, "twa_r": tr_, "D_r": dr_, "twa_o": to_, "D_o": do_, "yuruyus_payi": doz_r[1] / dr_,
                     "sabah": np.mean([P[h] for h in (6, 7, 8)]), "aksam": np.mean([P[h] for h in (16, 17, 18)])})
    t = pd.DataFrame(rows).set_index("gun")
    t["oran_twa"] = t.twa_o / t.twa_r
    t["oran_D"] = t.D_o / t.D_r
    sira = t.sort_values("twa_o")
    tip = sira.index[(len(sira) - 1) // 2]
    temiz, kotu = sira.index[0], sira.index[-1]
    secili = [("en temiz gün", temiz), ("tipik gün (ortanca)", tip), ("en kötü gün", kotu)]
    for ad, k in secili:
        r = t.loc[k]
        S.ekle(f"F.{ad.split()[0]}_{ad.split()[1]}", {
            "tarih": k, "TWA_gercekci": round(r.twa_r, 2), "TWA_dis": round(r.twa_o, 2), "D_gercekci_ug": round(r.D_r, 2),
            "D_dis_ug": round(r.D_o, 2), "Dis_Ic_TWA": round(r.oran_twa, 2), "Dis_Ic_D": round(r.oran_D, 2),
            "yuruyus_saatinin_doz_payi_yuzde": round(r.yuruyus_payi * 100, 1)},
            "µg/m³ · µg · oran", f"{ad}: günler 09–17 dış ortam TWA'sına göre sıralanır; ortanca = ({len(t)}−1)/2. sıradaki gün", Q)
    for c_, ad, b in [("twa_r", "TWA_gercekci", "µg/m³"), ("twa_o", "TWA_dis", "µg/m³"), ("D_r", "D_gercekci", "µg"), ("D_o", "D_dis", "µg"),
                      ("oran_twa", "Dis_Ic_TWA", "oran"), ("oran_D", "Dis_Ic_D", "oran"), ("yuruyus_payi", "yuruyus_doz_payi", "oran")]:
        S.ekle(f"F.dagilim_{ad}", {"ortanca": round(float(t[c_].median()), 3), "en_kucuk": round(float(t[c_].min()), 3),
                                    "en_buyuk": round(float(t[c_].max()), 3)}, b, f"{len(t)} senaryo gününde dağılım", Q)

    # Uygulamanın profili (tüm günlerin saatlik ortalaması; maruziyet.js → buildModel P)
    Papp = v.groupby("saat").pm.mean().to_dict()
    a_r = hesap(Papp, GERCEKCI)
    a_o = hesap(Papp, disari(GERCEKCI))
    S.ekle("F.uygulama_profili", {"TWA_gercekci": round(a_r[0], 2), "TWA_dis": round(a_o[0], 2), "D_gercekci_ug": round(a_r[1], 2),
                                  "D_dis_ug": round(a_o[1], 2), "Dis_Ic_TWA": round(a_o[0] / a_r[0], 2), "Dis_Ic_D": round(a_o[1] / a_r[1], 2)},
           "µg/m³ · µg · oran", "uygulamanın P profiliyle (1 Mayıs – 12 Ekim tüm geçerli saatlerin saat ortalaması) aynı senaryolar", Q)

    # Duyarlılık (tipik gün)
    P = P_gun[tip]
    taban = hesap(P, GERCEKCI)
    dis = hesap(P, disari(GERCEKCI))
    varyant = [("Temel: kapalı pencere F 0,5", {}, {}),
               ("Kapalı pencere F 0,3", {"closed": F_ARALIK["closed"][0]}, {}),
               ("Kapalı pencere F 0,75", {"closed": F_ARALIK["closed"][1]}, {}),
               ("Mekanik havalandırma F 0,25", {"closed": F["mech"]}, {}),
               ("Açık pencere F 0,8", {"closed": F["vent"]}, {}),
               ("Ölçülen K: Kimya binası 0,65", {"closed": 0.65}, {}),
               ("Solunum hızı %95 (0,39 / 2,28)", {}, {"sit": IR_P95["sit"], "walk": IR_P95["walk"]})]
    duy = []
    for ad, fu, iu in varyant:
        twa_, D_, _ = hesap(P, GERCEKCI, fu, iu)
        twa_o, D_o, _ = hesap(P, disari(GERCEKCI), fu, iu)
        duy.append((ad, twa_, D_, twa_o, D_o))
        S.ekle(f"F.duyarlilik_{ad}", {"TWA": round(twa_, 2), "D_ug": round(D_, 2), "D_dis_ug": round(D_o, 2), "Dis_Ic_D": round(D_o / D_, 2)},
               "µg/m³ · µg · oran", f"tipik gün ({tip}) için duyarlılık: {ad}", Q)

    # Saat seçimi: sabah 06–09 / akşamüstü 16–19
    fark = t.sabah - t.aksam
    S.ekle("F.sabah_ortanca", round(float(t.sabah.median()), 2), "µg/m³", "06:00–09:00 penceresinin günlük ortalaması, günler arası ortanca", Q)
    S.ekle("F.aksam_ortanca", round(float(t.aksam.median()), 2), "µg/m³", "16:00–19:00 penceresinin günlük ortalaması, ortanca", Q)
    S.ekle("F.sabah_aksam_oran_ortanca", round(float((t.sabah / t.aksam).median()), 2), "oran", "sabah / akşamüstü oranının ortancası", Q)
    S.ekle("F.sabah_kotu_gun_payi", round(float((fark > 0).mean() * 100), 1), "%", "sabah penceresinin akşamüstünden yüksek olduğu günlerin payı", Q)
    S.ekle("F.yuruyus_1sa_sabah", round(float(t.sabah.median() * IR["walk"]), 1), "µg", "1 saat tempolu yürüme (1,56 m³/sa), sabah penceresi ortanca düzeyinde", Q)
    S.ekle("F.yuruyus_1sa_aksam", round(float(t.aksam.median() * IR["walk"]), 1), "µg", "aynısı akşamüstü penceresinde", Q)
    S.ekle("F.spor_1sa_sabah", round(float(t.sabah.median() * IR["sport"]), 1), "µg", "1 saat spor (3,0 m³/sa), sabah ortanca düzeyinde", Q)
    S.ekle("F.spor_1sa_aksam", round(float(t.aksam.median() * IR["sport"]), 1), "µg", "1 saat spor, akşamüstü ortanca düzeyinde", Q)

    # ── Şekil 14 (v1.1: Şekil 11) ──
    fig = plt.figure(figsize=(7.5, 7.6))
    konum = {"a": [0.09, 0.62, 0.38, 0.32], "b": [0.60, 0.62, 0.38, 0.32], "c": [0.30, 0.17, 0.30, 0.34], "d": [0.73, 0.17, 0.25, 0.34]}
    c_r, c_o = KATEGORIK[0], KATEGORIK[1]
    for k_, (col_r, col_o, baslik, birim) in enumerate([("twa_r", "twa_o", "(a) Zaman ağırlıklı ortalama (09–17)", "µg/m³"),
                                                         ("D_r", "D_o", "(b) Solunan PM₂.₅ (8 saat)", "µg")]):
        ax = fig.add_axes(konum["ab"[k_]])
        x = np.arange(3)
        vr = [t.loc[g_, col_r] for _, g_ in secili]
        vo = [t.loc[g_, col_o] for _, g_ in secili]
        ax.bar(x - 0.19, vr, width=0.36, color=c_r, label="gerçekçi (7 sa iç + 1 sa dış)")
        ax.bar(x + 0.19, vo, width=0.36, color=c_o, label="tamamen dış ortam")
        for xi, a_, b_ in zip(x, vr, vo):
            ax.text(xi - 0.19, a_ + max(vo) * 0.02, tr(a_), ha="center", fontsize=7.5)
            ax.text(xi + 0.19, b_ + max(vo) * 0.02, tr(b_), ha="center", fontsize=7.5)
        ax.set_xticks(x, [f"{ad.split(' (')[0]}\n{pd.Timestamp(g_).strftime('%d.%m')}" for ad, g_ in secili], fontsize=8)
        ax.set_ylabel(birim)
        ax.set_ylim(0, max(vo) * 1.15)
        ax.set_title(baslik, loc="left", fontsize=10)
        virgul_eksen(ax)
        if k_ == 0:
            ax.legend(frameon=False, fontsize=7.6, loc="upper left")
    ax = fig.add_axes(konum["c"])
    y = np.arange(len(duy))[::-1]
    for yi, (ad, twa_, D_, twa_o, D_o) in zip(y, duy):
        ax.barh(yi, D_, height=0.55, color=c_r if yi != y[0] else "#1c5cab")
        ax.text(D_ + 0.6, yi, tr(D_), va="center", fontsize=7.5)
    ax.axvline(dis[1], color=c_o, lw=1.2, alpha=0.9, zorder=0)
    ax.text(dis[1] - 0.8, y[-1] - 0.75, f"tamamen dış ortam (temel IR): {tr(dis[1])}", fontsize=7.2, ha="right", va="center",
            color=MUREKKEP)
    ax.set_ylim(y[-1] - 1.1, y[0] + 0.5)
    ax.set_yticks(y, [d_[0] for d_ in duy], fontsize=7.6)
    ax.set_xlabel("solunan PM₂.₅, gerçekçi senaryo (µg)")
    ax.set_title(f"(c) Duyarlılık: tipik gün ({pd.Timestamp(tip).strftime('%d.%m')})", loc="left", fontsize=10)
    ax.set_xlim(0, max(dis[1], max(d_[2] for d_ in duy)) * 1.22)
    ax.grid(axis="y", visible=False)
    virgul_eksen(ax, "x")
    ax = fig.add_axes(konum["d"])
    for xi, (col, ad) in enumerate([("sabah", "sabah\n06:00–09:00"), ("aksam", "akşamüstü\n16:00–19:00")]):
        vals = t[col].values
        q25, q50, q75 = np.percentile(vals, [25, 50, 75])
        jit = (np.random.default_rng(1).random(len(vals)) - 0.5) * 0.3
        ax.plot(xi + jit, vals, "o", ms=2.6, color=DEVICE_COLOR["purpleair"], alpha=0.45)
        ax.add_patch(plt.Rectangle((xi - 0.22, q25), 0.44, q75 - q25, fc="none", ec=MUREKKEP, lw=1.0))
        ax.plot([xi - 0.22, xi + 0.22], [q50, q50], color=MUREKKEP, lw=1.8)
        ax.text(xi + 0.27, q50, f"ortanca\n{tr(q50)}", fontsize=7.4, va="center", color=MUREKKEP)
    ax.set_xticks([0, 1], ["sabah\n06:00–09:00", "akşamüstü\n16:00–19:00"], fontsize=8)
    ax.set_xlim(-0.5, 1.75)
    ax.set_ylim(0, min(60, float(t[["sabah", "aksam"]].max().max()) * 1.05))
    ax.set_ylabel("PM₂.₅ (µg/m³)")
    ax.set_title("(d) Açık hava saati", loc="left", fontsize=10)
    ax.text(0.99, 0.97, f"günlerin %{tr((fark > 0).mean() * 100, 0)}'inde\nsabah daha yüksek", transform=ax.transAxes, ha="right",
            va="top", fontsize=7.6, color=MUREKKEP)
    ax.grid(axis="x", visible=False)
    virgul_eksen(ax)
    kaynak_notu(fig, "Model: C = P̄ × R × F, D = C × IR × t (maruziyet_yontemi.md); P̄: o günün US EPA düzeltmeli saatlik PurpleAir değerleri; R = 1.\n"
                     f"Günler: 1 Mayıs – 12 Ekim 2026, hafta içi tam günler (n = {len(t)}); günler 09–17 dış ortam ortalamasına göre sıralanmıştır.\n"
                     "(c) Koyu çubuk: temel varsayım. (d) Her nokta bir gün; kutu: çeyrekler arası; kalın çizgi: ortanca.\n"
                     "Değerler yalnızca kampüste geçen 8 saat içindir; WHO 24 saatlik değeriyle karşılaştırılmaz.")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil14_senaryo.png"))
    plt.close(fig)

    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("F tamam:", len(S.d), "sayı")
    print(t.loc[[temiz, tip, kotu]].round(2).to_string())
    print(t.describe().round(2).to_string())
    for d_ in duy:
        print([d_[0]] + [round(x, 2) for x in d_[1:]])
    print("app", [round(x, 2) for x in a_r[:2]], [round(x, 2) for x in a_o[:2]])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
