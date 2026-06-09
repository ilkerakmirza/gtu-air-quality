"""
Atmotube CSV upload pipeline.
Parses a CSV file, validates columns, and bulk-inserts into the database.
"""

import io
import pandas as pd

# Map possible CSV column names (Atmotube app has changed headers across versions)
COLUMN_ALIASES = {
    "recorded_at":  ["Date", "date", "Timestamp", "timestamp", "Time", "time", "datetime"],
    "voc_ppm":      ["VOC (ppm)", "VOC(ppm)", "voc", "VOC"],
    "pm1_0":        ["PM1 (ug/m3)", "PM1(ug/m3)", "PM1.0 (ug/m3)", "PM1", "pm1.0"],
    "pm2_5":        ["PM2.5 (ug/m3)", "PM2.5(ug/m3)", "PM2.5", "pm2.5"],
    "pm10_0":       ["PM10 (ug/m3)", "PM10(ug/m3)", "PM10", "pm10"],
    "temperature_c": ["Temperature (C)", "Temperature(C)", "Temp (C)", "temperature", "temp"],
    "humidity_pct": ["Humidity (%)", "Humidity(%)", "humidity", "RH (%)"],
    "pressure_hpa": ["Pressure (hPa)", "Pressure(hPa)", "pressure"],
    "lat":          ["Latitude", "latitude", "lat", "Lat"],
    "lon":          ["Longitude", "longitude", "lon", "Lon", "lng"],
}

REQUIRED_COLUMNS = {"recorded_at", "pm2_5"}


def _detect_column(df_columns: list, aliases: list) -> str | None:
    for alias in aliases:
        if alias in df_columns:
            return alias
    return None


def parse_csv(file_bytes: bytes, filename: str = "upload.csv") -> tuple[list[dict], dict]:
    """
    Parse Atmotube CSV bytes.
    Returns (rows, stats) where stats = {count, start_time, end_time, has_gps, warnings}
    Raises ValueError with a user-friendly message on bad input.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8-sig")
    except Exception as e:
        raise ValueError(f"CSV okunamadı: {e}")

    if df.empty:
        raise ValueError("CSV dosyası boş.")

    # Rename columns to canonical names
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        matched = _detect_column(list(df.columns), aliases)
        if matched:
            rename_map[matched] = canonical

    df = df.rename(columns=rename_map)

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Gerekli sütunlar eksik: {', '.join(missing)}. "
            f"Mevcut sütunlar: {', '.join(df.columns)}"
        )

    # Parse timestamp
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True, errors="coerce")
    invalid_ts = df["recorded_at"].isna().sum()
    if invalid_ts == len(df):
        raise ValueError("Hiçbir tarih/saat değeri ayrıştırılamadı. Sütun formatını kontrol edin.")
    df = df.dropna(subset=["recorded_at"])

    # Numeric columns — coerce to float
    numeric_cols = ["voc_ppm", "pm1_0", "pm2_5", "pm10_0", "temperature_c", "humidity_pct", "pressure_hpa", "lat", "lon"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # GPS presence flag
    has_gps = ("lat" in df.columns and "lon" in df.columns and
                df["lat"].notna().any() and df["lon"].notna().any())

    # Build row dicts (session_id will be set by caller)
    rows = []
    for _, r in df.iterrows():
        row = {
            "session_id":   None,
            "recorded_at":  r["recorded_at"].isoformat(),
            "voc_ppm":      _val(r, "voc_ppm"),
            "pm1_0":        _val(r, "pm1_0"),
            "pm2_5":        _val(r, "pm2_5"),
            "pm10_0":       _val(r, "pm10_0"),
            "temperature_c": _val(r, "temperature_c"),
            "humidity_pct": _val(r, "humidity_pct"),
            "pressure_hpa": _val(r, "pressure_hpa"),
            "lat":          _val(r, "lat"),
            "lon":          _val(r, "lon"),
        }
        rows.append(row)

    warnings = []
    if invalid_ts > 0:
        warnings.append(f"{invalid_ts} satırda geçersiz tarih/saat atlandı.")
    if not has_gps:
        warnings.append("GPS koordinatı bulunamadı; bu oturum haritada rota olarak görünmeyecek.")

    stats = {
        "count":      len(rows),
        "start_time": rows[0]["recorded_at"] if rows else None,
        "end_time":   rows[-1]["recorded_at"] if rows else None,
        "has_gps":    bool(has_gps),
        "warnings":   warnings,
    }

    return rows, stats


def _val(row, col):
    if col not in row.index:
        return None
    v = row[col]
    if pd.isna(v):
        return None
    return float(v) if col not in ("recorded_at",) else v
