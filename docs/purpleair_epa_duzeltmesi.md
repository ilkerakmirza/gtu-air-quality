# PurpleAir PM₂.₅ için US EPA düzeltmesi

**Belge sürümü:** 2.0 · 12 Ekim 2026 (asıl yöntem EPA'nın ABD geneli denklemine, yayımlandığı girdi cf_1 ile geçti)
**Kodda:** `frontend_v2/js/colorscale.js` → `epaCf1()` (asıl yöntem), `epaPM25()` (yedek yöntem), `paChannelsAgree()`,
`paCorrect()`; uygulandığı tek yer `frontend_v2/js/api.js` (`purpleairLatest`, `purpleairHistory`). Sunucu `cf_1` ve `cf_atm`
kanallarını kaydeder (`backend/purpleair.py`), saatlik/günlük geçmişte kanal ortalamalarını döndürür (`backend/db.py` →
`get_purpleair_history()`).
**İlgili belge:** Uygulamadaki tüm eşik ve hesapların kaydı → [`hesaplama_ve_kaynaklar.md`](hesaplama_ve_kaynaklar.md)

---

## Kısaca (savunma için)

1. **Sorun:** PurpleAir gibi düşük maliyetli optik sensörler PM₂.₅'i referans (resmî) cihazlara göre yüksek okur ve
   nemden etkilenir. ABD genelinde ham değer yaklaşık **%40 yüksektir** (Barkjohn vd., 2021).
2. **Yöntem:** ABD Çevre Koruma Ajansı'nın (US EPA) yaklaşık 12 000 eş zamanlı ölçümle geliştirdiği ABD geneli düzeltme
   denklemi, **yayımlandığı girdiyle** aynen uygulanır:
   **PM₂.₅ = 0,524 × cf_1 − 0,0862 × nem + 5,75** (cf_1 = A ve B kanalının `pm2.5_cf_1` ortalaması, nem = PurpleAir'in nemi).
   Yeni bir formül türetilmedi.
3. **Tekrarlanabilirlik:** PurpleAir haritasında "Apply conversion: US EPA" seçildiğinde görülen değer de bu denklemle
   hesaplanır (PurpleAir topluluk sayfaları). Uygulamadaki değer haritadakiyle karşılaştırılabilir (§5).
4. **Neden bu biçim:** EPA'nın denklemi cf_1 verisiyle geliştirildi. Daha önce kullanılan "genişletilmiş" biçim aynı
   denklemi cf_atm'ye uygular ve cf_atm'nin yüksek derişimde cf_1'in üçte ikisi olduğunu varsayar. Bu sensörde oran derişimle
   değişiyor (1,00 → 0,89 → 0,73 → 0,66, §5); bu yüzden genişletilmiş biçim ham değer 35–65 µg/m³ arasındayken
   4 µg/m³ kadar yüksek çıkıyordu. Denklemi kendi girdisiyle kullanmak bu varsayımı ortadan kaldırır.
5. **Kalite kontrolü:** A ve B kanalı birbirinden çok farklıysa (hem ≥ 5 µg/m³ hem ≥ %70) o ölçüm kullanılmaz.
6. **Eski kayıtlar:** 12 Ekim 2026'dan önce sunucu cf_1 kaydetmiyordu. cf_1'i olmayan kayıtlarda EPA'nın genişletilmiş
   denklemi cf_atm ile kullanılır (yedek yöntem). Ham değer 30 µg/m³'ün altında iki biçim aynı sonucu verir (fark en çok
   0,3 µg/m³). 6 Ekim öncesi saatlerin %83'ü bu düzeydedir; %9'u 35–65 µg/m³ aralığındadır ve bu saatlerde yedek yöntem
   ortalama 4 µg/m³ yüksek kalabilir (§7). 6–12 Ekim kayıtlarına cf_1 PurpleAir'in kendi verisinden eklendi (§3).
7. **Sınırlılık:** Denklem ABD verisiyle geliştirildi; Türkiye'de resmî bir cihazın yanında (kolokasyon) doğrulanmadı.
   Çöl tozu olaylarında PM₂.₅ olduğundan düşük görünebilir. PM₁₀ ve Atmotube saha ölçümleri düzeltilmez.

---

## 1. Formül

**Asıl yöntem (cf_1 kaydı olan ölçümler):**

> **PM₂.₅ (düzeltilmiş) = 0,524 × cf_1 − 0,0862 × RH + 5,75**

- **cf_1** = PurpleAir `pm2.5_cf_1` değeri, A ve B kanallarının ortalaması (µg/m³). Sunucu 2 dakikada bir kaydeder.
- **RH** = PurpleAir'in kendi bağıl nem ölçümü (%). Eksikse ya da 0–100 dışındaysa **%50** alınır (EPA kuralı).
- Denklem Barkjohn vd. (2021) ABD geneli düzeltmesinin kendisidir; 24 saatlik verilerle geliştirildi, EPA ve PurpleAir
  haritası saatlik ve anlık veride de kullanır.
- **Negatif sonuç:** Çok temiz ve çok nemli havada sonuç 0'ın altına inebilir; derişim negatif olamayacağından 0 alınır
  (**uygulama kuralı**).

**Yedek yöntem (cf_1 kaydı olmayan eski ölçümler):** EPA'nın AirNow Yangın ve Duman Haritası'nda kullandığı genişletilmiş
denklem, girdi PA = `pm2.5_atm` (A/B ortalaması):

| PA aralığı (µg/m³) | Düzeltilmiş PM₂.₅ |
|---|---|
| PA < 30 | 0,524 × PA − 0,0862 × RH + 5,75 |
| 30 ≤ PA < 50 | [0,786 × w + 0,524 × (1 − w)] × PA − 0,0862 × RH + 5,75 ; w = PA/20 − 1,5 |
| 50 ≤ PA < 210 | 0,786 × PA − 0,0862 × RH + 5,75 |
| 210 ≤ PA < 260 | [0,69 × w + 0,786 × (1 − w)] × PA − 0,0862 × RH × (1 − w) + 2,966 × w + 5,75 × (1 − w) + 8,84×10⁻⁴ × PA² × w ; w = PA/50 − 4,2 |
| PA ≥ 260 | 2,966 + 0,69 × PA + 8,84×10⁻⁴ × PA² |

- cf_atm ile cf_1 düşük derişimde aynıdır; bu yüzden ham değer 30 µg/m³'ün altındayken iki yöntem aynı sonucu verir
  (fark en çok 0,3 µg/m³). 30–35 arasında fark ortalama 0,7, en çok 2,3 µg/m³'tür (6–12 Ekim verisi, §5).
- 0,786 eğimi, cf_atm'nin cf_1'in üçte ikisi olduğu varsayımıyla 0,524'ün karşılığıdır (0,524 × 1,5). Bu sensörde oran
  ancak ham değer 80 µg/m³'ün üstünde üçte ikiye iniyor; asıl yöntemin seçilme sebebi budur (§5).

## 2. Kalite kontrolü (A ve B kanalları)

PurpleAir PA-II içinde iki ayrı lazer sayacı vardır. Biri arızalanır ya da kirlenirse iki kanal ayrışır.

- Göreli fark = |A − B| / ((A + B) / 2).
- **Hem |A − B| ≥ 5 µg/m³ hem göreli fark ≥ %70 ise** ölçüm geçersizdir ve hiçbir hesaba girmez.
- Asıl yöntemde cf_1 kanalları, yedek yöntemde cf_atm kanalları karşılaştırılır. Saatlik değerlendirmede A ve B'nin saatlik
  ortalamaları karşılaştırılır.
- 6–12 Ekim 2026'daki 3892 iki dakikalık kaydın hiçbiri bu kural nedeniyle elenmedi.
- Kanal bilgisi gelmezse kural uygulanamaz; değer yine düzeltilir ve `qa_ab = null` olarak işaretlenir.

## 3. Uygulamadaki akış

```
PurpleAir API (pm2.5_cf_1 A/B, pm2.5_atm A/B, nem)  →  sunucu (2 dk'da bir kayıt, ham)  →  /api/purpleair/latest | /history
      →  api.js: paCorrect(her kayıt)  →  pm2_5 = düzeltilmiş (geçersizse boş), pm2_5_raw = ham (cf_atm), pm2_5_method = cf1 | atm
      →  Özet (HKİ), Sağlık (WHO), kampüs–bölge, maruziyet, harita, paneller
```

- Veritabanı **ham** değerleri saklar; düzeltme yalnızca gösterimde ve hesaplarda yapılır. Yöntem değişirse geçmiş veri
  kaybolmadan yeniden hesaplanır.
- Ekranda "ham sensör değeri" olarak gösterilen değer cf_atm'dir; PurpleAir haritasında dönüşüm seçilmediğinde görülen
  değerle aynıdır.
- **cf_1 kaydı:** Sunucu cf_1'i 12 Ekim 2026 13:06'dan (Türkiye saati) beri kendisi kaydeder. 6–12 Ekim için PurpleAir'in
  kendi verisinden (§5'teki indirme dosyası, `docs/veri/`) zaman damgası ve A/B cf_atm değerleri aynı olan 3389 kayda cf_1 A
  ve B değerleri eklendi; bu günler de asıl yöntemle hesaplanır. cf_1'i olmayan kayıtlar yedek yöntemle hesaplanır:
  27 Nisan – 2 Ekim arasındaki 4129 kayıt ve 6 Ekim sonrasındaki 28 kayıt (indirme dosyasında karşılığı olmayan 14 kayıt,
  12 Ekim 12:24–13:05 arasındaki 14 kayıt).
- **Aynı temelde karşılaştırma:** Kampüs–Tuzla karşılaştırmasında PurpleAir düzeltilmiş değeriyle girer (Tuzla resmî
  ölçümdür, düzeltilmez). Araştırma'daki sensör karşılaştırma grafiğinde Atmotube düzeltilmediği için PurpleAir'in de
  **ham** değeri kullanılır.
- **Tuzla neden düzeltilmez?** Denklem PurpleAir'in okumasını resmî cihazın okuyacağı değere çevirir; Tuzla resmî cihazdır.
- **Atmotube:** Denklem PurpleAir'in Plantower sensörüne özgüdür; Atmotube'a (Sensirion SPS30) uygulanmaz. Ayrıntı
  `hesaplama_ve_kaynaklar.md` §5.
- **Düzeltilmeyenler:** PM₁₀, Atmotube saha ölçümleri, Tuzla istasyonu.

## 4. Elle izlenebilir örnekler (gerçek saatler, 6–12 Ekim 2026)

| Saat | cf_1 | Nem | Hesap | Düzeltilmiş | Ham (cf_atm) → düzeltilmiş HKİ |
|---|---|---|---|---|---|
| 7 Ekim 13:00 | 11,7 | %36 | 0,524 × 11,7 − 0,0862 × 36 + 5,75 = 6,13 − 3,10 + 5,75 | **8,8** | 11,7 → 8,8 (İyi) |
| 8 Ekim 14:00 | 46,0 | %45 | 24,10 − 3,88 + 5,75 | **26,0** | 40,2 (Hassas) → 26,0 (Orta) |
| 9 Ekim 09:00 | 62,5 | %50 | 32,75 − 4,31 + 5,75 | **34,2** | 49,9 (Hassas) → 34,2 (Orta) |
| 9 Ekim 00:00 | 109,8 | %65 | 57,54 − 5,60 + 5,75 | **57,7** | 72,4 → 57,7 (ikisi de Sağlıksız) |

Değerler saat ortalamasıdır. Aynı saatlerde eski (genişletilmiş) yöntem 8,8 / 28,3 / 40,6 / 57,1 µg/m³ veriyordu; 9 Ekim
09:00'da HKİ sınıfı Hassas'tan Orta'ya iner.

**Yedek yöntem örneği:** cf_1'i olmayan eski bir kayıt, PA = 42,8, RH = %49: w = 0,64; eğim = 0,692;
0,692 × 42,8 − 0,0862 × 49,4 + 5,75 = **31,1** µg/m³.

## 5. Doğrulama

**Birim testleri** (kodun kendisi çalıştırılarak; 8 ve 12 Ekim 2026):
- Asıl yöntem: yukarıdaki örnekler, nem eksikse %50, negatif sonucun 0 olması, metin olarak gelen sayılar, cf_1 kanalları
  uyuşmayınca değerin boş kalması, cf_1 yoksa yedek yönteme geçilmesi doğrulandı.
- Yedek yöntem: beş bölümün sınırlarında süreksizlik yok; 0–600 µg/m³ aralığında monoton; elle hesaplanan örnekler tutuyor.

**PurpleAir'in kendi verisiyle denetim (12 Ekim 2026).** PurpleAir Data Download Tool ile sensör 229263'ün
6 Ekim 16:53 – 12 Ekim 12:23 (TR) arası 2 dakikalık kayıtları indirildi (3892 kayıt; `pm2.5_atm_a/b`, `pm2.5_cf_1_a/b`,
`pm2.5_alt_a/b` (ALT-CF3, sabit 3), `humidity`). Dosya: [`veri/purpleair_229263_2dk_2026-10-06_2026-10-12.csv`](veri/purpleair_229263_2dk_2026-10-06_2026-10-12.csv).

- **Kayıt hattı doğru:** Sunucu kayıtlarıyla aynı zaman damgalı 3389 kayıtta A, B ve nem değerleri aynı (en büyük fark
  0,05 µg/m³, yuvarlama). Sunucu 503 kaydı kaçırmış (%13); 413'ü 6–7 Ekim'de (sunucu uyuyordu, uyanık tutma işi 7 Ekim'de
  kuruldu). Günlük kayıt oranı: 6 Ekim %20, 7 Ekim %65, 8–11 Ekim %97–99, 12 Ekim (öğlene kadar) %90.
- **Saatlik hesap doğru:** Sunucu kayıtlarından hesaplanan saatlik düzeltilmiş değer ile PurpleAir dosyasından hesaplanan
  arasındaki ortalama mutlak fark 0,13 µg/m³; 1 µg/m³'ten büyük fark yalnızca kaydı eksik 3 saatte var.
- **cf_atm / cf_1 oranı derişimle değişiyor (saatlik):**

| Ham (cf_atm) | Saat | cf_atm / cf_1 |
|---|---|---|
| 0–25 µg/m³ | 27 | 1,00 |
| 25–50 | 45 | 0,89 |
| 50–80 | 59 | 0,73 |
| 80–200 | 3 | 0,66 |

- **İki yöntemin karşılaştırması (3892 iki dakikalık değer):**

| Ham (cf_atm) | Değer | Eski yöntem (genişletilmiş, cf_atm) | Asıl yöntem (cf_1) | Fark | HKİ sınıfı aynı |
|---|---|---|---|---|---|
| 0–25 µg/m³ | 759 | 10,2 | 10,2 | 0,0 | %100 |
| 25–35 | 356 | 18,0 | 17,7 | +0,3 | %100 |
| 35–50 | 930 | 31,9 | 27,8 | +4,1 (+%15) | %75 |
| 50–65 | 1346 | 46,5 | 42,1 | +4,4 (+%10) | %84 |
| 65–80 | 419 | 55,1 | 55,1 | 0,0 | %94 |
| 80 üstü | 82 | 76,8 | 77,5 | −0,8 | %100 |

  Haftalık ortalama: eski yöntem 34,9, asıl yöntem 32,4 µg/m³; ham 46,0. HKİ sınıfı zamanın %88'inde aynı; "Hassas" payı
  %48'den %35'e iner. Fark yalnızca orta aralıkta; sebebi yukarıdaki oran tablosu.
- **Bağımsız ikinci düzeltmeyle uyum:** PurpleAir'in kendi alternatif yöntemi ALT-CF3 (parçacık sayılarından; Wallace vd.)
  ile asıl yöntem, ham değer 12 µg/m³'ün üstündeki her aralıkta ±%20 içinde (ALT-CF3,4 sabitiyle). Eski yöntem ise
  35–65 aralığında ALT-CF3,4'ten %14–18 yüksekti. İki bağımsız yöntemin bu aralıkta asıl yöntemde buluşması seçimi destekler.
- **Ham değer düzeltmesiz gösterilseydi:** Ham değer, her derişim aralığında düzeltilmiş değerden %25–70 yüksek; HKİ sınıfı
  zamanın %67'sinde bir kademe kötü çıkardı ("Sağlıksız" payı ham değerde %37, düzeltilmiş değerde %7).
- **PurpleAir haritasıyla karşılaştırma:** 12 Ekim 12:46'da haritada ham değer 36 µg/m³ iken "US EPA" dönüşümü 25 µg/m³
  gösterdi; sunucunun o dakikalardaki kayıtlarıyla uygulamanın hesabı 24–25 µg/m³. Bu düzeyde iki yöntem aynı sonucu
  verdiği için orta düzeyde (ham 45–55) bir karşılaştırma ayrıca yapılmalıdır (§9).
- **Tuzla:** Bu karar Tuzla ile karşılaştırmaya dayanmaz (iki nokta 6,4 km uzakta; kolokasyon değil). Kayıt için: aynı
  haftada Tuzla'ya göre ortalama fark ham +%45, eski yöntem +%11, asıl yöntem +%3.

## 6. Uygulamadaki sonuçlara etkisi

**8 Ekim 2026 (eski yöntemle hesaplanmıştı):**

| Ay | Değerlendirilen gün | Ham ortalama | Düzeltilmiş ortalama | WHO günlük değeri (15) aşılan gün: ham → düzeltilmiş |
|---|---|---|---|---|
| Nisan | 4 | 14,4 | 11,0 | 2 → 2 |
| Haziran | 6 | 13,1 | 9,6 | 3 → 0 |
| Temmuz | 6 | 21,9 | 14,1 | 5 → 2 |
| Ağustos | 1 | 31,7 | 20,3 | 1 → 1 |
| Ekim | 2 | 33,6 | 23,3 | 2 → 1 |
| **Tümü** | **19** | **19,3** | **13,3** | **13 → 6** |

Nisan–Ağustos kayıtları büyük ölçüde iki yöntemin aynı sonuç verdiği düzeydedir; 12 Ekim yöntem değişikliği bu ayları
neredeyse değiştirmez. Ekim'in etkisi yukarıdaki iki yöntem tablosundadır. Kampüs ortalaması WHO yıllık kılavuz değerinin
(5 µg/m³) hâlâ üstündedir.

## 7. Sınırlılıklar

1. **Türkiye'de yerinde doğrulanmadı.** Denklem ABD'deki 16 eyaletten veriyle geliştirildi. En güvenilir yol, PurpleAir'i
   birkaç hafta resmî bir istasyonun yanına koyup (kolokasyon) yerel performansı ölçmektir.
2. **Toz olayları:** Çöl tozu gibi iri parçacıklarda optik sensörler PM₂.₅'i belirgin düşük gösterir; EPA düzeltmesi bunu
   gidermez (Jaffe vd., 2023). Sahra tozu taşınan günlerde düzeltilmiş değer gerçek değerin altında kalabilir.
3. **Aşırı duman:** Asıl denklem olağan ortam düzeyleri için geliştirildi; yüzlerce µg/m³'lük orman yangını dumanında düşük
   tahmin ettiği için EPA genişletilmiş denklemi çıkarmıştır (Barkjohn vd., 2022). Kampüste bu düzey görülmedi (6–12 Ekim'de
   en yüksek iki dakikalık cf_1 173, saatlik 156 µg/m³).
4. **İki yöntemli geçmiş:** cf_1'i olmayan eski kayıtlar (27 Nisan – 2 Ekim 2026) yedek yöntemle hesaplanır. Ham değer
   30 µg/m³'ün altında fark en çok 0,3 µg/m³'tür (bu dönemin saatlerinin %83'ü). Saatlerin %9'u 35–65 aralığındadır; bu
   saatlerde değer 6–12 Ekim verisine göre ortalama 4, en çok 9 µg/m³ yüksek olabilir. Bu kayıtlara da cf_1 PurpleAir
   geçmişinden eklenirse tüm geçmiş tek yöntemle hesaplanır (§9).
5. **Nem:** PurpleAir'in nem sensörü gövde içinde olduğundan ortamdan birkaç puan düşük okur. Denklem PurpleAir'in kendi nem
   ölçümüyle geliştirildiği için bu değer düzeltilmeden kullanılır (doğru kullanım budur).
6. **Anlık değer:** 2 dakikalık tek ölçüme uygulanan düzeltme saatlik değer kadar kararlı değildir; gösterge niteliğindedir
   (6–12 Ekim'de iki dakikalık düzeltilmiş değer kendi saat ortalamasından ortanca 1,1, %90'ında en çok 4 µg/m³ sapıyor).
7. **PM₁₀:** EPA'nın PM₁₀ için yerleşik bir düzeltmesi yoktur; PM₁₀ ham gösterilir ve olduğundan düşük okunabilir.

## 8. Kaynaklar ve doğrulama durumu

| Bilgi | Kaynak | Doğrulama |
|---|---|---|
| ABD geneli denklem 0,524 × cf_1 − 0,0862 × RH + 5,75; ham değerin ~%40 yüksek olması; ~12 000 ölçüm, 16 eyalet | Barkjohn, Gantt, Clements (2021) | **İkincil:** makale özeti, 2024 düzeltme notu (Barkjohn vd. 2022'ye) ve birden çok bağımsız kaynakta aynı katsayılar ve aynı girdi (cf_1). Tam metin bu ortamdan açılamadı. |
| PurpleAir haritasındaki "US EPA" dönüşümünün bu denklemi cf_1 ile kullanması | PurpleAir Community sayfaları | **İkincil;** haritayla tek noktada tutarlı (§5), orta düzeyde karşılaştırma bekleniyor (§9). |
| cf_atm/cf_1 oranının derişimle değişmesi | Bu sensörün kendi verisi (12 Ekim indirmesi, §5) | **Birincil ölçüm.** cf_atm'nin ~25 µg/m³ üstünde doğrusal olmadığı literatürde de belirtilir (Barkjohn vd. 2021 hakem süreci). |
| Genişletilmiş denklem (yedek yöntem) | EPA AirNow Yangın ve Duman Haritası; Barkjohn vd. (2022) | **İkincil:** AirGradient, Maine DEP ve PurpleAir topluluğu aynı denklemi veriyor. |
| Kanal kuralı (≥ 5 µg/m³ ve ≥ %70), nem eksikse %50 | AirNow Soru-Cevap; Barkjohn vd. 2022 | **İkincil.** 2021 makalesi 24 saatlik veride %61 kullanmıştı; saatlik veride güncel kural %70'tir. |
| Toz olaylarında düşük tahmin | Jaffe vd. (2023) | **İkincil** (makale özeti). |

**Kaynakça**
- Barkjohn, K. K., Gantt, B., Clements, A. L. (2021). Development and application of a United States-wide correction for
  PM2.5 data collected with the PurpleAir sensor. *Atmospheric Measurement Techniques*, 14, 4617–4637.
  https://doi.org/10.5194/amt-14-4617-2021
- Barkjohn, K. K., Holder, A. L., Frederick, S. G., Clements, A. L. (2022). Correction and accuracy of PurpleAir PM2.5
  measurements for extreme wildfire smoke. *Sensors*, 22(24), 9669. https://doi.org/10.3390/s22249669
  Düzeltme notu (2024): *Sensors*, 24, 7871. https://doi.org/10.3390/s24247871
- Jaffe, D. A. vd. (2023). An evaluation of the U.S. EPA's correction equation for PurpleAir sensor data in smoke, dust,
  and wintertime urban pollution events. *Atmospheric Measurement Techniques*, 16, 1311. https://doi.org/10.5194/amt-16-1311-2023
- PurpleAir Community. Which PurpleAir parameters to use for EPA PM2.5 correction?
  https://community.purpleair.com/t/which-purpleair-parameters-to-use-for-epa-pm2-5-correction/2072 (erişim 12 Ekim 2026)
- PurpleAir Community. Is there a field that returns data with US EPA pm2.5 conversion formula applied?
  https://community.purpleair.com/t/is-there-a-field-that-returns-data-with-us-epa-pm2-5-conversion-formula-applied/4593
- U.S. EPA / AirNow. AirNow Fire and Smoke Map: Questions and Answers.
  https://document.airnow.gov/airnow-fire-and-smoke-map-questions-and-answers.pdf (erişim 8 Ekim 2026)
- U.S. EPA ORD. Sensor Data Cleaning and Correction: Application on the AirNow Fire and Smoke Map (sunum).
  https://cfpub.epa.gov/si/si_public_file_download.cfm?p_download_id=544231&Lab=CEMM
- Wallace, L. vd. (2022). Intercomparison of PurpleAir sensor performance over three years indoors and outdoors at a home.
  *Sensors*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9002513/

## 9. Kontrol listesi (savunmadan önce)

- [x] Yöntem kararı (12 Ekim 2026): EPA'nın ABD geneli denklemi, cf_1 girdisiyle; cf_1'i olmayan eski kayıtlar için yedek yöntem.
- [ ] PurpleAir haritasında orta düzeyde bir saatin (ham 45–55 µg/m³; ör. 11 Ekim 06:00, saatlik ortalama) "US EPA" değerini
      uygulamanın değeriyle karşılaştır. Beklenen: asıl yöntemle aynı (11 Ekim 06:00 için ~35,7 µg/m³).
- [ ] Barkjohn vd. (2021) makalesinde denklemin (0,524 / 0,0862 / 5,75), girdinin (cf_1) ve kanal kuralının metnini kontrol et.
- [ ] Mümkünse PurpleAir'i birkaç hafta resmî bir istasyonun yanına koyarak (kolokasyon) yerel doğrulama yap.
- [x] 6–12 Ekim 2026 kayıtlarına cf_1 eklendi (3389 kayıt; PurpleAir indirme dosyası, A/B cf_atm kanalları da aynı
      olan kayıtlarla eşleştirildi).
- [ ] İstenirse eski kayıtlara da cf_1 ekle ve sunucunun kaçırdığı kayıtları doldur: PurpleAir Data Download Tool'dan
      27 Nisan – 6 Ekim 2026, Average 0, alanlar `pm1.0_atm`, `pm2.5_atm_a`, `pm2.5_atm_b`, `pm2.5_cf_1_a`, `pm2.5_cf_1_b`,
      `pm10.0_atm`, `temperature`, `humidity`. Dosya `docs/veri/`'ye konur; zaman damgasıyla eşleşen kayıtlara cf_1 yazılır,
      eksik zamanlar yeni kayıt olarak eklenir (§3'teki yöntemle). Böylece tüm geçmiş tek yöntemle hesaplanır.
- [ ] Tuzla saatlik değerinin etiketinin saatin başını mı sonunu mu gösterdiğini İBB/ÇŞB belgesinden doğrula; sonunu
      gösteriyorsa kampüs–Tuzla aynı saat eşleştirmesini (`app.js` → `paSameHour`, `kiyas.js`) bir saat kaydır.
- [ ] Atmotube yan yana ölçüm (karar 8 Ekim 2026): 5 cihaz SUMER çatısında PurpleAir'in yanında en az 24 saat (tercihen 48);
      kurulum ve karar kuralı `hesaplama_ve_kaynaklar.md` §5'te. Her cihaz için düzeltilmiş PurpleAir'e göre oranı hesapla.
