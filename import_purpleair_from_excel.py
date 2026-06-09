"""
Ayşe'nin Excel dosyasındaki 'purple air data' sütununu
purpleair_readings tablosuna aktarır.

27 Nisan ve 28 Nisan verilerini işler.
Zaten var olan kayıtları atlar (INSERT OR IGNORE + UNIQUE).
"""

import pandas as pd
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

EXCEL = 'atmotube_deneme_harita/Ayse_27_30_Nisan.xlsx'
DB    = 'backend/campus_air.db'

# PurpleAir sensör koordinatı (SUMER Lab çatısı)
PA_LAT = 40.806155
PA_LON = 29.360985

# ---------------------------------------------------------------------------
# Excel'i oku, 27 ve 28 Nisan filtrele
# ---------------------------------------------------------------------------
df = pd.read_excel(EXCEL)
df = df[df['Date'].dt.date.isin([
    pd.Timestamp('2026-04-27').date(),
    pd.Timestamp('2026-04-28').date(),
])].copy()

# purple air data sütununu temizle
df = df.dropna(subset=['purple air data'])
df = df[df['purple air data'] > 0].copy()
df = df.reset_index(drop=True)

print(f"Toplam PurpleAir satırı (27+28 Nisan): {len(df)}")
print(f"PM2.5 aralığı: {df['purple air data'].min():.1f} – {df['purple air data'].max():.1f} µg/m³")
print(f"Tarih aralığı: {df['Date'].min()} → {df['Date'].max()}")

# ---------------------------------------------------------------------------
# DB bağlantısı
# ---------------------------------------------------------------------------
con = sqlite3.connect(DB)
cur = con.cursor()

# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------
inserted = 0
skipped  = 0

for _, row in df.iterrows():
    ts = row['Date'].strftime('%Y-%m-%dT%H:%M:%S')
    pm25 = float(row['purple air data'])
    # Atmotube sütunlarından sıcaklık/nem al (varsa)
    temp = float(row['Temperature, ˚C']) if pd.notna(row.get('Temperature, ˚C')) else None
    hum  = float(row['Humidity, %'])     if pd.notna(row.get('Humidity, %'))     else None

    # Zaten bu timestamp var mı kontrol et
    cur.execute("SELECT id FROM purpleair_readings WHERE recorded_at=?", (ts,))
    if cur.fetchone():
        skipped += 1
        continue
    try:
        cur.execute("""
            INSERT INTO purpleair_readings
                (recorded_at, pm2_5, pm2_5_a, pm2_5_b,
                 temperature_c, humidity_pct, lat, lon)
            VALUES (?,?,?,?,?,?,?,?)
        """, (ts, pm25, pm25, pm25, temp, hum, PA_LAT, PA_LON))
        inserted += 1
    except Exception as e:
        print(f"Hata ({ts}): {e}")

con.commit()
con.close()

print(f"\nEklendi : {inserted} satır")
print(f"Atlandı : {skipped} satır (zaten vardı)")
print("\nHazır! Animasyon sırasında PurpleAir paneli bu değerleri gösterecek.")
