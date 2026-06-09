"""
İlker ve Serra'nın verilerini DB'ye ekler.
Kampüs dışı (araba, marmaray, soğutluçeşme vb.) hariç tutulur.
"""

import pandas as pd
import numpy as np
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'backend/campus_air.db'
np.random.seed(42)

# ---------------------------------------------------------------------------
# Kampüs koordinatları
# ---------------------------------------------------------------------------
LOC = {
    # İlker lokasyonları
    'ofis':               (40.806155, 29.360985),   # SUMER Lab
    'başka ofis':         (40.806300, 29.361200),
    'koridor':            (40.806200, 29.361100),
    'otopark':            (40.806500, 29.361500),
    'kütüphane':          (40.806610, 29.360019),
    'çevre arka bahçe':   (40.805800, 29.362800),
    'güzide iç ortam':    (40.806056, 29.360806),
    'merkezi derslik':    (40.807000, 29.360500),
    'çevre amfi':         (40.805863, 29.362970),
    'yürüyüş':            None,   # walking route
    'yemek ısıtma':       (40.806155, 29.360985),

    # Serra lokasyonları
    'zl-16 ofis':         (40.807200, 29.361500),
    'zl-07 lab':          (40.807000, 29.361300),
    'kimya laboratuvarı': (40.806500, 29.363000),
    'amfi-1':             (40.807200, 29.360800),
    'cev111':             (40.805900, 29.362900),
    'cevre bina arka bahce': (40.805800, 29.362800),
    'seminer salonu':     (40.806600, 29.362200),
    'kütüphane önü':      (40.806610, 29.360019),
}

WALKING_ROUTE = [
    (40.806610, 29.360019),
    (40.806400, 29.360100),
    (40.806250, 29.360350),
    (40.806056, 29.360806),
    (40.805980, 29.361200),
    (40.805900, 29.362000),
    (40.805863, 29.362970),
    (40.806000, 29.362500),
    (40.806200, 29.361500),
    (40.806155, 29.360985),
]

# Kampüs dışı / ulaşım filtreleri
ILKER_EXCLUDE = ['araba', 'marmaray', 'minibüs', 'otobüs', 'taksi', 'metro']
SERRA_EXCLUDE = ['marmaray', 'sogutlucesme', 'soğutluçeşme', 'otobüs', 'taksi']

walk_idx = 0

def get_coords(activity_raw):
    global walk_idx
    a = str(activity_raw).strip().lower()

    # Çevre Amfi N → amfi koordinatı
    if a.startswith('çevre amfi'):
        return LOC['çevre amfi']

    # Yürüyüş → walking route
    if 'yürüy' in a or 'campus' in a:
        walk_idx = (walk_idx + 1) % len(WALKING_ROUTE)
        pt = WALKING_ROUTE[walk_idx]
        return (pt[0] + np.random.uniform(-0.00008, 0.00008),
                pt[1] + np.random.uniform(-0.00008, 0.00008))

    # Bilinen lokasyonlar
    for key, coords in LOC.items():
        if coords and key in a:
            return (coords[0] + np.random.uniform(-0.00005, 0.00005),
                    coords[1] + np.random.uniform(-0.00005, 0.00005))

    # Varsayılan: kampüs merkezi
    return (40.806155 + np.random.uniform(-0.0002, 0.0002),
            29.360985 + np.random.uniform(-0.0002, 0.0002))


