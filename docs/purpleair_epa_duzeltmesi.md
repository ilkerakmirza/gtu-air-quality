# PurpleAir PM₂.₅ için US EPA düzeltmesi

**Belge sürümü:** 1.0 · 8 Ekim 2026
**Kodda:** `frontend_v2/js/colorscale.js` → `epaPM25()`, `paChannelsAgree()`, `paCorrect()`; uygulandığı tek yer
`frontend_v2/js/api.js` (`purpleairLatest`, `purpleairHistory`). Sunucu saatlik/günlük geçmişte A ve B kanal
ortalamalarını da döndürür (`backend/db.py` → `get_purpleair_history()`).
**İlgili belge:** Uygulamadaki tüm eşik ve hesapların kaydı → [`hesaplama_ve_kaynaklar.md`](hesaplama_ve_kaynaklar.md)

---

## Kısaca (savunma için)

1. **Sorun:** PurpleAir gibi düşük maliyetli optik sensörler PM₂.₅'i referans (resmî) cihazlara göre yüksek okur ve
   nemden etkilenir. ABD genelinde ham değer yaklaşık **%40 yüksektir** (Barkjohn vd., 2021).
2. **Çözüm:** ABD Çevre Koruma Ajansı'nın (US EPA) yaklaşık 12 000 eş zamanlı ölçümle geliştirdiği ve kendi
   **AirNow Yangın ve Duman Haritası**'nda bugün de uyguladığı düzeltme formülü kullanılır. Yeni bir formül
   türetilmedi; yayımlanmış, hakemli ve resmî olarak kullanılan yöntem aynen uygulandı.
3. **Girdiler:** PurpleAir'in iki lazer kanalının (A ve B) ortalaması ve sensörün kendi nem ölçümü.
4. **Kalite kontrolü:** İki kanal birbirinden çok farklıysa (hem ≥ 5 µg/m³ hem ≥ %70) o ölçüm kullanılmaz (EPA kuralı).
5. **Yerel tutarlılık:** 6,4 km uzaktaki resmî Tuzla istasyonuyla aynı saatlerde (241 saat) karşılaştırıldığında
   kampüs ham değerleri ortalama **%43 yüksekken**, düzeltilmiş değerler **%2 düşüktür**. Ortalama mutlak fark
   10,3'ten 6,4 µg/m³'e iner. Bu bir kolokasyon (yan yana ölçüm) değildir ama düzeltmenin yönünü ve büyüklüğünü destekler.
6. **Sınırlılık:** Formül ABD verisiyle geliştirildi; Türkiye'de yerinde doğrulanmadı. Çöl tozu olaylarında PM₂.₅
   olduğundan düşük görünebilir. PM₁₀ ve Atmotube saha ölçümleri için yerleşik bir düzeltme yoktur; bunlar ham gösterilir.

---

## 1. Formül

Girdiler:
- **PA** = PurpleAir `pm2.5_atm` değeri, A ve B kanallarının ortalaması (µg/m³). Sunucu bu değeri 2 dakikada bir kaydeder.
- **RH** = PurpleAir'in kendi bağıl nem ölçümü (%). Eksikse ya da 0–100 dışındaysa **%50** alınır (EPA kuralı).

| PA aralığı (µg/m³) | Düzeltilmiş PM₂.₅ |
|---|---|
| PA < 30 | 0,524 × PA − 0,0862 × RH + 5,75 |
| 30 ≤ PA < 50 | [0,786 × w + 0,524 × (1 − w)] × PA − 0,0862 × RH + 5,75 ; w = PA/20 − 1,5 |
| 50 ≤ PA < 210 | 0,786 × PA − 0,0862 × RH + 5,75 |
| 210 ≤ PA < 260 | [0,69 × w + 0,786 × (1 − w)] × PA − 0,0862 × RH × (1 − w) + 2,966 × w + 5,75 × (1 − w) + 8,84×10⁻⁴ × PA² × w ; w = PA/50 − 4,2 |
| PA ≥ 260 | 2,966 + 0,69 × PA + 8,84×10⁻⁴ × PA² |

