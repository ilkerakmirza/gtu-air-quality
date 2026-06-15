"""
GTU Campus Air Quality API — Flask backend.
Run locally:  python app.py
Production:   gunicorn app:app (Procfile)
"""

import datetime
from flask import Flask, request, jsonify, abort, Response
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

import config
import db
import purpleair
import upload as uploader

app = Flask(__name__)
CORS(app, origins=config.CORS_ORIGINS)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

db.init_db()

# Seed demo data if DB is empty (yalnızca SQLite modunda; Postgres'te veri kalıcı)
def _seed_if_empty():
    import os, sqlite3 as _sq
    if os.environ.get("DATABASE_URL", "").strip():
        # Postgres (Supabase) kullanılıyor — demo verisi orada kalıcı, SQLite seed gereksiz
        return
    db_path = os.environ.get("DB_PATH", "campus_air.db")
    seed_path = os.path.join(os.path.dirname(__file__), "seed.sql")
    if not os.path.exists(seed_path):
        return
    try:
        con = _sq.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM upload_sessions")
        count = cur.fetchone()[0]
        if count == 0:
            with open(seed_path, "r", encoding="utf-8") as f:
                sql = f.read()
            con.executescript(sql)
            con.commit()
            print("[seed] Demo veriler yüklendi.")
        else:
            print(f"[seed] DB zaten dolu ({count} oturum), seed atlandı.")
        con.close()
    except Exception as e:
        print(f"[seed] Hata: {e}")

_seed_if_empty()

# Kalıcı arşiv (Supabase) — DATABASE_URL ayarlıysa aktifleşir
import archive
import collector
archive.init()

scheduler = BackgroundScheduler()
scheduler.add_job(purpleair.poll, "interval", minutes=config.POLL_INTERVAL_MINUTES, id="pa_poll")
# Üç kaynağı kalıcı arşive yaz: hızlı (PurpleAir+Atmotube) + saatlik (İBB)
scheduler.add_job(collector.collect_fast, "interval", minutes=config.POLL_INTERVAL_MINUTES, id="archive_fast")
scheduler.add_job(collector.collect_hourly, "interval", minutes=60, id="archive_ibb")
scheduler.start()

# Run first poll + collection immediately on startup (background thread)
import threading
def _startup_jobs():
    purpleair.poll()
    collector.collect_fast()
    collector.collect_hourly()
threading.Thread(target=_startup_jobs, daemon=True).start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_required():
    token = request.headers.get("X-Admin-Token") or request.args.get("token")
    if token != config.ADMIN_TOKEN:
        abort(403, description="Admin token gerekli.")


def _jsonify_rows(rows):
    return jsonify({"data": rows, "count": len(rows)})


def _now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# PurpleAir endpoints
# ---------------------------------------------------------------------------

@app.get("/api/purpleair/latest")
def purpleair_latest():
    row = db.get_latest_purpleair()
    if not row:
        return jsonify({"data": None, "message": "Henüz veri yok."}), 200
    row["aqi_category"] = _aqi_category(row.get("pm2_5"))
    return jsonify({"data": row})


@app.get("/api/purpleair/history")
def purpleair_history():
    start = request.args.get("start", _days_ago(7))
    end   = request.args.get("end", _now_iso())
    interval = request.args.get("interval", "raw")
    rows = db.get_purpleair_history(start, end, interval)
    return _jsonify_rows(rows)


@app.get("/api/purpleair/status")
def purpleair_status():
    return jsonify(purpleair.get_poll_status())


# ---------------------------------------------------------------------------
# Atmotube Cloud API — canlı cihaz verileri (ATP-1..5)
# ---------------------------------------------------------------------------

import atmotube_cloud

@app.get("/api/atmotube/live")
def atmotube_live():
    """5 Atmotube Pro cihazının bulut API'sindeki son ölçümleri (60 sn önbellekli)."""
    force = request.args.get("force") == "1"
    return jsonify({"data": atmotube_cloud.get_live_devices(force=force)})


