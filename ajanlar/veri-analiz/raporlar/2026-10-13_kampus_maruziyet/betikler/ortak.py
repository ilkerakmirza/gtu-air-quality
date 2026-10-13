"""Ortak yardımcılar (Ajan 5 · kampüs hava kalitesi ve kişisel maruziyet raporu, 13 Ekim 2026).

Uygulamanın yöntemlerinin Python karşılıkları; her biri kaynağını belirtir:
  * PurpleAir US EPA düzeltmesi ve kanal denetimi  → frontend_v2/js/colorscale.js (epaCf1, epaPM25, paChannelsAgree, paCorrect)
  * HKİ (0,1'e kesme, doğrusal ara değer)          → colorscale.js (HKI_PM25, hki)
  * Maruziyet modeli F ve IR değerleri              → frontend_v2/js/maruziyet.js (ENV, ACT), docs/maruziyet_yontemi.md
  * Bina eşleştirmesi (içinde ya da sınıra ≤ 15 m)  → frontend_v2/js/campus.js (groupPoints, nearestBuilding)
  * Kampüs sınırı (merkez 40,8114 / 29,3563; 2 km)   → backend/kampus.py, backend/config.py
Bu sabitler betik başında uygulama dosyalarıyla karşılaştırılır (uygulama_ile_esles()); fark varsa betik durur.

Güvenlik: betikler `python3 -I` ile çalıştırılır. -I kullanıcı site-packages'ını yoldan çıkardığı için (numpy, pandas,
matplotlib orada) yalnızca o klasör açıkça eklenir; veri klasörü hiçbir zaman sys.path'e eklenmez.
"""
import json
import math
import os
import re
import site
import sys

if sys.flags.isolated:
    site.addsitedir(site.getusersitepackages())

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5))
TZ = "Europe/Istanbul"

# ── MCP (Supabase execute_sql) çıktısını okuma ─────────────────────────────────────────────
def oku_mcp(yol):
    """Kaydedilmiş execute_sql çıktısından satır listesini döndürür (güvenilmeyen veri: yalnızca JSON olarak ayrıştırılır)."""
    s = open(yol, encoding="utf-8").read()
    if s.lstrip().startswith("{\"result\""):
        s = json.loads(s)["result"]
    m = re.search(r"<untrusted-data-[0-9a-f-]+>\s*(\[.*\])\s*</untrusted-data", s, re.S)
    return json.loads(m.group(1) if m else s)


def oku_tablo(yol):
    """Sorgunun tek satır/tek sütunluk {'alanlar': [...], 'satirlar': [[...]]} çıktısını sözlük listesine çevirir."""
    rows = oku_mcp(yol)
    v = next(iter(rows[0].values()))
    out = {}
    if "satirlar" in v:
        return [dict(zip(v["alanlar"], r)) for r in (v["satirlar"] or [])]
    for k, t in v.items():   # birden çok tablo: {'ad': {'alanlar':…, 'satirlar':…}, …}
        if isinstance(t, dict) and "satirlar" in t:
            out[k] = [dict(zip(t["alanlar"], r)) for r in (t["satirlar"] or [])]
    return out


# ── PurpleAir US EPA düzeltmesi (colorscale.js ile birebir) ───────────────────────────────
def _num(v):
    try:
        return None if v is None or v == "" or (isinstance(v, float) and math.isnan(v)) else float(v)
    except (TypeError, ValueError):
        return None


def _rh(rh):
    rh = _num(rh)
    return 50.0 if rh is None or rh < 0 or rh > 100 else rh


def epa_cf1(cf1, rh):
    cf1 = _num(cf1)
    if cf1 is None:
        return None
    return max(0.0, 0.524 * cf1 - 0.0862 * _rh(rh) + 5.75)


def epa_pm25(x, rh):
    x = _num(x)
    if x is None:
        return None
    rh = _rh(rh)
    if x < 30:
        y = 0.524 * x - 0.0862 * rh + 5.75
    elif x < 50:
        w = x / 20 - 1.5
        y = (0.786 * w + 0.524 * (1 - w)) * x - 0.0862 * rh + 5.75
    elif x < 210:
        y = 0.786 * x - 0.0862 * rh + 5.75
    elif x < 260:
        w = x / 50 - 4.2
        y = ((0.69 * w + 0.786 * (1 - w)) * x - 0.0862 * rh * (1 - w)
             + 2.966 * w + 5.75 * (1 - w) + 8.84e-4 * x * x * w)
    else:
        y = 2.966 + 0.69 * x + 8.84e-4 * x * x
    return max(0.0, y)


