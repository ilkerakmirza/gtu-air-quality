"""
Atmotube Cloud API entegrasyonu.
5 adet Atmotube Pro cihazının son ölçümlerini bulut API'sinden çeker.
Bulut senkronizasyonu ~1-2 dk gecikmeli çalışır.
"""

import os
import time
import datetime
import requests

# API anahtarı ortam değişkeninden gelir (Render → Environment → ATMOTUBE_API_KEY).
# Repo public olduğu için anahtar asla koda yazılmamalı.
ATMOTUBE_API_KEY = os.environ.get("ATMOTUBE_API_KEY", "")
ATMOTUBE_URL = "https://api.atmotube.com/api/v1/data"

DEVICES = {
    "ATP-1": "E1:15:C2:A9:8D:80",
    "ATP-2": "CE:38:18:F5:48:5D",
    "ATP-3": "C0:32:F1:B5:04:77",
    "ATP-4": "FC:EB:EE:F3:52:32",
    "ATP-5": "D7:23:65:E9:0E:25",
}

# Basit bellek içi önbellek — Atmotube API'sini her istekte yormamak için
_cache = {"ts": 0, "data": None}
CACHE_SECONDS = 60


def _fetch_device_latest(mac):
    """Bir cihazın son ölçümünü döner. Son okumada GPS yoksa, yakın geçmişteki
    son bilinen konumu (lat/lon) ekler — böylece kapalı alanda bile harita işaretçisi çıkar."""
    today = datetime.date.today()
    params = {
        "api_key": ATMOTUBE_API_KEY,
        "mac": mac,
        "start_date": (today - datetime.timedelta(days=2)).isoformat(),
        "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        "limit": 300,   # son okuma + son bilinen GPS için yeterli, hızlı
        "offset": 0,
    }
    r = requests.get(ATMOTUBE_URL, params=params, timeout=20)
    r.raise_for_status()
    items = r.json().get("data", {}).get("items", [])
    if not items:
        return None
    # En yeni okuma (değerler için)
    it = items[0]
    # GPS yumuşatma: son ~10 GPS'li okumanın ortalaması (ham GPS ~5-10m titrer;
    # sabit cihazda ortalama daha kararlı/doğru konum verir). items en yeniden eskiye sıralı.
    gps = []
    for r in items:
        c = r.get("coords") or {}
        if c.get("lat") is not None and c.get("lon") is not None:
            gps.append((c["lat"], c["lon"]))
        if len(gps) >= 10:
            break
    if gps:
        lat = sum(g[0] for g in gps) / len(gps)
        lon = sum(g[1] for g in gps) / len(gps)
    else:
        lat = lon = None
    return {
        "recorded_at": it.get("time"),
        "voc_ppm": it.get("voc"),
        "pm1_0": it.get("pm1"),
        "pm2_5": it.get("pm25"),
        "pm10_0": it.get("pm10"),
        "temperature_c": it.get("t"),
        "humidity_pct": it.get("h"),
        "pressure_hpa": it.get("p"),
        "lat": lat,
        "lon": lon,
    }


def get_live_devices(force=False):
    """Tüm cihazların son durumunu döner. 60 sn önbellekli."""
    if not ATMOTUBE_API_KEY:
        return [{"device": n, "mac": m, "reading": None,
                 "error": "ATMOTUBE_API_KEY tanımlı değil"} for n, m in DEVICES.items()]
    now = time.time()
    if not force and _cache["data"] is not None and now - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]

    result = []
    for name, mac in DEVICES.items():
        entry = {"device": name, "mac": mac, "reading": None, "error": None}
        try:
            entry["reading"] = _fetch_device_latest(mac)
        except Exception as e:
            entry["error"] = str(e)
        result.append(entry)

    _cache["ts"] = now
    _cache["data"] = result
    return result


def fetch_device_history(mac, start_date, end_date, limit=2000):
    """Bir cihazın tarih aralığındaki tüm ölçümlerini döner (sayfalı)."""
    all_items = []
    offset = 0
    while True:
        params = {
            "api_key": ATMOTUBE_API_KEY,
            "mac": mac,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        }
        r = requests.get(ATMOTUBE_URL, params=params, timeout=30)
        r.raise_for_status()
        items = r.json().get("data", {}).get("items", [])
        all_items.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return all_items
