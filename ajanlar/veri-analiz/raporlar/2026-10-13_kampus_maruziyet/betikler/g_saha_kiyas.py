"""3.4 Saha ölçümlerinin karşılaştırması (sürüm 1.2): gün, ölçümcü ve oturum düzeyinde kişisel / dış ortam oranı ve farkın etkenleri.

Kullanım: python3 -I g_saha_kiyas.py <ham klasörü> <rapor klasörü>
Girdi: Q2 (saha noktaları) + docs/veri PurpleAir arşivi (27–30 Nisan, 2 dk, US EPA düzeltmeli; veri.saha ile aynı eşleştirme, ±3 dk).

Tanımlar (karar_kaydi.md'de gerekçeleriyle):
  * Kayıt süresi Δt = oturumun örnekleme aralığı (1 ya da 2 dk). Yalnızca PM₂.₅ ve eş zamanlı PurpleAir değeri olan kayıtlar.
  * TWA = Σ c·Δt / Σ Δt; P = aynı kayıtların düzeltilmiş PurpleAir ortalaması (aynı ağırlık); K_TWA = Σ c·Δt / Σ P·Δt.
  * Solunan miktar D = Σ c·IR·Δt; IR: bina içi (poligon içi ya da ≤ 15 m) 0,25 m³/sa (oturma), bina dışı 1,56 m³/sa (tempolu
    yürüme) — uygulamanın varsayılan gününe koşut. K_D = D / Σ P·IR·Δt (aynı etkinlikle çatı havasında solunacak miktara oran).
    Duyarlılık: bina içi IR = 0,72 m³/sa (hafif etkinlik).
  * Belirsizlik: oturum içinde 30 dakikalık bloklarla blok bootstrap (Künsch, 1989), 2000 yineleme, %2,5–97,5 yüzdelikleri.
    Gün ve ölçümcü düzeyinde her oturumun blokları kendi içinde yeniden örneklenir.
  * Aynı gün farkı: en yüksek / en düşük (oran) ve en yüksek − en düşük (fark); ortak zaman penceresinde de (üç oturumun kesişimi).
  * Ayrıştırma: (1) 3 × 4 dengeli düzende log K_TWA ve log TWA için iki yönlü toplamsal varyans ayrıştırması (ölçümcü, gün, kalan);
    (2) aynı günün en yüksek ve en düşük K'li iki ölçümcüsü arasında Kitagawa (1955) ayrıştırması: K = Σ w_s K_s
    (s: Kimya binası, diğer binalar, bina dışı; w_s = Σ_s P·Δt / Σ P·Δt). ΔK = yer dağılımı etkisi + yerdeki düzey etkisi.
    Bir ölçümcüde boş olan katmanın K_s'si diğerininkine eşitlenir (o katmanın düzey etkisi 0).
  * Tepeler: en yüksek %10 kayıt (c'ye göre) hesaptan çıkarılarak K yeniden hesaplanır — yalnızca duyarlılık; veri ayıklanmaz.
Ani yükselmeler ayıklanmaz (kullanıcı kararı, 8 Ekim 2026).
KVKK: ölçümcüler "Ölçümcü A/B/C" (app.js → PEOPLE "Saha ekibi A/B/C"); ad, oturum adı ve koordinat yazılmaz; ölçümcü etiketiyle
dakikalık konum (bina içi/dışı zaman çizelgesi) verilmez — yalnızca oturum toplamı payları.
Üretir: sekiller/sekil10_gun_kisi.png, sekil11_bilesenler.png, sekil12_saat_gorel.png; sayilar.json'a 'S.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, virgul_eksen, DEVICE_COLOR, GRI, MUREKKEP, IKINCIL, IZGARA, IR,  # noqa: E402
                   TABAN, uygulama_ile_esles)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

Q = "Q2 (saha noktaları) + docs/veri PurpleAir arşivi (27–30 Nisan, 2 dk, US EPA düzeltmeli)"
# Ölçümcü renkleri (doğrulayıcı: PurpleAir #6380f0 ile birlikte açık zeminde geçti; yeşil–pembe CVD 7,7 → ikincil kodlama: işaret biçimi + harf)
RENK = {"A": "#eb6834", "B": "#c64f8d", "C": "#1baf7a"}
ISARET = {"A": "o", "B": "s", "C": "^"}
KISILER = ["A", "B", "C"]
BLOK = "30min"
NBOOT = 2000
IR_IC, IR_DIS = IR["sit"], IR["walk"]


def hazirla(ham):
    d, blds, pa = veri.saha(ham)
    e = d.dropna(subset=["pm2_5", "pa_epa"]).copy()
    e["dt"] = e.adim_s / 3600.0                                   # sa
    e["ic"] = e.gk.notna()                                        # bina poligonu içi ya da ≤ 15 m
    e["kimya"] = e.gk.fillna("").str.contains("Kimya")
    e["katman"] = np.where(e.kimya, "kimya", np.where(e.ic, "diger", "dis"))
    e["gun"] = e.tl.dt.strftime("%d.%m")
    e["kisi"] = e.ekip
    e["ir"] = np.where(e.ic, IR_IC, IR_DIS)
    e["ir_hafif"] = np.where(e.ic, IR["light"], IR_DIS)
    t0 = e.groupby("oturum").t.transform("min")
    e["blok"] = ((e.t - t0) // pd.Timedelta(BLOK)).astype(int)
    return d, e, pa


def ozet(x):
    """Bir kayıt kümesinin (oturum, gün, ölçümcü) özet büyüklükleri."""
    w = x.dt
    c, p = x.pm2_5, x.pa_epa
    out = {"kayit": len(x), "sure_sa": float(w.sum()), "twa": float((c * w).sum() / w.sum()),
           "P": float((p * w).sum() / w.sum()), "K": float((c * w).sum() / (p * w).sum()),
           "D": float((c * x.ir * w).sum()), "D_ref": float((p * x.ir * w).sum()),
           "K_D_hafif": float((c * x.ir_hafif * w).sum() / (p * x.ir_hafif * w).sum()),
           "dis_payi": float(w[~x.ic].sum() / w.sum() * 100), "kimya_payi": float(w[x.kimya].sum() / w.sum() * 100),
           "diger_payi": float(w[x.ic & ~x.kimya].sum() / w.sum() * 100)}
    out["K_D"] = out["D"] / out["D_ref"]
    out["D_saat"] = out["D"] / out["sure_sa"]
    for s in ("kimya", "diger", "dis"):
        m = x.katman == s
        out[f"K_{s}"] = float((c[m] * w[m]).sum() / (p[m] * w[m]).sum()) if m.any() else np.nan
        out[f"w_{s}"] = float((p[m] * w[m]).sum() / (p * w).sum())
    # tepeler hariç (duyarlılık): her oturumda en yüksek %10 kayıt çıkarılarak
    keep = np.ones(len(x), bool)
    for _, g in x.groupby("oturum"):
        n10 = max(1, int(round(0.10 * len(g))))
        top = g.pm2_5.sort_values(ascending=False).index[:n10]
        keep[x.index.get_indexer(top)] = False
    xk = x[keep]
    out["K_tepesiz"] = float((xk.pm2_5 * xk.dt).sum() / (xk.pa_epa * xk.dt).sum())
    out["tepe_payi_c"] = float(1 - (xk.pm2_5 * xk.dt).sum() / (c * w).sum()) * 100
    # Atmotube 1 µg/m³ çözünürlüğü: değer kesilerek ya da yuvarlanarak yazılmış olabilir → ±0,5 µg/m³ sistematik sınır
    out["K_cozunurluk_alt"] = float((np.maximum(c - 0.5, 0) * w).sum() / (p * w).sum())
    out["K_cozunurluk_ust"] = float(((c + 0.5) * w).sum() / (p * w).sum())
    return out


def bootstrap(x, rng):
    """Oturum içi 30 dk blok bootstrap: K_TWA ve K_D için %95 aralık."""
    parca = []
    for _, g in x.groupby("oturum"):
        b = g.groupby("blok").apply(lambda h: pd.Series({"cw": (h.pm2_5 * h.dt).sum(), "pw": (h.pa_epa * h.dt).sum(),
                                                         "ciw": (h.pm2_5 * h.ir * h.dt).sum(),
                                                         "piw": (h.pa_epa * h.ir * h.dt).sum()}))
        parca.append(b.values)
    kt, kd = np.zeros(NBOOT), np.zeros(NBOOT)
    for i in range(NBOOT):
        s = np.zeros(4)
        for v in parca:
            s += v[rng.integers(0, len(v), len(v))].sum(axis=0)
        kt[i], kd[i] = s[0] / s[1], s[2] / s[3]
    return np.percentile(kt, [2.5, 97.5]), np.percentile(kd, [2.5, 97.5])


def spearman(a, b):
    """Spearman sıra korelasyonu (scipy olmadan: sıraların Pearson korelasyonu, eşitlikte ortalama sıra)."""
    return pd.Series(np.asarray(a, float)).rank().corr(pd.Series(np.asarray(b, float)).rank())


def kitagawa(a, b):
    """a, b: ozet() sözlükleri (b: yüksek K). ΔK = yer dağılımı + yerdeki düzey (üç katman)."""
    dag = duz = 0.0
    for s in ("kimya", "diger", "dis"):
        ka, kb = a[f"K_{s}"], b[f"K_{s}"]
        if np.isnan(ka) and np.isnan(kb):
            continue
        ka = kb if np.isnan(ka) else ka
        kb = ka if np.isnan(kb) else kb
        dag += (b[f"w_{s}"] - a[f"w_{s}"]) * (ka + kb) / 2
        duz += (kb - ka) * (a[f"w_{s}"] + b[f"w_{s}"]) / 2
    return dag, duz


def anova2(tab):
    """3 × 4 dengeli düzen, hücre başına tek gözlem: toplamsal model kareler toplamı payları (%)."""
    y = tab.values
    m = y.mean()
    ss_t = ((y - m) ** 2).sum()
    ss_k = y.shape[1] * ((y.mean(axis=1) - m) ** 2).sum()
    ss_g = y.shape[0] * ((y.mean(axis=0) - m) ** 2).sum()
    return {"kisi": ss_k / ss_t * 100, "gun": ss_g / ss_t * 100, "kalan": (ss_t - ss_k - ss_g) / ss_t * 100}


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    import matplotlib.dates as mdates
    from matplotlib.lines import Line2D
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    d, e, pa = hazirla(ham)
    rng = np.random.default_rng(20261013)
    gunler = sorted(e.gun.unique())

    # ── Envanter (Soru 1) ──
    S.ekle("S.gun_sayisi", int(e.gun.nunique()), "gün", "saha ölçümü yapılan takvim günü (27–30 Nisan 2026, TR)", Q)
    S.ekle("S.oturum_sayisi", int(e.oturum.nunique()), "oturum", "saha oturumu (upload_sessions, kampüs içi)", Q)
    S.ekle("S.olcumcu_sayisi", int(e.kisi.nunique()), "kişi", "ölçüm yapan kişi (app.js → PEOPLE: Saha ekibi A/B/C)", Q)
    duz = e.groupby(["gun", "kisi"]).oturum.nunique()
    S.ekle("S.duzen", f"her gün {int(duz.groupby('gun').size().min())} ölçümcü, her ölçümcü-gün {int(duz.max())} oturum",
           "", "gün × ölçümcü düzeni: 4 gün × 3 ölçümcü = 12 oturum (oturum ≡ ölçümcü-gün)", Q)
    for k in KISILER:
        g = e[e.kisi == k]
        S.ekle(f"S.olcumcu_{k}_envanter", {"oturum": int(g.oturum.nunique()), "kayit": int(len(g)),
                                          "adim_dk": sorted(set((g.adim_s / 60).round(0).astype(int).tolist())),
                                          "sure_sa": round(float(g.dt.sum()), 1),
                                          "atmotube_nem_kayit_payi_yuzde": round(float(g.humidity_pct.notna().mean() * 100), 1),
                                          "tam_sayi_payi_yuzde": round(float((g.pm2_5 == g.pm2_5.round()).mean() * 100), 1)},
               "oturum · kayıt · dk · sa · %", "ölçümcü başına envanter; nem alanı ve tam sayı payı kayıt yolunun (cihaz/dışa aktarım) "
               "farklı olduğunu gösterir", Q)

    # ── Ölçümcü-gün, gün ve ölçümcü özetleri + bootstrap (Soru 2) ──
    kg = {}
    for (gn, k), x in e.groupby(["gun", "kisi"]):
        o = ozet(x)
        o["ci_K"], o["ci_KD"] = bootstrap(x, rng)
        o["bas"], o["bit"] = x.tl.min(), x.tl.max()
        kg[(gn, k)] = o
    for (gn, k), o in kg.items():
        S.ekle(f"S.kg_{k}_{gn}", {
            "TWA": round(o["twa"], 2), "PurpleAir_ayni_anlar": round(o["P"], 2), "K_TWA": round(o["K"], 2),
            "K_TWA_GA95": [round(v, 2) for v in o["ci_K"]], "K_D": round(o["K_D"], 2), "K_D_GA95": [round(v, 2) for v in o["ci_KD"]],
            "K_D_ic_hafif": round(o["K_D_hafif"], 2), "D_ug": round(o["D"], 1), "D_saat_ug": round(o["D_saat"], 2),
            "sure_sa": round(o["sure_sa"], 2), "bina_disi_payi_yuzde": round(o["dis_payi"], 1),
            "kimya_payi_yuzde": round(o["kimya_payi"], 1), "diger_bina_payi_yuzde": round(o["diger_payi"], 1),
            "K_kimya": None if np.isnan(o["K_kimya"]) else round(o["K_kimya"], 2),
            "K_diger_bina": None if np.isnan(o["K_diger"]) else round(o["K_diger"], 2),
            "K_bina_disi": None if np.isnan(o["K_dis"]) else round(o["K_dis"], 2),
            "K_tepesiz": round(o["K_tepesiz"], 2), "tepe10_payi_yuzde": round(o["tepe_payi_c"], 1),
            "K_cozunurluk_sinir": [round(o["K_cozunurluk_alt"], 2), round(o["K_cozunurluk_ust"], 2)]},
            "µg/m³ · oran · µg · sa · %",
            "ölçümcü-gün (= oturum) özeti: TWA = Σc·Δt/ΣΔt; K_TWA = Σc·Δt/ΣP·Δt; K_D = Σc·IR·Δt/ΣP·IR·Δt (IR iç 0,25, dış 1,56);"
            " GA95: 30 dk blok bootstrap (2000); K_tepesiz: en yüksek %10 kayıt hariç (duyarlılık); çözünürlük sınırı c ∓ 0,5", Q)
    gun_oz, kisi_oz = {}, {}
    for gn, x in e.groupby("gun"):
        o = ozet(x)
        o["ci_K"], o["ci_KD"] = bootstrap(x, rng)
        gun_oz[gn] = o
        S.ekle(f"S.gun_{gn}", {"TWA": round(o["twa"], 2), "PurpleAir_ayni_anlar": round(o["P"], 2), "K_TWA": round(o["K"], 2),
                               "K_TWA_GA95": [round(v, 2) for v in o["ci_K"]], "K_D": round(o["K_D"], 2),
                               "K_D_GA95": [round(v, 2) for v in o["ci_KD"]], "sure_sa": round(o["sure_sa"], 1)},
               "µg/m³ · oran · sa", "günün üç oturumu birlikte (Δt ağırlıklı); GA95 oturum içi blok bootstrap", Q)
    for k, x in e.groupby("kisi"):
        o = ozet(x)
        o["ci_K"], o["ci_KD"] = bootstrap(x, rng)
        kisi_oz[k] = o
        S.ekle(f"S.olcumcu_{k}", {"TWA": round(o["twa"], 2), "PurpleAir_ayni_anlar": round(o["P"], 2), "K_TWA": round(o["K"], 2),
                                  "K_TWA_GA95": [round(v, 2) for v in o["ci_K"]], "K_D": round(o["K_D"], 2),
                                  "K_D_GA95": [round(v, 2) for v in o["ci_KD"]], "bina_disi_payi_yuzde": round(o["dis_payi"], 1),
                                  "kimya_payi_yuzde": round(o["kimya_payi"], 1), "sure_sa": round(o["sure_sa"], 1)},
               "µg/m³ · oran · % · sa", "ölçümcünün dört oturumu birlikte (Δt ağırlıklı); GA95 oturum içi blok bootstrap", Q)
    tum = ozet(e)
    tum["ci_K"], tum["ci_KD"] = bootstrap(e, rng)
    S.ekle("S.tum_K_TWA", round(tum["K"], 2), "oran", "12 oturum birlikte Σc·Δt/ΣP·Δt", Q)
    S.ekle("S.tum_TWA", round(tum["twa"], 2), "µg/m³", "12 oturum birlikte Σc·Δt/ΣΔt (Atmotube ham)", Q)
    S.ekle("S.tum_P", round(tum["P"], 2), "µg/m³", "aynı kayıtların düzeltilmiş PurpleAir ortalaması", Q)
    S.ekle("S.tum_sure", round(tum["sure_sa"], 1), "sa", "eş zamanlı PurpleAir değeri olan kayıtların toplam süresi (kayıt × Δt)", Q)
    S.ekle("S.tum_K_TWA_GA95", [round(v, 2) for v in tum["ci_K"]], "oran", "blok bootstrap %95 aralık", Q)
    S.ekle("S.tum_K_D", round(tum["K_D"], 2), "oran", "12 oturum birlikte K_D (IR iç 0,25 / dış 1,56)", Q)
    S.ekle("S.tum_K_D_GA95", [round(v, 2) for v in tum["ci_KD"]], "oran", "blok bootstrap %95 aralık", Q)
    ks = pd.Series({k: o["K"] for k, o in kg.items()})
    kd = pd.Series({k: o["K_D"] for k, o in kg.items()})
    S.ekle("S.kg_K_1_alti", int((ks < 1).sum()), "ölçümcü-gün", "K_TWA < 1 olan ölçümcü-gün (12'den)", Q)
    S.ekle("S.kg_K_GA_1_alti", int(sum(o["ci_K"][1] < 1 for o in kg.values())), "ölçümcü-gün",
           "K_TWA'nın %95 aralığının tamamı 1'in altında olan ölçümcü-gün", Q)
    S.ekle("S.kg_K_GA_1_ustu", int(sum(o["ci_K"][0] > 1 for o in kg.values())), "ölçümcü-gün",
           "K_TWA'nın %95 aralığının tamamı 1'in üstünde olan ölçümcü-gün", Q)
    S.ekle("S.kg_KD_KTWA_fark_enb", round(float((kd - ks).abs().max()), 2), "oran", "|K_D − K_TWA| en büyük ölçümcü-gün farkı", Q)
    S.ekle("S.kg_KD_buyuk", int((kd > ks).sum()), "ölçümcü-gün", "K_D > K_TWA olan ölçümcü-gün (bina dışı kayıtları daha kirli)", Q)

    # ── Aynı gün farkları (Soru 3) ──
    fark_satir = []
    for gn in gunler:
        os_ = {k: kg[(gn, k)] for k in KISILER}
        tw = pd.Series({k: o["twa"] for k, o in os_.items()})
        kk = pd.Series({k: o["K"] for k, o in os_.items()})
        dh = pd.Series({k: o["D_saat"] for k, o in os_.items()})
        # ortak pencere: üç oturumun kesişimi
        bas = max(o["bas"] for o in os_.values())
        bit = min(o["bit"] for o in os_.values())
        cw = {}
        for k in KISILER:
            x = e[(e.gun == gn) & (e.kisi == k) & (e.tl >= bas) & (e.tl <= bit)]
            cw[k] = ozet(x)
        cwt = pd.Series({k: o["twa"] for k, o in cw.items()})
        cwk = pd.Series({k: o["K"] for k, o in cw.items()})
        hi, lo = kk.idxmax(), kk.idxmin()
        dag, duz_ = kitagawa(os_[lo], os_[hi])
        ktp = pd.Series({k: o["K_tepesiz"] for k, o in os_.items()})
        r = {"gun": gn, "twa_oran": tw.max() / tw.min(), "twa_fark": tw.max() - tw.min(), "twa_enb": tw.idxmax(),
             "twa_enk": tw.idxmin(), "K_oran": kk.max() / kk.min(), "K_fark": kk.max() - kk.min(), "K_enb": hi, "K_enk": lo,
             "D_saat_oran": dh.max() / dh.min(), "D_saat_fark": dh.max() - dh.min(),
             "ortak_bas": bas.strftime("%H:%M"), "ortak_bit": bit.strftime("%H:%M"), "ortak_sa": (bit - bas).total_seconds() / 3600,
             "ortak_twa_oran": cwt.max() / cwt.min(), "ortak_twa_fark": cwt.max() - cwt.min(), "ortak_K_oran": cwk.max() / cwk.min(),
             "ortak_P": float(np.mean([o["P"] for o in cw.values()])),
             "kit_dagilim": dag, "kit_duzey": duz_, "dK": kk[hi] - kk[lo], "dK_tepesiz": ktp[hi] - ktp[lo],
             "K_tepesiz_oran": ktp.max() / ktp.min(), "ortak_K": {k: round(v, 2) for k, v in cwk.items()},
             "ortak_twa": {k: round(v, 2) for k, v in cwt.items()}}
        fark_satir.append(r)
        S.ekle(f"S.ayni_gun_{gn}", {
            "TWA_oran_enb_enk": round(r["twa_oran"], 2), "TWA_fark_ugm3": round(r["twa_fark"], 2),
            "TWA_en_yuksek": f"Ölçümcü {r['twa_enb']}", "TWA_en_dusuk": f"Ölçümcü {r['twa_enk']}",
            "K_TWA_oran_enb_enk": round(r["K_oran"], 2), "K_TWA_fark": round(r["K_fark"], 2),
            "K_en_yuksek": f"Ölçümcü {hi}", "K_en_dusuk": f"Ölçümcü {lo}",
            "D_saat_oran": round(r["D_saat_oran"], 2), "D_saat_fark_ug": round(r["D_saat_fark"], 2),
            "ortak_pencere": f"{r['ortak_bas']}–{r['ortak_bit']}", "ortak_pencere_sa": round(r["ortak_sa"], 2),
            "ortak_TWA": r["ortak_twa"], "ortak_K_TWA": r["ortak_K"],
            "ortak_TWA_oran": round(r["ortak_twa_oran"], 2), "ortak_TWA_fark_ugm3": round(r["ortak_twa_fark"], 2),
            "ortak_K_oran": round(r["ortak_K_oran"], 2),
            "Kitagawa_dK": round(r["dK"], 2), "Kitagawa_yer_dagilimi": round(dag, 2), "Kitagawa_yerdeki_duzey": round(duz_, 2),
            "dK_tepesiz": round(r["dK_tepesiz"], 2), "K_tepesiz_oran_enb_enk": round(r["K_tepesiz_oran"], 2)},
            "oran · µg/m³ · µg/sa", "aynı gün üç ölçümcü: en yüksek/en düşük oranı ve farkı; D_saat = D / süre (IR iç 0,25, dış 1,56);"
            " ortak pencere = üç oturumun zaman kesişimi; Kitagawa: K'si en yüksek ve en düşük iki ölçümcü, katmanlar Kimya / diğer"
            " bina / bina dışı, ağırlık ΣP·Δt payı", Q)
    fr = pd.DataFrame(fark_satir).set_index("gun")
    S.ekle("S.ayni_gun_TWA_oran_aralik", f"{tr(fr.twa_oran.min(), 2)}–{tr(fr.twa_oran.max(), 2)}", "oran",
           "dört günde aynı gün en yüksek / en düşük TWA oranı aralığı", Q)
    S.ekle("S.ayni_gun_TWA_fark_aralik", f"{tr(fr.twa_fark.min(), 1)}–{tr(fr.twa_fark.max(), 1)}", "µg/m³",
           "aynı gün en yüksek − en düşük TWA aralığı", Q)
    S.ekle("S.ayni_gun_K_oran_aralik", f"{tr(fr.K_oran.min(), 2)}–{tr(fr.K_oran.max(), 2)}", "oran",
           "aynı gün en yüksek / en düşük K_TWA oranı aralığı", Q)
    S.ekle("S.ayni_gun_K_oran_ortak_aralik", f"{tr(fr.ortak_K_oran.min(), 2)}–{tr(fr.ortak_K_oran.max(), 2)}", "oran",
           "aynı oran, ortak zaman penceresinde", Q)
    S.ekle("S.ayni_gun_tepesiz_K_oran_aralik", f"{tr(fr.K_tepesiz_oran.min(), 2)}–{tr(fr.K_tepesiz_oran.max(), 2)}", "oran",
           "aynı oran, her oturumun en yüksek %10 kaydı hariç (duyarlılık)", Q)

    # Aynı bina, aynı saatler: A ve C yalnızca Kimya binası kayıtlarında, iki oturumun ortak penceresinde
    # (yer ve saat aynı → kalan fark oda/mikro konum, etkinlik ve cihaz farkının toplamına bir üst sınır verir)
    ac = {}
    for gn in gunler:
        a_, c_ = kg[(gn, "A")], kg[(gn, "C")]
        bas, bit = max(a_["bas"], c_["bas"]), min(a_["bit"], c_["bit"])
        v = {}
        for k in ("A", "C"):
            x = e[(e.gun == gn) & (e.kisi == k) & e.kimya & (e.tl >= bas) & (e.tl <= bit)]
            v[k] = float((x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum())
        ac[gn] = {"pencere": f"{bas:%H:%M}–{bit:%H:%M}", "K_A": round(v["A"], 2), "K_C": round(v["C"], 2), "C_A": round(v["C"] / v["A"], 2)}
    S.ekle("S.kimya_A_C_ortak", ac, "oran", "A ve C, yalnızca Kimya binası kayıtları, iki oturumun ortak penceresi: Σc·Δt/ΣP·Δt ve C/A oranı", Q)
    oranlar = [v["C_A"] for g, v in ac.items() if g != "27.04"]
    S.ekle("S.kimya_C_A_aralik_27_haric", f"{tr(min(oranlar), 2)}–{tr(max(oranlar), 2)}", "oran", "aynı C/A oranı, 28–30 Nisan", Q)

    # ── Ayrıştırma (Soru 4) ──
    tabK = pd.DataFrame({gn: {k: np.log(kg[(gn, k)]["K"]) for k in KISILER} for gn in gunler})
    tabT = pd.DataFrame({gn: {k: np.log(kg[(gn, k)]["twa"]) for k in KISILER} for gn in gunler})
    aK, aT = anova2(tabK), anova2(tabT)
    tabK4 = tabK.drop(columns=["27.04"])
    aK3 = anova2(tabK4)
    S.ekle("S.varyans_logK", {k: round(v, 1) for k, v in aK.items()}, "%",
           "log K_TWA, 3 ölçümcü × 4 gün toplamsal ayrıştırma: kareler toplamı payı (kalan = etkileşim + gürültü)", Q)
    S.ekle("S.varyans_logK_27_haric", {k: round(v, 1) for k, v in aK3.items()}, "%",
           "aynı ayrıştırma, çok temiz 27 Nisan hariç (3 × 3)", Q)
    S.ekle("S.varyans_logTWA", {k: round(v, 1) for k, v in aT.items()}, "%", "log TWA için aynı ayrıştırma", Q)
    S.ekle("S.kisi_etkisi_K_geo", {k: round(float(np.exp(tabK.loc[k].mean() - tabK.values.mean())), 2) for k in KISILER}, "kat",
           "toplamsal modelde ölçümcü etkisi: exp(ölçümcünün log K ortalaması − genel ortalama)", Q)
    S.ekle("S.gun_etkisi_K_geo", {g: round(float(np.exp(tabK[g].mean() - tabK.values.mean())), 2) for g in gunler}, "kat",
           "toplamsal modelde gün etkisi", Q)
    # dış ortam düzeyi ve K (oturum düzeyi)
    sP = pd.Series({k: o["P"] for k, o in kg.items()})
    rho = float(spearman(ks, sP))
    S.ekle("S.K_P_spearman", round(rho, 2), "ρ", "12 oturumda K_TWA ile eş zamanlı PurpleAir ortalaması arasında Spearman sıra korelasyonu", Q)
    # kayıt düzeyinde dış ortam sınıfına göre K (ölçümcü bazında, Σc/ΣP)
    e["P_sinif"] = pd.cut(e.pa_epa, [0, 6, 12, 100], right=False, labels=["<6", "6–12", "≥12"])
    pk = e.groupby(["kisi", "P_sinif"], observed=True).apply(lambda x: (x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum())
    S.ekle("S.K_P_sinifi", {f"{k} {s}": round(float(v), 2) for (k, s), v in pk.items()}, "oran",
           "ölçümcü ve eş zamanlı PurpleAir sınıfına (µg/m³) göre Σc·Δt/ΣP·Δt", Q)
    e["dilim"] = pd.cut(e.tl.dt.hour, [0, 11, 14, 24], right=False, labels=["08–11", "11–14", "14–19"])
    dk_ = e.groupby(["kisi", "dilim"], observed=True).apply(lambda x: (x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum())
    S.ekle("S.K_saat_dilimi", {f"{k} {s}": round(float(v), 2) for (k, s), v in dk_.items()}, "oran",
           "ölçümcü ve saat dilimine göre Σc·Δt/ΣP·Δt", Q)
    # yer: katman K'leri (ölçümcü başına)
    for k in KISILER:
        o = kisi_oz[k]
        S.ekle(f"S.olcumcu_{k}_katman", {"K_kimya": None if np.isnan(o["K_kimya"]) else round(o["K_kimya"], 2),
                                         "K_diger_bina": None if np.isnan(o["K_diger"]) else round(o["K_diger"], 2),
                                         "K_bina_disi": None if np.isnan(o["K_dis"]) else round(o["K_dis"], 2),
                                         "kimya_payi_yuzde": round(o["kimya_payi"], 1), "diger_payi_yuzde": round(o["diger_payi"], 1),
                                         "bina_disi_payi_yuzde": round(o["dis_payi"], 1)},
               "oran · %", "ölçümcünün dört oturumu: yer katmanlarına göre Σc·Δt/ΣP·Δt ve süre payları (15 m kuralı)", Q)
    katK = e.groupby("katman").apply(lambda x: (x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum())
    S.ekle("S.katman_K", {k: round(float(v), 2) for k, v in katK.items()}, "oran", "tüm ölçümcüler: katmanlara göre Σc·Δt/ΣP·Δt", Q)
    # ölçümcü ile katman K'si Güzide Kafe / Kütüphane (diğer binaların büyük kısmı)
    ad = {b["gk"]: b["ad"] for b in veri.binalar()}
    e["bina_ad"] = e.gk.map(ad)
    for b in ("Güzide Kafe", "Kütüphane"):
        x = e[e.bina_ad == b]
        S.ekle(f"S.bina_K_{b.replace(' ', '_')}", {"K": round(float((x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum()), 2),
                                                   "sure_sa": round(float(x.dt.sum()), 2), "oturum": int(x.oturum.nunique())},
               "oran · sa", f"{b} poligonu (≤ 15 m) içindeki tüm saha kayıtları: Σc·Δt/ΣP·Δt", Q)
    # bina dışı süre payı ile K (12 ölçümcü-gün)
    sd = pd.Series({k: o["dis_payi"] for k, o in kg.items()})
    sk = pd.Series({k: 100 - o["kimya_payi"] for k, o in kg.items()})
    S.ekle("S.K_dis_payi_spearman", round(float(spearman(ks, sd)), 2), "ρ",
           "12 ölçümcü-günde K_TWA ile bina dışı süre payı arasında Spearman", Q)
    S.ekle("S.K_kimya_disi_payi_spearman", round(float(spearman(ks, sk)), 2), "ρ",
           "12 ölçümcü-günde K_TWA ile Kimya binası dışında geçen süre payı arasında Spearman", Q)
    # tepeler
    tp = pd.Series({k: o["tepe_payi_c"] for k, o in kg.items()})
    kt = pd.Series({k: o["K_tepesiz"] for k, o in kg.items()})
    S.ekle("S.tepe10_payi_aralik", f"{tr(tp.min())}–{tr(tp.max())}", "%", "en yüksek %10 kaydın Σc·Δt içindeki payı, ölçümcü-gün aralığı", Q)
    S.ekle("S.K_tepesiz_aralik", f"{tr(kt.min(), 2)}–{tr(kt.max(), 2)}", "oran", "K, en yüksek %10 kayıt hariç (duyarlılık), aralık", Q)
    S.ekle("S.K_tepeli_aralik", f"{tr(ks.min(), 2)}–{tr(ks.max(), 2)}", "oran", "K_TWA aralığı (karşılaştırma için)", Q)
    # örnekleme aralığı: 1 dk oturumları 2 dk'ya seyreltme (iki evre)
    deg, deg15 = [], []
    for (gn, k), x in e[e.adim_s == 60].groupby(["gun", "kisi"]):
        x = x.sort_values("t")
        k0 = (x.pm2_5 * x.dt).sum() / (x.pa_epa * x.dt).sum()
        m0 = x.set_index("t").pm2_5.rolling("15min").mean().max()
        for ph in (0, 1):
            y = x.iloc[ph::2]
            deg.append(abs((y.pm2_5.sum() / y.pa_epa.sum()) / k0 - 1) * 100)
            deg15.append(abs(y.set_index("t").pm2_5.rolling("15min").mean().max() / m0 - 1) * 100)
    S.ekle("S.seyreltme_K_degisim_enb", round(float(max(deg)), 1), "%",
           "1 dk'lık 8 oturum her ikinci kayıt alınarak 2 dk'ya seyreltildiğinde K_TWA'nın en büyük göreli değişimi (iki evre)", Q)
    S.ekle("S.seyreltme_15dk_degisim_enb", round(float(max(deg15)), 1), "%",
           "aynı seyreltmede en yüksek 15 dk kayan ortalamanın en büyük göreli değişimi", Q)
    # çözünürlük
    cz = pd.Series({k: (o["K_cozunurluk_ust"] - o["K_cozunurluk_alt"]) / 2 / o["K"] * 100 for k, o in kg.items()})
    S.ekle("S.cozunurluk_K_yari_genislik", f"{tr(cz.min())}–{tr(cz.max())}", "%",
           "c ∓ 0,5 µg/m³ sınırıyla K_TWA'nın göreli yarı genişliği, ölçümcü-gün aralığı (en büyüğü en temiz günde)", Q)
    # nem
    pr = []
    for o in kg.values():
        p = pa[(pa.t >= o["bas"].tz_convert("UTC")) & (pa.t <= o["bit"].tz_convert("UTC"))]
        pr.append(p.humidity.max())
    S.ekle("S.nem_PA_enb", round(float(np.nanmax(pr)), 0), "%", "oturum süreleri içinde PurpleAir gövde içi nem en yüksek değeri", Q)
    S.ekle("S.nem_atmotube_enb", round(float(e.humidity_pct.max()), 0), "%", "saha kayıtlarında Atmotube nemi en yüksek değeri (A ve B)", Q)
    S.ekle("S.nem_75_ustu_kayit", int((e.humidity_pct >= 75).sum()), "kayıt", "Atmotube nemi ≥ %75 olan saha kaydı", Q)
    # cihaz farkı: ölçümcü K oranları (ortak cihaz çarpanı bilinmiyor)
    kpo = {f"{a}/{b}": round(kisi_oz[a]["K"] / kisi_oz[b]["K"], 2) for a, b in (("B", "A"), ("B", "C"), ("C", "A"))}
    S.ekle("S.olcumcu_K_oranlari", kpo, "oran", "ölçümcülerin dört gün birlikte K_TWA oranları (farkın tümü cihazdan gelseydi gereken çarpan)", Q)
    S.yaz(os.path.join(cikti, "sayilar.json"))

    # ════════ Şekil 10: gün × ölçümcü TWA ve K ════════
    fig, axs = plt.subplots(2, 1, figsize=(7.5, 7.2), sharex=True, gridspec_kw={"height_ratios": [1, 1.15]})
    off = {"A": -0.22, "B": 0.0, "C": 0.22}
    ax = axs[0]
    for i, gn in enumerate(gunler):
        for k in KISILER:
            o = kg[(gn, k)]
            xx = i + off[k]
            ax.plot([xx, xx], [o["P"], o["twa"]], color=IZGARA, lw=2.0, zorder=1)
            ax.plot(xx, o["P"], marker="_", ms=11, mew=2.2, color=DEVICE_COLOR["purpleair"], zorder=2)
            ax.plot(xx, o["twa"], ISARET[k], ms=7, color=RENK[k], mec="white", mew=0.8, zorder=3)
            ax.text(xx, o["twa"] + 0.6, k, ha="center", va="bottom", fontsize=7.5, color=RENK[k], fontweight="bold")
    ax.set_ylabel("ortalama PM₂.₅ (µg/m³)")
    ax.set_ylim(0, 22)
    ax.set_title("(a) Kişisel TWA (renkli) ve aynı anlarda çatı (mavi çizgi)", loc="left", fontsize=10)
    virgul_eksen(ax)
    ax = axs[1]
    for i, gn in enumerate(gunler):
        for k in KISILER:
            o = kg[(gn, k)]
            xx = i + off[k]
            ax.plot([xx, xx], o["ci_K"], color=RENK[k], lw=1.4, alpha=0.7, zorder=2)
            ax.plot(xx, o["K"], ISARET[k], ms=7, color=RENK[k], mec="white", mew=0.8, zorder=3)
            ax.plot(xx + 0.07, o["K_D"], ISARET[k], ms=5, mfc="white", mec=RENK[k], mew=1.1, zorder=3)
            ax.text(xx - 0.05, o["K"], tr(o["K"], 2), ha="right", va="center", fontsize=6.6, color=MUREKKEP)
        go = gun_oz[gn]
        ax.plot([i - 0.33, i + 0.33], [go["K"], go["K"]], color=GRI, lw=1.0, ls="--", zorder=1)
    ax.axhline(1, color=MUREKKEP, lw=0.8)
    ax.text(1.5, 1.02, "K = 1: çatıyla aynı", fontsize=7, color=IKINCIL, ha="center", va="bottom")
    ax.set_yscale("log")
    ax.set_ylim(0.38, 3.4)
    ax.set_yticks([0.4, 0.5, 0.7, 1, 1.5, 2, 3], ["0,4", "0,5", "0,7", "1", "1,5", "2", "3"])
    ax.minorticks_off()
    ax.set_ylabel("K = kişisel / çatı (log eksen)")
    ax.set_title("(b) K_TWA (dolu, %95 blok bootstrap aralığı) ve K_D (boş); kesikli: günün K'si", loc="left", fontsize=10)
    ax.set_xticks(range(len(gunler)), [f"{g}.2026" for g in gunler])
    ax.set_xlim(-0.5, len(gunler) - 0.5)
    h = [Line2D([], [], color=RENK[k], marker=ISARET[k], lw=0, ms=7, label=f"Ölçümcü {k}") for k in KISILER]
    h += [Line2D([], [], color=DEVICE_COLOR["purpleair"], marker="_", lw=0, ms=10, mew=2, label="PurpleAir, aynı anlar"),
          Line2D([], [], color=GRI, marker="s", lw=0, ms=5, mfc="white", label="K_D (solunan miktar)")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 0.085), ncol=5, frameon=False, fontsize=7.6, handletextpad=0.3,
               columnspacing=1.0)
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha ölçümleri (ham PM₂.₅; 27–30 Nisan 2026; her ölçümcü-gün bir oturum) ve PurpleAir PA-II\n"
                     "(SUMER çatısı, 2 dk, US EPA düzeltmeli; ±3 dk eşleştirme). TWA: zaman ağırlıklı ortalama. K_D: bina içi 0,25,\n"
                     "bina dışı 1,56 m³/sa solunum hızıyla. Ani yükselmeler ayıklanmamıştır.")
    fig.subplots_adjust(top=0.96, bottom=0.19, hspace=0.22, left=0.11, right=0.98)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil10_gun_kisi.png"))
    plt.close(fig)

    # ════════ Şekil 11: farkın bileşenleri ════════
    fig = plt.figure(figsize=(7.5, 7.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1.25, 1], hspace=0.55, wspace=0.42)
    # (a) Kitagawa: aynı gün K farkı = yer dağılımı + yerdeki düzey
    ax = fig.add_subplot(gs[0, :])
    yy = np.arange(len(gunler))[::-1]
    for y_, gn in zip(yy, gunler):
        r = fr.loc[gn]
        a_, b_ = r.kit_dagilim, r.kit_duzey
        ax.barh(y_ + 0.17, a_, height=0.3, color=GRI, zorder=2)
        ax.barh(y_ - 0.17, b_, height=0.3, color=MUREKKEP, alpha=0.75, zorder=2)
        ax.text(max(a_, 0) + 0.015, y_ + 0.17, f"yer dağılımı {tr(a_, 2)}", va="center", fontsize=7.2, color=IKINCIL)
        ax.text(max(b_, 0) + 0.015, y_ - 0.17, f"yerdeki düzey {tr(b_, 2)}", va="center", fontsize=7.2, color=IKINCIL)
    ax.set_yticks(yy, [f"{g}: {fr.loc[g, 'K_enb']} − {fr.loc[g, 'K_enk']} (ΔK {tr(fr.loc[g, 'dK'], 2)})" for g in gunler], fontsize=8)
    ax.axvline(0, color=TABAN, lw=0.8)
    ax.set_xlim(min(-0.1, fr[["kit_dagilim", "kit_duzey"]].min().min() - 0.05), 1.45)
    ax.set_xlabel("K_TWA farkına katkı (oran birimi)")
    ax.set_title("(a) Aynı gün en yüksek − en düşük K farkının iki bileşeni", loc="left", fontsize=10)
    virgul_eksen(ax, "x")
    ax.grid(axis="y", visible=False)
    # (b) K_TWA ve tepeler hariç K
    ax = fig.add_subplot(gs[1, 0])
    yy = np.arange(12)[::-1]
    etik = []
    for y_, (gn, k) in zip(yy, [(g, k) for g in gunler for k in KISILER]):
        o = kg[(gn, k)]
        ax.plot([o["K_tepesiz"], o["K"]], [y_, y_], color=IZGARA, lw=2, zorder=1)
        ax.plot(o["K"], y_, ISARET[k], ms=6, color=RENK[k], mec="white", mew=0.7, zorder=3)
        ax.plot(o["K_tepesiz"], y_, ISARET[k], ms=5.5, mfc="white", mec=RENK[k], mew=1.1, zorder=3)
        etik.append(f"{gn} · {k}")
    ax.set_yticks(yy, etik, fontsize=7)
    ax.axvline(1, color=MUREKKEP, lw=0.7)
    ax.set_xscale("log")
    ax.set_xlim(0.35, 2.2)
    ax.set_xticks([0.4, 0.5, 0.7, 1, 1.5, 2], ["0,4", "0,5", "0,7", "1", "1,5", "2"])
    ax.minorticks_off()
    ax.set_xlabel("K (log eksen)")
    ax.set_title("(b) K_TWA (dolu) ve en yüksek\n%10 kayıt hariç K (boş)", loc="left", fontsize=9.5)
    ax.grid(axis="y", visible=False)
    # (c) varyans ayrıştırması
    ax = fig.add_subplot(gs[1, 1])
    sat = [("log K_TWA", aK), ("log K_TWA\n(27 Nisan hariç)", aK3), ("log TWA", aT)]
    renkler = {"kisi": "#3d3c39", "gun": GRI, "kalan": IZGARA}   # nötr griler: ölçümcü ve cihaz renkleriyle karışmasın
    adlar = {"kisi": "ölçümcü", "gun": "gün", "kalan": "kalan"}
    for i, (ad_, a) in enumerate(sat):
        sol = 0
        for kk_ in ("kisi", "gun", "kalan"):
            ax.barh(len(sat) - 1 - i, a[kk_], left=sol, color=renkler[kk_], height=0.55, edgecolor="white", lw=0.6)
            if a[kk_] >= 9:
                ax.text(sol + a[kk_] / 2, len(sat) - 1 - i, f"{tr(a[kk_], 0)}", ha="center", va="center", fontsize=7.2,
                        color="white" if kk_ != "kalan" else MUREKKEP)
            if i == 0:
                ax.text(sol + a[kk_] / 2, len(sat) - 1 - i + 0.33, adlar[kk_], ha="center", va="bottom", fontsize=7.2,
                        color=MUREKKEP if kk_ == "kisi" else IKINCIL, fontweight="bold")
            sol += a[kk_]
    ax.set_yticks(range(len(sat))[::-1], [s[0] for s in sat], fontsize=7.6)
    ax.set_ylim(-0.5, len(sat) - 0.2)
    ax.set_xlim(0, 100)
    ax.set_xlabel("kareler toplamı payı (%)")
    ax.set_title("(c) Ölçümcü mü, gün mü?\n(3 × 4 düzen)", loc="left", fontsize=9.5)
    ax.grid(axis="y", visible=False)
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha ölçümleri (ham; 27–30 Nisan 2026) ve PurpleAir PA-II (US EPA düzeltmeli, 2 dk). (a) Kitagawa ayrıştırması;\n"
                     "katmanlar Kimya binası / diğer binalar / bina dışı (bina poligonu ve 15 m kuralı). (b) Tepeler veriden çıkarılmamıştır; boş işaret\n"
                     "yalnızca duyarlılık hesabıdır. (c) 3 ölçümcü × 4 gün toplamsal ayrıştırma; 'kalan' etkileşim ve gürültüyü birlikte içerir.")
    fig.subplots_adjust(top=0.95, bottom=0.15, left=0.25, right=0.97)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil11_bilesenler.png"))
    plt.close(fig)

    # ════════ Şekil 12: aynı gün, saat ekseninde göreli maruziyet (konum yok) ════════
    secim = [g for g in ("28.04", "30.04") if g in gunler]
    fig, axs = plt.subplots(len(secim), 1, figsize=(7.5, 6.2), sharey=True)
    for ax, gn, harf in zip(np.atleast_1d(axs), secim, "ab"):
        for k in KISILER:
            x = e[(e.gun == gn) & (e.kisi == k)].copy()
            x["yarim"] = x.tl.dt.floor(BLOK)
            b = x.groupby("yarim").apply(lambda h: pd.Series({"K": (h.pm2_5 * h.dt).sum() / (h.pa_epa * h.dt).sum(),
                                                              "kap": h.dt.sum() / 0.5}))
            b = b[b.kap >= 0.75]
            idx = b.index + pd.Timedelta("15min")
            ser = pd.Series(b.K.values, index=idx)
            # 30 dk'dan uzun boşlukları birleştirme
            full = ser.reindex(pd.date_range(ser.index.min(), ser.index.max(), freq="30min"))
            ax.plot(full.index, full.values, color=RENK[k], lw=1.4, marker=ISARET[k], ms=4.5, mec="white", mew=0.6)
            son = ser.dropna()
            ax.text(son.index[-1] + pd.Timedelta("8min"), son.values[-1], k, color=RENK[k], fontsize=8, fontweight="bold",
                    va="center")
        ax.axhline(1, color=MUREKKEP, lw=0.8)
        ax.set_yscale("log")
        ax.set_ylim(0.25, 9)
        ax.set_yticks([0.25, 0.5, 1, 2, 4, 8], ["0,25", "0,5", "1", "2", "4", "8"])
        ax.minorticks_off()
        ax.set_ylabel("K (30 dk; log)")
        go = gun_oz[gn]
        ax.set_title(f"({harf}) {gn}.2026 · günün K_TWA'sı {tr(go['K'], 2)} · çatı ortalaması {tr(go['P'], 1)} µg/m³",
                     loc="left", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=veri.TZ))
        ax.set_xlim(pd.Timestamp(f"2026-{gn[3:5]}-{gn[0:2]} 08:30", tz=veri.TZ), pd.Timestamp(f"2026-{gn[3:5]}-{gn[0:2]} 18:45", tz=veri.TZ))
    np.atleast_1d(axs)[-1].set_xlabel("Saat (Türkiye saati; 30 dakikalık dilimin ortası)")
    h = [Line2D([], [], color=RENK[k], marker=ISARET[k], lw=1.4, ms=5, label=f"Ölçümcü {k}") for k in KISILER]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 0.06), ncol=3, frameon=False, fontsize=8)
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha ölçümleri (ham PM₂.₅) ve PurpleAir PA-II (US EPA düzeltmeli, 2 dk). K = Σc·Δt / ΣP·Δt, 30 dakikalık\n"
                     "dilimlerde (en az %75 dolu). Konum bilgisi bilinçli olarak gösterilmemiştir (KVKK). Ani yükselmeler ayıklanmamıştır.")
    fig.subplots_adjust(top=0.95, bottom=0.2, hspace=0.42, left=0.11, right=0.96)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil12_saat_gorel.png"))
    plt.close(fig)

    print("S tamam:", len(S.d), "sayı")
    tab = pd.DataFrame({f"{g} {k}": {kk_: (round(v, 2) if isinstance(v, float) else v) for kk_, v in o.items()
                                     if kk_ in ("twa", "P", "K", "K_D", "K_D_hafif", "D", "D_saat", "dis_payi", "kimya_payi",
                                                "K_kimya", "K_diger", "K_dis", "K_tepesiz", "tepe_payi_c")}
                        for (g, k), o in kg.items()}).T
    print(tab.to_string())
    print({k: (round(o["K"], 2), [round(v, 2) for v in o["ci_K"]], round(o["K_D"], 2)) for k, o in kg.items()})
    print(fr.drop(columns=["ortak_K", "ortak_twa"]).round(2).T.to_string())
    print("gün", {g: (round(o["twa"], 2), round(o["P"], 2), round(o["K"], 2), [round(v, 2) for v in o["ci_K"]], round(o["K_D"], 2)) for g, o in gun_oz.items()})
    print("kişi", {g: (round(o["twa"], 2), round(o["P"], 2), round(o["K"], 2), [round(v, 2) for v in o["ci_K"]], round(o["K_D"], 2), round(o["dis_payi"], 1)) for g, o in kisi_oz.items()})
    print("anova", aK, aK3, aT)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
