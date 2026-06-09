"""
29 ve 30 Nisan verilerini DB'ye ekler.
PurpleAir verilerini de purpleair_readings tablosuna aktarır.
"""
import pandas as pd
import numpy as np
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

LAT_KUTUPHANE = (40.80660983568877, 29.36001945835103)
LAT_CEVRE     = (40.80586271172931, 29.362969888267397)
LAT_KONGRE    = (40.81448660918803, 29.360856307563672)
LAT_GUZIDE    = (40.80605556, 29.36080556)
PA_LAT, PA_LON = 40.806155, 29.360985

LOCATIONS = {
    "kütüphane":       LAT_KUTUPHANE,
    "iç güzide":       LAT_GUZIDE,
    "dış güzide":      (LAT_GUZIDE[0]+0.00008, LAT_GUZIDE[1]-0.00005),
    "çevre amfi":      (LAT_CEVRE[0]+0.00015, LAT_CEVRE[1]-0.00020),
    "çevre koridor":   LAT_CEVRE,
    "kçevre koridor":  LAT_CEVRE,
    "genel kimya lab": LAT_CEVRE,
    "kongre":          LAT_KONGRE,
    "ofis":            LAT_CEVRE,
    "yurt":            (40.81100, 29.36150),
}
WALKING_ROUTE = [
    LAT_KUTUPHANE, (40.80640,29.36010), (40.80625,29.36035),
    LAT_GUZIDE, (40.80598,29.36050), (40.80595,29.36120),
    (40.80590,29.36200), LAT_CEVRE, (40.80600,29.36150),
    (40.80615,29.36080), LAT_KUTUPHANE,
]
TRANSPORT = ['otobüs','marmaray','marmaray istasyon','istasyon','yürüme']

df_all = pd.read_excel('atmotube_deneme_harita/Ayse_27_30_Nisan.xlsx')
DB = 'backend/campus_air.db'
con = sqlite3.connect(DB)
cur = con.cursor()

for gun_str in ['2026-04-29', '2026-04-30']:
    gun = pd.Timestamp(gun_str).date()
    df = df_all[~df_all['Activity'].str.strip().isin(TRANSPORT)]
    df = df[df['Date'].dt.date == gun].copy().reset_index(drop=True)
    print(f"\n{'='*40}")
    print(f"{gun_str}: {len(df)} satır")
    print("Aktiviteler:", df['Activity'].value_counts().to_dict())

    walk_idx = 0
    def assign_coords(row):
        global walk_idx
        activity = str(row['Activity']).strip().lower()
        for key, coords in LOCATIONS.items():
            if key in activity:
                return coords[0]+np.random.uniform(-0.00005,0.00005), \
                       coords[1]+np.random.uniform(-0.00005,0.00005)
        if 'yürüme' in activity or 'kampüs' in activity:
            walk_idx = (walk_idx+1) % len(WALKING_ROUTE)
            pt = WALKING_ROUTE[walk_idx]
            return pt[0]+np.random.uniform(-0.00008,0.00008), \
                   pt[1]+np.random.uniform(-0.00008,0.00008)
        return 40.806155+np.random.uniform(-0.0002,0.0002), \
               29.360985+np.random.uniform(-0.0002,0.0002)

    coords = df.apply(assign_coords, axis=1)
    df['Latitude']  = [c[0] for c in coords]
    df['Longitude'] = [c[1] for c in coords]

    out = pd.DataFrame({
        'Date':             df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'VOC (ppm)':        (df['VOC, ppm']/1000).round(3),
        'PM1 (ug/m3)':      df['PM1, ug/m³'],
        'PM2.5 (ug/m3)':    df['PM2.5, ug/m³'],
        'PM10 (ug/m3)':     df['PM10, ug/m³'],
        'Temperature (C)':  df['Temperature, ˚C'],
        'Humidity (%)':     df['Humidity, %'],
        'Pressure (hPa)':   (df['Pressure, mbar']/100).round(2),
        'Latitude':         df['Latitude'].round(6),
        'Longitude':        df['Longitude'].round(6),
    })

    session_name = f"Ayse_{gun_str.replace('-','')[2:]}Demo"
    cur.execute("""INSERT INTO upload_sessions
        (session_name,micro_environment,sensor_number,reading_count,start_time,end_time,notes)
        VALUES (?,?,?,?,?,?,?)""",
        (session_name,'outdoor','1',len(out),out['Date'].min(),out['Date'].max(),
         f'{gun_str} kampüs ölçümleri'))
    sid = cur.lastrowid
    ins = 0
    for _, row in out.iterrows():
        cur.execute("""INSERT OR IGNORE INTO atmotube_readings
            (session_id,recorded_at,voc_ppm,pm1_0,pm2_5,pm10_0,
             temperature_c,humidity_pct,pressure_hpa,lat,lon)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (sid,row['Date'],row['VOC (ppm)'],row['PM1 (ug/m3)'],
             row['PM2.5 (ug/m3)'],row['PM10 (ug/m3)'],row['Temperature (C)'],
             row['Humidity (%)'],row['Pressure (hPa)'],row['Latitude'],row['Longitude']))
        if cur.rowcount: ins += 1
    print(f"Atmotube → {ins} satır eklendi (Session ID={sid})")

    # PurpleAir verilerini de ekle
    pa_df = df_all[df_all['Date'].dt.date == gun].dropna(subset=['purple air data'])
    pa_df = pa_df[pa_df['purple air data'] > 0]
    pa_ins = 0
    for _, row in pa_df.iterrows():
        ts = row['Date'].strftime('%Y-%m-%dT%H:%M:%S')
        cur.execute("SELECT id FROM purpleair_readings WHERE recorded_at=?", (ts,))
        if cur.fetchone(): continue
        pm25 = float(row['purple air data'])
        temp = float(row['Temperature, ˚C']) if pd.notna(row.get('Temperature, ˚C')) else None
        hum  = float(row['Humidity, %'])     if pd.notna(row.get('Humidity, %'))     else None
        cur.execute("""INSERT INTO purpleair_readings
            (recorded_at,pm2_5,pm2_5_a,pm2_5_b,temperature_c,humidity_pct,lat,lon)
            VALUES (?,?,?,?,?,?,?,?)""",
            (ts,pm25,pm25,pm25,temp,hum,PA_LAT,PA_LON))
        if cur.rowcount: pa_ins += 1
    print(f"PurpleAir → {pa_ins} satır eklendi")

con.commit()
con.close()
print("\nTüm veriler hazır!")
