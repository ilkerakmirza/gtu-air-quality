"""
Database layer — supports both SQLite (local dev) and PostgreSQL (production).
Switch by setting DATABASE_URL in .env. If DATABASE_URL is empty, SQLite is used.
"""

import sqlite3
import os
from contextlib import contextmanager
from config import DATABASE_URL, SQLITE_PATH

_USE_POSTGRES = bool(DATABASE_URL)

if _USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

@contextmanager
def get_conn():
    if _USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


import datetime as _dt

def _isoize(d):
    """datetime/date değerlerini ISO 8601 string'e çevirir (frontend ISO bekler).
    Postgres'ten gelen datetime'lar aksi halde RFC formatında serileşip 'Invalid Date' verir."""
    for k, v in d.items():
        if isinstance(v, (_dt.datetime, _dt.date)):
            d[k] = v.isoformat()
    return d


def fetchall(cursor):
    rows = cursor.fetchall()
    if _USE_POSTGRES:
        cols = [desc[0] for desc in cursor.description]
        return [_isoize(dict(zip(cols, row))) for row in rows]
    return [dict(row) for row in rows]


def fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    if _USE_POSTGRES:
        cols = [desc[0] for desc in cursor.description]
        return _isoize(dict(zip(cols, row)))
    return dict(row)


