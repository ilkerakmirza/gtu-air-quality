"""
Tuya Cloud — CO₂ sensörü entegrasyonu.
Novato / Tuya NDIR CO₂ + sıcaklık + nem sensörlerinin son ölçümlerini
Tuya Cloud API'sinden çeker. Atmotube (atmotube_cloud.py) ile aynı desende.

CO₂ sensörleri SABİT (kapalı alan) cihazlardır — GPS yok. Her cihazın konumu
(lat/lon) config'ten gelir. Birden çok sensör desteklenir.

Gerekli ortam değişkenleri (Render/Railway → Environment, ya da yerel .env):
    TUYA_ACCESS_ID       Cloud Project → Access ID (Client ID)
    TUYA_ACCESS_SECRET   Cloud Project → Access Secret (Client Secret)
    TUYA_API_ENDPOINT    Bölge sunucusu (Central Europe için varsayılan: tuyaeu)

Cihaz kayıtları — iki yoldan biri:
  (a) Çok sensör (önerilen, ölçeklenir): TUYA_CO2_DEVICES = JSON liste, örn:
      [{"name":"CO2-1","device_id":"abc","location":"SUMER Lab","lat":40.806,"lon":29.361}]
  (b) Tek sensör (hızlı başlangıç):
      TUYA_CO2_DEVICE_ID, TUYA_CO2_LAT, TUYA_CO2_LON, TUYA_CO2_LOCATION

Anahtarlar asla koda yazılmamalı (repo public).
"""

import os
import json
import time
import datetime

# Kampüs merkezi — konum verilmezse cihaz buraya düşer (placeholder)
GTU_CENTER = (40.806155, 29.360985)

ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "").strip()
ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "").strip()
API_ENDPOINT = os.environ.get("TUYA_API_ENDPOINT", "https://openapi.tuyaeu.com").strip()

# Tuya DP (data point) kodu → bizim alan adımız.
# İlk çalıştırmada cihazdan gelen ham kodlar farklıysa (co2 / co2_state vb.)
# bu sözlüğün SOL tarafını gerçek kodlarla güncelle (ham çıktı get_live_devices
# içinde error/raw olarak da görünür).
DP_MAP = {
    "co2_value": "co2_ppm",
    "co2": "co2_ppm",
    "temp_current": "temperature_c",
    "va_temperature": "temperature_c",
    "humidity_value": "humidity_pct",
    "va_humidity": "humidity_pct",
}

# 60 sn bellek içi önbellek — Tuya API'sini her istekte yormamak için
_cache = {"ts": 0, "data": None}
CACHE_SECONDS = 60

_api = None  # TuyaOpenAPI istemcisi (tembel başlatılır)


def _load_devices():
    """Cihaz kayıtlarını ortam değişkenlerinden oku. Liste döner."""
    raw = os.environ.get("TUYA_CO2_DEVICES", "").strip()
    if raw:
        try:
            devs = json.loads(raw)
            out = []
            for i, d in enumerate(devs):
                out.append({
                    "name": d.get("name") or f"CO2-{i+1}",
                    "device_id": (d.get("device_id") or "").strip(),
                    "location": d.get("location") or "Kampüs",
                    # anchor: bir Atmotube cihazına (örn. "ATP-2") bağla → o cihazın
                    # canlı GPS konumunu kullan (birlikte taşınıyorlar). lat/lon yedek.
                    "anchor": (d.get("anchor") or "").strip() or None,
                    "lat": float(d.get("lat", GTU_CENTER[0])),
                    "lon": float(d.get("lon", GTU_CENTER[1])),
                })
            return out
        except Exception as e:
            print(f"[tuya_co2] TUYA_CO2_DEVICES çözümlenemedi: {e}")

    # Tek sensör (hızlı başlangıç)
    dev_id = os.environ.get("TUYA_CO2_DEVICE_ID", "").strip()
    return [{
        "name": os.environ.get("TUYA_CO2_NAME", "CO2-1"),
        "device_id": dev_id,
        "location": os.environ.get("TUYA_CO2_LOCATION", "Kampüs"),
        "anchor": os.environ.get("TUYA_CO2_ANCHOR", "").strip() or None,
        "lat": float(os.environ.get("TUYA_CO2_LAT", GTU_CENTER[0])),
        "lon": float(os.environ.get("TUYA_CO2_LON", GTU_CENTER[1])),
    }]


DEVICES = _load_devices()


def _is_configured():
    return bool(ACCESS_ID and ACCESS_SECRET and any(d["device_id"] for d in DEVICES))


def _get_api():
    """TuyaOpenAPI istemcisini tembel başlat (kütüphane yoksa zarifçe None)."""
    global _api
    if _api is not None:
        return _api
    try:
        from tuya_connector import TuyaOpenAPI
    except Exception as e:
        raise RuntimeError(f"tuya-connector-python kurulu değil: {e}")
    api = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_SECRET)
    api.connect()
    _api = api
    return api