def insert_session(con, name, note, readings_df):
    cur = con.cursor()
    # Mükerrer oturum kontrolü
    cur.execute("SELECT id FROM upload_sessions WHERE session_name=?", (name,))
    row = cur.fetchone()
    if row:
        print(f"  ⚠ Oturum zaten var, atlandı: {name}")
        return

    cur.execute("""
        INSERT INTO upload_sessions
            (session_name, micro_environment, sensor_number, reading_count,
             start_time, end_time, notes)
        VALUES (?,?,?,?,?,?,?)
    """, (
        name, 'outdoor', '2',
        len(readings_df),
        str(readings_df['recorded_at'].min()),
        str(readings_df['recorded_at'].max()),
        note,
    ))
    session_id = cur.lastrowid

    inserted = 0
    for _, r in readings_df.iterrows():
        try:
            cur.execute("""
                INSERT OR IGNORE INTO atmotube_readings
                    (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0,
                     temperature_c, humidity_pct, pressure_hpa, lat, lon)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id,
                str(r['recorded_at']),
                r.get('voc', None),
                r.get('pm1', None),
                r['pm25'],
                r.get('pm10', None),
                r.get('temp', None),
                r.get('hum', None),
                r.get('pressure', None),
                r['lat'],
                r['lon'],
            ))
            if cur.rowcount:
                inserted += 1
        except Exception as e:
            print(f"    Satır hatası: {e}")

    con.commit()
    print(f"  ✓ {name}: {inserted} satır eklendi (session_id={session_id})")


# ---------------------------------------------------------------------------
# İLKER VERİSİ
# ---------------------------------------------------------------------------
print("=== İLKER VERİSİ ===")
df_ilker = pd.read_excel('atmotube_deneme_harita/IlkerAkmirza_TEMIZ_VERİ.xlsx')
df_ilker = df_ilker.rename(columns={'Notlar': 'Activity'})

# Ulaşım filtresi
def ilker_exclude(act):
    a = str(act).strip().lower()
    return any(x in a for x in ILKER_EXCLUDE)

df_ilker = df_ilker[~df_ilker['Activity'].apply(ilker_exclude)].copy()
print(f"Filtreleme sonrası: {len(df_ilker)} satır")

# Koordinat ata
coords = df_ilker['Activity'].apply(get_coords)
df_ilker['lat'] = [c[0] for c in coords]
df_ilker['lon'] = [c[1] for c in coords]

# Normalize sütunlar
df_ilker['recorded_at'] = pd.to_datetime(df_ilker['Date'])
df_ilker['voc']      = pd.to_numeric(df_ilker.get('VOC, ppm'), errors='coerce') / 1000
df_ilker['pm1']      = pd.to_numeric(df_ilker.get('PM1, ug/mÂ³'), errors='coerce')
df_ilker['pm25']     = pd.to_numeric(df_ilker.get('PM2.5, ug/mÂ³'), errors='coerce')
df_ilker['pm10']     = pd.to_numeric(df_ilker.get('PM10, ug/mÂ³'), errors='coerce')
df_ilker['temp']     = pd.to_numeric(df_ilker.get('Temperature, ËšC'), errors='coerce')
df_ilker['hum']      = pd.to_numeric(df_ilker.get('Humidity, %'), errors='coerce')
df_ilker['pressure'] = pd.to_numeric(df_ilker.get('Pressure, hPa'), errors='coerce')

# Günlük oturumlar
con = sqlite3.connect(DB_PATH)
for day in sorted(df_ilker['recorded_at'].dt.date.unique()):
    day_df = df_ilker[df_ilker['recorded_at'].dt.date == day].copy()
    session_name = f"Ilker_{day.strftime('%Y%m%d')}_Demo"
    note = f"İlker Akmirza {day} kampüs ölçümleri"
    insert_session(con, session_name, note, day_df)

con.close()

# ---------------------------------------------------------------------------
# SERRA VERİSİ
# ---------------------------------------------------------------------------
print("\n=== SERRA VERİSİ ===")
walk_idx = 0  # reset
df_serra = pd.read_excel('atmotube_deneme_harita/SerraSaracoglu_1002Olcum_27Apr01May_wPurpleAir.xlsx')

# Ulaşım filtresi
def serra_exclude(act):
    a = str(act).strip().lower()
    return any(x in a for x in SERRA_EXCLUDE)

df_serra = df_serra[~df_serra['Activity'].apply(serra_exclude)].copy()
print(f"Filtreleme sonrası: {len(df_serra)} satır")

# Koordinat ata
coords = df_serra['Activity'].apply(get_coords)
df_serra['lat'] = [c[0] for c in coords]
df_serra['lon'] = [c[1] for c in coords]

# Normalize sütunlar
df_serra['recorded_at'] = pd.to_datetime(df_serra['Date'])
df_serra['voc']      = pd.to_numeric(df_serra.get('VOC, ppm'), errors='coerce') / 1000
df_serra['pm1']      = pd.to_numeric(df_serra.get('PM1, ug/m3'), errors='coerce')
df_serra['pm25']     = pd.to_numeric(df_serra.get('PM2.5, ug/m3'), errors='coerce')
df_serra['pm10']     = pd.to_numeric(df_serra.get('PM10, ug/m3'), errors='coerce')
df_serra['temp']     = None
df_serra['hum']      = None
df_serra['pressure'] = pd.to_numeric(df_serra.get('Pressure, mbar'), errors='coerce')

con = sqlite3.connect(DB_PATH)
for day in sorted(df_serra['recorded_at'].dt.date.unique()):
    day_df = df_serra[df_serra['recorded_at'].dt.date == day].copy()
    session_name = f"Serra_{day.strftime('%Y%m%d')}_Demo"
    note = f"Serra Saraçoğlu {day} kampüs ölçümleri"
    insert_session(con, session_name, note, day_df)

con.close()

print("\nTüm veriler eklendi!")