def kanal_uyumlu(a, b):
    """True = uyumlu, False = geçersiz (hem ≥ 5 µg/m³ hem ≥ %70 ayrışma), None = kanal verisi yok."""
    a, b = _num(a), _num(b)
    if a is None or b is None:
        return None
    d, m = abs(a - b), (a + b) / 2
    return not (d >= 5 and m > 0 and d / m >= 0.70)


def duzelt(r):
    """paCorrect: (düzeltilmiş PM₂.₅ ya da None, yöntem 'cf1'/'atm', kanal denetimi)."""
    c1a, c1b = _num(r.get("pm2_5_cf1_a")), _num(r.get("pm2_5_cf1_b"))
    cf1 = c1a is not None and c1b is not None
    ok = kanal_uyumlu(c1a, c1b) if cf1 else kanal_uyumlu(r.get("pm2_5_a"), r.get("pm2_5_b"))
    if ok is False:
        return None, ("cf1" if cf1 else "atm"), ok
    if cf1:
        return epa_cf1((c1a + c1b) / 2, r.get("humidity_pct")), "cf1", ok
    raw = _num(r.get("pm2_5"))
    return (None if raw is None else epa_pm25(raw, r.get("humidity_pct"))), "atm", ok


# ── HKİ (colorscale.js → HKI_PM25, hki) ─────────────────────────────────────────────────
HKI_PM25 = [
    (0, 50, 0.0, 12.0, "İyi", "#00cc00"),
    (51, 100, 12.1, 35.4, "Orta", "#ffcc00"),
    (101, 150, 35.5, 55.4, "Hassas", "#ff8800"),
    (151, 200, 55.5, 150.4, "Sağlıksız", "#ff0000"),
    (201, 300, 150.5, 250.4, "Kötü", "#bb44bb"),
    (301, 500, 250.5, 500.4, "Tehlikeli", "#7e0023"),
]


def hki(v):
    """(indeks, sınıf adı, renk) — C 0,1 µg/m³'e kesilir; tablonun üstü 500."""
    v = _num(v)
    if v is None:
        return None
    c = max(0.0, math.floor(v * 10) / 10)   # colorscale.js ile aynı: Math.floor(v * 10) / 10
    for ilo, ihi, clo, chi, ad, renk in HKI_PM25:
        if c <= chi:
            return round((ihi - ilo) / (chi - clo) * (c - clo) + ilo), ad, renk
    ilo, ihi, clo, chi, ad, renk = HKI_PM25[-1]
    return 500, ad, renk


# ── Renkler ──────────────────────────────────────────────────────────────────────────────
DEVICE_COLOR = {"purpleair": "#6380f0", "tuzla": "#bf8418", "atmotube": "#2fa79a"}   # colorscale.js
# Veri görselleştirme rehberinin belgelenmiş paleti (açık zemin): kategorik sıra, tek tonlu mavi rampa, ıraksak çift
KATEGORIK = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SIRALI_MAVI = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
               "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
IRAKSAK = ("#2a78d6", "#f0efec", "#e34948")   # mavi ↔ gri orta nokta ↔ kırmızı
GRI = "#898781"          # soluk (eksen, bağlam)
MUREKKEP = "#0b0b0b"     # birincil metin
IKINCIL = "#52514e"      # ikincil metin
IZGARA = "#e1e0d9"       # kılavuz çizgisi
TABAN = "#c3c2b7"        # eksen çizgisi
ZEMIN = "#ffffff"        # şekil zemini (açık)

# ── Maruziyet modeli (maruziyet.js → ENV, ACT) ─────────────────────────────────────────
F = {"out": 1.0, "vent": 0.8, "closed": 0.5, "mech": 0.25}
F_ARALIK = {"vent": (0.6, 1.0), "closed": (0.3, 0.75), "mech": (0.12, 0.28)}    # maruziyet_yontemi.md §4.4
IR = {"sit": 0.25, "light": 0.72, "walk": 1.56, "sport": 3.0}                     # m³/sa, EPA EFH 2011 Tablo 6-2
IR_P95 = {"sit": 0.39, "light": 0.96, "walk": 2.28, "sport": 4.56}                # m³/sa, aynı tablo, 95. yüzdelik

# ── Kampüs geometrisi (campus.js, kampus.py) ─────────────────────────────────────────────
CAMPUS_LAT, CAMPUS_LON, CAMPUS_RADIUS_KM = 40.8114, 29.3563, 2.0
NEAR_M = 15.0
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(40.81))
GENERIC = re.compile(r"^(bina \d+|küçük binalar)$", re.I)


