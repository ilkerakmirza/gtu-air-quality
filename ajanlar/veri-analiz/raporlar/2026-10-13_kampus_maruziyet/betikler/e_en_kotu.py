"""3.4 En kötü durum — sabit sensörün (PurpleAir) her günkü en yüksek 15 ve 60 dakikalık kayan ortalaması.

Kullanım: python3 -I e_en_kotu.py <ham klasörü> <rapor klasörü>
Pencere hesapları SQL'de (Q3 → gunluk_tepe): 2 dk kayıtlar, US EPA düzeltmesi SQL'de, pencere tamamen aynı Türkiye günü
içinde, 15 dk için ≥ 6 kayıt, 60 dk için ≥ 23 kayıt. "Kampüs saatleri": pencere 08:00–18:00 içinde.
Yalnızca tam günler (Q1'e göre ≥ 18 geçerli saat). Kişisel tepeler d_kisisel.py ile aynı tanımla (saha oturumları).
Üretir: sekiller/sekil13_en_kotu.png; sayilar.json'a 'E.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, virgul_eksen, DEVICE_COLOR, GRI, MUREKKEP, IKINCIL, KATEGORIK,  # noqa: E402
                   HKI_PM25, uygulama_ile_esles)
from d_kisisel import kayan_enb  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

Q = "Q3 gunluk_tepe (SQL pencere fonksiyonları) + Q1 (tam gün)"


def kes(x):
    return np.floor(x * 10) / 10   # colorscale.js → hki ile aynı kesme


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    import matplotlib.dates as mdates
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    g, _, _ = veri.q3(ham)
    df = veri.pa_saatlik(ham)
    gun = veri.gunluk(df)
    g = g.set_index("gun").join(gun[["n", "ort", "tam", "enb"]].rename(columns={"n": "saat"}), how="left")
    t = g[g.tam == True].copy()   # noqa: E712
    S.ekle("E.gun", int(len(t)), "gün", "değerlendirilen tam gün (1 Mayıs – 12 Ekim)", Q)
    adlar = {"m15": "15 dk, tüm gün", "m60": "60 dk, tüm gün", "k15": "15 dk, kampüs saatleri (08–18)",
             "k60": "60 dk, kampüs saatleri (08–18)"}
    for col, ad in adlar.items():
        x = t[col]
        i = x.idxmax()
        S.ekle(f"E.{col}_ortanca", round(float(x.median()), 1), "µg/m³", f"günlük en yüksek kayan ortalama ({ad}): günler arası ortanca", Q)
        S.ekle(f"E.{col}_p95", round(float(x.quantile(0.95)), 1), "µg/m³", f"aynı ölçünün 95. yüzdeliği", Q)
        S.ekle(f"E.{col}_enb", round(float(x.max()), 1), "µg/m³", f"aynı ölçünün en yükseği", Q)
        S.ekle(f"E.{col}_enb_zaman", f"{i} {t.loc[i, col + '_t']}", "", f"en yüksek pencerenin bittiği gün ve saat (TR)", Q)
        S.ekle(f"E.{col}_hassas_gun", int((kes(x) >= 35.5).sum()), "gün", f"{ad}: en yüksek penceresi ≥ 35,5 µg/m³ olan gün (HKİ Hassas aralığı; gösterge)", Q)
        S.ekle(f"E.{col}_saglksiz_gun", int((kes(x) >= 55.5).sum()), "gün", f"{ad}: ≥ 55,5 µg/m³ olan gün (HKİ Sağlıksız aralığı; gösterge)", Q)
    S.ekle("E.tepe_ortalama_orani", round(float((t.m60 / t.ort).median()), 2), "oran", "günlük en yüksek 60 dk / günlük ortalama, günler arası ortanca", Q)
    S.ekle("E.tepe_ortalama_orani_kampus", round(float((t.k60 / t.ort).median()), 2), "oran", "kampüs saatleri en yüksek 60 dk / günlük ortalama, ortanca", Q)
    S.ekle("E.kampus_disi_tepe_payi", round(float((t.m60 > t.k60 * 1.0001).mean() * 100), 1), "%",
           "günün en yüksek 60 dk penceresinin kampüs saatleri dışında kaldığı günlerin payı", Q)
    h = t.m60_t.str[:2].astype(int)
    S.ekle("E.m60_saat_01_10_payi", round(float(h.between(1, 10).mean() * 100), 1), "%", "en yüksek 60 dk penceresinin 01:00–10:59 arasında bittiği günlerin payı", Q)
    S.ekle("E.m60_saat_mod", f"{int(h.mode().iloc[0]):02d}", "saat", "en yüksek 60 dk penceresinin en sık bittiği saat", Q)
    hk = t.k60_t.str[:2].astype(int)
    S.ekle("E.k60_bitis_09_payi", round(float((hk == 9).mean() * 100), 1), "%",
           "kampüs saatlerindeki en yüksek 60 dk penceresinin 09:00–09:59 arasında bittiği (yani 08:00–10:00 arasına düştüğü) günlerin payı", Q)
    S.ekle("E.kisa_olaylar", ", ".join(f"{k} (2 dk {tr(r.pm2dk_max)}, 15 dk {tr(r.m15)}, 60 dk {tr(r.m60)})"
                                       for k, r in t[t.pm2dk_max > 100].iterrows()), "µg/m³",
           "2 dk düzeltilmiş değeri 100 µg/m³'ü aşan günler: en yüksek 2 dk, 15 dk ve 60 dk", Q)
    S.ekle("E.m60_saat_max_fark", round(float((t.m60 - t.enb).median()), 2), "µg/m³", "en yüksek 60 dk kayan ortalama − en yüksek saatlik (saat başı) değer, ortanca", Q)

    # kişisel tepeler (saha)
    d, _, _ = veri.saha(ham)
    kis = []
    for o, gg in d.dropna(subset=["pm2_5"]).groupby("oturum"):
        adim = float(gg.adim_s.iloc[0]) / 60
        kis.append({"oturum": o, "m15": kayan_enb(gg.sort_values("t"), 15, adim)[0], "m60": kayan_enb(gg.sort_values("t"), 60, adim)[0],
                    "enb": float(gg.pm2_5.max())})
    kis = pd.DataFrame(kis).set_index("oturum")
    S.ekle("E.kisisel_m15_ortanca", round(float(kis.m15.median()), 1), "µg/m³", "saha oturumlarının en yüksek 15 dk kayan ortalamaları, ortanca (Atmotube ham)", "Q2")
    S.ekle("E.kisisel_m60_ortanca", round(float(kis.m60.median()), 1), "µg/m³", "saha oturumlarının en yüksek 60 dk kayan ortalamaları, ortanca (Atmotube ham)", "Q2")
    S.ekle("E.kisisel_m15_enb", round(float(kis.m15.max()), 1), "µg/m³", f"en yüksek 15 dk (Oturum {int(kis.m15.idxmax())})", "Q2")
    S.ekle("E.kisisel_m60_enb", round(float(kis.m60.max()), 1), "µg/m³", f"en yüksek 60 dk (Oturum {int(kis.m60.idxmax())})", "Q2")

    # ── Şekil 13 (v1.1: Şekil 10) ──
    from matplotlib.ticker import FuncFormatter
    fig = plt.figure(figsize=(7.5, 6.9))
    ax = fig.add_axes([0.09, 0.62, 0.89, 0.30])
    tt = pd.to_datetime(t.index).tz_localize(veri.TZ) + pd.Timedelta("12h")
    ax.bar(tt, t.ort, width=0.8, color="#d6d4cc", label="günlük ortalama")
    ax.plot(tt, t.m60, "o", ms=3.0, color=DEVICE_COLOR["purpleair"], label="en yüksek 60 dk (tüm gün)")
    ax.plot(tt, t.k60, "o", ms=3.0, mfc="none", mec=KATEGORIK[1], mew=0.9, label="en yüksek 60 dk (08–18)")
    ax.axhline(35.5, color=MUREKKEP, lw=0.7)
    ax.text(tt.min(), 37, "35,5 µg/m³: HKİ 'Hassas' aralığının başı (24 saatlik tanım; gösterge)", fontsize=7.2, color=IKINCIL)
    ax.set_ylim(0, 90)
    ax.set_ylabel("PM₂.₅ (µg/m³)")
    ax.xaxis.set_major_locator(mdates.MonthLocator(tz=veri.TZ))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: veri.AY_KISA.get(mdates.num2date(x, tz=veri.TZ).month, "")))
    ax.set_title("(a) Her tam günün ortalaması ve en kötü 60 dakikası", loc="left", fontsize=10, pad=18)
    ax.legend(loc="lower left", frameon=False, fontsize=7.8, ncol=3, bbox_to_anchor=(0, 0.98))
    i = t.m60.idxmax()
    ax.annotate(f"{tr(t.loc[i, 'm60'])} µg/m³ ({pd.Timestamp(i).strftime('%d.%m')}, {t.loc[i, 'm60_t']})",
                xy=(tt[list(t.index).index(i)], t.loc[i, "m60"]), xytext=(-18, 2), textcoords="offset points", fontsize=7.2,
                ha="right", va="center", color=MUREKKEP)
    virgul_eksen(ax)

    ax2 = fig.add_axes([0.29, 0.15, 0.44, 0.36])
    satir = [("PurpleAir · 15 dk · tüm gün", t.m15, DEVICE_COLOR["purpleair"]),
             ("PurpleAir · 60 dk · tüm gün", t.m60, DEVICE_COLOR["purpleair"]),
             ("PurpleAir · 15 dk · 08–18", t.k15, KATEGORIK[1]),
             ("PurpleAir · 60 dk · 08–18", t.k60, KATEGORIK[1]),
             ("Atmotube oturumları · 15 dk", kis.m15, DEVICE_COLOR["atmotube"]),
             ("Atmotube oturumları · 60 dk", kis.m60, DEVICE_COLOR["atmotube"])]
    for ilo, ihi, clo, chi, adh, renk in HKI_PM25[:4]:
        ax2.axvspan(max(clo, 3), min(chi, 160), color=renk, alpha=0.10, lw=0)
    y = np.arange(len(satir))[::-1]
    for yi, (ad, x, renk) in zip(y, satir):
        x = x.dropna()
        if ad.startswith("Atmotube"):
            ax2.plot(x.values, np.full(len(x), yi), "o", ms=3.6, color=renk, alpha=0.75)
            ax2.plot(x.median(), yi, "|", ms=14, mew=2.2, color=MUREKKEP)
            et = f"ortanca {tr(x.median())}\nen yüksek {tr(x.max())} ({len(x)} oturum)"
        else:
            lo, hi = x.quantile(0.05), x.quantile(0.95)
            ax2.plot([lo, hi], [yi, yi], color=renk, lw=1.6, solid_capstyle="round")
            ax2.plot(x.median(), yi, "o", ms=6, color=renk, mec="white", mew=1.0)
            ax2.plot(x.max(), yi, "x", ms=6, color=MUREKKEP, mew=1.3)
            et = f"ortanca {tr(x.median())} · %95 {tr(x.quantile(0.95))}\nen yüksek {tr(x.max())}"
        ax2.text(1.02, yi, et, transform=ax2.get_yaxis_transform(), fontsize=7.2, va="center", ha="left", color=MUREKKEP)
    ax2.set_yticks(y, [s_[0] for s_ in satir], fontsize=8)
    ax2.set_xscale("log")
    ax2.set_xlim(3, 165)
    ax2.set_xticks([5, 12, 20, 35.4, 55.4, 100], ["5", "12", "20", "35,4", "55,4", "100"])
    ax2.minorticks_off()
    ax2.set_ylim(-0.6, len(satir) - 0.4)
    ax2.set_xlabel("PM₂.₅ (µg/m³, logaritmik eksen)")
    ax2.set_title("(b) Günlük en kötü pencerelerin dağılımı", loc="left", fontsize=10)
    ax2.grid(axis="y", visible=False)
    kaynak_notu(fig, "Kaynak: PurpleAir PA-II (SUMER çatısı), 2 dk kayıtlar; US EPA düzeltmesi ve kayan ortalamalar SQL'de (Q3); 1 Mayıs – 12 Ekim 2026,\n"
                     f"{len(t)} tam gün. Pencere tamamen aynı Türkiye günü içinde; 08–18: pencere 08:00–18:00 arasında. (b) Nokta: ortanca; çizgi: %5–95;\n"
                     "×: en yüksek; zemin: HKİ sınıf aralıkları. Atmotube: 27–30 Nisan saha oturumları (ham; PurpleAir'le mutlak düzeyde karşılaştırılamaz).")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil13_en_kotu.png"))
    plt.close(fig)

    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("E tamam:", len(S.d), "sayı")
    print(t[["m15", "m15_t", "m60", "m60_t", "k15", "k15_t", "k60", "k60_t"]].sort_values("m60", ascending=False).head(8).to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
