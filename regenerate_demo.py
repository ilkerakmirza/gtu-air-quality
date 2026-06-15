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

# Çevre Mühendisliği binası — uydudan doğrulandı (avlulu binanın batı kanadı çatısı).
# Eski (40.80586, 29.36297) binanın doğu kenarına/yola düşüyordu; bina merkezine alındı.
CEVRE  = (40.80570, 29.36260)                       # Çevre binası (çatı, bina içi)
KUTUP  = (40.80660983568877, 29.36001945835103)    # Kütüphane
GUZIDE = (40.80605556, 29.36080556)                # Güzide kafe
KONGRE = (40.81448660918803, 29.360856307563672)   # Kongre/Kültür merkezi
YURT   = (40.81100, 29.36150)                       # Yurt

# Ofis/lab/derslik aktiviteleri Çevre binası ÇATISI üzerinde kalır (küçük ofset + ~4m jitter).
# İlker Çevre Müh. öğretim üyesi, Serra da Çevre (CEV111) — ofis/lab Çevre binasında.
L = {
    'cevre_koridor': CEVRE,
    'cev111':        CEVRE,
    'kimya_lab':     (CEVRE[0] - 0.00003, CEVRE[1] + 0.00004),
    'seminer':       (CEVRE[0] + 0.00003, CEVRE[1] - 0.00002),
    'cevre_amfi':    (CEVRE[0] + 0.00004, CEVRE[1] + 0.00003),
    'amfi1':         (CEVRE[0] + 0.00005, CEVRE[1] + 0.00004),
    'merkezi_ders':  (CEVRE[0] + 0.00006, CEVRE[1] + 0.00005),
    # İlker ofisi — bina batı kanadı
    'ilker_ofis':    (CEVRE[0] + 0.00002, CEVRE[1] - 0.00002),
    'ilker_koridor': CEVRE,
    # Serra ofis/lab — bina (farklı köşe)
    'zl_ofis':       (CEVRE[0] - 0.00003, CEVRE[1] + 0.00003),
    'zl_lab':        (CEVRE[0] - 0.00004, CEVRE[1] + 0.00004),
    # Kasıtlı dış mekanlar
    'cevre_arka':    (CEVRE[0] - 0.00010, CEVRE[1] + 0.00012),  # arka bahçe
    'otopark':       (CEVRE[0] - 0.00012, CEVRE[1] - 0.00010),  # otopark
    # Bina dışı bilinen noktalar
    'kutuphane':     KUTUP,
    'kutuphane_onu': (KUTUP[0] - 0.00004, KUTUP[1] + 0.00006),
    'ic_guzide':     GUZIDE,
    'dis_guzide':    (GUZIDE[0] + 0.00008, GUZIDE[1] - 0.00005),
    'kongre':        KONGRE,
    'yurt':          YURT,
    # Varsayılan: Çevre binası
    'kampus':        CEVRE,
}

WALK = [
    KUTUP, (40.806400, 29.360200), (40.806250, 29.360500),
    GUZIDE, (40.805980, 29.361200), (40.805900, 29.362000),
    CEVRE, (40.806000, 29.362400), (40.806300, 29.361500), (40.806450, 29.360900),
]

# Aktivite → lokasyon eşlemesi. ÖNEM SIRASINA göre kontrol edilir (en özgül önce).
# (anahtar_alt_dize, lokasyon) — ilk eşleşen kazanır.
RULES = [
    ('zl-16 ofis',    'zl_ofis'),
    ('zl-07 lab',     'zl_lab'),
    ('başka ofis',    'ilker_ofis'),
    ('ofis /cam',     'ilker_ofis'),
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

def jitter(coord, amt=0.00004):
    # Küçük dağılım (~4m) — noktalar bina çatısında kalır, üst üste binmez
    return (coord[0] + np.random.uniform(-amt, amt),
            coord[1] + np.random.uniform(-amt, amt))

def assign(activity):
    global walk_idx
    a = str(activity).strip().lower()
    if a in ('nan', 'none', ''):
        return jitter(L['kampus'])
    # Yürüyüş → rota üzerinde ilerle
    if any(k in a for k in WALK_KEYS):
        walk_idx = (walk_idx + 1) % len(WALK)
        return jitter(WALK[walk_idx], 0.00008)
    # Kurallar (özgülden genele)
    for key, loc in RULES:
        if key in a:
            return jitter(L[loc])
    # Varsayılan: Çevre binası (PA/bahçe DEĞİL)
    return jitter(L['kampus'])

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
