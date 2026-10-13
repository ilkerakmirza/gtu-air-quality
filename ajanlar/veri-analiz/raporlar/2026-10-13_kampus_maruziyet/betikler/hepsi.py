"""Raporun (sürüm 1.2) bütün şekillerini (Şekil 1–14) ve sayilar.json'u baştan üretir.

Kullanım: python3 -I hepsi.py <ham klasörü> <rapor klasörü>
<ham klasörü>: sorgular.sql'deki Q1, Q2, Q3'ün Supabase execute_sql çıktıları (Q1.txt, Q2.txt, Q3.txt; MCP yanıtı olduğu gibi).
Ek girdi: depodaki docs/veri/purpleair_229263_2dk_2026-04-27_2026-10-06.csv ve frontend_v2/data/campus.geojson.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a_envanter, b_zaman, c_mekan, d_kisisel, e_en_kotu, f_senaryo, g_saha_kiyas  # noqa: E401,E402

if __name__ == "__main__":
    ham, cikti = sys.argv[1], sys.argv[2]
    yol = os.path.join(cikti, "sayilar.json")
    if os.path.exists(yol):
        os.remove(yol)
    for m in (a_envanter, b_zaman, c_mekan, d_kisisel, e_en_kotu, f_senaryo, g_saha_kiyas):
        m.main(ham, cikti)
