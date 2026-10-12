# Veri kontrolü · hafıza

## Kararlar ve bulgular
- **12 Ekim 2026, PurpleAir arşivi (27 Nis – 6 Eki, sensör 229263, 2 dk):** UYGUN. Sunucu kayıtlarının 3391'inden 3385'i arşivle
  aynı zaman damgalı, 3384'ü aynı değerli (fark ≤ 0,05 µg/m³; sunucu 2, arşiv 1 ondalık); 1 tutarsız kayıt (22 Haziran 11:50:28Z,
  B kanalı 9,0 / 8,3). Tamlık %94,4; 3718 saat; 153 tam gün (≥ 18 saat), 4 gösterge gün. Kesintiler iki kaynakta aynı
  (5–7 Temmuz, 3–5 Ekim: sensör kapalı). A/B denetimi: 134 iki dakikalık kayıt (%0,12), 5 saat; Mayıs başında B kanalı hafif yüksek.
  27 kısa ani yükselme, 24'ünde iki kanal uyumlu (gerçek olay; ayıklanmaz).
- Beklenen sayılar (içe aktarma): 781 Nisan kaydı değişir, 3341 kayda cf_1, 107 361 yeni kayıt; sonuçta 6 Ekim 21:00 UTC öncesi
  110 752 kayıt, 110 745'inde cf_1. Elle denetim (TR): 15 Mayıs 14:00 → 11,053; 1 Ağustos 08:00 → 7,370; 6 Mayıs 08:00 → 27,931 µg/m³.

## Literatür durumu
- Barkjohn, Gantt, Clements (2021), *AMT* 14:4617–4637, doi:10.5194/amt-14-4617-2021: girdi cf_1 ve PurpleAir nemi, %90 günlük
  tamlık **birincil (özetten)**; katsayılar 0,524 / 0,0862 / 5,75 ve 5 µg/m³ + %70 kanal kuralı **ikincil** (tam metin bulut
  ortamından açılamadı).
- 18 saat (%75) günlük tamlık kuralı: 40 CFR 50 **Ek K** (PM₁₀). Ek N (PM₂.₅) için 18/24 ifadesi doğrulanmadı.
- Üretici arşivi ile canlı API kaydının eşdeğerliği için literatür kaynağı bulunamadı; veriyle gösterildi.

## Açık sorular
- Katsayıları masaüstü oturumunda makalenin tam metninden teyit et.

## Betikler
`betikler/`: `ortak.py` (yükleyiciler), `tahmin.py` (adım sayıları), `kalite.py` (uygunluk), `nokta.py` (elle denetim saatleri),
`gun.py` (günlük tamlık), `ek.py` (boşluklar, aykırılar), `bulanik.py` (1 s kayık kayıtlar), `dosya.py`.
Kullanım: `python3 -I <betik> <csv> [<veritabanı anlık görüntüsü>] <betik klasörü>`.
