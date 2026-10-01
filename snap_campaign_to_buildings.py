"""
Kampanya saha ölçümlerini (Ayşe / İlker / Serra, 27-30 Nisan) Serra'nın kampüs
haritasındaki GERÇEK bina poligonlarının içine yerleştirir.

Neden: Bu ölçümlerde GPS yok; koordinatlar aktiviteye göre elle verilmişti ve bazıları
bina sınırının kenarına/dışına düşüyordu. Artık her ölçüm, Excel'deki aktivitesine
karşılık gelen binanın (veya yeşil alan/otoparkın) içinde, kenardan biraz içeride,
tekrarlanabilir (deterministik) rastgele bir noktaya konur.

- ATP-1..5 canlı oturumlarına (gerçek GPS) DOKUNMAZ.
- Yürüyüş ölçümlerinin koordinatı korunur (binalar arası rota).
- Yazmadan önce mevcut koordinatların yedeğini backups/ altına CSV olarak yazar.
- Her zaman yerel SQLite'ı (backend/campus_air.db) günceller; SUPABASE_DB_URL
  ortam değişkeni verilirse Supabase'i de (atmotube_readings + measurements/saha).

Kullanım:
    python snap_campaign_to_buildings.py --dry-run          # sadece rapor
    set SUPABASE_DB_URL=postgresql://...  (Render > Environment > DATABASE_URL)
    python snap_campaign_to_buildings.py
"""
import os, sys, json, csv, math, random, hashlib, sqlite3, datetime
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.abspath(__file__))
DRY = "--dry-run" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# ── kampüs poligonları ────────────────────────────────────────────────
FC = json.load(open(os.path.join(ROOT, "frontend_v2", "data", "campus.geojson"), encoding="utf-8"))
FEATS = [f for f in FC["features"] if f["geometry"]["type"] == "Polygon"]

def ring(f):      return f["geometry"]["coordinates"][0]          # [[lon,lat],...]
def holes(f):     return f["geometry"]["coordinates"][1:]
def bbox(r):      xs = [p[0] for p in r]; ys = [p[1] for p in r]; return min(xs), min(ys), max(xs), max(ys)
def centroid(r):  return sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
def area(r):      return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2

