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


def _fahrenheit_to_celsius(f):
    if f is None:
        return None
    return round((f - 32) * 5 / 9, 1)


def poll():
    global _last_poll_status
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

        db.save_purpleair_reading(data)
        _last_poll_status = {"success": True, "error": None, "at": _now()}
        print(f"[purpleair] Polled OK — PM2.5={data['pm2_5']} µg/m³ at {recorded_at}")

    except Exception as e:
        _last_poll_status = {"success": False, "error": str(e), "at": _now()}
        print(f"[purpleair] Poll error: {e}")


def get_poll_status():
    return _last_poll_status


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"
