"""
İBB Hava Kalitesi entegrasyonu.
İstanbul Büyükşehir Belediyesi hava kalitesi istasyonlarından, GTÜ kampüsüne
en yakın olanın (Tuzla, ~7.7 km) PM2.5 arka plan verisini çeker.

Kaynak: https://havakalitesi.ibb.gov.tr/Pages/GetAirQualityStations?type=0
İBB verisi saatlik güncellenir.
"""

import re
import time
import math
import requests

IBB_URL = "https://havakalitesi.ibb.gov.tr/Pages/GetAirQualityStations?type=0"

# GTÜ kampüs merkezi
GTU_LAT, GTU_LON = 40.806155, 29.360985

# 5 dk önbellek (İBB zaten saatlik günceller)
_cache = {"ts": 0, "data": None}
CACHE_SECONDS = 300

_POINT_RE = re.compile(r"POINT \(([\d.]+) ([\d.]+)\)")


def _parse_location(loc):
    m = _POINT_RE.match(loc or "")
    if not m:
        return None, None
    lon, lat = float(m.group(1)), float(m.group(2))
    return lat, lon


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def get_nearest_station(force=False):
    """GTÜ'ye en yakın, PM2.5 verisi olan İBB istasyonunu döner."""
    now = time.time()
    if not force and _cache["data"] is not None and now - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]

    r = requests.get(IBB_URL, timeout=20)
    r.raise_for_status()
    objects = r.json().get("objects", [])

    # ANLIK (saatlik) değer için LastMeasurement kullanılır; Values.PM25 ise
    # AQI'nin 24 saatlik ortalamasıdır (kullanıcı anlık istiyor).
    best = None
    best_km = 1e9
    for s in objects:
        lat, lon = _parse_location(s.get("Location"))
        if lat is None:
            continue
        last = s.get("LastMeasurement") or {}
        pm25 = last.get("PM25")
        if pm25 is None:
            pm25 = (s.get("Values") or {}).get("PM25")  # yedek
        if pm25 is None:
            continue  # sadece PM2.5 verisi olan istasyonlar
        km = _haversine_km(GTU_LAT, GTU_LON, lat, lon)
        if km < best_km:
            best_km = km
            best = (s, lat, lon)

    if not best:
        result = None
    else:
        s, lat, lon = best
        last = s.get("LastMeasurement") or {}
        vals = s.get("Values") or {}
        result = {
            "station_name": s.get("Name"),
            "town": s.get("Town_Title"),
            "type": s.get("SubType_Title"),
            "lat": lat,
            "lon": lon,
            "distance_km": round(best_km, 1),
            "pm2_5": last.get("PM25") if last.get("PM25") is not None else vals.get("PM25"),  # anlık
            "pm10_0": last.get("PM10") if last.get("PM10") is not None else vals.get("PM10"),
            "temperature_c": last.get("Sicaklik"),
            "humidity_pct": last.get("Nem"),
            "wind_speed": last.get("RuzgarHizi"),
            "recorded_at": last.get("DataDate") or vals.get("Date"),  # anlık zaman
        }

    _cache["ts"] = now
    _cache["data"] = result
    return result