def in_ring(x, y, r):
    inside = False
    for i in range(len(r)):
        (xi, yi), (xj, yj) = r[i], r[i - 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
    return inside

def inside(f, x, y):
    return in_ring(x, y, ring(f)) and not any(in_ring(x, y, h) for h in holes(f))

INSET = 0.000018   # ~1.5-2 m: nokta kenar çizgisinin üstüne düşmesin

def sample(fs, rng):
    """Bir veya birkaç poligonun içinde (alan ağırlıklı) kenardan içeride rastgele nokta."""
    f = rng.choices(fs, weights=[area(ring(f)) for f in fs])[0]
    a, b, c, d = bbox(ring(f))
    for _ in range(4000):
        x, y = rng.uniform(a, c), rng.uniform(b, d)
        if all(inside(f, x + dx, y + dy) for dx, dy in
               ((0, 0), (INSET, 0), (-INSET, 0), (0, INSET), (0, -INSET))):
            return y, x
    x, y = centroid(ring(f))
    return y, x

def by_name(name):
    fs = [f for f in FEATS if f["properties"]["name"] == name]
    if not fs:
        raise SystemExit(f"Bina bulunamadı: {name}")
    return fs

def nearest(cat, to_name):
    cx, cy = centroid(ring(by_name(to_name)[0]))
    cands = [f for f in FEATS if f["properties"]["cat"] == cat]
    return [min(cands, key=lambda f: math.dist(centroid(ring(f)), (cx, cy)))]

CEVRE = "Kimya ve Çevre Mühendisliği Bölümü"
T = {
    "cevre":      by_name(CEVRE),
    "guzide":     by_name("Güzide Kafe"),
    "guzide_dis": nearest("yesil", "Güzide Kafe"),
    "kutuphane":  by_name("Kütüphane"),
    "kut_onu":    by_name("Bina 9 Kütüphane Açık Alanı"),
    "kongre":     by_name("Kongre ve Kültür Merkezi"),
    "yurt":       by_name("KYK Nilüfer Hatun Kız Yurdu"),
    "merkez":     by_name("Merkez Amfi"),
    "otopark":    nearest("otopark", CEVRE),
    "arka":       nearest("yesil", CEVRE),
}

# Aktivite → hedef. Sıra önemli: özgül anahtarlar önce. None = koordinatı koru.
RULES = [
    ("yürüy", None), ("yürüme", None), ("kampüs içi", None),
    ("kütüphane önü", "kut_onu"), ("kütüphane", "kutuphane"),
    ("dış güzide", "guzide_dis"), ("iç güzide", "guzide"), ("güzide", "guzide"),
    ("kongre", "kongre"), ("yurt", "yurt"), ("merkezi", "merkez"),
    ("otopark", "otopark"),
    ("arka bahçe", "arka"), ("arka bahce", "arka"),
    # Çevre/Kimya binası içi: ofisler, koridor, laboratuvarlar, amfi, seminer, CEV111, ZL
    ("ofis", "cevre"), ("koridor", "cevre"), ("yemek", "cevre"), ("amfi", "cevre"),
    ("kimya", "cevre"), ("cev111", "cevre"), ("seminer", "cevre"), ("zl-", "cevre"),
]
TRANSPORT = ("araba", "marmaray", "otobüs", "istasyon", "sogutlucesme", "soğutluçeşme",
             "taksi", "minibüs", "metro")

def target(act):
    a = str(act).strip().lower()
    for key, t in RULES:
        if key in a:
            return t
    return None

# ── Excel → (kişi, yerel zaman) → aktivite ─────────────────────────────
FILES = [("Ayse", "Ayşe", "Ayse_27_30_Nisan.xlsx", "Activity"),
         ("Ilker", "İlker", "IlkerAkmirza_TEMIZ_VERİ.xlsx", "Notlar"),
         ("Serra", "Serra", "SerraSaracoglu_1002Olcum_27Apr01May_wPurpleAir.xlsx", "Activity")]
PERSON = {k: p for k, p, _, _ in FILES}
ACT = {}
for key, _, fname, col in FILES:
    df = pd.read_excel(os.path.join(ROOT, "atmotube_deneme_harita", fname))
    df = df[~df[col].astype(str).str.lower().apply(lambda a: any(t in a for t in TRANSPORT))]
    for d, a in zip(pd.to_datetime(df["Date"]), df[col]):
        ACT.setdefault((key, d.strftime("%Y-%m-%d %H:%M:%S")), a)   # mükerrer zamanda ilki
print(f"Excel'den {len(ACT)} (kişi, zaman) → aktivite eşlemesi okundu.")

def new_coord(key, ts):
    a = ACT.get((key, ts))
    t = target(a) if a is not None else None
    if t is None:
        return None, a
    seed = int(hashlib.md5(f"{key}|{ts}".encode()).hexdigest()[:12], 16)
    lat, lon = sample(T[t], random.Random(seed))
    return (round(lat, 7), round(lon, 7)), t

def plan(rows, label):
    """rows: (id, session_name, 'YYYY-MM-DD HH:MM:SS' TR, lat, lon) → güncelleme listesi."""
    upd, stats, kept = [], {}, {}
    for rid, sname, ts, lat, lon in rows:
        key = sname.split("_")[0]
        c, t = new_coord(key, ts)
        if c is None:
            k = f"{key}: {t}"; kept[k] = kept.get(k, 0) + 1
            continue
        upd.append((rid, key, ts, c[0], c[1]))
        stats[t] = stats.get(t, 0) + 1
    print(f"\n[{label}] {len(rows)} kampanya ölçümü → yeniden yerleştirilecek {len(upd)}, "
          f"koordinatı korunan {sum(kept.values())}")
    for t, n in sorted(stats.items(), key=lambda x: -x[1]):
        p = T[t][0]["properties"]
        print(f"   {n:>5}  {t:<11} → {p['name'] or p['cat']}")
    print("   korunanlar (yürüyüş / eşleşmeyen):")
    for a, n in sorted(kept.items(), key=lambda x: -x[1])[:25]:
        print(f"   {n:>5}  {a}")
    return upd

def backup(rows, label):
    path = os.path.join(ROOT, "backups", f"kampanya_koordinat_yedek_{label}_{STAMP}.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["reading_id", "session", "recorded_at_TR", "lat", "lon"]); w.writerows(rows)
    print("   yedek:", os.path.relpath(path, ROOT))

# ── yerel SQLite (zaman yerel metin olarak saklı) ──────────────────────
sl = sqlite3.connect(os.path.join(ROOT, "backend", "campus_air.db"))
sc = sl.cursor()
sc.execute("""SELECT r.id, s.session_name, replace(substr(r.recorded_at,1,19),'T',' '), r.lat, r.lon
              FROM atmotube_readings r JOIN upload_sessions s ON s.id = r.session_id
              WHERE s.session_name GLOB 'Ayse_*_Demo' OR s.session_name GLOB 'Ilker_*_Demo'
                 OR s.session_name GLOB 'Serra_*_Demo'""")
rows = sc.fetchall()
upd = plan(rows, "yerel SQLite")
if not DRY:
    backup(rows, "sqlite")
    sc.executemany("UPDATE atmotube_readings SET lat=?, lon=? WHERE id=?",
                   [(lat, lon, rid) for rid, _, _, lat, lon in upd])
    sl.commit()
    print("   yerel SQLite güncellendi:", len(upd))
sl.close()

# ── Supabase (isteğe bağlı) ────────────────────────────────────────────
PG_URL = os.environ.get("SUPABASE_DB_URL", "").strip()
if not PG_URL:
    print("\nSUPABASE_DB_URL verilmedi → Supabase atlandı.")
    sys.exit()

import psycopg2, psycopg2.extras
pg = psycopg2.connect(PG_URL, sslmode="require", connect_timeout=20)
cur = pg.cursor()
cur.execute("""SELECT r.id, s.session_name,
                      to_char(r.recorded_at AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI:SS'),
                      r.lat, r.lon
               FROM atmotube_readings r JOIN upload_sessions s ON s.id = r.session_id
               WHERE s.session_name ~ '^(Ayse|Ilker|Serra)_[0-9]{8}_Demo$'""")
rows = cur.fetchall()
upd = plan(rows, "Supabase")
if DRY:
    print("\n--dry-run: hiçbir veritabanına yazılmadı."); pg.close(); sys.exit()

backup(rows, "supabase")
psycopg2.extras.execute_values(cur, """
    UPDATE atmotube_readings r SET lat = v.lat, lon = v.lon
    FROM (VALUES %s) AS v(id, lat, lon) WHERE r.id = v.id""",
    [(rid, lat, lon) for rid, _, _, lat, lon in upd], page_size=1000)
psycopg2.extras.execute_values(cur, """
    UPDATE measurements m SET lat = v.lat, lon = v.lon
    FROM (VALUES %s) AS v(device, ts, lat, lon)
    WHERE m.source = 'saha' AND m.device = v.device
      AND m.recorded_at = (v.ts::timestamp AT TIME ZONE 'Europe/Istanbul')""",
    [(PERSON[k], ts, lat, lon) for _, k, ts, lat, lon in upd], page_size=1000)
pg.commit(); pg.close()
print("   Supabase atmotube_readings + measurements(saha) güncellendi:", len(upd))
