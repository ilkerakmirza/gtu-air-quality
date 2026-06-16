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


def sync_atmotube_sessions():
    """Arşivdeki Atmotube (ATP-1..5) verisini, saha ölçümleri panelinde seçilebilir
    olsun diye cihaz-gün bazlı oturumlara (upload_sessions + atmotube_readings) dönüştürür.
    Son 3 gün işlenir; tekrar çalıştırılabilir (ON CONFLICT ile mükerrer engellenir)."""
    if not archive.is_enabled():
        return
    try:
        with db.get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT device, (recorded_at AT TIME ZONE 'Europe/Istanbul')::date AS d,
                       COUNT(*), MIN(recorded_at), MAX(recorded_at)
                FROM measurements
                WHERE source='atmotube' AND recorded_at > now() - interval '3 days'
                GROUP BY device, d ORDER BY device, d
            """)
            groups = cur.fetchall()
            for device, d, cnt, mn, mx in groups:
                name = f"{device}_{d.strftime('%Y%m%d')}"
                try:
                    sn = int(str(device).split("-")[1])
                except Exception:
                    sn = 1
                cur.execute("SELECT id FROM upload_sessions WHERE session_name=%s", (name,))
                row = cur.fetchone()
                if row:
                    sid = row[0]
                    cur.execute("UPDATE upload_sessions SET reading_count=%s, end_time=%s WHERE id=%s",
                                (cnt, mx, sid))
                else:
                    cur.execute("""INSERT INTO upload_sessions
                        (session_name, micro_environment, sensor_number, reading_count, start_time, end_time, notes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (name, 'portable', sn, cnt, mn, mx, f"{device} canlı saha ölçümü"))
                    sid = cur.fetchone()[0]
                # Ölçümleri ekle (mükerrer atlanır)
                cur.execute("""
                    INSERT INTO atmotube_readings
                        (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0,
                         temperature_c, humidity_pct, pressure_hpa, lat, lon)
                    SELECT %s, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0,
                           temperature_c, humidity_pct, pressure_hpa, lat, lon
                    FROM measurements
                    WHERE source='atmotube' AND device=%s
                      AND (recorded_at AT TIME ZONE 'Europe/Istanbul')::date = %s
                    ON CONFLICT (session_id, recorded_at) DO NOTHING
                """, (sid, device, d))
    except Exception as e:
        print(f"[sync_atmotube] {e}")


def collect_fast():
    """2 dakikada bir: PurpleAir + Atmotube (+ cihaz oturumlarını güncelle)."""
    n = collect_purpleair() + collect_atmotube()
    sync_atmotube_sessions()
    if n:
        print(f"[collector] {n} yeni kayıt arşivlendi (PurpleAir+Atmotube).")


def collect_hourly():
    """Saatte bir. (İBB kaldırıldı — CSB Tuzla ile aynı istasyon; CSB yerel
    toplayıcı tarafından toplanır.)"""
    return 0
