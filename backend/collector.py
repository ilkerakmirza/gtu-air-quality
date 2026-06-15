"""
Canlı veri toplayıcı — üç kaynağı (PurpleAir, İBB, Atmotube) kalıcı arşive yazar.
Scheduler tarafından düzenli çağrılır (app.py).
"""

import datetime
import archive
import db
import ibb
import csb
import atmotube_cloud

# Türkiye sabit UTC+3 (2016'dan beri yaz saati yok)
def _tr_local_to_utc(naive_iso):
    """İBB'nin Türkiye yerel saatini (tz'siz) UTC ISO'ya çevirir."""
    if not naive_iso:
        return naive_iso
    try:
        dt = datetime.datetime.fromisoformat(naive_iso.replace("Z", ""))
        return (dt - datetime.timedelta(hours=3)).isoformat() + "+00:00"
    except Exception:
        return naive_iso


def collect_purpleair():
    """PurpleAir son okumasını arşive ekle (poll zaten SQLite'a yazdı)."""
    try:
        d = db.get_latest_purpleair()
        if not d:
            return 0
        return archive.log_rows([{
            "source": "purpleair", "device": "PA-II",
            "recorded_at": d.get("recorded_at"),
            "pm1_0": d.get("pm1_0"), "pm2_5": d.get("pm2_5"), "pm10_0": d.get("pm10_0"),
            "voc_ppm": None,
            "temperature_c": d.get("temperature_c"), "humidity_pct": d.get("humidity_pct"),
            "pressure_hpa": d.get("pressure_hpa"),
            "lat": d.get("lat"), "lon": d.get("lon"),
        }])
    except Exception as e:
        print(f"[collector/purpleair] {e}")
        return 0


def collect_ibb():
    """İBB en yakın istasyon (Tuzla) saatlik değerini arşive ekle."""
    try:
        d = ibb.get_nearest_station(force=True)
        if not d or d.get("pm2_5") is None:
            return 0
        return archive.log_rows([{
            "source": "ibb", "device": d.get("station_name"),
            "recorded_at": _tr_local_to_utc(d.get("recorded_at")),
            "pm1_0": None, "pm2_5": d.get("pm2_5"), "pm10_0": d.get("pm10_0"),
            "voc_ppm": None,
            "temperature_c": d.get("temperature_c"), "humidity_pct": d.get("humidity_pct"),
            "pressure_hpa": None,
            "lat": d.get("lat"), "lon": d.get("lon"),
        }])
    except Exception as e:
        print(f"[collector/ibb] {e}")
        return 0


def collect_csb():
    """CSB Tuzla istasyonu saatlik PM2.5 değerini arşive ekle (Türkiye saati → UTC)."""
    try:
        d = csb.get_latest(force=True)
        if not d or d.get("pm2_5") is None:
            return 0
        return archive.log_rows([{
            "source": "csb", "device": d.get("station_name"),
            "recorded_at": _tr_local_to_utc(d.get("recorded_at")),
            "pm1_0": None, "pm2_5": d.get("pm2_5"), "pm10_0": None,
            "voc_ppm": None, "temperature_c": None, "humidity_pct": None,
            "pressure_hpa": None, "lat": d.get("lat"), "lon": d.get("lon"),
        }])
    except Exception as e:
        print(f"[collector/csb] {e}")
        return 0


def collect_atmotube():
    """5 Atmotube cihazının son okumalarını arşive ekle."""
    try:
        devices = atmotube_cloud.get_live_devices(force=True)
        rows = []
        for d in devices:
            r = d.get("reading")
            if not r:
                continue
            rows.append({
                "source": "atmotube", "device": d.get("device"),
                "recorded_at": r.get("recorded_at"),
                "pm1_0": r.get("pm1_0"), "pm2_5": r.get("pm2_5"), "pm10_0": r.get("pm10_0"),
                "voc_ppm": r.get("voc_ppm"),
                "temperature_c": r.get("temperature_c"), "humidity_pct": r.get("humidity_pct"),
                "pressure_hpa": r.get("pressure_hpa"),
                "lat": r.get("lat"), "lon": r.get("lon"),
            })
        return archive.log_rows(rows)
    except Exception as e:
        print(f"[collector/atmotube] {e}")
        return 0


def collect_fast():
    """2 dakikada bir: PurpleAir + Atmotube."""
    n = collect_purpleair() + collect_atmotube()
    if n:
        print(f"[collector] {n} yeni kayıt arşivlendi (PurpleAir+Atmotube).")


def collect_hourly():
    """Saatte bir: İBB + CSB."""
    n = collect_ibb() + collect_csb()
    if n:
        print(f"[collector] {n} yeni İBB/CSB kaydı arşivlendi.")