def kampus_ici(lat, lon):
    """backend/kampus.py → near(): konum yoksa False."""
    lat, lon = _num(lat), _num(lon)
    if lat is None or lon is None:
        return False
    dy = (lat - CAMPUS_LAT) * 111.32
    dx = (lon - CAMPUS_LON) * 111.32 * math.cos(math.radians(CAMPUS_LAT))
    return math.hypot(dx, dy) <= CAMPUS_RADIUS_KM


def xy(lat, lon):
    """Yerel düzlem (m), kampüs merkezine göre; campus.js'teki M_LAT / M_LON katsayıları."""
    return (lon - CAMPUS_LON) * M_LON, (lat - CAMPUS_LAT) * M_LAT


def _rings(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


def _in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def kampus_geojson():
    return json.load(open(os.path.join(REPO, "frontend_v2", "data", "campus.geojson"), encoding="utf-8"))


def binalar(fc=None):
    """campus.js → groupPoints: 'bina' poligonları ve grup anahtarı (gk). Aynı bölge ve addaki bloklar tek binadır."""
    fc = fc or kampus_geojson()
    out = []
    for i, f in enumerate([f for f in fc["features"] if f["properties"].get("cat") == "bina"]):
        p = f["properties"]
        ad = (p.get("name") or "").strip()
        gk = f"{p.get('region')}|{p.get('name')}" if p.get("name") else f"#{i}"
        xs = [pt[0] for poly in _rings(f["geometry"]) for pt in poly[0]]
        ys = [pt[1] for poly in _rings(f["geometry"]) for pt in poly[0]]
        out.append({"gk": gk, "ad": ad, "adsiz": (not ad) or bool(GENERIC.match(ad)), "bolge": p.get("region"),
                    "f": f, "bbox": (min(xs), min(ys), max(xs), max(ys))})
    return out


def _icinde(b, lon, lat):
    a, bb, c, d = b["bbox"]
    if lon < a or lon > c or lat < bb or lat > d:
        return False
    return any(_in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:])
               for poly in _rings(b["f"]["geometry"]))


def _kenar_uzakligi(b, lon, lat):
    best = float("inf")
    for poly in _rings(b["f"]["geometry"]):
        for r in poly:
            for i in range(len(r) - 1):
                ax, ay = (r[i][0] - lon) * M_LON, (r[i][1] - lat) * M_LAT
                dx, dy = (r[i + 1][0] - r[i][0]) * M_LON, (r[i + 1][1] - r[i][1]) * M_LAT
                l2 = dx * dx + dy * dy
                t = max(0.0, min(1.0, -(ax * dx + ay * dy) / l2)) if l2 else 0.0
                best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def bina_bul(blds, lat, lon):
    """(gk, yakın mı) — önce içinde olan ilk bina; yoksa sınırına ≤ 15 m olan en yakın bina (eşitlikte sonraki)."""
    for b in blds:
        if _icinde(b, lon, lat):
            return b["gk"], False
    pad_lat, pad_lon = NEAR_M / M_LAT, NEAR_M / M_LON
    best, best_d = None, NEAR_M
    for b in blds:
        a, bb, c, d = b["bbox"]
        if lon < a - pad_lon or lon > c + pad_lon or lat < bb - pad_lat or lat > d + pad_lat:
            continue
        dist = _kenar_uzakligi(b, lon, lat)
        if dist <= best_d:
            best_d, best = dist, b
    return (best["gk"], True) if best else (None, False)


def bina_etiketi(b):
    """Raporda gösterilecek ad: adsız ya da genel adlı ('Bina 3', 'Küçük Binalar') binalar 'adsız bina'."""
    return "adsız bina" if b["adsiz"] else b["ad"]