def _scale(code, value):
    """Bazı cihazlar sıcaklık/nemi 10x ölçekli verir (235 = 23.5)."""
    if isinstance(value, (int, float)) and value > 100:
        if code in ("temp_current", "va_temperature", "humidity_value", "va_humidity"):
            return value / 10.0
    return value


def _parse_status(status_list):
    """Tuya DP listesini bizim alanlara eşler. Ham kodları da döner (teşhis)."""
    reading = {"co2_ppm": None, "temperature_c": None, "humidity_pct": None}
    raw = {}
    for dp in status_list or []:
        code = dp.get("code")
        value = dp.get("value")
        raw[code] = value
        if code in DP_MAP:
            reading[DP_MAP[code]] = _scale(code, value)
    return reading, raw


def _fetch_device(dev):
    """Tek cihazın anlık durumunu çeker → reading dict (konum eklenmiş)."""
    api = _get_api()
    resp = api.get(f"/v1.0/iot-03/devices/{dev['device_id']}/status")
    if not resp.get("success", False):
        raise RuntimeError(f"Tuya API: {resp.get('msg') or resp}")
    reading, raw = _parse_status(resp.get("result", []))
    reading["recorded_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    reading["lat"] = dev["lat"]
    reading["lon"] = dev["lon"]
    reading["raw"] = raw
    return reading


def _anchor_coords():
    """anchor olarak kullanılan Atmotube cihazlarının konumlarını döner:
    {'ATP-2': (lat, lon, live)}. Önce canlı GPS; yoksa arşivdeki son bilinen konum.
    live=True canlı GPS, live=False son bilinen (saha ölçümü/eski) konum demek."""
    needed = {d["anchor"] for d in DEVICES if d.get("anchor")}
    if not needed:
        return {}
    coords = {}
    # 1) canlı GPS (Atmotube bulut)
    try:
        import atmotube_cloud
        for dev in atmotube_cloud.get_live_devices():
            if dev.get("device") not in needed:
                continue
            r = dev.get("reading") or {}
            if r.get("lat") is not None and r.get("lon") is not None:
                coords[dev["device"]] = (r["lat"], r["lon"], True)
    except Exception as e:
        print(f"[tuya_co2] canlı anchor konumu alınamadı: {e}")
    # 2) canlı GPS olmayanlar için arşivdeki son bilinen konum
    for name in needed - set(coords):
        try:
            import archive
            g = archive.last_device_gps(name)
            if g:
                coords[name] = (g[0], g[1], False)
        except Exception as e:
            print(f"[tuya_co2] arşiv anchor konumu alınamadı ({name}): {e}")
    return coords


def _apply_anchor(entry, dev, coords):
    """Cihaz bir Atmotube'a bağlıysa, CO₂ işaretçisini o cihazın konumuna taşı
    (canlı GPS ya da son bilinen). Hem entry hem reading güncellenir."""
    anchor = dev.get("anchor")
    if not anchor or anchor not in coords:
        return
    lat, lon, live = coords[anchor]
    entry["lat"], entry["lon"] = lat, lon
    entry["anchored_to"] = anchor
    entry["anchor_live"] = live   # True: ATP'nin canlı GPS'i; False: son bilinen konum
    if entry.get("reading"):
        entry["reading"]["lat"], entry["reading"]["lon"] = lat, lon


def get_live_devices(force=False):
    """Tüm CO₂ cihazlarının son durumunu döner. 60 sn önbellekli.
    Atmotube ile aynı dış biçim: [{device, location, lat, lon, reading, error}].
    anchor tanımlıysa konum o Atmotube cihazının canlı GPS'inden alınır."""
    if not _is_configured():
        coords = _anchor_coords()
        result = []
        for d in DEVICES:
            entry = {
                "device": d["name"], "location": d["location"],
                "lat": d["lat"], "lon": d["lon"], "reading": None,
                "error": "Tuya kimlik bilgileri (TUYA_ACCESS_ID/SECRET/DEVICE_ID) tanımlı değil",
            }
            _apply_anchor(entry, d, coords)
            result.append(entry)
        return result

    now = time.time()
    if not force and _cache["data"] is not None and now - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]

    coords = _anchor_coords()
    result = []
    for d in DEVICES:
        entry = {"device": d["name"], "location": d["location"],
                 "lat": d["lat"], "lon": d["lon"], "reading": None, "error": None}
        if not d["device_id"]:
            entry["error"] = "device_id boş"
        else:
            try:
                entry["reading"] = _fetch_device(d)
            except Exception as e:
                entry["error"] = str(e)
        _apply_anchor(entry, d, coords)
        result.append(entry)

    _cache["ts"] = now
    _cache["data"] = result
    return result
