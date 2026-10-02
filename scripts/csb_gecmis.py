"""
Tuzla istasyonunun saatlik PM2.5 (ve PM10) geçmişini resmî ÇŞB sitesinden (sim.csb.gov.tr) indirir ve
frontend_v2/data/tuzla_saatlik.json dosyasına ekler. Kampüs–bölge karşılaştırması bu dosyayı kullanır.

ÇŞB sitesi yurt dışı IP'lerini engeller: bu betik TÜRKİYE'deki bir bilgisayarda çalıştırılmalıdır
(ör. masaüstü Claude uygulamasının çalıştığı bilgisayar). İBB açık veri servisi Tuzla için PM2.5 geçmişi vermiyor.

Kullanım (depo kökünden):
    pip install requests
    python scripts/csb_gecmis.py 2026-04-01            # başlangıç tarihi; bitiş bugün
    git add frontend_v2/data/tuzla_saatlik.json && git commit -m "Tuzla PM2.5 geçmişi (ÇŞB)" && git push origin main
"""
import os, sys, json, time, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import requests
import csb   # backend/csb.py: adresler, istasyon kimliği, CSRF token ayrıştırma

OUT = os.path.join(os.path.dirname(__file__), "..", "frontend_v2", "data", "tuzla_saatlik.json")


def session():
    s = requests.Session()
    s.verify = csb._VERIFY
    s.headers.update({"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    page = s.get(csb.PAGE, timeout=30)
    m = csb._TOKEN_RE.search(page.text)
    if not m:
        raise RuntimeError("ÇŞB sayfasından CSRF token alınamadı (Türkiye dışından mı çalışıyor?)")
    return s, m.group(1)


def fetch(s, token, a, z):
    payload = {
        "__RequestVerificationToken": token, "StationType": "1", "StationIds": csb.STATION_ID,
        "Parameters": "PM25,PM10", "DataPeriods": "8",   # 8 = saatlik
        "StartDateTime": a.strftime("%d.%m.%Y") + " 00:00", "EndDateTime": z.strftime("%d.%m.%Y") + " 23:00",
    }
    r = s.post(csb.DATA, data=payload, timeout=90)
    return ((r.json().get("Object") or {}).get("Data")) or []


def main():
    start = dt.date.fromisoformat(sys.argv[1] if len(sys.argv) > 1 else "2026-04-01")
    end = dt.date.today()
    with open(OUT, encoding="utf-8") as f:
        doc = json.load(f)
    rows = {r["t"]: r for r in doc.get("veri", [])}
    s, token = session()
    d, added = start, 0
    while d <= end:                                   # 10 günlük parçalar (site uzun aralıkları reddedebiliyor)
        z = min(d + dt.timedelta(days=9), end)
        for r in fetch(s, token, d, z):
            t = str(r.get("ReadTime") or "").replace(" ", "T")[:16]   # Türkiye saati
            if not t:
                continue
            row = rows.setdefault(t, {"t": t, "pm2_5": None, "pm10": None})
            if r.get("PM25") is not None:
                row["pm2_5"] = r["PM25"]; added += 1
            if r.get("PM10") is not None and row.get("pm10") is None:
                row["pm10"] = r["PM10"]
        print(f"{d} → {z}: tamam")
        d = z + dt.timedelta(days=1)
        time.sleep(1)
    doc["veri"] = sorted(rows.values(), key=lambda r: r["t"])
    doc["kaynak"] = "PM2.5: ÇŞB (sim.csb.gov.tr) · PM10: İBB Açık Veri / ÇŞB"
    doc["guncelleme"] = dt.datetime.utcnow().isoformat(timespec="minutes") + "Z"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    n = sum(r["pm2_5"] is not None for r in doc["veri"])
    print(f"Bitti: {added} saatlik PM2.5 değeri eklendi; dosyada toplam {n} saat PM2.5 var → {OUT}")


if __name__ == "__main__":
    main()
