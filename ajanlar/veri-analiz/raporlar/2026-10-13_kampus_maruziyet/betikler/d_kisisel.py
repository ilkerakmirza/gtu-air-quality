"""3.3 Kişisel maruziyet (ölçülen) — saha oturumları ve Atmotube canlı kayıtları.

Kullanım: python3 -I d_kisisel.py <ham klasörü> <rapor klasörü>
Tanımlar:
  * Her kayıt kendi örnekleme aralığını temsil eder (oturumun ortanca adımı: 1 ya da 2 dk); ölçüm süresi = kayıt × adım.
  * TWA = kayıtların ortalaması (eşit süre ağırlığı). K_TWA = TWA / eş zamanlı düzeltilmiş PurpleAir ortalaması (aynı kayıtlar).
  * Kayan ortalama: (t − 15 dk, t] ve (t − 60 dk, t] içindeki kayıtlar; pencerenin en az %75'i dolu olmalı.
  * En yüksek %10 kaydın katkısı = en yüksek %10 kaydın Σc'si / Σc (IR sabitken doza katkı payı).
  * Solunan miktar = TWA × IR × süre; IR = 1,56 m³/sa (tempolu yürüme, EPA 2011 Tablo 6-2) ve alt sınır olarak 0,25 m³/sa (oturma).
Ani yükselmeler ayıklanmaz (kullanıcı kararı, 8 Ekim 2026).
Üretir: sekiller/sekil08_oturum_seri.png, sekil09_kisisel_oran.png; sayilar.json'a 'D.*'.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402
from ortak import (Sayilar, stil, tr, kaynak_notu, virgul_eksen, DEVICE_COLOR, GRI, MUREKKEP, IKINCIL, IZGARA, IR,  # noqa: E402
                   KATEGORIK, uygulama_ile_esles, bosluk_kir)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

Q = "Q2 (saha noktaları) + docs/veri PurpleAir arşivi (27–30 Nisan); Q3 atp_canli"
SON = pd.Timestamp("2026-10-12T21:00:00Z")


def kayan_enb(g, dk, adim_dk):
    s = g.set_index("t").pm2_5.dropna()
    m = s.rolling(f"{dk}min", closed="right").mean()
    n = s.rolling(f"{dk}min", closed="right").count()
    ok = n >= 0.75 * dk / adim_dk
    if not ok.any():
        return np.nan, None
    m = m[ok]
    return float(m.max()), m.idxmax()


def main(ham, cikti):
    uygulama_ile_esles()
    plt = stil()
    import matplotlib.dates as mdates
    os.makedirs(os.path.join(cikti, "sekiller"), exist_ok=True)
    S = Sayilar()
    d, blds, pa = veri.saha(ham)
    d["kimya"] = d.gk.fillna("").str.contains("Kimya")
    rows = []
    for o, g in d.groupby("oturum"):
        g = g.sort_values("t")
        adim_dk = float(g.adim_s.iloc[0]) / 60
        gp = g.dropna(subset=["pm2_5"])
        n = len(gp)
        sure_sa = n * adim_dk / 60
        twa = float(gp.pm2_5.mean())
        e = gp.dropna(subset=["pa_epa"])
        pa_twa = float(e.pa_epa.mean())
        k_twa = float(e.pm2_5.mean() / e.pa_epa.mean())
        m15, t15 = kayan_enb(gp, 15, adim_dk)
        m60, t60 = kayan_enb(gp, 60, adim_dk)
        c = np.sort(gp.pm2_5.values)[::-1]
        ust = max(1, int(round(0.10 * n)))
        pay10 = float(c[:ust].sum() / c.sum() * 100)
        imax = gp.pm2_5.idxmax()
        rows.append({"oturum": o, "ekip": g.ekip.iloc[0], "tarih": g.tl.iloc[0].strftime("%d.%m"),
                     "bas": g.tl.iloc[0].strftime("%H:%M"), "bit": g.tl.iloc[-1].strftime("%H:%M"), "adim_dk": adim_dk,
                     "n": n, "sure_sa": sure_sa, "kimya_payi": float(g.kimya.mean() * 100), "twa": twa, "pa_twa": pa_twa,
                     "k_twa": k_twa, "enb_kayit": float(gp.pm2_5.max()), "enb_kayit_t": gp.loc[imax, "tl"].strftime("%H:%M"),
                     "enb_kayit_kimya": bool(gp.loc[imax, "kimya"]), "m15": m15,
                     "m15_t": t15.tz_convert(veri.TZ).strftime("%H:%M") if t15 is not None else None,
                     "m60": m60, "m60_t": t60.tz_convert(veri.TZ).strftime("%H:%M") if t60 is not None else None,
                     "pay10": pay10, "doz_yurume": twa * IR["walk"] * sure_sa, "doz_oturma": twa * IR["sit"] * sure_sa,
                     "doz_pa_yurume": pa_twa * IR["walk"] * sure_sa})
    t = pd.DataFrame(rows).set_index("oturum")
    for o, r in t.iterrows():
        S.ekle(f"D.oturum_{o:02d}", {
            "ekip": f"Saha ekibi {r.ekip}", "tarih": f"{r.tarih}.2026", "saat": f"{r.bas}–{r.bit}", "adim_dk": r.adim_dk,
            "kayit": int(r.n), "olcum_suresi_sa": round(r.sure_sa, 2), "kimya_binasi_payi_yuzde": round(r.kimya_payi, 1),
            "TWA": round(r.twa, 2), "PurpleAir_EPA_es_zamanli": round(r.pa_twa, 2), "K_TWA": round(r.k_twa, 2),
            "enb_tek_kayit": round(r.enb_kayit, 1), "enb_tek_kayit_saat": r.enb_kayit_t, "enb_15dk": round(r.m15, 2),
            "enb_15dk_bitis": r.m15_t, "enb_60dk": round(r.m60, 2), "enb_60dk_bitis": r.m60_t,
            "en_yuksek_yuzde10_katki": round(r.pay10, 1), "doz_yurume_ug": round(r.doz_yurume, 1),
            "doz_oturma_ug": round(r.doz_oturma, 1)},
            "µg/m³ · sa · µg · oran",
            "oturum özeti: TWA = kayıtların ortalaması; K_TWA = TWA / eş zamanlı düzeltilmiş PurpleAir; kayan pencereler ≥ %75 dolu;"
            " doz = TWA × IR × süre (IR 1,56 ve 0,25 m³/sa)", Q)
    S.ekle("D.oturum_sayisi", int(len(t)), "oturum", "27–30 Nisan saha oturumları", Q)
    S.ekle("D.toplam_sure", round(float(t.sure_sa.sum()), 1), "sa", "12 oturumun toplam ölçüm süresi (kayıt × adım)", Q)
    S.ekle("D.twa_aralik", f"{tr(t.twa.min())}–{tr(t.twa.max())}", "µg/m³", "oturum TWA'larının en küçüğü ve en büyüğü (Atmotube ham)", Q)
    S.ekle("D.k_twa_aralik", f"{tr(t.k_twa.min(), 2)}–{tr(t.k_twa.max(), 2)}", "oran", "oturum K_TWA aralığı", Q)
    S.ekle("D.k_twa_ortanca", round(float(t.k_twa.median()), 2), "oran", "12 oturumun K_TWA ortancası", Q)
    ic = t[t.kimya_payi >= 85]
    S.ekle("D.k_twa_ic_oturum_ortanca", round(float(ic.k_twa.median()), 2), "oran",
           f"noktalarının ≥ %85'i Kimya binasında olan {len(ic)} oturumun K_TWA ortancası", Q)
    ic2 = ic[ic.pa_twa >= 6]
    S.ekle("D.k_twa_ic_oturum_dis6", f"{tr(ic2.k_twa.min(), 2)}–{tr(ic2.k_twa.max(), 2)} (n = {len(ic2)})", "oran",
           "aynı oturumlardan eş zamanlı PurpleAir ortalaması ≥ 6 µg/m³ olanların K_TWA aralığı (27 Nisan'ın çok temiz günü hariç)", Q)
    S.ekle("D.enb_tek_kayit", round(float(t.enb_kayit.max()), 1), "µg/m³", f"tüm oturumlarda en yüksek tek kayıt (Oturum {int(t.enb_kayit.idxmax())})", Q)
    S.ekle("D.enb_15dk", round(float(t.m15.max()), 2), "µg/m³", f"en yüksek 15 dk kayan ortalama (Oturum {int(t.m15.idxmax())})", Q)
    S.ekle("D.enb_60dk", round(float(t.m60.max()), 2), "µg/m³", f"en yüksek 60 dk kayan ortalama (Oturum {int(t.m60.idxmax())})", Q)
    S.ekle("D.pay10_aralik", f"{tr(t.pay10.min())}–{tr(t.pay10.max())}", "%", "en yüksek %10 kaydın Σc içindeki payı, oturum aralığı", Q)
    S.ekle("D.pay10_ortanca", round(float(t.pay10.median()), 1), "%", "aynı payın 12 oturum ortancası", Q)
    S.ekle("D.doz_yurume_aralik", f"{tr(t.doz_yurume.min())}–{tr(t.doz_yurume.max())}", "µg", "TWA × 1,56 m³/sa × süre, oturum aralığı", Q)
    S.ekle("D.doz_oturma_aralik", f"{tr(t.doz_oturma.min())}–{tr(t.doz_oturma.max())}", "µg", "TWA × 0,25 m³/sa × süre, oturum aralığı", Q)
    # tepelerin yeri
    S.ekle("D.enb_kayit_kimya_disi", int((~t.enb_kayit_kimya).sum()), "oturum", "en yüksek tek kaydı Kimya binası dışında alınan oturum sayısı", Q)
    # Ani yükselmeler: komşu kayıtların 5 katını aşan kayıtlar (yalnızca sayım; ayıklanmaz)
    say = 0
    for o, g in d.dropna(subset=["pm2_5"]).groupby("oturum"):
        v = g.sort_values("t").pm2_5.values
        if len(v) > 2:
            kom = np.maximum((np.r_[v[1:], np.nan] + np.r_[np.nan, v[:-1]]) / 2, 1.0)
            say += int(np.nansum(v[1:-1] > 5 * kom[1:-1]))
    S.ekle("D.ani_yukselme_sayisi", say, "kayıt", "komşu iki kaydın ortalamasının 5 katını aşan kayıt (ayıklanmadı; gerçek kısa süreli maruziyet olarak raporlanır)", Q)

    # ── Atmotube canlı (ATP-1…5): kişisel / dış ortam oranı ──
    _, a, _ = veri.q3(ham)
    a = a[a.t < SON]
    S.ekle("D.atp_kayit", int(len(a)), "kayıt", "Atmotube canlı kayıtları (measurements, source='atmotube'), 13 Ekim 00:00'a kadar", "Q3 atp_canli")
    S.ekle("D.atp_pm", int(a.pm2_5.notna().sum()), "kayıt", "PM₂.₅ değeri olanlar", "Q3 atp_canli")
    S.ekle("D.atp_kampus", int((a.pm2_5.notna() & a.kampus_ici).sum()), "kayıt", "PM₂.₅ değeri olan ve konumu kampüs içinde (2 km) olanlar", "Q3 atp_canli")
    aa = a[a.pm2_5.notna() & a.kampus_ici & a.pa_epa.notna() & (a.pa_n >= 4)].copy()
    aa = aa[aa.pa_epa > 0]
    aa["K"] = aa.pm2_5 / aa.pa_epa
    S.ekle("D.atp_esli", int(len(aa)), "kayıt", "±8 dk içinde en az 4 düzeltilmiş PurpleAir kaydıyla eşleşen kampüs içi kayıt", "Q3 atp_canli")
    q = aa.K.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    S.ekle("D.atp_K_ortanca", round(float(q[0.5]), 2), "oran", "ATP kayıtlarında K = Atmotube / düzeltilmiş PurpleAir ortancası", "Q3 atp_canli")
    S.ekle("D.atp_K_ceyrek", f"{tr(q[0.25], 2)}–{tr(q[0.75], 2)}", "oran", "K'nin çeyrekler arası aralığı", "Q3 atp_canli")
    S.ekle("D.atp_K_p10_p90", f"{tr(q[0.1], 2)}–{tr(q[0.9], 2)}", "oran", "K'nin 10. ve 90. yüzdeliği", "Q3 atp_canli")
    S.ekle("D.atp_K_1_alti", round(float((aa.K < 1).mean() * 100), 1), "%", "K < 1 olan kayıtların payı", "Q3 atp_canli")
    S.ekle("D.atp_K_0_75_alti", round(float((aa.K < 0.75).mean() * 100), 1), "%", "K < 0,75 olan kayıtların payı", "Q3 atp_canli")
    S.ekle("D.atp_K_1_25_ustu", round(float((aa.K >= 1.25).mean() * 100), 1), "%", "K ≥ 1,25 olan kayıtların payı", "Q3 atp_canli")
    S.ekle("D.atp_09_17_payi", round(float(aa.tl.dt.hour.between(9, 16).mean() * 100), 1), "%", "eşleşen kayıtların 09:00–16:59 arasındaki payı", "Q3 atp_canli")
    S.ekle("D.atp_cihaz_gun", int(aa.assign(g=aa.tl.dt.strftime("%Y-%m-%d")).groupby(["cihaz", "g"]).ngroups), "cihaz-gün",
           "eşleşen kayıtların dağıldığı cihaz-gün sayısı", "Q3 atp_canli")
    S.ekle("D.atp_nem_80_ustu", int((aa.humidity_pct > 80).sum()), "kayıt", "eşleşen kayıtlarda Atmotube nemi > %80 olan kayıt", "Q3 atp_canli")
    pd_ = d.dropna(subset=["pm2_5", "pa_epa"])
    pd_ = pd_[pd_.pa_epa > 0]
    kk = pd_.pm2_5 / pd_.pa_epa

    # ── Şekil 8: iki oturumun zaman serisi ──
    secim = [(8, "K_TWA 1'in altında", 60, "sol"), (10, "K_TWA 1'e yakın", 80, "sag")]
    fig, axs = plt.subplots(2, 1, figsize=(7.5, 6.4))
    for k_, (ax, (o, aciklama, ust, kutu)) in enumerate(zip(axs, secim)):
        g = d[d.oturum == o].sort_values("t")
        r = t.loc[o]
        t0, t1 = g.t.min() - pd.Timedelta("20min"), g.t.max() + pd.Timedelta("20min")
        p = pa[(pa.t >= t0) & (pa.t <= t1)]
        # v1.2: bina içi/dışı gölgelendirmesi kaldırıldı (KVKK: §3.4 ölçümcü etiketleriyle birleşince dakikalık konum izlenebilirdi)
        px, py = bosluk_kir(p.tl, p.epa, "10min")
        ax.plot(px, py, color=DEVICE_COLOR["purpleair"], lw=1.3)
        gx, gy = bosluk_kir(g.tl, g.pm2_5, "10min")
        ax.plot(gx, gy, color=DEVICE_COLOR["atmotube"], lw=1.0)
        m15 = g.set_index("t").pm2_5.rolling("15min", closed="right").mean()
        ax.plot(m15.index.tz_convert(veri.TZ), m15.values, color=MUREKKEP, lw=1.0, alpha=0.85)
        ax.set_ylim(0, ust)
        # ölçek dışı kayıtlar: üst kenarda ok ve değer
        dis_k = g[g.pm2_5 > ust]
        if len(dis_k):
            im = dis_k.pm2_5.idxmax()
            ax.annotate(f"ölçek dışı: {len(dis_k)} kayıt, en yüksek {tr(dis_k.pm2_5.max(), 0)} µg/m³ ({dis_k.loc[im, 'tl'].strftime('%H:%M')})",
                        xy=(dis_k.loc[im, "tl"], ust), xytext=(-14, -34), textcoords="offset points", ha="right", va="top",
                        fontsize=7.5, color=MUREKKEP, arrowprops=dict(arrowstyle="-|>", color=MUREKKEP, lw=0.8))
        else:
            im = g.pm2_5.idxmax()
            ax.plot(g.loc[im, "tl"], g.loc[im, "pm2_5"], "o", ms=7, mfc="none", mec=MUREKKEP, mew=1.3)
            ax.annotate(f"en yüksek kayıt {tr(g.loc[im, 'pm2_5'], 0)} µg/m³ ({g.loc[im, 'tl'].strftime('%H:%M')})",
                        xy=(g.loc[im, "tl"], g.loc[im, "pm2_5"]), xytext=(-14, 8), textcoords="offset points", fontsize=7.5,
                        va="bottom", ha="right", color=MUREKKEP)
        ax.set_title(f"({'ab'[k_]}) Oturum {o} · {r.tarih}.2026 · {aciklama}", loc="left", fontsize=10)
        ax.text(0.01 if kutu == "sol" else 0.99, 0.95,
                f"K_TWA = {tr(r.k_twa, 2)}\nen yüksek kayan ortalama: 15 dk {tr(r.m15)} · 60 dk {tr(r.m60)} µg/m³",
                transform=ax.transAxes, fontsize=7.8, va="top", ha="left" if kutu == "sol" else "right", color=MUREKKEP,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
        ax.set_ylabel("PM₂.₅ (µg/m³)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=veri.TZ))
        virgul_eksen(ax)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=DEVICE_COLOR["purpleair"], lw=1.3, label="PurpleAir, US EPA düzeltmeli (2 dk)"),
         Line2D([], [], color=DEVICE_COLOR["atmotube"], lw=1.0, label="Atmotube, ham (kişisel; 1–2 dk)"),
         Line2D([], [], color=MUREKKEP, lw=1.0, label="Atmotube 15 dk kayan ortalama")]
    fig.legend(handles=h, loc="lower left", bbox_to_anchor=(0.08, 0.075), ncol=2, frameon=False, fontsize=7.8)
    axs[1].set_xlabel("Saat (Türkiye saati)")
    kaynak_notu(fig, "Kaynak: Atmotube PRO saha oturumları (ham PM₂.₅) ve PurpleAir PA-II (SUMER çatısı; sensör arşivi, 2 dk, US EPA düzeltmeli).\n"
                     "Konum bilgisi gösterilmemiştir (KVKK). Ani yükselmeler ayıklanmamıştır.")
    fig.subplots_adjust(top=0.95, bottom=0.21, hspace=0.38, left=0.09, right=0.98)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil08_oturum_seri.png"))
    plt.close(fig)

    # ── Şekil 9: (a) oturum TWA ve eş zamanlı PurpleAir; (b) K dağılımları ──
    fig = plt.figure(figsize=(7.5, 6.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.30)
    ax = fig.add_subplot(gs[0])
    y = np.arange(len(t))[::-1]
    for yi, (o, r) in zip(y, t.iterrows()):
        ax.plot([r.twa, r.pa_twa], [yi, yi], color=IZGARA, lw=2.2, zorder=2, solid_capstyle="round")
        ax.plot(r.pa_twa, yi, "o", color=DEVICE_COLOR["purpleair"], ms=6.5, mec="white", mew=1.2, zorder=3)
        ax.plot(r.twa, yi, "o", color=DEVICE_COLOR["atmotube"], ms=6.5, mec="white", mew=1.2, zorder=4)
        ax.text(21.3, yi, tr(r.k_twa, 2), va="center", ha="left", fontsize=7.5, color=MUREKKEP)
    ax.text(21.3, y.max() + 0.85, "K_TWA", fontsize=7.5, color=IKINCIL, ha="left")
    ax.set_yticks(y, [f"Oturum {o} · {r.tarih}" for o, r in t.iterrows()], fontsize=8)
    ax.set_xlim(0, 21)
    ax.set_ylim(-0.7, y.max() + 1.3)
    ax.set_xlabel("ortalama PM₂.₅ (µg/m³)")
    ax.set_title("(a) Oturum ortalaması: kişisel ve çatı", loc="left", fontsize=10)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=DEVICE_COLOR["atmotube"], marker="o", lw=0, ms=6, label="Atmotube (kişisel, ham)"),
         Line2D([], [], color=DEVICE_COLOR["purpleair"], marker="o", lw=0, ms=6, label="PurpleAir (EPA, aynı anlar)")]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.45, -0.11), frameon=False, fontsize=7.5, ncol=1)
    virgul_eksen(ax, "x")
    ax2 = fig.add_subplot(gs[1])
    gruplar = [("Saha: Kimya binası (büyük olasılıkla iç ortam)", kk[pd_.kimya].values),
               ("Saha: bina dışı ve diğer binalar", kk[~pd_.kimya].values),
               ("ATP canlı kayıtlar (Haziran–Ekim)", aa.K.values)]
    pos = [2.6, 1.6, 0.6]
    for p_, (ad, v) in zip(pos, gruplar):
        v = v[np.isfinite(v) & (v > 0)]
        q5, q25, q50, q75, q95 = np.percentile(v, [5, 25, 50, 75, 95])
        ax2.plot([q5, q95], [p_, p_], color=GRI, lw=1.2, zorder=2)
        ax2.add_patch(plt.Rectangle((q25, p_ - 0.16), q75 - q25, 0.32, fc=DEVICE_COLOR["atmotube"], alpha=0.35, ec="none", zorder=3))
        ax2.plot([q50, q50], [p_ - 0.2, p_ + 0.2], color=MUREKKEP, lw=1.8, zorder=4)
        ax2.text(0.125, p_ + 0.27, ad, fontsize=7.6, color=MUREKKEP, va="bottom")
        ax2.text(q50 * 1.04, p_ - 0.24, f"ortanca {tr(q50, 2)} · n = {tr(len(v), 0)}", fontsize=7.2, color=IKINCIL, va="top")
    for f_, ad, yy, ha_ in [(0.25, "0,25 mekanik", 3.55, "center"), (0.5, "kapalı pencere 0,5 ", 3.32, "right"),
                            (0.8, "0,8 açık pencere", 3.55, "center"), (1.0, " 1 açık hava", 3.32, "left")]:
        ax2.axvline(f_, color=GRI, lw=0.7, zorder=1, ymax=(yy - 0.1 + 0.05) / 3.95)
        ax2.text(f_, yy, ad, fontsize=6.8, ha=ha_, va="bottom", color=IKINCIL)
    ax2.text(0.125, 3.78, "uygulamanın F değerleri:", fontsize=6.8, color=IKINCIL, va="bottom")
    ax2.set_xscale("log")
    ax2.set_xlim(0.12, 4)
    ax2.set_xticks([0.25, 0.5, 1, 2, 4], ["0,25", "0,5", "1", "2", "4"])
    ax2.minorticks_off()
    ax2.set_ylim(0.1, 4.05)
    ax2.set_yticks([])
    ax2.spines["left"].set_visible(False)
    ax2.set_xlabel("K = Atmotube / düzeltilmiş PurpleAir\n(logaritmik eksen)")
    ax2.set_title("(b) Kişisel / çatı oranı K", loc="left", fontsize=10)
    ax2.grid(axis="y", visible=False)
    kaynak_notu(fig, "Kaynak: Atmotube PRO (saha oturumları 27–30 Nisan; ATP-1…5 canlı kayıtlar 15 Haziran – 12 Ekim, kampüs içi) ve\n"
                     "PurpleAir PA-II (US EPA düzeltmeli). (b) Kutu: çeyrekler arası; kalın çizgi: ortanca; ince çizgi: %5–95.\n"
                     "F: uygulamanın iç/dış katsayıları (maruziyet_yontemi.md §4.4).")
    fig.subplots_adjust(top=0.93, bottom=0.22, left=0.20, right=0.98)
    fig.savefig(os.path.join(cikti, "sekiller", "sekil09_kisisel_oran.png"))
    plt.close(fig)

    S.ekle("D.saha_K_kimya_ortanca", round(float(kk[pd_.kimya].median()), 2), "oran", "saha noktaları, Kimya binası: K ortancası", Q)
    S.ekle("D.saha_K_disari_ortanca", round(float(kk[~pd_.kimya].median()), 2), "oran", "saha noktaları, Kimya binası dışı: K ortancası", Q)
    S.yaz(os.path.join(cikti, "sayilar.json"))
    print("D tamam:", len(S.d), "sayı")
    print(t.round(2).to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
