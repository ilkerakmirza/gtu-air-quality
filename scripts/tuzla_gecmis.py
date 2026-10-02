"""
Tuzla hava kalitesi istasyonunun saatlik geçmişini İBB Açık Veri servisinden çeker ve
frontend_v2/data/tuzla_saatlik.json dosyasına yazar (kampüs–bölge karşılaştırması için).

ÇŞB sitesi yurt dışı IP'leri engellediği için İBB servisi kullanılır (aynı istasyon).
İBB bu istasyon için PM2.5 geçmişi VERMİYOR (yalnızca PM10, SO2, O3, NO2, CO); PM2.5 için scripts/csb_gecmis.py.
Var olan dosyadaki PM2.5 değerleri korunur. Her yerden (GitHub Actions dahil) çalışır.
Kullanım:  python scripts/tuzla_gecmis.py [BASLANGIC=2026-04-01]
"""
import json, sys, ssl, datetime as dt, urllib.request, urllib.parse

STATION_ID = "30a7a252-f4ea-43f8-a8db-fdea5ca332d3"   # İBB: Tuzla
URL = "https://api.ibb.gov.tr/havakalitesi/OpenDataPortalHandler/GetAQIByStationId?"
OUT = "frontend_v2/data/tuzla_saatlik.json"

ctx = ssl.create_default_context()


def fetch(a, z):
    q = urllib.parse.urlencode({"StationId": STATION_ID,
                                "StartDate": a.strftime("%d.%m.%Y %H:%M:%S"),
                                "EndDate": z.strftime("%d.%m.%Y %H:%M:%S")})
    req = urllib.request.Request(URL + q, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    start = dt.date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 else "2026-04-01")
    end = dt.date.today() + dt.timedelta(days=1)
    # Var olan dosyadaki ÇŞB PM2.5 değerlerini koru; İBB yalnızca PM10 (ve PM2.5 verirse onu) doldurur
    rows = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            rows = {r["t"]: r for r in json.load(f).get("veri", [])}
    except FileNotFoundError:
        pass
    d = start
    while d < end:                                   # 7 günlük parçalar
        z = min(d + dt.timedelta(days=7), end)
        for r in fetch(dt.datetime.combine(d, dt.time()), dt.datetime.combine(z, dt.time())):
            c = r.get("Concentration") or {}
            t = (r.get("ReadTime") or "")[:16]      # Türkiye saati, "YYYY-MM-DDTHH:MM"
            pm25, pm10 = c.get("PM25"), c.get("PM10")
            if t and (pm25 is not None or pm10 is not None):
                row = rows.setdefault(t, {"t": t, "pm2_5": None, "pm10": None})
                if pm25 is not None: row["pm2_5"] = pm25
                if pm10 is not None: row["pm10"] = pm10
        d = z
    data = sorted(rows.values(), key=lambda r: r["t"])
    n25 = sum(r["pm2_5"] is not None for r in data); n10 = sum(r["pm10"] is not None for r in data)
    print(f"{len(data)} saat · PM2.5 olan: {n25} · PM10 olan: {n10} · {data[0]['t'] if data else '-'} → {data[-1]['t'] if data else '-'}")
    months = {}
    for r in data:
        m = months.setdefault(r["t"][:7], [0, 0, 0]); m[0] += 1; m[1] += r["pm2_5"] is not None; m[2] += r["pm10"] is not None
    for k, v in sorted(months.items()): print(f"  {k}: {v[0]} saat · PM2.5 {v[1]} · PM10 {v[2]}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"istasyon": "Tuzla (İBB/ÇŞB)", "kaynak": "PM10: İBB Açık Veri (GetAQIByStationId) · PM2.5: ÇŞB (scripts/csb_gecmis.py)",
                   "saat_dilimi": "Europe/Istanbul", "guncelleme": dt.datetime.utcnow().isoformat(timespec="minutes") + "Z",
                   "veri": data}, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