# ── Uygulama dosyalarıyla eşleşme denetimi ───────────────────────────────────────────────
def uygulama_ile_esles():
    cs = open(os.path.join(REPO, "frontend_v2/js/colorscale.js"), encoding="utf-8").read()
    mx = open(os.path.join(REPO, "frontend_v2/js/maruziyet.js"), encoding="utf-8").read()
    cp = open(os.path.join(REPO, "frontend_v2/js/campus.js"), encoding="utf-8").read()
    kontrol = [
        ("0.524 * cf1 - 0.0862 * rh + 5.75" in cs, "epaCf1 katsayıları"),
        ("d >= 5 && m > 0 && d / m >= 0.70" in cs, "kanal kuralı"),
        (all(f"chi: {c}" in cs for c in ("12.0", "35.4", "55.4", "150.4", "250.4", "500.4")), "HKİ kesim noktaları"),
        ('purpleair: "#6380f0"' in cs and 'atmotube: "#2fa79a"' in cs, "DEVICE_COLOR"),
        (all(s in mx for s in ("f: 1.0", "f: 0.8", "f: 0.5", "f: 0.25")), "ENV (F)"),
        (all(s in mx for s in ("ir: 0.25", "ir: 0.72", "ir: 1.56", "ir: 3.0")), "ACT (IR)"),
        ("const NEAR_M = 15;" in cp, "15 m kuralı"),
    ]
    bad = [ad for ok, ad in kontrol if not ok]
    if bad:
        raise SystemExit("Uygulama sabitleri değişmiş, betik güncellenmeli: " + ", ".join(bad))


def ekip_esleme():
    """app.js → PEOPLE: oturum adının ön ekinin md5 özeti → 'Saha ekibi X' / 'ATP-n'. Adlar hiçbir çıktıya yazılmaz."""
    import hashlib
    src = open(os.path.join(REPO, "frontend_v2/js/app.js"), encoding="utf-8").read()
    blk = re.search(r"const PEOPLE = \[(.*?)\];", src, re.S).group(1)
    return {hashlib.md5(k.encode()).hexdigest()[:8]: ad
            for k, ad in re.findall(r'key:\s*"([^"]+)",\s*name:\s*"([^"]+)"', blk)}


# ── Biçim ────────────────────────────────────────────────────────────────────────────────
def tr(v, nd=1):
    """Türkçe sayı biçimi (12,3; binlik ayırıcı nokta)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    s = f"{v:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def stil():
    """Açık zeminli, okunaklı matplotlib ayarları (DejaVu Sans: Türkçe karakterler)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11.5, "axes.titleweight": "bold",
        "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "figure.facecolor": ZEMIN, "axes.facecolor": ZEMIN, "savefig.facecolor": ZEMIN,
        "axes.edgecolor": TABAN, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": IZGARA,
        "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "xtick.color": IKINCIL, "ytick.color": IKINCIL,
        "axes.labelcolor": MUREKKEP, "text.color": MUREKKEP, "axes.titlecolor": MUREKKEP,
        "lines.linewidth": 1.6, "lines.solid_capstyle": "round", "axes.formatter.use_locale": False,
        "savefig.dpi": 200, "figure.dpi": 100,
    })
    return plt


def tr_kisa(v):
    """Eksen etiketi: tam sayıysa ondalıksız, değilse en çok iki ondalık (virgülle)."""
    if abs(v - round(v)) < 1e-9:
        return tr(round(v), 0)
    s = tr(v, 2).rstrip("0").rstrip(",")
    return s


def virgul_eksen(ax, eksen="y", nd=None):
    """Eksen etiketlerinde ondalık virgül (nd verilmezse gereken kadar ondalık)."""
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: tr_kisa(v) if nd is None else tr(v, nd))
    (ax.yaxis if eksen == "y" else ax.xaxis).set_major_formatter(fmt)


def bosluk_kir(t, y, en_cok="90min"):
    """Çizgi grafiklerinde veri boşluğunu birleştirmemek için: ardışık iki nokta arası en_cok'tan fazlaysa araya NaN koyar."""
    import pandas as pd
    s = pd.Series(list(y), index=pd.DatetimeIndex(t)).sort_index()
    fark = s.index.to_series().diff() > pd.Timedelta(en_cok)
    ek = s.index[fark] - pd.Timedelta("1min")
    s = pd.concat([s, pd.Series(float("nan"), index=ek)]).sort_index()
    return s.index, s.values


def kaynak_notu(fig, metin, y=0.005):
    fig.text(0.01, y, metin, ha="left", va="bottom", fontsize=7.8, color=IKINCIL)


# ── Sayı kaydı (sayilar.json) ────────────────────────────────────────────────────────────
class Sayilar:
    def __init__(self):
        self.d = {}

    def ekle(self, anahtar, deger, birim, tarif, kaynak, nd=None):
        if isinstance(deger, float) and nd is not None:
            deger = round(deger, nd)
        self.d[anahtar] = {"deger": deger, "birim": birim, "tarif": tarif, "kaynak": kaynak}
        return deger

    def yaz(self, yol):
        old = {}
        if os.path.exists(yol):
            old = json.load(open(yol, encoding="utf-8"))
        old.update(self.d)
        json.dump(dict(sorted(old.items())), open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
