# Veri analizi · hafıza

## Kararlar ve bulgular
- 13 Ekim 2026: ajan kuruldu. İlk görev: kampüste sorunlu alanlar (nerede, ne zaman) ve kişisel maruziyet (ölçülen, en kötü durum,
  iç/dış ortam senaryoları).

## Veri durumu (13 Ekim 2026)
- PurpleAir: 27 Nisan'dan beri 2 dk; 1 Mayıs – 11 Ekim arasında 153 tam gün (gün sınırı Türkiye saati). Kesintiler: 5–7 Temmuz,
  3–5 Ekim. 27–30 Nisan'daki 781 kayıt eski biçimde (arşiv içe aktarımı yarım; `scripts/purpleair_arsiv/BENIOKU.md`).
- Saha (Atmotube yürüyüşleri): 27–30 Nisan, 12 oturum, 4 015 konumlu nokta, üç kişi (Saha ekibi A/B/C).
- Atmotube canlı (ATP-1…5): Haziran–Ekim, seyrek; yalnızca telefonla eşitlenen son değerler.
- CO₂ (iç ortam): 22 Haziran – 21 Temmuz 2026; sonra bulut hizmetinin süresi doldu.

## Açık sorular
- (yok)

## Raporlar
- **13 Ekim 2026 · kampüs maruziyet raporu** (`raporlar/2026-10-13_kampus_maruziyet/`, PDF dahil; kesim 13 Ekim 00:00 TR). Ajan 1 sekiz
  kritik sayıyı bağımsız doğruladı, hepsi tuttu. Ana ajan Tablo 4 ve Şekil 8–9'dan ekip harflerini kaldırdı (oturum + saat + bina
  içi/dışı birlikte kişiyi izlenebilir kılıyordu). Yeniden üretim: Q1–Q3 çıktıları → `python3 -I -B betikler/hepsi.py <ham> <rapor>`;
  ham çıktılar depoya konmaz (saha konumları).
- Saha oturumları (27–30 Nisan) çoğunlukla tek binada geçen çalışma günleri: noktaların %87,8'i Kimya ve Çevre Müh. binasında. G iç–dış
  farkını da içerir; dış ortam sıcak noktaları için K (Atmotube / düzeltilmiş PurpleAir) kullanılmalı.
- Ölçülen kişisel/çatı oranı: Kimya binası 0,65 (oturumlar 0,53–0,88), canlı ATP 0,75; uygulamanın F = 0,5–0,8 aralığıyla uyumlu.
  Atmotube yan yana ölçümü bitince cihaz çarpanıyla yeniden hesaplanmalı.
- CO₂ verisi 22 Haziran 2026 15:01'den itibaren donmuş (2 798 kayıt: 400 ppm / 27,2 °C / %49).
- Yöntem notları (Ajan 1): döngü ve en kötü %5 tam olmayan günlerin saatlerini de içerir (tanımı yaz); kayan pencereler gün sınırında
  kesilir, gece yarısını aşan olaylar iki güne bölünebilir.
- Teknik: ATP canlı analizinde koordinat istenmez (izin sistemi reddetti; yalnızca "kampüs içi" bayrağı). `saatlik.json`'un son saati yarım.
- Açık: Güzide Kafe H1 hücresindeki fazlalık (K = 1,36) tekrarlı ölçümle doğrulanmalı; 10 Mayıs ve 19 Temmuz kısa tepelerin kaynağı bilinmiyor.
- **v1.2 (13 Ekim 2026):** saha karşılaştırması eklendi (§2.8, §3.4; Tablo 5–7; Şekil 10–12). 4 gün, 3 ölçümcü, 12 oturum, 78,5 sa.
  Genel K_TWA 0,80 (%95 blok bootstrap 0,73–0,88), K_D 0,92; 12 ölçümcü-günün 7'sinde aralığın tamamı 1'in altında. Aynı gün
  kişiler arası TWA oranı 1,14–2,20; 28.04'te farkın ~%84'ü kısa tepelerden, 30.04'te ölçüm saatlerinden (ortak pencerede K oranı
  1,83 → 1,32). Kimya binası K 0,70, diğer binalar 1,24. Varyans payları betimseldir, kişi etkisi diye yorumlanmaz. Neyin neden
  kullanıldığı: rapor klasöründeki `karar_kaydi.md`. KVKK: kişi karşılaştırması yalnızca "Ölçümcü A/B/C", konum zaman çizelgesi yok.
