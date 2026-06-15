"""
Çevre ve Şehircilik Bakanlığı (CSB) ulusal hava kalitesi ağı entegrasyonu.
sim.csb.gov.tr — GTÜ'ye en yakın PM2.5 ölçen istasyon: İstanbul - Tuzla (~6.4 km).

Site ASP.NET form tabanlı: önce sayfa GET edilip CSRF token + session cookie alınır,
sonra StationDataDownloadNewData'ya POST atılır. Veri saatlik güncellenir.
"""
import re
import time
import datetime
import requests
import urllib3

# CSB sunucusunun sertifika zinciri bazı ortamlarda doğrulanamıyor; kamuya açık
# veri olduğu için SSL doğrulamasını kapatıyoruz (curl --ssl-no-revoke gibi).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_VERIFY = False

BASE = "https://sim.csb.gov.tr/STN/STN_Report"
PAGE = BASE + "/StationDataDownloadNew"
DATA = BASE + "/StationDataDownloadNewData"

# İstasyon: İstanbul - Tuzla (PM2.5 ölçen, GTÜ'ye en yakın CSB istasyonu)
STATION_ID = "3de006fe-6252-4f09-8a08-4539ed5cb43c"
STATION_NAME = "İstanbul - Tuzla"
STATION_LAT = 40.84311606243338
STATION_LON = 29.3026191609436
GTU_LAT, GTU_LON = 40.806155, 29.360985

_TOKEN_RE = re.compile(r'__RequestVerificationToken" type="hidden" value="([^"]+)"')

_cache = {"ts": 0, "data": None}
CACHE_SECONDS = 600  # 10 dk (CSB saatlik günceller)


def _haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1); dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def get_latest(force=False):
    """Tuzla istasyonunun son (boş olmayan) PM2.5 saatlik değerini döner."""
    now = time.time()
    if not force and _cache["data"] is not None and now - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]

    s = requests.Session()
    s.verify = _VERIFY
    s.headers.update({"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})

    page = s.get(PAGE, timeout=20)
    m = _TOKEN_RE.search(page.text)
    if not m:
        raise RuntimeError("CSRF token bulunamadı")
    token = m.group(1)

    today = datetime.date.today()
    start = today - datetime.timedelta(days=2)
    fmt = lambda d: d.strftime("%d.%m.%Y") + " 00:00"
    payload = {
        "__RequestVerificationToken": token,
        "StationType": "1",
        "StationIds": STATION_ID,
        "Parameters": "PM25",
        "DataPeriods": "8",  # saatlik
        "StartDateTime": fmt(start),
        "EndDateTime": today.strftime("%d.%m.%Y") + " 23:00",
    }
    r = s.post(DATA, data=payload, timeout=40)
    j = r.json()
    rows = (j.get("Object") or {}).get("Data") or []

    # Son boş olmayan PM2.5 kaydını bul
    latest = None
    for row in rows:
        if row.get("PM25") is not None:
            if latest is None or row["ReadTime"] > latest["ReadTime"]:
                latest = row

    km = _haversine_km(GTU_LAT, GTU_LON, STATION_LAT, STATION_LON)
    result = {
        "station_name": STATION_NAME,
        "lat": STATION_LAT, "lon": STATION_LON,
        "distance_km": round(km, 1),
        "pm2_5": latest["PM25"] if latest else None,
        "recorded_at": latest["ReadTime"] if latest else None,  # Türkiye yereli (tz'siz)
    }
    _cache["ts"] = now
    _cache["data"] = result
    return result