import ibb

# ---------------------------------------------------------------------------
# Kalıcı arşiv — istatistik + CSV indirme (analiz için)
# ---------------------------------------------------------------------------

@app.get("/api/archive/stats")
def archive_stats():
    """Arşivdeki kayıt sayısı ve tarih aralığı (kaynak başına)."""
    return jsonify(archive.stats())


@app.get("/api/export.csv")
def export_csv():
    """Tüm ölçümleri tek CSV olarak indir.
    Opsiyonel: ?source=ibb|purpleair|atmotube&start=YYYY-MM-DD&end=YYYY-MM-DD"""
    source = request.args.get("source")
    start  = request.args.get("start")
    end    = request.args.get("end")
    fname  = "gtu_hava_kalitesi_" + datetime.date.today().isoformat() + ".csv"
    return Response(
        archive.iter_csv(source, start, end),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/ibb/latest")
def ibb_latest():
    """GTÜ'ye en yakın İBB istasyonunun (Tuzla) PM2.5 arka plan verisi (5 dk önbellekli)."""
    force = request.args.get("force") == "1"
    try:
        data = ibb.get_nearest_station(force=force)
    except Exception as e:
        return jsonify({"data": None, "error": str(e)}), 200
    return jsonify({"data": data})


import csb

@app.get("/api/csb/latest")
def csb_latest():
    """CSB (Çevre Şehircilik Bakanlığı) Tuzla istasyonu PM2.5 verisi (10 dk önbellekli)."""
    force = request.args.get("force") == "1"
    try:
        data = csb.get_latest(force=force)
    except Exception as e:
        return jsonify({"data": None, "error": str(e)}), 200
    return jsonify({"data": data})


@app.get("/api/atmotube/history")
def atmotube_history():
    """Tek cihazın tarih aralığındaki ham bulut verisi.
    Parametreler: device=ATP-1, start=YYYY-MM-DD, end=YYYY-MM-DD"""
    device = request.args.get("device", "ATP-1")
    mac = atmotube_cloud.DEVICES.get(device)
    if not mac:
        abort(400, description=f"Bilinmeyen cihaz: {device}")
    start = request.args.get("start", _days_ago(1)[:10])
    end   = request.args.get("end", _now_iso()[:10])
    try:
        items = atmotube_cloud.fetch_device_history(mac, start, end)
    except Exception as e:
        abort(502, description=f"Atmotube API hatası: {e}")
    return jsonify({"device": device, "count": len(items), "data": items})


# ---------------------------------------------------------------------------
# Atmotube upload
# ---------------------------------------------------------------------------

@app.post("/api/upload")
def upload_csv():
    import traceback
    try:
        return _upload_csv_inner()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def _upload_csv_inner():
    if "file" not in request.files:
        return jsonify({"error": "CSV dosyası (file) eksik."}), 400

    file = request.files["file"]
    session_name      = request.form.get("session_name", "").strip()
    micro_environment = request.form.get("micro_environment", "").strip()
    sensor_number     = request.form.get("sensor_number", None)
    notes             = request.form.get("notes", "").strip()

    if not session_name:
        return jsonify({"error": "session_name zorunlu."}), 400

    try:
        rows, stats = uploader.parse_csv(file.read(), filename=file.filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    meta = {
        "session_name":      session_name,
        "micro_environment": micro_environment or None,
        "sensor_number":     int(sensor_number) if sensor_number else None,
        "csv_filename":      file.filename,
        "reading_count":     int(stats["count"]),
        "start_time":        str(stats["start_time"]) if stats["start_time"] else None,
        "end_time":          str(stats["end_time"]) if stats["end_time"] else None,
        "notes":             notes or None,
    }

    try:
        session_id = db.create_upload_session(meta)
        for r in rows:
            r["session_id"] = session_id
        inserted = db.bulk_insert_atmotube(rows)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Veritabanı hatası: {str(e)}"}), 500

    return jsonify({
        "session_id":    int(session_id),
        "reading_count": int(inserted),
        "start_time":    str(stats["start_time"]) if stats["start_time"] else None,
        "end_time":      str(stats["end_time"]) if stats["end_time"] else None,
        "has_gps":       bool(stats["has_gps"]),
        "warnings":      [str(w) for w in stats["warnings"]],
        "message":       f"{inserted} ölçüm başarıyla yüklendi.",
    }), 201


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.get("/api/sessions")
def list_sessions():
    sessions = db.get_sessions()
    return _jsonify_rows(sessions)


@app.get("/api/sessions/<int:session_id>/readings")
def session_readings(session_id):
    rows = db.get_session_readings(session_id)
    return _jsonify_rows(rows)


@app.delete("/api/sessions/<int:session_id>")
def delete_session(session_id):
    _admin_required()
    with db.get_conn() as conn:
        conn.cursor().execute(
            "DELETE FROM upload_sessions WHERE id = %s" if db._USE_POSTGRES else "DELETE FROM upload_sessions WHERE id = ?",
            (session_id,) if db._USE_POSTGRES else (session_id,)
        )
    return jsonify({"message": f"Oturum {session_id} silindi."})


# ---------------------------------------------------------------------------
# Map data
# ---------------------------------------------------------------------------

@app.get("/api/map/tracks")
def map_tracks():
    ids_param = request.args.get("session_ids", "")
    if not ids_param:
        sessions = db.get_sessions()
        session_ids = [s["id"] for s in sessions]
    else:
        try:
            session_ids = [int(x) for x in ids_param.split(",") if x.strip()]
        except ValueError:
            return jsonify({"error": "session_ids must be comma-separated integers"}), 400

    raw = db.get_map_tracks(session_ids)

    # Group by session
    tracks = {}
    for row in raw:
        sid = row["session_id"]
        if sid not in tracks:
            tracks[sid] = {
                "session_id":       sid,
                "session_name":     row["session_name"],
                "micro_environment": row["micro_environment"],
                "points":           [],
            }
        tracks[sid]["points"].append({
            "lat":         row["lat"],
            "lon":         row["lon"],
            "pm2_5":       row["pm2_5"],
            "recorded_at": row["recorded_at"],
        })

    return jsonify({"tracks": list(tracks.values())})


@app.get("/api/map/heatmap")
def map_heatmap():
    pollutant = request.args.get("pollutant", "pm2_5")
    start     = request.args.get("start")
    end       = request.args.get("end")
    rows = db.get_heatmap_data(pollutant, start, end)
    return jsonify({"points": rows, "pollutant": pollutant})


@app.get("/api/map/summary")
def map_summary():
    summary = db.get_map_summary()
    if summary["purpleair"]:
        summary["purpleair"]["aqi_category"] = _aqi_category(summary["purpleair"].get("pm2_5"))
    return jsonify(summary)


# ---------------------------------------------------------------------------
# Admin — manual PurpleAir poll trigger
# ---------------------------------------------------------------------------

@app.post("/api/admin/purpleair/poll")
def admin_poll():
    _admin_required()
    threading.Thread(target=purpleair.poll, daemon=True).start()
    return jsonify({"message": "Manuel polling tetiklendi."})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": _now_iso()})


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

def _aqi_category(pm25):
    if pm25 is None:
        return "unknown"
    if pm25 <= 12:
        return "good"
    if pm25 <= 35.4:
        return "moderate"
    if pm25 <= 55.4:
        return "sensitive"
    if pm25 <= 150.4:
        return "unhealthy"
    if pm25 <= 250.4:
        return "very_unhealthy"
    return "hazardous"


def _days_ago(n):
    d = datetime.datetime.utcnow() - datetime.timedelta(days=n)
    return d.isoformat() + "Z"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
