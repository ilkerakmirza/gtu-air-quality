"""
Tüm Atmotube demo oturumlarını (Ayşe, İlker, Serra) düzgün koordinatlarla
yeniden üretir. Önceki hata: çoğu nokta PurpleAir konumuna (SUMER Lab çatısı)
yığılıyordu — çünkü 'ofis' anahtarı GTU_CENTER'a eşleniyor ve alt-dize
eşleşmesiyle 'zl-16 ofis' gibi aktiviteleri de oraya çekiyordu; eşleşmeyenler de
varsayılan olarak oraya düşüyordu.

Bu script: upload_sessions + atmotube_readings tablolarını siler (purpleair_readings
korunur), üç Excel dosyasından düzgün koordinatlarla yeniden yükler.
"""

import pandas as pd
import numpy as np
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'backend/campus_air.db'
np.random.seed(42)

# PurpleAir / SUMER Lab çatısı — ÖLÇÜMLER BURAYA KONMAMALI
PA = (40.806155, 29.360985)

# GTÜ kampüs lokasyonları (PurpleAir noktasından ayrı, gerçekçi dağılım)
L = {
    # Çevre Mühendisliği binası bölgesi
    'cevre_amfi':    (40.805863, 29.362970),
    'cevre_koridor': (40.805820, 29.362900),
    'cevre_arka':    (40.805650, 29.363300),
    'cev111':        (40.805900, 29.362930),
    # Kütüphane
    'kutuphane':     (40.806610, 29.360019),
    'kutuphane_onu': (40.806550, 29.360110),
    # Güzide kafe
    'ic_guzide':     (40.806056, 29.360806),
    'dis_guzide':    (40.806140, 29.360760),
    # Kongre / Kültür merkezi
    'kongre':        (40.814487, 29.360856),
    # Laboratuvarlar / derslikler
    'kimya_lab':     (40.806500, 29.362800),
    'merkezi_ders':  (40.807200, 29.360500),
    'amfi1':         (40.807000, 29.360800),
    'seminer':       (40.806600, 29.362200),
    # Yurt
    'yurt':          (40.811000, 29.361500),
    # İlker ofisi (Çevre binası ofis kanadı) — PA'dan AYRI
    'ilker_ofis':    (40.805750, 29.363150),
    'ilker_ofis2':   (40.805950, 29.363250),
    'ilker_koridor': (40.805840, 29.363050),
    'otopark':       (40.805200, 29.362400),
    # Serra ZL binası — PA'dan AYRI
    'zl_ofis':       (40.805250, 29.361750),
    'zl_lab':        (40.805320, 29.361850),
    # Kampüs ortası (varsayılan — PA değil!)
    'kampus':        (40.806400, 29.361600),
}

WALK = [
    L['kutuphane'], (40.806400, 29.360200), (40.806250, 29.360500),
    L['ic_guzide'], (40.805980, 29.361200), (40.805900, 29.362000),
    L['cevre_amfi'], (40.806000, 29.362400), (40.806300, 29.361500), (40.806450, 29.360900),
]

# Aktivite → lokasyon eşlemesi. ÖNEM SIRASINA göre kontrol edilir (en özgül önce).
# (anahtar_alt_dize, lokasyon) — ilk eşleşen kazanır.
RULES = [
    ('zl-16 ofis',    'zl_ofis'),
    ('zl-07 lab',     'zl_lab'),
    ('başka ofis',    'ilker_ofis2'),
    ('ofis /cam',     'ilker_ofis2'),
    ('ofis/kolonya',  'ilker_ofis'),
    ('ofis /kolonya', 'ilker_ofis'),
    ('yemek',         'ilker_ofis'),
    ('koridor',       'ilker_koridor'),
    ('çevre koridor', 'cevre_koridor'),
    ('kçevre koridor','cevre_koridor'),
    ('çevre arka',    'cevre_arka'),
    ('cevre bina arka','cevre_arka'),
    ('çevre amfi',    'cevre_amfi'),
    ('cev111',        'cev111'),
    ('amfi-1',        'amfi1'),
    ('amfi',          'amfi1'),
    ('seminer',       'seminer'),
    ('kimya',         'kimya_lab'),
    ('genel kimya',   'kimya_lab'),
    ('merkezi',       'merkezi_ders'),
    ('kütüphane önü', 'kutuphane_onu'),
    ('kütüphane',     'kutuphane'),
    ('kongre',        'kongre'),
    ('iç güzide',     'ic_guzide'),
    ('güzide iç',     'ic_guzide'),
    ('dış güzide',    'dis_guzide'),
    ('güzide',        'ic_guzide'),
    ('yurt',          'yurt'),
    ('otopark',       'otopark'),
    ('ofis',          'ilker_ofis'),   # genel 'ofis' EN SONDA (zl-16/başka ofis önce yakalanır)
]

WALK_KEYS = ('yürüy', 'yürüme', 'kampüs içi')
TRANSPORT = ('araba', 'marmaray', 'otobüs', 'istasyon', 'sogutlucesme', 'soğutluçeşme',
             'taksi', 'minibüs', 'metro')

walk_idx = 0