- İlk satır, Barkjohn vd. (2021) ABD geneli düzeltmesinin kendisidir. Diğer satırlar EPA'nın yüksek derişimler için
  yaptığı genişletmedir (Barkjohn vd., 2022). w ağırlıkları geçiş bölgelerinde iki denklemi yumuşakça birleştirir;
  fonksiyon sınırlarda süreklidir (birim testleriyle doğrulandı, §5).
- **Neden cf_atm?** Formül sensörün `cf_1` çıktısıyla geliştirildi. EPA ise haritasında, PurpleAir API'si
  ortalamalı `cf_1` vermediği için aynı düzeltmeyi `cf_atm` üzerinde uygular (AirNow Soru-Cevap belgesi). İki değer
  düşük derişimde (~25–28 µg/m³'e kadar) aynıdır; yüksek derişimde `cf_atm` ≈ ⅔ × `cf_1` olur. 30 µg/m³ üstündeki
  0,786 eğimi, 0,524 eğiminin bu orana göre karşılığıdır (0,524 × 1,5 = 0,786). Uygulamamız sunucunun kaydettiği
  `pm2.5_atm` değerini kullandığından EPA haritasıyla birebir aynı girdiyle çalışır.
- **Negatif sonuç:** Çok temiz ve çok nemli havada formül 0'ın altına inebilir (ör. PA = 0,5, RH = %95). Derişim negatif
  olamayacağından sonuç 0 alınır. Bu bir **uygulama kuralıdır**; EPA belgelerinde ayrıca belirtilmemiştir.
- **Ortalama alma:** Formül 24 saatlik veriyle geliştirilmiş, EPA tarafından saatlik veride kullanılmaktadır.
  Uygulamada saatlik ortalamalara (Sağlık, Özet aylık, kampüs–bölge, maruziyet) ve en son 2 dakikalık ölçüme
  (Özet'teki anlık HKİ, harita, panel) uygulanır. Anlık değer **gösterge** niteliğindedir.

## 2. Kalite kontrolü (A ve B kanalları)

PurpleAir PA-II içinde iki ayrı lazer sayacı vardır. Biri arızalanır ya da kirlenirse iki kanal ayrışır.

- Göreli fark = |A − B| / ((A + B) / 2).
- **Hem |A − B| ≥ 5 µg/m³ hem göreli fark ≥ %70 ise** ölçüm geçersizdir ve hiçbir hesaba girmez (EPA haritasının saatlik kuralı).
- Saatlik değerlendirmede A ve B'nin saatlik ortalamaları karşılaştırılır.
- 8 Ekim 2026 itibarıyla 272 saatlik kampüs verisinin **hiçbiri** bu kural nedeniyle elenmedi (kanallar uyumlu).
- Kanal bilgisi gelmezse (eski sunucu yanıtı) kural uygulanamaz; değer yine düzeltilir ve `qa_ab = null` olarak işaretlenir.

## 3. Uygulamadaki akış

```
PurpleAir API (pm2.5_atm, A, B, nem)  →  sunucu (2 dk'da bir kayıt, ham)  →  /api/purpleair/latest | /history
      →  api.js: paCorrect(her kayıt)  →  pm2_5 = düzeltilmiş (geçersizse boş), pm2_5_raw = ham
      →  Özet (HKİ), Sağlık (WHO), kampüs–bölge, maruziyet, harita, paneller
```

- Veritabanı **ham** değeri saklar; düzeltme yalnızca gösterimde ve hesaplarda yapılır. Formül değişirse geçmiş veri
  kaybolmadan yeniden hesaplanır.
- Ham değer, Araştırma görünümündeki PurpleAir panelinde ("ham sensör değeri") ve haritadaki PurpleAir kutusunda görünür.
- CSV dışa aktarımı ham değeri verir; düzeltilmiş değer bu belgedeki formülle hesaplanabilir.
- **Aynı temelde karşılaştırma:** Kampüs–Tuzla karşılaştırmasında PurpleAir düzeltilmiş değeriyle girer (Tuzla resmî ölçümdür,
  düzeltme gerekmez; düzeltme PurpleAir'i bu ölçeğe çeker). Araştırma'daki sensör karşılaştırma grafiğinde ise Atmotube
  düzeltilmediği için PurpleAir'in de **ham** değeri kullanılır (ikisi de ham).
- **Tuzla neden düzeltilmez?** Formül, PurpleAir'in okumasını resmî cihazların okuyacağı değere çevirmek için çıkarıldı;
  Tuzla o resmî cihaz tarafındadır. Formül Tuzla'ya uygulansaydı resmî değer haksız yere ~%40 düşerdi
  (ör. 17,4 µg/m³, nem %50 → 10,6).
- **Atmotube:** EPA formülü PurpleAir'e (Plantower sensörü) özgüdür; farklı sensör olan Atmotube'a uygulanmaz. Atmotube
  ham değerleri bina–bina (göreli) karşılaştırmada kullanılır. Cihazlar aynı havayı farklı okuyabilir: mevcut veride
  birkaç dakikalık yan yana ölçümlerde ATP-2 ile ATP-4 yakın (10 ölçüm, ortalama fark 1 µg/m³), ATP-3 ile ATP-4 uzak
  (7 ölçüm, 17,0'a karşı 7,4 µg/m³; örnek küçük). Öneri: cihazları bir gün PurpleAir'in yanında çalıştırıp cihaz başına
  basit bir çarpan çıkarmak (kontrol listesi §9).
- **Düzeltilmeyenler:** PM₁₀ (yerleşik bir düzeltme yok), Atmotube saha ölçümleri (farklı sensör), Tuzla istasyonu
  (resmî referans cihaz; düzeltmeye gerek yok).

## 4. Elle izlenebilir örnekler

| Ham PA | RH | Bölüm | Hesap | Sonuç | HKİ (ham → düzeltilmiş) |
|---|---|---|---|---|---|
| 12,0 | %40 | PA < 30 | 0,524×12 − 0,0862×40 + 5,75 = 6,288 − 3,448 + 5,75 | **8,6** | 50 → 35 (İyi) |
| 35,1 | %34 | 30–50 | w = 35,1/20 − 1,5 = 0,255; eğim = 0,786×0,255 + 0,524×0,745 = 0,591; 0,591×35,1 − 0,0862×34 + 5,75 = 20,74 − 2,93 + 5,75 | **23,6** | 99 → 75 (Orta) |
| 42,8 | %49 | 30–50 | w = 0,64; eğim = 0,692; 0,692×42,8 − 0,0862×49,4 + 5,75 | **31,1** | 119 (Hassas) → 91 (Orta) |
| 60,0 | %68 | 50–210 | 0,786×60 − 0,0862×68 + 5,75 = 47,16 − 5,86 + 5,75 | **47,1** | 153 (Sağlıksız) → 129 (Hassas) |

## 5. Doğrulama

**Birim testleri** (`epaPM25` doğrudan çalıştırılarak; 8 Ekim 2026):
- Beş bölümün sınırlarında (30, 50, 210, 260 µg/m³; RH %20/50/80) süreksizlik yok.
- 0–600 µg/m³ aralığında aynı nemde artan girdi daima artan çıktı verir (monoton).
- Yukarıdaki elle hesaplanan örnekler, eksik/geçersiz nemde %50, negatif sonucun 0 olması, kanal kuralı
  (6 µg/m³ ve %120 fark → geçersiz; 3 µg/m³ ve %120 fark → geçerli; 10 µg/m³ ve %67 fark → geçerli) doğrulandı.

**Yerel tutarlılık (Tuzla istasyonu, aynı saatler):** Kampüs PurpleAir ile resmî Tuzla istasyonunun (~6,4 km)
ikisinin de ölçüm yaptığı saatler (µg/m³; fark Tuzla'ya göre):

| Ay | Saat | Tuzla | Kampüs ham | Kampüs EPA düzeltmeli |
|---|---|---|---|---|
| Nisan 2026 | 27 | 12,8 | 16,6 (+%29) | 12,3 (−%5) |
| Haziran 2026 | 69 | 12,7 | 14,4 (+%14) | 10,4 (−%18) |
| Temmuz 2026 | 83 | 14,6 | 19,8 (+%35) | 12,8 (−%12) |
| Ağustos 2026 | 23 | 14,4 | 28,6 (+%99) | 18,2 (+%27) |
| Ekim 2026 | 39 | 17,4 | 30,6 (+%76) | 21,2 (+%22) |
| **Tümü** | **241** | **14,3** | **20,5 (+%43)** | **13,9 (−%2)** |

Ortalama mutlak fark: ham 10,3 → düzeltilmiş 6,4 µg/m³. Ham/düzeltilmiş ortalama oranı 0,68, literatürdeki
"ham değer yaklaşık %40 yüksek" bulgusuyla uyumludur. Aylar arasındaki farklar beklenir: iki nokta 6,4 km uzaktadır
ve yerel kaynaklar (kampüs içi trafik, inşaat, rüzgâr yönü) farklıdır. **Bu karşılaştırma kolokasyon değildir;**
düzeltmenin yönünü ve büyüklüğünü destekleyen bir tutarlılık göstergesidir.

## 6. Uygulamadaki sonuçlara etkisi (8 Ekim 2026)

| Ay | Değerlendirilen gün | Ham ortalama | Düzeltilmiş ortalama | WHO günlük değeri (15) aşılan gün: ham → düzeltilmiş |
|---|---|---|---|---|
| Nisan | 4 | 14,4 | 11,0 | 2 → 2 |
| Haziran | 6 | 13,1 | 9,6 | 3 → 0 |
| Temmuz | 6 | 21,9 | 14,1 | 5 → 2 |
| Ağustos | 1 | 31,7 | 20,3 | 1 → 1 |
| Ekim | 2 | 33,6 | 23,3 | 2 → 1 |
| **Tümü** | **19** | **19,3** | **13,3** | **13 → 6** |

Kampüs ortalaması WHO yıllık kılavuz değerinin (5 µg/m³) hâlâ üstündedir; düzeltme sonucun yönünü değil büyüklüğünü değiştirir.

## 7. Sınırlılıklar

1. **Türkiye'de yerinde doğrulanmadı.** Formül ABD'deki 16 eyaletten veriyle geliştirildi. En güvenilir yol, PurpleAir'i
   birkaç hafta resmî bir istasyonun yanına koyup (kolokasyon) yerel performansı ölçmektir. Bu yapılırsa yerel katsayılar
   türetilebilir ya da EPA formülünün yeterliliği gösterilebilir.
2. **Toz olayları:** Çöl tozu gibi iri ve farklı yapılı parçacıklarda optik sensörler PM₂.₅'i belirgin düşük gösterir;
   EPA düzeltmesi bunu gidermez (Jaffe vd., 2023: yaklaşık 5–6 kat düşük tahmin). İstanbul'da Sahra tozu taşınımı
   olan günlerde düzeltilmiş değer gerçek değerin altında kalabilir.
3. **cf_atm uygulaması:** Jaffe vd. (2023) EPA'nın cf_atm tabanlı denkleminin kentsel kirlilik olaylarında eğimini 0,95,
   duman olaylarında 0,88 bulmuştur (hafif düşük tahmin).
4. **Nem:** PurpleAir'in nem sensörü gövde içinde olduğundan ortamdan ~4 puan düşük okur. Formül PurpleAir'in kendi nem
   ölçümüyle geliştirildiği için bu değer düzeltilmeden kullanılır (doğru kullanım budur).
5. **Anlık değer:** 2 dakikalık tek ölçüme uygulanan düzeltme saatlik değer kadar kararlı değildir; gösterge niteliğindedir.
6. **PM₁₀:** PurpleAir'in PM₁₀ değeri için EPA'nın yerleşik bir düzeltmesi yoktur; PM₁₀ ham gösterilir ve olduğundan
   düşük okunabilir.

## 8. Kaynaklar ve doğrulama durumu

| Bilgi | Kaynak | Doğrulama |
|---|---|---|
| ABD geneli denklem (0,524 / −0,0862 RH / 5,75), ham değerin ~%40 yüksek olması, ~12 000 ölçüm, 16 eyalet | Barkjohn, Gantt, Clements (2021) | **İkincil:** makale özeti ve birden çok bağımsız kaynakta aynı katsayılar (EPA ORD sunumları, Barkjohn vd. 2022 Model A, AirGradient). Makale tam metnine bu çalışma ortamından erişilemedi. |
| Beş bölümlü cf_atm denklemi (30/50/210/260 sınırları, 0,786, 0,69, 2,966, 8,84×10⁻⁴) | EPA AirNow Yangın ve Duman Haritası uygulaması; Barkjohn vd. (2022) genişletmesi | **İkincil:** EPA belgesini kaynak gösteren AirGradient yazısı, Maine DEP sunumu ve PurpleAir topluluğu aynı denklemi veriyor. Kontrol listesinde. |
| EPA'nın düzeltmeyi cf_atm üzerinde uygulaması | AirNow Fire and Smoke Map Questions and Answers | **İkincil** (belge metninden alıntılanan arama özeti). |
| Kanal kuralı (≥ 5 µg/m³ ve ≥ %70), nem eksikse %50 | AirNow Soru-Cevap; EPA 2024 sunumu (Evans, ASIC 2024); Barkjohn vd. 2022 (saatlik veride %70) | **İkincil.** Not: 2021 makalesi 24 saatlik veride %61 kullanmıştı; saatlik veride güncel kural %70'tir. |
| cf_atm/cf_1 ilişkisi (~25–28 µg/m³'e kadar 1:1, sonra ~⅔) | Wallace vd. (2022) ve EPA sunumları | **İkincil.** |
| Toz olaylarında düşük tahmin, cf_atm denkleminin eğimleri (0,95; 0,88) | Jaffe vd. (2023) | **İkincil** (makale özeti). |

**Kaynakça**
- Barkjohn, K. K., Gantt, B., Clements, A. L. (2021). Development and application of a United States-wide correction for
  PM2.5 data collected with the PurpleAir sensor. *Atmospheric Measurement Techniques*, 14, 4617–4637.
  https://doi.org/10.5194/amt-14-4617-2021
- Barkjohn, K. K., Holder, A. L., Frederick, S. G., Clements, A. L. (2022). Correction and accuracy of PurpleAir PM2.5
  measurements for extreme wildfire smoke. *Sensors*, 22(24), 9669. https://doi.org/10.3390/s22249669
  (2024'te yayımlanan düzeltme notu Tablo 3'ü günceller; denklemi değiştirmez.)
- Jaffe, D. A. vd. (2023). An evaluation of the U.S. EPA's correction equation for PurpleAir sensor data in smoke, dust,
  and wintertime urban pollution events. *Atmospheric Measurement Techniques*, 16, 1311. https://doi.org/10.5194/amt-16-1311-2023
- U.S. EPA / AirNow. AirNow Fire and Smoke Map: Questions and Answers.
  https://document.airnow.gov/airnow-fire-and-smoke-map-questions-and-answers.pdf (erişim 8 Ekim 2026)
- U.S. EPA. Technical Approaches for the Sensor Data on the AirNow Fire and Smoke Map.
  https://www.epa.gov/air-sensor-toolbox/technical-approaches-sensor-data-airnow-fire-and-smoke-map (erişim 8 Ekim 2026)
- U.S. EPA ORD. Sensor Data Cleaning and Correction: Application on the AirNow Fire and Smoke Map (sunum).
  https://cfpub.epa.gov/si/si_public_file_download.cfm?p_download_id=544231&Lab=CEMM
- Wallace, L. vd. (2022). Intercomparison of PurpleAir sensor performance over three years indoors and outdoors at a home:
  bias, precision, and limit of detection using an improved algorithm for calculating PM2.5. *Sensors*.
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9002513/

## 9. Kontrol listesi (savunmadan önce)

- [ ] Beş bölümlü denklemi EPA'nın "Sensor Data Cleaning and Correction" sunumundan ya da AirNow Soru-Cevap belgesindeki
      denklem tablosundan birincil olarak teyit et (bu belge yazılırken EPA sitelerine erişilemedi).
- [ ] Barkjohn vd. (2021) makalesinde denklemin (0,524 / 0,0862 / 5,75) ve 24 saatlik kanal kuralının metnini kontrol et.
- [ ] Mümkünse PurpleAir'i birkaç hafta resmî bir istasyonun yanına koyarak (kolokasyon) yerel doğrulama yap.
- [ ] Atmotube yan yana ölçüm günü: 5 cihazı PurpleAir'in yanında (SUMER çatısı) en az birkaç saat çalıştır; her cihaz için
      düzeltilmiş PurpleAir'e göre çarpanı hesapla; cihazlar arası farkı ve çarpanları bu belgeye yaz.
