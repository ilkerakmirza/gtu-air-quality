"""
PurpleAir API polling — runs on a background scheduler every 2 minutes.
Stores readings to the database via db.save_purpleair_reading().
"""

import urllib.request
import json
import datetime
from config import PURPLEAIR_API_KEY, PURPLEAIR_SENSOR_ID, PURPLEAIR_LAT, PURPLEAIR_LON
import db

FIELDS = "pm1.0_atm,pm2.5_atm,pm2.5_atm_a,pm2.5_atm_b,pm10.0_atm,temperature,humidity,last_seen"
API_URL = f"https://api.purpleair.com/v1/sensors/{PURPLEAIR_SENSOR_ID}"

_last_poll_status = {"success": None, "error": None, "at": None}
_last_saved_at = None   # son kaydedilen ölçüm zamanı (sensör çevrimdışıyken aynı ölçüm tekrar kaydedilmesin)


def _fahrenheit_to_celsius(f):
    if f is None:
        return None
    return round((f - 32) * 5 / 9, 1)


def poll():
    global _last_poll_status, _last_saved_at
    if not PURPLEAIR_API_KEY:
        _last_poll_status = {"success": False, "error": "PURPLEAIR_API_KEY not set", "at": _now()}
        print("[purpleair] WARNING: API key not set, skipping poll")
        return

    try:
        url = API_URL + "?fields=" + urllib.request.quote(FIELDS, safe=",.")
        req = urllib.request.Request(url, headers={"X-API-Key": PURPLEAIR_API_KEY})
        with urllib.request.urlopen(req, timeout=10) as resp:
            sensor = json.loads(resp.read().decode()).get("sensor", {})

        # PurpleAir uses Unix timestamps for last_seen
        last_seen_unix = sensor.get("last_seen")
        if last_seen_unix:
            recorded_at = datetime.datetime.utcfromtimestamp(last_seen_unix).isoformat() + "Z"
        else:
            recorded_at = _now()

        data = {
            "recorded_at":  recorded_at,
            "pm1_0":        sensor.get("pm1.0_atm"),
            "pm2_5":        sensor.get("pm2.5_atm"),
            "pm2_5_a":      sensor.get("pm2.5_atm_a"),
            "pm2_5_b":      sensor.get("pm2.5_atm_b"),
            "pm10_0":       sensor.get("pm10.0_atm"),
            "temperature_c": _fahrenheit_to_celsius(sensor.get("temperature")),
            "humidity_pct": sensor.get("humidity"),
            "lat":          PURPLEAIR_LAT,
            "lon":          PURPLEAIR_LON,
        }

        # Sensör PurpleAir'e yeni veri göndermiyorsa API aynı son ölçümü döndürür; kopya kaydetme
        if _last_saved_at is None:
            latest = db.get_latest_purpleair()
            _last_saved_at = _ts(latest.get("recorded_at")) if latest else None
        new_at = _ts(recorded_at)
        if _last_saved_at is not None and new_at is not None and new_at <= _last_saved_at:
            _last_poll_status = {"success": True, "error": None, "at": _now(), "stale_since": recorded_at}
            print(f"[purpleair] Yeni ölçüm yok (son ölçüm {recorded_at}); kayıt atlandı")
            return

        db.save_purpleair_reading(data)
        _last_saved_at = new_at
        _last_poll_status = {"success": True, "error": None, "at": _now()}
        print(f"[purpleair] Polled OK — PM2.5={data['pm2_5']} µg/m³ at {recorded_at}")

    except Exception as e:
        _last_poll_status = {"success": False, "error": str(e), "at": _now()}
        print(f"[purpleair] Poll error: {e}")


def _ts(v):
    """Zaman damgasını karşılaştırılabilir UTC datetime'a çevir (str ya da datetime)."""
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v if v.tzinfo else v.replace(tzinfo=datetime.timezone.utc)
    s = str(v).replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def get_poll_status():
    return _last_poll_status


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"