def jitter(coord, amt=0.00012):
    return (coord[0] + np.random.uniform(-amt, amt),
            coord[1] + np.random.uniform(-amt, amt))

def assign(activity):
    global walk_idx
    a = str(activity).strip().lower()
    if a in ('nan', 'none', ''):
        return jitter(L['kampus'], 0.0002)
    # Yürüyüş → rota üzerinde ilerle
    if any(k in a for k in WALK_KEYS):
        walk_idx = (walk_idx + 1) % len(WALK)
        return jitter(WALK[walk_idx], 0.00010)
    # Kurallar (özgülden genele)
    for key, loc in RULES:
        if key in a:
            return jitter(L[loc])
    # Varsayılan: kampüs ortası (PA DEĞİL)
    return jitter(L['kampus'], 0.0002)

def is_transport(activity):
    a = str(activity).strip().lower()
    return any(t in a for t in TRANSPORT)

def col(df, *cands):
    """Esnek sütun bulucu (encoding farklılıklarına dayanıklı)."""
    for c in cands:
        if c in df.columns:
            return c
    # kısmi eşleşme
    for c in df.columns:
        for cand in cands:
            if cand.split(',')[0] in c:
                return c
    return None

# ---------------------------------------------------------------------------
FILES = [
    ('Ayse',  'atmotube_deneme_harita/Ayse_27_30_Nisan.xlsx', 'Activity', 'mbar'),
    ('Ilker', 'atmotube_deneme_harita/IlkerAkmirza_TEMIZ_VERİ.xlsx', 'Notlar', 'hPa'),
    ('Serra', 'atmotube_deneme_harita/SerraSaracoglu_1002Olcum_27Apr01May_wPurpleAir.xlsx', 'Activity', 'mbar'),
]

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Eski demo verisini temizle (PurpleAir korunur!)
cur.execute("DELETE FROM atmotube_readings")
cur.execute("DELETE FROM upload_sessions")
con.commit()
print("Eski Atmotube oturumları temizlendi (PurpleAir korundu).\n")

total_sessions = 0
for who, path, act_col, press_unit in FILES:
    df = pd.read_excel(path)
    df = df.rename(columns={act_col: 'Activity'})
    df = df[~df['Activity'].apply(is_transport)].copy()
    df['Date'] = pd.to_datetime(df['Date'])

    c_voc  = col(df, 'VOC, ppm')
    c_pm1  = col(df, 'PM1, ug/m³', 'PM1, ug/mÂ³', 'PM1, ug/m3')
    c_pm25 = col(df, 'PM2.5, ug/m³', 'PM2.5, ug/mÂ³', 'PM2.5, ug/m3')
    c_pm10 = col(df, 'PM10, ug/m³', 'PM10, ug/mÂ³', 'PM10, ug/m3')
    c_temp = col(df, 'Temperature, ˚C', 'Temperature, ËšC')
    c_hum  = col(df, 'Humidity, %')
    c_press= col(df, f'Pressure, {press_unit}', 'Pressure, mbar', 'Pressure, hPa')

    for day in sorted(df['Date'].dt.date.unique()):
        day_df = df[df['Date'].dt.date == day].copy().reset_index(drop=True)
        if not len(day_df):
            continue
        coords = day_df['Activity'].apply(assign)
        day_df['lat'] = [c[0] for c in coords]
        day_df['lon'] = [c[1] for c in coords]

        name = f"{who}_{day.strftime('%Y%m%d')}_Demo"
        cur.execute("""INSERT INTO upload_sessions
            (session_name, micro_environment, sensor_number, reading_count, start_time, end_time, notes)
            VALUES (?,?,?,?,?,?,?)""",
            (name, 'outdoor', '1', len(day_df),
             str(day_df['Date'].min()), str(day_df['Date'].max()),
             f"{who} {day} kampüs ölçümleri"))
        sid = cur.lastrowid

        for _, r in day_df.iterrows():
            cur.execute("""INSERT OR IGNORE INTO atmotube_readings
                (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0,
                 temperature_c, humidity_pct, pressure_hpa, lat, lon)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, str(r['Date']),
                 (r[c_voc]/1000) if c_voc and pd.notna(r[c_voc]) else None,
                 r[c_pm1] if c_pm1 and pd.notna(r[c_pm1]) else None,
                 r[c_pm25] if c_pm25 and pd.notna(r[c_pm25]) else None,
                 r[c_pm10] if c_pm10 and pd.notna(r[c_pm10]) else None,
                 r[c_temp] if c_temp and pd.notna(r[c_temp]) else None,
                 r[c_hum] if c_hum and pd.notna(r[c_hum]) else None,
                 (r[c_press]/100 if press_unit=='mbar' else r[c_press]) if c_press and pd.notna(r[c_press]) else None,
                 round(r['lat'], 6), round(r['lon'], 6)))
        total_sessions += 1
        # PA civarındaki nokta sayısını kontrol et
        near = ((day_df['lat']-PA[0]).abs()<0.0002) & ((day_df['lon']-PA[1]).abs()<0.0002)
        print(f"  {name}: {len(day_df)} nokta (PA-civari: {near.sum()})")

con.commit()
con.close()
print(f"\n{total_sessions} oturum yeniden üretildi.")
