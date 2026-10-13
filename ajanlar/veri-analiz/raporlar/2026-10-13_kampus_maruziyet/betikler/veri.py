"""Veri yükleyiciler: sorgu çıktılarını (Q1–Q3) ve depodaki PurpleAir arşivini analiz tablolarına çevirir.

Analiz dönemi: PurpleAir için 1 Mayıs 2026 00:00 – 13 Ekim 2026 00:00 (Türkiye saati). 27–30 Nisan'daki eski biçimli
veritabanı kayıtları yalnızca saha oturumlarıyla eşleştirmede, sensörün kendi arşivinden (CSV) okunarak kullanılır.
"""
import os

import ortak  # noqa: F401  (site ayarı numpy/pandas'tan önce)
from ortak import (TZ, REPO, oku_tablo, duzelt, epa_cf1, kanal_uyumlu, xy, binalar, bina_bul, kampus_ici, ekip_esleme)

import numpy as np
import pandas as pd

BASLA = pd.Timestamp("2026-05-01 00:00", tz=TZ)
BITIS = pd.Timestamp("2026-10-13 00:00", tz=TZ)
GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AY_ADLARI = {5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim"}
AY_KISA = {4: "Nis", 5: "May", 6: "Haz", 7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki"}
PA_ARSIV = os.path.join(REPO, "docs", "veri", "purpleair_229263_2dk_2026-04-27_2026-10-06.csv")


def pa_saatlik(ham, tum=False):
    """Q1 → saatlik tablo; her satır uygulamadaki gibi düzeltilir (paCorrect). Varsayılan: yalnızca analiz dönemi."""
    rows = oku_tablo(os.path.join(ham, "Q1.txt"))
    df = pd.DataFrame(rows)
    res = [duzelt(r) for r in rows]
    df["pm"] = [x[0] for x in res]
    df["yontem"] = [x[1] for x in res]
    df["kanal_ok"] = [x[2] for x in res]
    df["t"] = pd.to_datetime(df.t_utc, utc=True)
    df["tl"] = df.t.dt.tz_convert(TZ)
    df["gun"] = df.tl.dt.strftime("%Y-%m-%d")
    df["saat"] = df.tl.dt.hour
    df["hg"] = df.tl.dt.weekday          # 0 = Pazartesi
    df["ay"] = df.tl.dt.month
    df["ham"] = df.pm2_5
    if not tum:
        df = df[(df.tl >= BASLA) & (df.tl < BITIS)].copy()
    return df


def gunluk(df):
    """Uygulamanın günlük ortalaması (who.js → dailyMeans): geçerli saatlik değerlerin ortalaması; tam gün ≥ 18 saat."""
    g = df.dropna(subset=["pm"]).groupby("gun").agg(n=("pm", "size"), ort=("pm", "mean"), enb=("pm", "max"),
                                                   rh=("humidity_pct", "mean"))
    g["tam"] = g.n >= 18
    return g


def pa_2dk_nisan():
    """27–30 Nisan PurpleAir 2 dk kayıtları (sensör arşivi, cf_1 dahil): ham (cf_atm) ve düzeltilmiş (asıl yöntem)."""
    pa = pd.read_csv(PA_ARSIV)
    pa["t"] = pd.to_datetime(pa.time_stamp, utc=True).astype("datetime64[ns, UTC]")
    pa = pa[(pa.t >= "2026-04-26T21:00:00Z") & (pa.t < "2026-04-30T21:00:00Z")].copy()
    pa["ham"] = (pa["pm2.5_atm_a"] + pa["pm2.5_atm_b"]) / 2
    pa["kanal_ok"] = [kanal_uyumlu(a, b) for a, b in zip(pa["pm2.5_cf_1_a"], pa["pm2.5_cf_1_b"])]
    pa["epa"] = [epa_cf1((a + b) / 2, h) if ok is not False else np.nan
                 for a, b, h, ok in zip(pa["pm2.5_cf_1_a"], pa["pm2.5_cf_1_b"], pa.humidity, pa.kanal_ok)]
    pa.loc[pa.kanal_ok == False, "ham"] = np.nan   # noqa: E712  (kanal kuralı ham değere de uygulanır)
    pa["tl"] = pa.t.dt.tz_convert(TZ)
    return pa.sort_values("t").reset_index(drop=True)


def saha(ham):
    """Q2 → saha noktaları + bina eşleştirmesi + eş zamanlı PurpleAir (2 dk en yakın kayıt, ±3 dk; saatlik ham ortalama)."""
    rows = oku_tablo(os.path.join(ham, "Q2.txt"))
    d = pd.DataFrame(rows)
    # Ad ön ekinin md5 özeti → app.js → PEOPLE etiketi ("Saha ekibi A/B/C"); ad hiçbir yerde açık yazılmaz.
    es = ekip_esleme()
    d["ekip"] = d.onek.map(lambda h: es.get(h, ""))
    if not d.ekip.str.startswith("Saha ekibi ").all():
        raise SystemExit("Bazı oturumlar app.js → PEOPLE listesindeki saha ekiplerine eşlenemedi.")
    d["ekip"] = d.ekip.str.replace("Saha ekibi ", "", regex=False)
    d = d.drop(columns=["onek"])
    d["t"] = pd.to_datetime(d.ep, unit="s", utc=True).astype("datetime64[ns, UTC]")
    d["tl"] = d.t.dt.tz_convert(TZ)
    d["kampus_ici"] = [kampus_ici(a, b) for a, b in zip(d.lat, d.lon)]
    d = d[d.kampus_ici].copy()
    d["x"], d["y"] = zip(*[xy(a, b) for a, b in zip(d.lat, d.lon)])
    blds = binalar()
    res = [bina_bul(blds, a, b) for a, b in zip(d.lat, d.lon)]
    d["gk"] = [r[0] for r in res]
    d["yakin"] = [r[1] for r in res]
    pa = pa_2dk_nisan()
    d = d.sort_values("t")
    d = pd.merge_asof(d, pa[["t", "epa", "ham"]].rename(columns={"epa": "pa_epa", "ham": "pa_ham"}), on="t",
                      direction="nearest", tolerance=pd.Timedelta("3min"))
    saatlik = pa.groupby(pa.tl.dt.floor("h")).agg(pa_ham_saat=("ham", "mean"), pa_epa_saat=("epa", "mean"))
    d["saat_bas"] = d.tl.dt.floor("h")
    d = d.merge(saatlik, left_on="saat_bas", right_index=True, how="left")
    # Örnekleme aralığı (oturumun ortanca adımı: 1 ya da 2 dk); her kayıt bu süreyi temsil eder
    d = d.sort_values(["oturum", "t"]).reset_index(drop=True)
    d["adim_s"] = d.groupby("oturum").ep.transform(lambda s: float(np.median(np.diff(s.values))) if len(s) > 1 else 60.0)
    return d, blds, pa


def q3(ham):
    t = oku_tablo(os.path.join(ham, "Q3.txt"))
    g = pd.DataFrame(t["gunluk_tepe"])
    a = pd.DataFrame(t["atp_canli"])
    a["t"] = pd.to_datetime(a.ep, unit="s", utc=True)
    a["tl"] = a.t.dt.tz_convert(TZ)
    c = pd.DataFrame(t["co2"])
    c["t"] = pd.to_datetime(c.ep, unit="s", utc=True)
    c["tl"] = c.t.dt.tz_convert(TZ)
    return g, a, c
