"""
Ayşe'nin 28 Nisan verisinden demo CSV oluşturur ve DB'ye ekler.
Ulaşım satırları çıkarılır, kampüs içi noktalara koordinat atanır.
"""

import pandas as pd
import numpy as np
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# GTÜ Kampüs lokasyon koordinatları
# ---------------------------------------------------------------------------
LAT_KUTUPHANE  = (40.80660983568877, 29.36001945835103)
LAT_CEVRE      = (40.80586271172931, 29.362969888267397)
LAT_KONGRE     = (40.81448660918803, 29.360856307563672)
LAT_GUZIDE     = (40.80605556, 29.36080556)

LOCATIONS = {
    "kütüphane":        LAT_KUTUPHANE,
    "iç güzide":        LAT_GUZIDE,
    "dış güzide":       (LAT_GUZIDE[0] + 0.00008, LAT_GUZIDE[1] - 0.00005),
    "çevre amfi":       (LAT_CEVRE[0] + 0.00015, LAT_CEVRE[1] - 0.00020),
    "çevre koridor":    LAT_CEVRE,
    "kçevre koridor":   LAT_CEVRE,
    "genel kimya lab":  LAT_CEVRE,
    "kongre":           LAT_KONGRE,
    "ofis":             LAT_CEVRE,
    "yurt":             (40.81100, 29.36150),
}

WALKING_ROUTE = [
    LAT_KUTUPHANE,
    (40.80640, 29.36010),
    (40.80625, 29.36035),
    LAT_GUZIDE,
    (40.80598, 29.36050),
    (40.80595, 29.36120),
    (40.80590, 29.36200),
    LAT_CEVRE,
    (40.80600, 29.36150),
    (40.80615, 29.36080),
    LAT_KUTUPHANE,
]

TRANSPORT = ['otobüs', 'marmaray', 'marmaray istasyon', 'istasyon', 'yürüme']

# ---------------------------------------------------------------------------
# Veriyi oku ve filtrele
# ---------------------------------------------------------------------------
df = pd.read_excel('atmotube_deneme_harita/Ayse_27_30_Nisan.xlsx')
df = df[~df['Activity'].str.strip().isin(TRANSPORT)]
df = df[df['Date'].dt.date == pd.Timestamp('2026-04-28').date()].copy()
df = df.reset_index(drop=True)
print(f"Filtreleme sonrası: {len(df)} satır")
print("Aktiviteler:", df['Activity'].value_counts().to_dict())

# ---------------------------------------------------------------------------
# Her satıra GPS koordinatı ata
# ---------------------------------------------------------------------------
walk_idx = 0

def assign_coords(row):
    global walk_idx
    activity = str(row['Activity']).strip().lower()
    for key, coords in LOCATIONS.items():
        if key in activity:
            jitter_lat = np.random.uniform(-0.00005, 0.00005)
            jitter_lon = np.random.uniform(-0.00005, 0.00005)
            return coords[0] + jitter_lat, coords[1] + jitter_lon
    if 'yürüme' in activity or 'kampüs' in activity:
        walk_idx = (walk_idx + 1) % len(WALKING_ROUTE)
        pt = WALKING_ROUTE[walk_idx]
        return pt[0] + np.random.uniform(-0.00008, 0.00008), \
               pt[1] + np.random.uniform(-0.00008, 0.00008)
    return 40.806155 + np.random.uniform(-0.0002, 0.0002), \
           29.360985 + np.random.uniform(-0.0002, 0.0002)

coords = df.apply(assign_coords, axis=1)
df['Latitude']  = [c[0] for c in coords]
df['Longitude'] = [c[1] for c in coords]

# ---------------------------------------------------------------------------
# Çıktı CSV
# ---------------------------------------------------------------------------
out = pd.DataFrame({
    'Date':              df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
    'VOC (ppm)':         (df['VOC, ppm'] / 1000).round(3),
    'PM1 (ug/m3)':       df['PM1, ug/m³'],
    'PM2.5 (ug/m3)':     df['PM2.5, ug/m³'],
    'PM10 (ug/m3)':      df['PM10, ug/m³'],
    'Temperature (C)':   df['Temperature, ˚C'],
    'Humidity (%)':      df['Humidity, %'],
    'Pressure (hPa)':    (df['Pressure, mbar'] / 100).round(2),
    'Latitude':          df['Latitude'].round(6),
    'Longitude':         df['Longitude'].round(6),
})

csv_path = 'ayse_28nisan_demo.csv'
out.to_csv(csv_path, index=False)
print(f"CSV oluşturuldu: {csv_path}  ({len(out)} satır)")
print(f"PM2.5 aralığı: {out['PM2.5 (ug/m3)'].min():.1f} – {out['PM2.5 (ug/m3)'].max():.1f} µg/m³")

# ---------------------------------------------------------------------------
# Doğrudan DB'ye ekle (backend/campus_air.db)
# ---------------------------------------------------------------------------
DB_PATH = 'backend/campus_air.db'
if not os.path.exists(DB_PATH):
    print(f"HATA: {DB_PATH} bulunamadı! Önce backend'i bir kere çalıştırın.")
    sys.exit(1)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Oturum oluştur
cur.execute("""
    INSERT INTO upload_sessions
        (session_name, micro_environment, sensor_number, reading_count,
         start_time, end_time, notes)
    VALUES (?,?,?,?,?,?,?)
""", (
    'Ayse_28Nisan_Demo',
    'outdoor',
    '1',
    len(out),
    out['Date'].min(),
    out['Date'].max(),
    '28 Nisan kampüs ölçümleri (kütüphane, iç güzide, kampüs yürüyüşü)',
))
session_id = cur.lastrowid
print(f"Oturum oluşturuldu: ID={session_id}")

# Ölçümleri ekle
inserted = 0
skipped  = 0
for _, row in out.iterrows():
    try:
        cur.execute("""
            INSERT OR IGNORE INTO atmotube_readings
                (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0,
                 temperature_c, humidity_pct, pressure_hpa, lat, lon)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id,
            row['Date'],
            row['VOC (ppm)'],
            row['PM1 (ug/m3)'],
            row['PM2.5 (ug/m3)'],
            row['PM10 (ug/m3)'],
            row['Temperature (C)'],
            row['Humidity (%)'],
            row['Pressure (hPa)'],
            row['Latitude'],
            row['Longitude'],
        ))
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1
    except Exception as e:
        print(f"Satır hatası: {e}")

con.commit()
con.close()
print(f"DB'ye eklendi: {inserted} satır  (atlandı: {skipped})")
print(f"\nHazır! Haritada 'Ayse_28Nisan_Demo' oturumu görünecek.")