# ---------------------------------------------------------------------------
# Schema initialisation (SQLite only; PostgreSQL schema created via Supabase UI)
# ---------------------------------------------------------------------------

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS purpleair_readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at  TEXT NOT NULL,
    pm1_0        REAL,
    pm2_5        REAL,
    pm2_5_a      REAL,
    pm2_5_b      REAL,
    pm10_0       REAL,
    temperature_c REAL,
    humidity_pct REAL,
    lat          REAL DEFAULT 40.80380,
    lon          REAL DEFAULT 29.44690,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS upload_sessions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name       TEXT NOT NULL,
    micro_environment  TEXT,
    sensor_number      INTEGER,
    csv_filename       TEXT,
    reading_count      INTEGER,
    start_time         TEXT,
    end_time           TEXT,
    notes              TEXT,
    uploaded_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS atmotube_readings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     INTEGER REFERENCES upload_sessions(id) ON DELETE CASCADE,
    recorded_at    TEXT NOT NULL,
    voc_ppm        REAL,
    pm1_0          REAL,
    pm2_5          REAL,
    pm10_0         REAL,
    temperature_c  REAL,
    humidity_pct   REAL,
    pressure_hpa   REAL,
    lat            REAL,
    lon            REAL,
    created_at     TEXT DEFAULT (datetime('now')),
    UNIQUE (session_id, recorded_at)
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS purpleair_readings (
    id            BIGSERIAL PRIMARY KEY,
    recorded_at   TIMESTAMPTZ NOT NULL,
    pm1_0         REAL,
    pm2_5         REAL,
    pm2_5_a       REAL,
    pm2_5_b       REAL,
    pm10_0        REAL,
    temperature_c REAL,
    humidity_pct  REAL,
    lat           REAL DEFAULT 40.80380,
    lon           REAL DEFAULT 29.44690,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS upload_sessions (
    id                BIGSERIAL PRIMARY KEY,
    session_name      TEXT NOT NULL,
    micro_environment TEXT,
    sensor_number     INTEGER CHECK (sensor_number BETWEEN 1 AND 6),
    csv_filename      TEXT,
    reading_count     INTEGER,
    start_time        TIMESTAMPTZ,
    end_time          TIMESTAMPTZ,
    notes             TEXT,
    uploaded_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS atmotube_readings (
    id            BIGSERIAL PRIMARY KEY,
    session_id    BIGINT REFERENCES upload_sessions(id) ON DELETE CASCADE,
    recorded_at   TIMESTAMPTZ NOT NULL,
    voc_ppm       REAL,
    pm1_0         REAL,
    pm2_5         REAL,
    pm10_0        REAL,
    temperature_c REAL,
    humidity_pct  REAL,
    pressure_hpa  REAL,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (session_id, recorded_at)
);
"""


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        if _USE_POSTGRES:
            for stmt in POSTGRES_SCHEMA.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            cur.executescript(SQLITE_SCHEMA)
    print(f"[db] Schema initialised ({'PostgreSQL' if _USE_POSTGRES else 'SQLite'})")


# ---------------------------------------------------------------------------
# PurpleAir writes / reads
# ---------------------------------------------------------------------------

def save_purpleair_reading(data: dict):
    sql = """
    INSERT INTO purpleair_readings
        (recorded_at, pm1_0, pm2_5, pm2_5_a, pm2_5_b, pm10_0, temperature_c, humidity_pct, lat, lon)
    VALUES
        (%(recorded_at)s, %(pm1_0)s, %(pm2_5)s, %(pm2_5_a)s, %(pm2_5_b)s, %(pm10_0)s,
         %(temperature_c)s, %(humidity_pct)s, %(lat)s, %(lon)s)
    """ if _USE_POSTGRES else """
    INSERT OR IGNORE INTO purpleair_readings
        (recorded_at, pm1_0, pm2_5, pm2_5_a, pm2_5_b, pm10_0, temperature_c, humidity_pct, lat, lon)
    VALUES
        (:recorded_at, :pm1_0, :pm2_5, :pm2_5_a, :pm2_5_b, :pm10_0,
         :temperature_c, :humidity_pct, :lat, :lon)
    """
    with get_conn() as conn:
        conn.cursor().execute(sql, data)


def get_latest_purpleair():
    sql = "SELECT * FROM purpleair_readings ORDER BY recorded_at DESC LIMIT 1"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return fetchone(cur)


def get_purpleair_history(start: str, end: str, interval: str = "raw"):
    if interval == "hourly":
        if _USE_POSTGRES:
            sql = """
            SELECT date_trunc('hour', recorded_at) AS recorded_at,
                   AVG(pm2_5) AS pm2_5, AVG(pm10_0) AS pm10_0,
                   AVG(temperature_c) AS temperature_c, AVG(humidity_pct) AS humidity_pct
            FROM purpleair_readings
            WHERE recorded_at BETWEEN %(start)s AND %(end)s
            GROUP BY 1 ORDER BY 1
            """
        else:
            sql = """
            SELECT strftime('%Y-%m-%dT%H:00:00', recorded_at) AS recorded_at,
                   AVG(pm2_5) AS pm2_5, AVG(pm10_0) AS pm10_0,
                   AVG(temperature_c) AS temperature_c, AVG(humidity_pct) AS humidity_pct
            FROM purpleair_readings
            WHERE recorded_at BETWEEN :start AND :end
            GROUP BY 1 ORDER BY 1
            """
    elif interval == "daily":
        if _USE_POSTGRES:
            sql = """
            SELECT date_trunc('day', recorded_at) AS recorded_at,
                   AVG(pm2_5) AS pm2_5, AVG(pm10_0) AS pm10_0,
                   AVG(temperature_c) AS temperature_c, AVG(humidity_pct) AS humidity_pct
            FROM purpleair_readings
            WHERE recorded_at BETWEEN %(start)s AND %(end)s
            GROUP BY 1 ORDER BY 1
            """
        else:
            sql = """
            SELECT strftime('%Y-%m-%dT00:00:00', recorded_at) AS recorded_at,
                   AVG(pm2_5) AS pm2_5, AVG(pm10_0) AS pm10_0,
                   AVG(temperature_c) AS temperature_c, AVG(humidity_pct) AS humidity_pct
            FROM purpleair_readings
            WHERE recorded_at BETWEEN :start AND :end
            GROUP BY 1 ORDER BY 1
            """
    else:
        sql = ("SELECT * FROM purpleair_readings WHERE recorded_at BETWEEN %(start)s AND %(end)s ORDER BY recorded_at"
               if _USE_POSTGRES else
               "SELECT * FROM purpleair_readings WHERE recorded_at BETWEEN :start AND :end ORDER BY recorded_at")

    params = {"start": start, "end": end} if _USE_POSTGRES else {"start": start, "end": end}
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return fetchall(cur)


# ---------------------------------------------------------------------------
# Atmotube writes / reads
# ---------------------------------------------------------------------------

def create_upload_session(meta: dict) -> int:
    if _USE_POSTGRES:
        sql = """
        INSERT INTO upload_sessions
            (session_name, micro_environment, sensor_number, csv_filename, reading_count, start_time, end_time, notes)
        VALUES (%(session_name)s, %(micro_environment)s, %(sensor_number)s, %(csv_filename)s,
                %(reading_count)s, %(start_time)s, %(end_time)s, %(notes)s)
        RETURNING id
        """
    else:
        sql = """
        INSERT INTO upload_sessions
            (session_name, micro_environment, sensor_number, csv_filename, reading_count, start_time, end_time, notes)
        VALUES (:session_name, :micro_environment, :sensor_number, :csv_filename,
                :reading_count, :start_time, :end_time, :notes)
        """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, meta)
        if _USE_POSTGRES:
            return cur.fetchone()[0]
        return cur.lastrowid


def bulk_insert_atmotube(rows: list[dict]):
    if not rows:
        return 0
    if _USE_POSTGRES:
        sql = """
        INSERT INTO atmotube_readings
            (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0, temperature_c, humidity_pct, pressure_hpa, lat, lon)
        VALUES (%(session_id)s, %(recorded_at)s, %(voc_ppm)s, %(pm1_0)s, %(pm2_5)s, %(pm10_0)s,
                %(temperature_c)s, %(humidity_pct)s, %(pressure_hpa)s, %(lat)s, %(lon)s)
        ON CONFLICT (session_id, recorded_at) DO NOTHING
        """
        with get_conn() as conn:
            psycopg2.extras.execute_batch(conn.cursor(), sql, rows)
    else:
        sql = """
        INSERT OR IGNORE INTO atmotube_readings
            (session_id, recorded_at, voc_ppm, pm1_0, pm2_5, pm10_0, temperature_c, humidity_pct, pressure_hpa, lat, lon)
        VALUES (:session_id, :recorded_at, :voc_ppm, :pm1_0, :pm2_5, :pm10_0,
                :temperature_c, :humidity_pct, :pressure_hpa, :lat, :lon)
        """
        with get_conn() as conn:
            conn.cursor().executemany(sql, rows)
    return len(rows)


def get_sessions():
    sql = "SELECT * FROM upload_sessions ORDER BY uploaded_at DESC"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        return fetchall(cur)


def get_session_readings(session_id: int):
    sql = ("SELECT * FROM atmotube_readings WHERE session_id = %(sid)s ORDER BY recorded_at"
           if _USE_POSTGRES else
           "SELECT * FROM atmotube_readings WHERE session_id = :sid ORDER BY recorded_at")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, {"sid": session_id})
        return fetchall(cur)


def get_map_tracks(session_ids: list[int]):
    if not session_ids:
        return []
    placeholders = ",".join(["%s"] * len(session_ids)) if _USE_POSTGRES else ",".join(["?"] * len(session_ids))
    sql = f"""
    SELECT r.session_id, r.recorded_at, r.pm2_5, r.lat, r.lon,
           s.session_name, s.micro_environment
    FROM atmotube_readings r
    JOIN upload_sessions s ON s.id = r.session_id
    WHERE r.session_id IN ({placeholders}) AND r.lat IS NOT NULL
    ORDER BY r.session_id, r.recorded_at
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, session_ids)
        return fetchall(cur)


def get_heatmap_data(pollutant: str = "pm2_5", start: str = None, end: str = None):
    allowed = {"pm2_5", "pm10_0", "pm1_0", "voc_ppm"}
    if pollutant not in allowed:
        pollutant = "pm2_5"

    conditions = ["lat IS NOT NULL"]
    params = {}
    if start:
        conditions.append("recorded_at >= :start" if not _USE_POSTGRES else "recorded_at >= %(start)s")
        params["start"] = start
    if end:
        conditions.append("recorded_at <= :end" if not _USE_POSTGRES else "recorded_at <= %(end)s")
        params["end"] = end

    where = " AND ".join(conditions)
    sql = f"SELECT lat, lon, {pollutant} AS value FROM atmotube_readings WHERE {where} AND {pollutant} IS NOT NULL"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return fetchall(cur)


def get_map_summary():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM purpleair_readings ORDER BY recorded_at DESC LIMIT 1")
        pa = fetchone(cur)
        cur.execute("SELECT COUNT(*) AS cnt FROM upload_sessions")
        sessions_count = fetchone(cur)["cnt"]
        cur.execute("""
        SELECT micro_environment, AVG(pm2_5) AS avg_pm2_5, COUNT(*) AS reading_count
        FROM atmotube_readings r
        JOIN upload_sessions s ON s.id = r.session_id
        WHERE r.pm2_5 IS NOT NULL
        GROUP BY micro_environment
        """)
        envs = fetchall(cur)
    return {"purpleair": pa, "sessions_count": sessions_count, "micro_environments": envs}
