"""
Ayşe'nin 27 Nisan verisinden demo CSV oluşturur.
- Ulaşım satırları çıkarılır
- Her kampüs lokasyonuna gerçek GTÜ koordinatı atanır
- Yürüme segmentleri lokasyonlar arası interpolasyon ile haritalanır
- Oluşan CSV backend'e otomatik yüklenir
"""

import pandas as pd
import numpy as np
import io, sys, requests, json
sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# GTÜ Kampüs lokasyon koordinatları (Google Maps'ten alındı — kullanıcı doğruladı)
# ---------------------------------------------------------------------------
LAT_KUTUPHANE  = (40.80660983568877, 29.36001945835103)
LAT_CEVRE      = (40.80586271172931, 29.362969888267397)   # Çevre Müh. + Kimya (aynı bina)
LAT_KONGRE     = (40.81448660918803, 29.360856307563672)
LAT_GUZIDE     = (40.80605556,       29.36080556)

LOCATIONS = {
    "kütüphane":        LAT_KUTUPHANE,
    "iç güzide":        LAT_GUZIDE,
    "dış güzide":       (LAT_GUZIDE[0] + 0.00008, LAT_GUZIDE[1] - 0.00005),
    "çevre amfi":       (LAT_CEVRE[0] + 0.00015, LAT_CEVRE[1] - 0.00020),
    "çevre koridor":    (LAT_CEVRE[0] + 0.00005, LAT_CEVRE[1] - 0.00010),
    "kçevre koridor":   LAT_CEVRE,
    "genel kimya lab":  LAT_CEVRE,
    "kongre":           LAT_KONGRE,
    "ofis":             LAT_CEVRE,
    "yurt":             (40.81100, 29.36150),
}

# Kampüs yürüme rotası — gerçek koordinatlar arası geçiş yolları
WALKING_ROUTE = [
    LAT_KUTUPHANE,                                   # Kütüphane
    (40.80640, 29.36010),                            # Kütüphane çıkış
    (40.80625, 29.36035),                            # Merkez yol
    LAT_GUZIDE,                                      # Güzide
    (40.80598, 29.36050),                            # Güzide - Çevre arası
    (40.80595, 29.36120),                            # Orta yol
    (40.80590, 29.36200),                            # Çevre binasına yaklaşım
    LAT_CEVRE,                                       # Çevre Müh. / Kimya
    (40.80600, 29.36150),                            # Geri dönüş
    (40.80615, 29.36080),                            # Merkez
    LAT_KUTUPHANE,                                   # Kütüphane
]

TRANSPORT = ['otobüs', 'marmaray', 'marmaray istasyon', 'istasyon', 'yürüme']

# ---------------------------------------------------------------------------
# Veriyi oku ve filtrele
# ---------------------------------------------------------------------------
df = pd.read_excel('atmotube_deneme_harita/Ayse_27_30_Nisan.xlsx')
df = df[~df['Activity'].str.strip().isin(TRANSPORT)]
df = df[df['Date'].dt.date == pd.Timestamp('2026-04-27').date()].copy()
df = df.reset_index(drop=True)
print(f"Filtreleme sonrası: {len(df)} satır")

# ---------------------------------------------------------------------------
# Her satıra GPS koordinatı ata
# ---------------------------------------------------------------------------
# Yürüme segmentleri için global counter
walk_idx = 0

def assign_coords(row):
    global walk_idx
    activity = str(row['Activity']).strip().lower()

    # Bilinen lokasyon mu?
    for key, coords in LOCATIONS.items():
        if key in activity:
            # Küçük random jitter ekle (sensör sabit değil, taşınabilir)
            jitter_lat = np.random.uniform(-0.00005, 0.00005)
            jitter_lon = np.random.uniform(-0.00005, 0.00005)
            return coords[0] + jitter_lat, coords[1] + jitter_lon

    # Kampüs içi yürüme → rota üzerinde ilerle
    if 'yürüme' in activity or 'kampüs' in activity:
        walk_idx = (walk_idx + 1) % len(WALKING_ROUTE)
        pt = WALKING_ROUTE[walk_idx]
        jitter_lat = np.random.uniform(-0.00008, 0.00008)
        jitter_lon = np.random.uniform(-0.00008, 0.00008)
        return pt[0] + jitter_lat, pt[1] + jitter_lon

    # Bilinmeyen → kampüs merkezi
    return 40.806155 + np.random.uniform(-0.0002, 0.0002), \
           29.360985 + np.random.uniform(-0.0002, 0.0002)

coords = df.apply(assign_coords, axis=1)
df['Latitude']  = [c[0] for c in coords]
df['Longitude'] = [c[1] for c in coords]

# ---------------------------------------------------------------------------
# Çıktı CSV formatına dönüştür (upload.py'nin beklediği format)
# ---------------------------------------------------------------------------
out = pd.DataFrame({
    'Date':              df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
    'VOC (ppm)':         (df['VOC, ppm'] / 1000).round(3),   # ppb → ppm
    'PM1 (ug/m3)':       df['PM1, ug/m³'],
    'PM2.5 (ug/m3)':     df['PM2.5, ug/m³'],
    'PM10 (ug/m3)':      df['PM10, ug/m³'],
    'Temperature (C)':   df['Temperature, ˚C'],
    'Humidity (%)':      df['Humidity, %'],
    'Pressure (hPa)':    (df['Pressure, mbar'] / 100).round(2),
    'Latitude':          df['Latitude'].round(6),
    'Longitude':         df['Longitude'].round(6),
})

csv_path = 'ayse_27nisan_demo.csv'
out.to_csv(csv_path, index=False)
print(f"CSV oluşturuldu: {csv_path}  ({len(out)} satır)")
print(f"PM2.5 aralığı: {out['PM2.5 (ug/m3)'].min():.1f} – {out['PM2.5 (ug/m3)'].max():.1f} µg/m³")

# ---------------------------------------------------------------------------
# Backend'e yükle
# ---------------------------------------------------------------------------
print("\nBackend'e yükleniyor...")
try:
    with open(csv_path, 'rb') as f:
        resp = requests.post(
            'http://localhost:5000/api/upload',
            files={'file': ('ayse_27nisan_demo.csv', f, 'text/csv')},
            data={
                'session_name':      'Ayse_27Nisan_Demo',
                'micro_environment': 'outdoor',
                'sensor_number':     '1',
                'notes':             'Demo: 27 Nisan kampüs ölçümleri (kütüphane, güzide, çevre amfi, ofis, yürüme)',
            },
            timeout=15,
        )
    result = resp.json()
    if resp.status_code == 201:
        print(f"BAŞARILI! Session ID: {result['session_id']}")
        print(f"Yüklenen ölçüm: {result['reading_count']}")
        print(f"GPS'li ölçüm var: {result['has_gps']}")
        if result.get('warnings'):
            print(f"Uyarılar: {result['warnings']}")
    else:
        print(f"HATA ({resp.status_code}): {result}")
except Exception as e:
    print(f"Bağlantı hatası: {e}")
    print("Backend çalışıyor mu? 'python backend/app.py' ile başlatın.")
