"""3.1 Ne zaman kötü? — PurpleAir (US EPA düzeltmeli, Türkiye saati) zamansal çözümleme.

Kullanım: python3 -I b_zaman.py <ham klasörü (Q1.txt…)> <rapor klasörü>
Üretir: sekiller/sekil02_saat_gun.png, sekil03_aylik_dongu.png, sekil04_en_kotu_saatler.png, sekil05_epizot_nem.png;
        sayilar.json'a 'B.*' anahtarları.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, virgul_eksen, kaynak_notu, hki, HKI_PM25, DEVICE_COLOR, SIRALI_MAVI, GRI,  # noqa: E402
                   MUREKKEP, IKINCIL, KATEGORIK, bosluk_kir, uygulama_ile_esles)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

KAYNAK = "Kaynak: PurpleAir PA-II (SUMER çatısı), US EPA düzeltmeli saatlik PM₂.₅ (µg/m³); Türkiye saati."


def spearman(a, b):
    m = a.notna() & b.notna()
    return float(np.corrcoef(a[m].rank(), b[m].rank())[0, 1])


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    from matplotlib.colors import LinearSegmentedColormap
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    df = veri.pa_saatlik(ham)
    v = df.dropna(subset=["pm"]).copy()
    g = veri.gunluk(df)
    tam = g[g.tam]
    ms = tam[(tam.index >= "2026-05-01") & (tam.index < "2026-10-01")]
    Q1 = "Q1 (PurpleAir saatlik) → paCorrect; Türkiye saati"

    # ── temel sayılar ──
    S.ekle("B.saat_gecerli", int(len(v)), "saat", "1 Mayıs 00:00 – 13 Ekim 00:00 (TR) arasında düzeltilmiş değeri olan saat", Q1)
    S.ekle("B.saat_kanal_disi", int(df.pm.isna().sum()), "saat", "A/B kanal kuralıyla dışarıda kalan saat", Q1)
    S.ekle("B.tam_gun", int(len(tam)), "gün", "≥ 18 geçerli saati olan Türkiye günü, 1 Mayıs – 12 Ekim", Q1)
    S.ekle("B.tam_gun_mayis_eylul", int(len(ms)), "gün", "Mayıs–Eylül tam günleri", Q1)
    S.ekle("B.ort_mayis_eylul", round(float(ms.ort.mean()), 2), "µg/m³", "Mayıs–Eylül tam günlerinin günlük ortalamalarının ortalaması", Q1)
    S.ekle("B.asim_mayis_eylul", int((ms.ort > 15).sum()), "gün", "Mayıs–Eylül'de günlük ortalaması 15 µg/m³'ü aşan tam gün", Q1)
    S.ekle("B.ort_tum", round(float(tam.ort.mean()), 2), "µg/m³", "1 Mayıs – 12 Ekim tam günlerinin ortalaması", Q1)
    S.ekle("B.asim_tum", int((tam.ort > 15).sum()), "gün", "1 Mayıs – 12 Ekim, günlük ortalaması > 15 µg/m³ olan tam gün", Q1)
    for ay in range(5, 11):
        x = tam[tam.index.str[5:7] == f"{ay:02d}"]
        S.ekle(f"B.ay_{ay:02d}_ort", round(float(x.ort.mean()), 2), "µg/m³", f"{veri.AY_ADLARI[ay]}: tam günlerin ortalaması (n = {len(x)})", Q1)
        S.ekle(f"B.ay_{ay:02d}_tam_gun", int(len(x)), "gün", f"{veri.AY_ADLARI[ay]} tam gün sayısı", Q1)
        S.ekle(f"B.ay_{ay:02d}_asim", int((x.ort > 15).sum()), "gün", f"{veri.AY_ADLARI[ay]}: günlük ort. > 15 µg/m³", Q1)

    vms = v[v.ay <= 9]
    dms = vms.groupby("saat").pm.mean()
    dall = v.groupby("saat").pm.mean()
    S.ekle("B.dongu_mayis_eylul_enb_saat", int(dms.idxmax()), "saat (TR)", "Mayıs–Eylül tüm geçerli saatler: saatlik ortalama profilin en yüksek saati", Q1)
    S.ekle("B.dongu_mayis_eylul_enb", round(float(dms.max()), 2), "µg/m³", "aynı profilin en yüksek değeri", Q1)
    S.ekle("B.dongu_mayis_eylul_enk_saat", int(dms.idxmin()), "saat (TR)", "aynı profilin en düşük saati", Q1)
    S.ekle("B.dongu_mayis_eylul_enk", round(float(dms.min()), 2), "µg/m³", "aynı profilin en düşük değeri", Q1)
    S.ekle("B.dongu_tum_enb", round(float(dall.max()), 2), "µg/m³", f"1 Mayıs – 12 Ekim profili, en yüksek saat {int(dall.idxmax()):02d}:00", Q1)
    S.ekle("B.dongu_tum_enk", round(float(dall.min()), 2), "µg/m³", f"1 Mayıs – 12 Ekim profili, en düşük saat {int(dall.idxmin()):02d}:00", Q1)

    # sabah / akşamüstü ve hafta içi / sonu
    v["hs"] = np.where(v.hg >= 5, "sonu", "ici")
    gunduz = v[(v.saat >= 10) & (v.saat < 16)]
    S.ekle("B.gunduz_hafta_ici_medyan", round(float(gunduz[gunduz.hs == "ici"].pm.median()), 2), "µg/m³", "10:00–16:00, hafta içi saatlerin ortancası", Q1)
    S.ekle("B.gunduz_hafta_sonu_medyan", round(float(gunduz[gunduz.hs == "sonu"].pm.median()), 2), "µg/m³", "10:00–16:00, hafta sonu saatlerin ortancası", Q1)
    sab = v[(v.saat >= 6) & (v.saat < 10)]
    S.ekle("B.sabah_hafta_ici_medyan", round(float(sab[sab.hs == "ici"].pm.median()), 2), "µg/m³", "06:00–10:00, hafta içi ortanca", Q1)
    S.ekle("B.sabah_hafta_sonu_medyan", round(float(sab[sab.hs == "sonu"].pm.median()), 2), "µg/m³", "06:00–10:00, hafta sonu ortanca", Q1)

    # günlük en yüksek saatin zamanı
    pk = v.loc[v.groupby("gun").pm.idxmax()]
    pk = pk[pk.gun.isin(tam.index)]
    S.ekle("B.gunluk_tepe_00_09_payi", round(float(((pk.saat >= 0) & (pk.saat <= 9)).mean() * 100), 1), "%",
           "tam günlerde günün en yüksek saatlik değerinin 00:00–09:59 arasına düştüğü günlerin payı", Q1)
    S.ekle("B.gunluk_tepe_06_07_payi", round(float(pk.saat.isin([6, 7]).mean() * 100), 1), "%",
           "tam günlerde günün en yüksek saatinin 06 ya da 07 olduğu günlerin payı", Q1)

    # HKİ sınıf payları (saatlik değerler; gösterge)
    sinif = v.pm.apply(lambda x: hki(x)[1])
    for ad in ["İyi", "Orta", "Hassas", "Sağlıksız"]:
        S.ekle(f"B.saat_hki_{ad}", round(float((sinif == ad).mean() * 100), 2), "%",
               f"geçerli saatlerin HKİ '{ad}' aralığındaki payı (saatlik değer, 0,1'e kesilerek; gösterge)", Q1)
    S.ekle("B.saat_hassas_ustu", int((v.pm.apply(lambda x: np.floor(x * 10) / 10) >= 35.5).sum()), "saat", "saatlik değeri ≥ 35,5 µg/m³ (Hassas ve üstü) saat sayısı", Q1)
    S.ekle("B.saat_hassas_ustu_ekim", int(((v.pm.apply(lambda x: np.floor(x * 10) / 10) >= 35.5) & (v.ay == 10)).sum()), "saat",
           "aynı sayının Ekim'e düşen kısmı", Q1)

    # ── Şekil 2: saat × haftanın günü (ortanca) ──
    med = v.pivot_table(index="saat", columns="hg", values="pm", aggfunc="median")
    cnt = v.pivot_table(index="saat", columns="hg", values="pm", aggfunc="size")
    S.ekle("B.isi_hucre_n_min", int(cnt.min().min()), "saat", "ısı haritasında hücre başına en az gözlem", Q1)
    S.ekle("B.isi_hucre_n_max", int(cnt.max().max()), "saat", "ısı haritasında hücre başına en çok gözlem", Q1)
    S.ekle("B.isi_enb", round(float(med.max().max()), 2), "µg/m³", "saat × gün ortancalarının en yükseği", Q1)
    S.ekle("B.isi_enk", round(float(med.min().min()), 2), "µg/m³", "saat × gün ortancalarının en düşüğü", Q1)
    imax = med.stack().idxmax()
    imin = med.stack().idxmin()
    S.ekle("B.isi_enb_hucre", f"{veri.GUN_ADLARI[int(imax[1])]} {int(imax[0]):02d}:00", "", "en yüksek hücre (gün, saat)", Q1)
    S.ekle("B.isi_enk_hucre", f"{veri.GUN_ADLARI[int(imin[1])]} {int(imin[0]):02d}:00", "", "en düşük hücre (gün, saat)", Q1)

    cmap = LinearSegmentedColormap.from_list("sirali_mavi", SIRALI_MAVI)
    fig = plt.figure(figsize=(7.5, 6.4))
    ax = fig.add_axes([0.10, 0.12, 0.52, 0.80])
    axp = fig.add_axes([0.66, 0.12, 0.20, 0.80], sharey=ax)
    cax = fig.add_axes([0.90, 0.30, 0.022, 0.50])
    im = ax.imshow(med.values, aspect="auto", cmap=cmap, vmin=6, vmax=18, origin="upper",
                   extent=(-0.5, 6.5, 23.5, -0.5), interpolation="nearest")
    ax.set_xticks(range(7), veri.GUN_ADLARI)
    ax.set_yticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
    ax.grid(False)
    ax.set_xlabel("Haftanın günü")
    ax.set_ylabel("Saat (Türkiye saati)")
    ax.set_title("Saat × gün: ortanca PM₂.₅", loc="left")
    for (h, d_), txt in [(imax, "en yüksek"), (imin, "en düşük")]:
        val = med.loc[h, d_]
        ax.text(d_, h, tr(val), ha="center", va="center", fontsize=8,
                color="white" if val > 13 else MUREKKEP, fontweight="bold")
    # sağda: saatlik ortalama ve ortanca profil (tüm günler)
    prof_ort = v.groupby("saat").pm.mean()
    prof_med = v.groupby("saat").pm.median()
    q25 = v.groupby("saat").pm.quantile(0.25)
    q75 = v.groupby("saat").pm.quantile(0.75)
    c = DEVICE_COLOR["purpleair"]
    axp.fill_betweenx(prof_med.index, q25.values, q75.values, color=c, alpha=0.12, lw=0)
    axp.plot(prof_ort.values, prof_ort.index, color=c, lw=1.4)
    axp.plot(prof_med.values, prof_med.index, color=GRI, lw=1.2)
    axp.set_xlim(0, 26)
    axp.set_title("Günlük profil", loc="left")
    axp.set_xlabel("µg/m³")
    axp.tick_params(labelleft=False)
    axp.text(prof_ort.max() + 0.6, prof_ort.idxmax(), f"ortalama\n{tr(prof_ort.max())} ({int(prof_ort.idxmax()):02d}:00)",
             fontsize=7.5, va="center", color=MUREKKEP)
    axp.text(prof_med.loc[3] - 0.6, 3, "ortanca", fontsize=7.5, ha="right", va="center", color=IKINCIL)
    axp.text(q75.loc[12] + 0.5, 12.5, "çeyrekler\narası", fontsize=7, color=IKINCIL, va="center")
    virgul_eksen(axp, "x")
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("ortanca PM₂.₅ (µg/m³)", fontsize=8.5)
    cb.ax.tick_params(labelsize=8)
    cb.ax.axhline(12.0, color=MUREKKEP, lw=1.0)
    cb.ax.text(-0.35, 12.0, "HKİ İyi\nsınırı ▸", transform=cb.ax.get_yaxis_transform(), fontsize=6.8, va="center",
               ha="right", color=IKINCIL)
    cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: tr(x, 0)))
    kaynak_notu(fig, KAYNAK + f"\n1 Mayıs – 12 Ekim 2026; {tr(len(v), 0)} geçerli saat; hücre başına {int(cnt.min().min())}–{int(cnt.max().max())} gözlem.")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil02_saat_gun.png"))
    plt.close(fig)

    # ── Şekil 3: aylara göre günlük döngü (küçük çoklu) ──
    fig, axs = plt.subplots(2, 3, figsize=(7.5, 5.0), sharex=True, sharey=True)
    ref = vms.groupby("saat").pm.mean()
    for ax, ay in zip(axs.flat, range(5, 11)):
        s = v[v.ay == ay]
        m_ = s.groupby("saat").pm.mean()
        a25 = s.groupby("saat").pm.quantile(0.25)
        a75 = s.groupby("saat").pm.quantile(0.75)
        ax.plot(ref.index, ref.values, color=GRI, lw=1.0, label="Mayıs–Eylül saatlik ortalaması")
        ax.fill_between(m_.index, a25.values, a75.values, color=c, alpha=0.12, lw=0, label="ayın çeyrekler arası")
        ax.plot(m_.index, m_.values, color=c, lw=1.4, label="ayın saatlik ortalaması")
        tg = tam[tam.index.str[5:7] == f"{ay:02d}"]
        baslik = veri.AY_ADLARI[ay] + (" (1–12)" if ay == 10 else "")
        ax.set_title(baslik, loc="left", fontsize=10)
        ax.text(0.98, 0.95, f"ay ort. {tr(tg.ort.mean())}\n{len(tg)} tam gün", transform=ax.transAxes, ha="right", va="top",
                fontsize=7.5, color=IKINCIL)
        ax.set_xticks([0, 6, 12, 18, 23], ["00", "06", "12", "18", "23"])
        ax.set_xlim(0, 23)
        ax.set_ylim(0, 50)
    for ax in axs[1]:
        ax.set_xlabel("Saat (TR)")
    for ax in axs[:, 0]:
        ax.set_ylabel("PM₂.₅ (µg/m³)")
    h_, l_ = axs[0, 0].get_legend_handles_labels()
    fig.legend(h_[::-1], l_[::-1], loc="upper left", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.005, 0.95))
    fig.suptitle("Aylara göre günlük döngü", x=0.01, y=0.985, ha="left", fontsize=11.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 0.90))
    kaynak_notu(fig, KAYNAK + "\nGri çizgi her panelde aynıdır (Mayıs–Eylül). Ay ortalaması = tam günlerin (≥ 18 saat) günlük ortalamalarının ortalaması.")
    fig.savefig(os.path.join(cikti, "sekiller", "sekil03_aylik_dongu.png"))
    plt.close(fig)
    for ay in range(5, 11):
        s = v[v.ay == ay].groupby("saat").pm.mean()
        S.ekle(f"B.dongu_ay_{ay:02d}_enb_saat", int(s.idxmax()), "saat (TR)", f"{veri.AY_ADLARI[ay]} saatlik ortalama profilinin en yüksek saati", Q1)
        S.ekle(f"B.dongu_ay_{ay:02d}_enb", round(float(s.max()), 2), "µg/m³", f"{veri.AY_ADLARI[ay]} profilinin en yüksek değeri", Q1)
        S.ekle(f"B.dongu_ay_{ay:02d}_enk", round(float(s.min()), 2), "µg/m³", f"{veri.AY_ADLARI[ay]} profilinin en düşük değeri (saat {int(s.idxmin()):02d})", Q1)

    # ── Şekil 4: en kötü %5 saat ──
    esik = float(v.pm.quantile(0.95))
    w = v[v.pm >= esik]
    esik2 = float(vms.pm.quantile(0.95))
    w2 = vms[vms.pm >= esik2]
    S.ekle("B.p95_esik", round(esik, 2), "µg/m³", "1 Mayıs – 12 Ekim geçerli saatlerin 95. yüzdeliği (en kötü %5 eşiği)", Q1)
    S.ekle("B.p95_saat_sayisi", int(len(w)), "saat", "eşiği aşan ya da eşit saat sayısı", Q1)
    S.ekle("B.p95_ekim_payi", round(float((w.ay == 10).mean() * 100), 1), "%", "en kötü %5 saatin Ekim'e düşen payı", Q1)
    S.ekle("B.p95_mayis_payi", round(float((w.ay == 5).mean() * 100), 1), "%", "en kötü %5 saatin Mayıs'a düşen payı", Q1)
    S.ekle("B.p95_mayis_eylul_esik", round(esik2, 2), "µg/m³", "yalnızca Mayıs–Eylül saatleriyle 95. yüzdelik", Q1)
    oran = (w.groupby("saat").size() / v.groupby("saat").size()).reindex(range(24)).fillna(0) * 100
    oran2 = (w2.groupby("saat").size() / vms.groupby("saat").size()).reindex(range(24)).fillna(0) * 100
    sab_pay = float(w.saat.between(3, 9).mean() * 100)
    S.ekle("B.p95_03_09_payi", round(sab_pay, 1), "%", "en kötü %5 saatin 03:00–09:59 arasına düşen payı (tüm dönem)", Q1)
    S.ekle("B.p95_03_09_payi_mayis_eylul", round(float(w2.saat.between(3, 9).mean() * 100), 1), "%",
           "aynı pay, yalnızca Mayıs–Eylül (eşik Mayıs–Eylül'ün 95. yüzdeliği)", Q1)
    S.ekle("B.p95_14_19_payi", round(float(w.saat.between(14, 19).mean() * 100), 1), "%", "en kötü %5 saatin 14:00–19:59 arasına düşen payı", Q1)
    S.ekle("B.p95_saat_orani_enb", round(float(oran.max()), 1), "%", f"bir saatin en kötü %5'e girme oranının en yükseği (saat {int(oran.idxmax()):02d})", Q1)
    gun_oran = (w.groupby("hg").size() / v.groupby("hg").size()).reindex(range(7)).fillna(0) * 100
    ay_say = w.groupby("ay").size().reindex(range(5, 11)).fillna(0)
    ay_oran = (w.groupby("ay").size() / v.groupby("ay").size()).reindex(range(5, 11)).fillna(0) * 100

    fig = plt.figure(figsize=(7.5, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.55, wspace=0.28)
    ax = fig.add_subplot(gs[0, :])
    ax.bar(np.arange(24) - 0.2, oran.values, width=0.38, color=c, label="1 Mayıs – 12 Ekim (eşik " + tr(esik) + " µg/m³)")
    ax.bar(np.arange(24) + 0.2, oran2.values, width=0.38, color=GRI, label="yalnız Mayıs–Eylül (eşik " + tr(esik2) + " µg/m³)")
    ax.axhline(5, color=MUREKKEP, lw=0.7)
    ax.text(23.6, 5.3, "%5 (eşit dağılım)", ha="right", fontsize=7.5, color=IKINCIL)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_xlim(-0.7, 23.7)
    ax.set_xlabel("Saat (Türkiye saati)")
    ax.set_ylabel("o saatin en kötü %5'e\ngirme oranı (%)")
    ax.set_title("(a) En kötü %5 saat: günün saatine göre", loc="left")
    ax.legend(loc="upper right", frameon=False)
    virgul_eksen(ax)
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.bar(range(7), gun_oran.values, width=0.6, color=c)
    ax2.axhline(5, color=MUREKKEP, lw=0.7)
    ax2.set_xticks(range(7), veri.GUN_ADLARI)
    ax2.set_ylabel("oran (%)")
    ax2.set_title("(b) Haftanın gününe göre", loc="left")
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.bar(range(6), ay_oran.values, width=0.6, color=c)
    ax3.axhline(5, color=MUREKKEP, lw=0.7)
    ax3.set_xticks(range(6), [veri.AY_KISA[a] for a in range(5, 11)])
    ax3.set_ylabel("oran (%)")
    ax3.set_title("(c) Aya göre", loc="left")
    for i, (o_, n_) in enumerate(zip(ay_oran.values, ay_say.values)):
        ax3.text(i, max(o_, 5) + 1.5, f"{int(n_)} sa", ha="center", fontsize=7.5, color=IKINCIL)
    ax3.set_ylim(0, max(ay_oran.values) * 1.18)
    for a_ in (ax2, ax3):
        virgul_eksen(a_)
    kaynak_notu(fig, KAYNAK + " 1 Mayıs – 12 Ekim 2026.\nOran = o gruptaki saatlerin en kötü %5'e giren payı; (c)'de çubuk üstü: en kötü %5'teki saat sayısı.")
    fig.subplots_adjust(top=0.93, bottom=0.17, left=0.11, right=0.98)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil04_en_kotu_saatler.png"))
    plt.close(fig)

    # ── epizot ve nem ──
    e = v[(v.gun >= "2026-10-08") & (v.gun <= "2026-10-12")]
    S.ekle("B.epizot_saat", int(len(e)), "saat", "8–12 Ekim geçerli saat", Q1)
    S.ekle("B.epizot_ort", round(float(e.pm.mean()), 2), "µg/m³", "8–12 Ekim saatlik değerlerin ortalaması", Q1)
    S.ekle("B.epizot_enb", round(float(e.pm.max()), 2), "µg/m³", "8–12 Ekim en yüksek saatlik değer", Q1)
    ie = e.loc[e.pm.idxmax()]
    S.ekle("B.epizot_enb_zaman", f"{ie.gun} {int(ie.saat):02d}:00", "", "en yüksek saatin başlangıcı (TR)", Q1)
    S.ekle("B.epizot_hassas_payi", round(float((e.pm.apply(lambda x: np.floor(x * 10) / 10) >= 35.5).mean() * 100), 1), "%",
           "8–12 Ekim saatlerinin ≥ 35,5 µg/m³ (Hassas ve üstü) payı", Q1)
    S.ekle("B.epizot_saglksiz_saat", int((e.pm.apply(lambda x: np.floor(x * 10) / 10) >= 55.5).sum()), "saat",
           "8–12 Ekim'de ≥ 55,5 µg/m³ (Sağlıksız) saat", Q1)
    for gun_, r_ in g.loc["2026-10-08":"2026-10-12"].iterrows():
        S.ekle(f"B.epizot_gun_{gun_}", round(float(r_.ort), 2), "µg/m³", f"{gun_} günlük ortalama ({int(r_.n)} saat)", Q1)
    yuksek = tam[tam.ort > 20]
    S.ekle("B.yuksek_gunler_20", ", ".join(f"{k} ({tr(x)})" for k, x in yuksek.ort.items()), "µg/m³",
           "günlük ortalaması 20 µg/m³'ü aşan tam günler", Q1)
    S.ekle("B.nem_spearman_tum", round(spearman(v.pm, v.humidity_pct), 2), "", "saatlik PM₂.₅ ile nem, Spearman sıra korelasyonu (tüm saatler)", Q1)
    vv = v.dropna(subset=["humidity_pct"]).copy()
    vv["pm_d"] = vv.pm - vv.groupby("gun").pm.transform("mean")
    vv["rh_d"] = vv.humidity_pct - vv.groupby("gun").humidity_pct.transform("mean")
    vv["pm_a"] = vv.pm - vv.groupby(["ay", "saat"]).pm.transform("median")
    vv["rh_a"] = vv.humidity_pct - vv.groupby(["ay", "saat"]).humidity_pct.transform("median")
    S.ekle("B.nem_spearman_gun_ici", round(spearman(vv.pm_d, vv.rh_d), 2), "", "gün içi sapmalar (günlük ortalamadan) arasında Spearman", Q1)
    S.ekle("B.nem_spearman_anomali", round(spearman(vv.pm_a, vv.rh_a), 2), "", "ay × saat ortancasından sapmalar arasında Spearman (günlük döngü çıkarılmış)", Q1)
    gd = tam.dropna(subset=["rh"])
    S.ekle("B.nem_spearman_gunluk", round(spearman(gd.ort, gd.rh), 2), "", "tam günlerin günlük ortalamaları arasında Spearman", Q1)
    S.ekle("B.nem_75_ustu_saat", int((v.humidity_pct > 75).sum()), "saat", "saatlik ortalama nemi %75'in üstünde olan geçerli saat (PurpleAir gövde içi nem)", Q1)
    S.ekle("B.nem_75_ustu_payi", round(float((v.humidity_pct > 75).mean() * 100), 2), "%", "aynı saatlerin payı", Q1)
    rh_saat = v.groupby("saat").humidity_pct.mean()
    S.ekle("B.nem_enb_saat", f"{int(rh_saat.idxmax()):02d}:00 ({tr(rh_saat.max(), 0)})", "%", "saatlik ortalama nemin en yüksek olduğu saat", Q1)
    S.ekle("B.nem_enk_saat", f"{int(rh_saat.idxmin()):02d}:00 ({tr(rh_saat.min(), 0)})", "%", "saatlik ortalama nemin en düşük olduğu saat", Q1)
    ek = df[(df.gun >= "2026-10-08") & (df.gun <= "2026-10-12")]
    S.ekle("B.epizot_sicaklik_aralik", f"{tr(ek.temperature_c.min())}–{tr(ek.temperature_c.max())}", "°C",
           "8–12 Ekim saatlik PurpleAir gövde içi sıcaklık aralığı (ortamdan ~4 °C yüksek okur)", Q1)

    fig = plt.figure(figsize=(7.5, 7.2))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.5, 0.75, 1.25], hspace=0.62)
    ax = fig.add_subplot(gs[0])
    ep = df[(df.tl >= pd.Timestamp("2026-10-06 12:00", tz=veri.TZ)) & (df.tl < veri.BITIS)].copy()
    for ilo, ihi, clo, chi, ad, renk in HKI_PM25[:4]:
        lo = 0 if clo == 0 else clo - 0.05
        hi = min(chi + 0.05, 95)
        ax.axhspan(lo, hi, color=renk, alpha=0.13, lw=0)
        ax.text(1.005, (lo + min(hi, 95)) / 2, ad, transform=ax.get_yaxis_transform(), fontsize=7.5, va="center",
                color=MUREKKEP)
    tx, ty = bosluk_kir(ep.tl, ep.pm)
    ax.plot(tx, ty, color=c, lw=1.3)
    for gun_, r_ in g.loc["2026-10-07":"2026-10-12"].iterrows():
        t0 = pd.Timestamp(gun_ + " 00:00", tz=veri.TZ)
        ax.hlines(r_.ort, t0, t0 + pd.Timedelta("24h"), color=MUREKKEP, lw=0.9)
        ek_ = "" if r_.n >= 18 else f" ({int(r_.n)} sa)"
        ax.text(t0 + pd.Timedelta("12h"), r_.ort + 2.0, tr(r_.ort) + ek_, ha="center", fontsize=7.5, color=MUREKKEP)
    ax.set_ylim(0, 90)
    ax.set_ylabel("PM₂.₅ (µg/m³)")
    ax.set_title("(a) 6–12 Ekim 2026: saatlik PM₂.₅ ve günlük ortalamalar (yatay çizgi)", loc="left")
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.DayLocator(tz=veri.TZ))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m", tz=veri.TZ))
    ax.annotate(f"en yüksek saat\n{tr(ie.pm)} µg/m³", xy=(ie.tl, ie.pm), xytext=(ie.tl - pd.Timedelta("40h"), 80),
                fontsize=7.5, arrowprops=dict(arrowstyle="-", color=IKINCIL, lw=0.7), color=MUREKKEP)
    ax.text(pd.Timestamp("2026-10-06 13:00", tz=veri.TZ), 70, "2 Eki 17:00 – 6 Eki 17:00\nsensör çevrimdışı", fontsize=7, color=IKINCIL)
    axr = fig.add_subplot(gs[1], sharex=ax)
    rx, ry = bosluk_kir(ep.tl, ep.humidity_pct)
    axr.plot(rx, ry, color=GRI, lw=1.2)
    axr.set_ylabel("Nem (%)")
    axr.set_ylim(20, 80)
    axr.set_title("(b) Aynı dönemde bağıl nem (PurpleAir gövde içi)", loc="left")
    axr.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m", tz=veri.TZ))
    ax3 = fig.add_subplot(gs[2])
    bins = [0, 30, 40, 50, 60, 70, 100]
    etik = ["≤30", "30–40", "40–50", "50–60", "60–70", ">70"]
    v["rhbin"] = pd.cut(v.humidity_pct, bins, labels=etik)
    bant = {"gece–sabah (00–09)": (0, 10), "gündüz (10–17)": (10, 18), "akşam (18–23)": (18, 24)}
    renk3 = [KATEGORIK[0], KATEGORIK[1], GRI]
    for (ad, (a_, b_)), rk in zip(bant.items(), renk3):
        s = v[(v.saat >= a_) & (v.saat < b_)]
        mm = s.groupby("rhbin", observed=False).pm.median()
        nn = s.groupby("rhbin", observed=False).pm.size()
        mm[nn < 20] = np.nan
        ax3.plot(range(len(etik)), mm.values, marker="o", ms=4.5, lw=1.3, color=rk, label=ad)
    ax3.set_xticks(range(len(etik)), etik)
    ax3.set_xlabel("Bağıl nem sınıfı (%)")
    ax3.set_ylabel("ortanca PM₂.₅ (µg/m³)")
    ax3.set_title("(c) Nem sınıfına göre ortanca PM₂.₅ (1 Mayıs – 12 Ekim)", loc="left")
    ax3.legend(frameon=False, loc="upper left", ncol=3, fontsize=8)
    ax3.set_ylim(0, 22)
    virgul_eksen(ax3)
    kaynak_notu(fig, KAYNAK + "\n(a) Renkli bantlar HKİ sınıf aralıklarıdır (24 saatlik tanım; saatlik değerde gösterge); veri boşlukları birleştirilmemiştir."
                     "\n(c) Yalnızca en az 20 saatlik nem sınıfları gösterilmiştir.")
    fig.subplots_adjust(top=0.95, bottom=0.145, left=0.11, right=0.92)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil05_epizot_nem.png"))
    plt.close(fig)

    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("B tamam:", len(S.d), "sayı")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
