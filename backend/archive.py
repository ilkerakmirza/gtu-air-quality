"""
Kalıcı veri arşivi — Supabase/PostgreSQL.

Üç kaynaktan (PurpleAir, İBB, Atmotube) gelen canlı ölçümleri tek ortak
`measurements` tablosunda biriktirir. İleride CSV olarak indirilip analiz edilir.

DATABASE_URL ortam değişkeni ayarlı değilse modül sessizce devre dışı kalır
(uygulama yine çalışır, sadece arşivleme yapılmaz).

Tablo:
  source        kaynak: 'purpleair' | 'ibb' | 'atmotube'
  device        cihaz/istasyon: 'PA-II' | 'Tuzla' | 'ATP-1'..'ATP-5'
  recorded_at   ölçüm zamanı (UTC)
  pm1_0, pm2_5, pm10_0, voc_ppm, temperature_c, humidity_pct, pressure_hpa
  lat, lon      konum (varsa)
  ingested_at   kayda eklenme zamanı
  UNIQUE(source, device, recorded_at) — aynı ölçüm iki kez yazılmaz
"""

import os
import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
_enabled = bool(DATABASE_URL)

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None
    _enabled = False


def is_enabled():
    return _enabled


def _connect():
    # Supabase bağlantıları SSL ister
    return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=15)


SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT NOT NULL,
    device        TEXT,
    recorded_at   TIMESTAMPTZ NOT NULL,
    pm1_0         DOUBLE PRECISION,
    pm2_5         DOUBLE PRECISION,
    pm10_0        DOUBLE PRECISION,
    voc_ppm       DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION,
    humidity_pct  DOUBLE PRECISION,
    pressure_hpa  DOUBLE PRECISION,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    ingested_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source, device, recorded_at)
);
CREATE INDEX IF NOT EXISTS idx_meas_time   ON measurements (recorded_at);
CREATE INDEX IF NOT EXISTS idx_meas_source ON measurements (source);
"""

_COLS = ["source", "device", "recorded_at", "pm1_0", "pm2_5", "pm10_0",
         "voc_ppm", "temperature_c", "humidity_pct", "pressure_hpa", "lat", "lon"]


def init():
    """Tabloyu oluştur (varsa dokunma). Açılışta bir kez çağrılır."""
    if not _enabled:
        print("[archive] DATABASE_URL yok — kalıcı arşiv devre dışı.")
        return
    try:
        con = _connect()
        cur = con.cursor()
        cur.execute(SCHEMA)
        con.commit()
        con.close()
        print("[archive] measurements tablosu hazır (Supabase).")
    except Exception as e:
        print(f"[archive] init hatası: {e}")


def log_rows(rows):
    """rows: dict listesi. Aynı (source,device,recorded_at) varsa atlanır."""
    if not _enabled or not rows:
        return 0
    try:
        con = _connect()
        cur = con.cursor()
        values = [tuple(r.get(c) for c in _COLS) for r in rows if r.get("recorded_at")]
        if not values:
            con.close()
            return 0
        sql = f"""INSERT INTO measurements ({','.join(_COLS)})
                  VALUES %s ON CONFLICT (source, device, recorded_at) DO NOTHING"""
        psycopg2.extras.execute_values(cur, sql, values)
        n = cur.rowcount
        con.commit()
        con.close()
        return n
    except Exception as e:
        print(f"[archive] log hatası: {e}")
        return 0


def latest_by_source(source):
    """Bir kaynağın arşivdeki en son kaydını döner (Türkiye saatiyle)."""
    if not _enabled:
        return None
    try:
        con = _connect(); cur = con.cursor()
        cur.execute("""SELECT device, pm2_5, pm10_0, lat, lon,
                         to_char(recorded_at AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI')
                       FROM measurements WHERE source=%s
                       ORDER BY recorded_at DESC LIMIT 1""", (source,))
        r = cur.fetchone(); con.close()
        if not r:
            return None
        return {"device": r[0], "pm2_5": r[1], "pm10_0": r[2],
                "lat": r[3], "lon": r[4], "recorded_at": r[5]}
    except Exception as e:
        print(f"[archive] latest_by_source hatası: {e}")
        return None


def stats():
    """Özet: kaynak başına kayıt sayısı ve tarih aralığı."""
    if not _enabled:
        return {"enabled": False}
    try:
        con = _connect()
        cur = con.cursor()
        cur.execute("""SELECT source, COUNT(*),
                         to_char(MIN(recorded_at) AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI'),
                         to_char(MAX(recorded_at) AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI')
                       FROM measurements GROUP BY source ORDER BY source""")
        by_source = [
            {"source": r[0], "count": r[1], "first_TR": r[2], "last_TR": r[3]}
            for r in cur.fetchall()
        ]
        cur.execute("SELECT COUNT(*) FROM measurements")
        total = cur.fetchone()[0]
        con.close()
        return {"enabled": True, "total": total, "by_source": by_source}
    except Exception as e:
        return {"enabled": True, "error": str(e)}


def iter_csv(source=None, start=None, end=None):
    """Tüm ölçümleri CSV satırları olarak akıt (export endpoint için).
    Zaman sütunları Türkiye saatiyle (Europe/Istanbul) verilir."""
    import io, csv
    # Başlık: zaman sütunları Türkiye saati olduğunu belli etsin
    header = (["source", "device", "recorded_at_TR"] + _COLS[3:] + ["ingested_at_TR"])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    if not _enabled:
        return
    con = _connect()
    cur = con.cursor()  # düz cursor (transaction pooler named cursor desteklemez)
    # recorded_at / ingested_at → Türkiye yerel saatine çevir
    mid = ",".join(_COLS[3:])  # pm/sensor kolonları
    q = (f"SELECT source, device, "
         f"to_char(recorded_at AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI:SS'), "
         f"{mid}, "
         f"to_char(ingested_at AT TIME ZONE 'Europe/Istanbul','YYYY-MM-DD HH24:MI:SS') "
         f"FROM measurements WHERE 1=1")
    params = []
    if source: q += " AND source=%s"; params.append(source)
    if start:  q += " AND recorded_at>=%s"; params.append(start)
    if end:    q += " AND recorded_at<=%s"; params.append(end)
    q += " ORDER BY recorded_at"
    cur.execute(q, params)
    while True:
        batch = cur.fetchmany(1000)
        if not batch:
            break
        for row in batch:
            w.writerow(row)
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
    con.close()
