import os
from dotenv import load_dotenv

load_dotenv()

PURPLEAIR_API_KEY = os.getenv("PURPLEAIR_API_KEY", "")
PURPLEAIR_SENSOR_ID = int(os.getenv("PURPLEAIR_SENSOR_ID", "229263"))
PURPLEAIR_LAT = float(os.getenv("PURPLEAIR_LAT", "40.806155"))
PURPLEAIR_LON = float(os.getenv("PURPLEAIR_LON", "29.360985"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", "campus_air.db")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "2"))

# CORS origins for the frontend
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
