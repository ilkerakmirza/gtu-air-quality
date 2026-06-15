"""
CSB Yerel Toplayıcı — Türkiye'deki bir bilgisayarda çalışır.

CSB sitesi (sim.csb.gov.tr) yurtdışı/datacenter IP'lerini engellediği için Render
sunucusu erişemiyor. Bu script Türkiye IP'sinden CSB Tuzla PM2.5'i çekip doğrudan
Supabase arşivine yazar. Web sitesi (/api/csb/latest) bu arşivden okur.

KULLANIM:
  1) DATABASE_URL ortam değişkenini Supabase bağlantı adresinle ayarla.
  2) Windows Görev Zamanlayıcı (Task Scheduler) ile saatte bir çalıştır:
       python csb_yerel_toplayici.py
  (CSB saatlik güncellediği için saatte bir yeterli.)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.stdout.reconfigure(encoding="utf-8")

# DATABASE_URL ayarlı değilse buraya yazabilirsin (veya ortam değişkeni kullan):
# os.environ.setdefault("DATABASE_URL", "postgresql://postgres.xxx:SIFRE@...:6543/postgres")

if not os.environ.get("DATABASE_URL"):
    print("HATA: DATABASE_URL ayarlı değil. Supabase bağlantı adresini ayarla.")
    sys.exit(1)

import collector
n = collector.collect_csb()
print(f"CSB toplayıcı: {n} yeni kayıt Supabase'e yazıldı.")
