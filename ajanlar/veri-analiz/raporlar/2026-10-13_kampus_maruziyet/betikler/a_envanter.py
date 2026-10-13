"""2.1 Veri envanteri ve kapsam zaman çizelgesi; 3.6 iç ortam (CO₂) veri denetimi.

Kullanım: python3 -I a_envanter.py <ham klasörü> <rapor klasörü>
Üretir: sekiller/sekil01_kapsam.png; sayilar.json'a 'A.*' ve 'G.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, DEVICE_COLOR, GRI, MUREKKEP, IKINCIL, uygulama_ile_esles)  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SON = pd.Timestamp("2026-10-12T21:00:00Z")


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    tum = veri.pa_saatlik(ham, tum=True)
    df = veri.pa_saatlik(ham)
    g = veri.gunluk(tum)
    d, _, _ = veri.saha(ham)
    gt, a, c = veri.q3(ham)
    a = a[a.t < SON]

    S.ekle("A.pa_kayit_2dk", int(df.n.sum()), "kayıt", "1 Mayıs – 12 Ekim (TR) PurpleAir 2 dk kayıt sayısı (Q1'deki saatlik n toplamı)", "Q1")
    S.ekle("A.pa_saat", int(df.pm.notna().sum()), "saat", "aynı dönemde düzeltilmiş değeri olan saat", "Q1")
    S.ekle("A.pa_tam_gun", int(g[(g.index >= "2026-05-01") & g.tam].shape[0]), "gün", "aynı dönemde tam gün (≥ 18 saat)", "Q1")
    takvim = pd.date_range("2026-05-01", "2026-10-12", freq="D").strftime("%Y-%m-%d")
    S.ekle("A.pa_takvim_gun", int(len(takvim)), "gün", "1 Mayıs – 12 Ekim takvim günü", "")
    eksik = [k for k in takvim if k not in g.index or not g.loc[k, "tam"]]
    S.ekle("A.pa_tam_olmayan_gunler", ", ".join(eksik), "", "tam gün olmayan takvim günleri (kesinti ya da < 18 saat)", "Q1")
    S.ekle("A.pa_nisan_saat", int(tum[(tum.tl < veri.BASLA)].pm.notna().sum()), "saat",
           "27–30 Nisan'da veritabanındaki eski biçimli kayıtlardan saatlik değer (analiz dönemine alınmadı)", "Q1")
    S.ekle("A.cf1_payi", round(float((df.yontem == "cf1").mean() * 100), 2), "%", "analiz dönemindeki saatlerin asıl yöntemle (cf_1) düzeltilen payı", "Q1")
    S.ekle("A.saha_oturum", int(d.oturum.nunique()), "oturum", "saha oturumu (27–30 Nisan)", "Q2")
    S.ekle("A.saha_nokta", int(len(d)), "nokta", "saha noktası (konumlu)", "Q2")
    S.ekle("A.saha_ekip", int(d.ekip.nunique()), "ekip", "saha ekibi (A, B, C)", "Q2")
    S.ekle("A.saha_oturum_ekip", d.groupby("ekip").oturum.nunique().to_dict(), "oturum", "ekip başına oturum", "Q2")
    S.ekle("A.atp_kayit", int(len(a)), "kayıt", "Atmotube canlı kayıt (13 Ekim 00:00'a kadar)", "Q3 atp_canli")
    S.ekle("A.atp_cihaz_kayit", a.groupby("cihaz").size().to_dict(), "kayıt", "cihaz başına canlı kayıt", "Q3 atp_canli")
    S.ekle("A.atp_ilk_son", f"{a.tl.min():%d.%m.%Y} – {a.tl.max():%d.%m.%Y}", "", "canlı kayıtların ilk ve son günü (TR)", "Q3 atp_canli")
    S.ekle("A.atp_gun", int(a.tl.dt.strftime('%Y-%m-%d').nunique()), "gün", "en az bir canlı kaydı olan gün", "Q3 atp_canli")

    # ── CO₂ denetimi ──
    c = c.sort_values("t").reset_index(drop=True)
    ayni = c[["co2_ppm", "temperature_c", "humidity_pct"]].diff().abs().sum(axis=1) == 0
    donuk = (c.co2_ppm == 400) & (c.temperature_c == 27.2) & (c.humidity_pct == 49)
    ilk_donuk = c.loc[donuk.idxmax(), "tl"] if donuk.any() else None
    S.ekle("G.co2_kayit", int(len(c)), "kayıt", "iç ortam CO₂ kayıtları (tek cihaz)", "Q3 co2")
    S.ekle("G.co2_donem", f"{c.tl.min():%d.%m.%Y %H:%M} – {c.tl.max():%d.%m.%Y %H:%M}", "", "ilk ve son kayıt (TR)", "Q3 co2")
    S.ekle("G.co2_gun", int(c.tl.dt.date.nunique()), "gün", "en az bir kaydı olan gün", "Q3 co2")
    S.ekle("G.co2_400_payi", round(float((c.co2_ppm == 400).mean() * 100), 2), "%", "CO₂ = 400 ppm olan kayıtların payı", "Q3 co2")
    S.ekle("G.co2_donuk_kayit", int(donuk.sum()), "kayıt", "CO₂ 400 ppm, sıcaklık 27,2 °C ve nem %49'un birlikte tekrarlandığı kayıt", "Q3 co2")
    S.ekle("G.co2_donuk_basi", f"{ilk_donuk:%d.%m.%Y %H:%M}" if ilk_donuk is not None else "", "", "aynı değer üçlüsünün ilk görüldüğü kayıt (TR)", "Q3 co2")
    S.ekle("G.co2_degisken_kayit", int((~donuk).sum()), "kayıt", "değer üçlüsü farklı olan kayıt (gerçek ölçüm olabilecek)", "Q3 co2")
    S.ekle("G.co2_degisken_aralik", f"{int(c[~donuk].co2_ppm.min())}–{int(c[~donuk].co2_ppm.max())}", "ppm", "bu kayıtların CO₂ aralığı", "Q3 co2")
    S.ekle("G.co2_onceki_ile_ayni", int(ayni.sum()), "kayıt", "bir önceki kayıtla üç değeri de aynı olan kayıt", "Q3 co2")
    S.ekle("G.co2_1000_ustu", int((c.co2_ppm > 1000).sum()), "kayıt", "1000 ppm'i aşan kayıt (veri donmuş olduğundan yorumlanamaz)", "Q3 co2")

    # ── Şekil 1: kapsam zaman çizelgesi ──
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    gunler = pd.date_range("2026-04-27", "2026-10-12", freq="D", tz=veri.TZ)
    satir = {"PurpleAir\n(SUMER çatısı)": 3.0, "Saha oturumları\n(Atmotube, 12)": 2.0, "Atmotube canlı\n(ATP-1…5)": 1.0}
    # PurpleAir: günlük geçerli saat sayısı → çubuk yüksekliği
    for k, r in g.iterrows():
        x = pd.Timestamp(k, tz=veri.TZ)
        renk = DEVICE_COLOR["purpleair"] if r.tam else GRI
        ax.bar(x + pd.Timedelta("12h"), r.n / 24 * 0.75, bottom=3.0 - 0.375, width=0.9, color=renk, lw=0)
    sg = d.groupby(d.tl.dt.floor("D")).oturum.nunique()
    for x, n in sg.items():
        ax.bar(x + pd.Timedelta("12h"), 0.75 * n / 3, bottom=2.0 - 0.375, width=0.9, color=DEVICE_COLOR["atmotube"], lw=0)
    ag = a.groupby(a.tl.dt.floor("D")).size()
    for x, n in ag.items():
        ax.bar(x + pd.Timedelta("12h"), 0.75 * min(n, 40) / 40, bottom=1.0 - 0.375, width=0.9, color=DEVICE_COLOR["atmotube"],
               alpha=0.7, lw=0)
    ax.set_yticks(list(satir.values()), list(satir.keys()), fontsize=8)
    ax.set_ylim(0.4, 3.6)
    ax.set_xlim(gunler[0] - pd.Timedelta("1D"), gunler[-1] + pd.Timedelta("2D"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(tz=veri.TZ))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: veri.AY_KISA.get(mdates.num2date(x, tz=veri.TZ).month, "")))
    ax.grid(axis="y", visible=False)
    ax.set_title("Veri kapsamı (27 Nisan – 12 Ekim 2026, Türkiye günü)", loc="left")
    ax.text(pd.Timestamp("2026-07-05", tz=veri.TZ), 3.45, "5–7 Tem\nkesinti", fontsize=6.8, ha="center", color=IKINCIL)
    ax.text(pd.Timestamp("2026-10-04", tz=veri.TZ), 3.45, "2–6 Eki\nkesinti", fontsize=6.8, ha="center", color=IKINCIL)
    ax.text(pd.Timestamp("2026-05-03", tz=veri.TZ), 1.9, "27–30 Nisan", fontsize=6.8, ha="left", color=IKINCIL)
    kaynak_notu(fig, "PurpleAir: çubuk yüksekliği = günün geçerli saat sayısı (mavi: tam gün ≥ 18 saat; gri: eksik gün). Saha: gün başına oturum (en çok 3).\n"
                     "Atmotube canlı: gün başına kayıt (40'ta kesilmiş).")
    fig.subplots_adjust(top=0.91, bottom=0.18, left=0.19, right=0.98)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil01_kapsam.png"))
    plt.close(fig)
    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("A/G tamam:", len(S.d), "sayı")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
