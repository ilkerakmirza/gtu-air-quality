# Kişisel maruziyet hesabı (taslak) — yöntem ve kabuller

**Proje:** GTÜ AirLab, kampüs hava kalitesi platformu
**Kod:** `frontend_v2/js/maruziyet.js` (arayüzde Özet → "Kampüste geçirdiğim süreye göre maruziyetimi hesapla")
**Belge sürümü:** 1.0 · 3 Ekim 2026
**Durum:** Taslak model. Sonuçlar senaryo tahminidir, kişisel ölçüm değildir.

Bu belge, hesabın hangi verilerle, hangi kabullerle ve hangi adımlarla yapıldığını ileride denetlenebilmesi için kayda geçirir.
Koddaki bir değer değişirse bu belge de aynı commit'te güncellenmelidir (bkz. §11).

---

## 1. Amaç ve kapsam

Kampüsteki bir kişinin (öğrenci, akademik ya da idari personel) gün içinde kampüste geçirdiği sürede maruz kaldığı
PM₂.₅ düzeyini ve soluduğu PM₂.₅ miktarını, eldeki kampüs ölçümlerine dayanarak **kabaca** tahmin etmek. Amaç, kişinin
hangi zaman dilimi ya da etkinliğin maruziyetine en çok katkı yaptığını görmesi ve olası davranış değişikliklerinin
(örneğin açık hava sporunun saatini değiştirmek) etkisini karşılaştırabilmesidir.

Kapsam dışı: kampüs dışındaki saatler, iç ortam kaynakları, kişisel ölçüm cihazı verisi, tıbbi değerlendirme.

## 2. Kullanıcı girdileri

Her satır kampüste geçirilen bir zaman dilimidir:

| Alan | Seçenekler | Açıklama |
|---|---|---|
| Başlangıç–bitiş | 15 dakikalık adımlarla saat | Bitiş başlangıçtan sonra olmalıdır; gece yarısını geçen satırlar desteklenmez |
| Yer | "Kampüs geneli" ya da saha ölçümü olan bir bina | Binalar `Campus.buildingStats` listesinden gelir (en az 3 ölçüm) |
| Ortam | Açık hava · İç, açık pencere · İç, kapalı pencere · İç, mekanik havalandırma | Ortam katsayısı F'yi belirler (§4.3) |
| Etkinlik | Oturma (ders, ofis) · Hafif (ayakta, laboratuvar) · Tempolu yürüme · Spor | Solunum hızını belirler (§4.4) |

## 3. Veri kaynakları

| Veri | Kaynak | Kodda |
|---|---|---|
| Kampüs PM₂.₅ (saatlik) | PurpleAir PA-II, SUMER çatısı; sunucu `/api/purpleair/history?interval=hourly`, 1 Ocak 2026'dan bugüne | `WHO.history()` |
| Saha ölçümleri (nokta) | Atmotube Pro yürüyüş ölçümleri; sunucu `/api/map/tracks` | `WHO.fieldPoints()` |
| Bina eşleştirmesi | Saha noktalarının bina poligonlarıyla eşleştirilmesi (`data/campus.geojson`) | `Campus.buildingStats()` |

Kampüs sensörü değerleri **ham (düzeltilmemiş)** PurpleAir `pm2.5_atm` değerleridir.

## 4. Model

Her satır *i* için:

```
C_i   = P̄_i × R_i × F_i                      (µg/m³)   satırdaki tahmini derişim
D_i   = C_i × IR_i × t_i                     (µg)      satırda solunan PM₂.₅
TWA   = Σ(C_i × t_i) / Σ t_i                  (µg/m³)   zaman ağırlıklı ortalama maruziyet
D     = Σ D_i                                (µg)      toplam solunan miktar
pay_i = D_i / D                              (%)       satırın toplam dozdaki payı
```

### 4.1 P — saatlik kampüs profili

1. Saatlik PurpleAir kayıtları Türkiye saatine (Europe/Istanbul) göre günün 24 saatine dağıtılır.
2. Her saat *h* için ortalama alınır: `P[h] = ortalama(o saatteki tüm PM₂.₅ değerleri)`.
3. Bir saatte 3'ten az kayıt varsa o saat için tüm kayıtların genel ortalaması kullanılır.

**Kabul:** Kampüsün gün içi kirlilik deseni, ölçüm yapılan tüm günlerin ortalamasıyla temsil edilir (mevsim ayrımı yapılmaz).

### 4.2 P̄_i — satırın saatlerine düşen profil değeri

Satırın kapsadığı saatler dakika ağırlıklı ortalanır. Örnek: 09:30–11:15 →
`(30 × P[9] + 60 × P[10] + 15 × P[11]) / 105`.

### 4.3 R — bina oranı

```
R_bina = min(2, max(0,5, bina_saha_ortalaması / tüm_saha_ölçümleri_ortalaması))
```

* Bina ortalaması, binaya eşleşen saha noktalarının PM₂.₅ ortalamasıdır (en az 3 nokta). 30'dan az noktası olan binalar
  seçim listesinde "(az ölçüm)" diye işaretlenir.
* "Kampüs geneli" ya da saha ölçümü olmayan yerler için R = 1.
* **Neden oran?** Saha ölçümleri kısa süreli yürüyüş ölçümleridir; mutlak değerleri değil, binanın kampüs ortalamasına
  göre **görece** konumunu taşırlar. Mutlak düzey P'den (sabit sensör) gelir.
* **Neden 0,5–2 sınırı?** Birkaç dakikalık ölçümlerdeki anlık uç değerlerin (geçen bir araç, yakındaki bir kaynak) tahmini
  aşırı büyütmesini önlemek için.

### 4.4 F — ortam (iç/dış) katsayısı

F, dış ortamdaki PM₂.₅'in iç ortama geçen payıdır (sızma faktörü, *F_inf*). İç kaynaklar dahil değildir.

| Ortam | F | Dayanak | Belirsizlik aralığı |
|---|---|---|---|
| Açık hava | 1,0 | Tanım gereği | — |
| İç · açık pencere | 0,8 | Sızma pencereler açıkken ve yaz aylarında artar (Hänninen ve ark., 2011) | ~0,6–1,0 |
| İç · kapalı pencere | 0,5 | Doğal havalandırmalı binalarda ortalama PM₂.₅ sızma faktörü ≈ 0,55 (Chen ve Zhao, 2011); düşük maliyetli sensörlerle dış kaynak payı %29–75 (Salamalikis ve ark., 2025) | 0,3–0,75 |
| İç · mekanik havalandırma | 0,25 | Filtreli mekanik havalandırmalı üniversite binalarında I/O = 0,12 ± 0,07 (MERV13) ve 0,28 ± 0,14 (MERV8) (Afroz ve ark., 2025) | 0,12–0,28 |

**Önemli sınırlılık:** Kalabalık sınıflarda tozun yeniden havalanması gibi iç kaynaklar nedeniyle iç ortam dış ortamdan
yüksek olabilir (I/O > 1; Branco ve ark., 2024). Model bunu içermediği için sınıflarda gerçek maruziyeti olduğundan düşük
tahmin edebilir.

### 4.5 IR — solunum hızı

Kaynak: U.S. EPA *Exposure Factors Handbook*, Bölüm 6, **Tablo 6-2** (kısa süreli maruziyet, kadın ve erkek birlikte),
**21–31 yaş ortalaması**. Tabloda m³/dakika verilir; burada ×60 ile m³/saate çevrilmiştir.

| Etkinlik (arayüz) | EPA etkinlik düzeyi | Ortalama (m³/dk) | Kullanılan IR (m³/sa) | 95. yüzdelik (m³/sa) |
|---|---|---|---|---|
| Oturma (ders, ofis, kütüphane) | Sedentary/Passive | 4,2 × 10⁻³ | **0,25** | 0,39 |
| Hafif (ayakta, laboratuvar, yavaş yürüme) | Light intensity | 1,2 × 10⁻² | **0,72** | 0,96 |
| Tempolu yürüme | Moderate intensity | 2,6 × 10⁻² | **1,56** | 2,28 |
| Spor | High intensity | 5,0 × 10⁻² | **3,0** | 4,56 |

* Yaş grubu seçimi: kullanıcıların çoğu öğrenci olduğu için 21–31 yaş. 31–61 yaş ortalamaları yaklaşık %0–20 daha yüksektir
  (örn. oturma 4,3–5,0 × 10⁻³ m³/dk); 16–21 yaş için oturma 5,3 × 10⁻³ m³/dk'dır.
* Bölüm 6'nın içeriği 2011'den beri güncellenmemiştir; EPA 2025'te bölümü erişilebilir PDF olarak yeniden yayımlamıştır.
  Bu nedenle hâlâ geçerli resmî kaynaktır (kontrol tarihi: 3 Ekim 2026).

## 5. Adım adım hesap (kodun yaptığı sıra)

1. **Veriyi yükle:** saatlik PurpleAir geçmişi ve tüm saha noktaları (`buildModel`).
2. **Saatlik profili kur:** 24 saatlik P dizisi (§4.1).
3. **Bina oranlarını kur:** tüm saha ortalaması ve her binanın R değeri (§4.3).
4. Her satır için:
   1. saatleri dakikaya çevir, geçersizse (bitiş ≤ başlangıç) satırı uyarıyla atla;
   2. P̄'yi hesapla (§4.2);
   3. `C = P̄ × R × F`;
   4. `D = C × IR × süre(saat)`.
5. **Toplamları al:** TWA, D ve satır payları.
6. **Karşılaştırma değeri:** aynı saatlerde açık havada kampüs geneli (R = 1, F = 1), yani `Σ(P̄ × t) / Σt`.
7. **Öneri kuralı (§7).**

## 6. Sayısal örnek

Varsayılan profil değerleri: P[9] = 10, P[10] = 12, P[11] = 11, P[12] = 13 µg/m³; bina oranı R = 1,2.

| Satır | P̄ | R | F | C (µg/m³) | IR (m³/sa) | t (sa) | D (µg) |
|---|---|---|---|---|---|---|---|
| 09:00–12:00 · bina · kapalı pencere · oturma | 11 | 1,2 | 0,5 | 6,6 | 0,25 | 3 | 4,95 |
| 12:00–13:00 · kampüs geneli · açık hava · tempolu yürüme | 13 | 1,0 | 1,0 | 13,0 | 1,56 | 1 | 20,28 |

* TWA = (6,6 × 3 + 13 × 1) / 4 = **8,2 µg/m³**
* D = 4,95 + 20,28 = **25,2 µg**
* Paylar: oturma %20, yürüyüş **%80**. Kısa ama yoğun bir açık hava etkinliği toplam dozun büyük kısmını oluşturabilir.

## 7. Öneri kuralı

Bir satır şu üç koşulu sağlıyorsa saat kaydırma önerisi gösterilir:

1. ortam açık hava;
2. etkinlik tempolu yürüme ya da spor (IR ≥ 1,5 m³/sa);
3. satırın P̄ değeri, 07:00–21:00 arasında profilin en düşük olduğu saatin değerinden en az %10 yüksek.

Öneri metni ölçülüdür ("… almak maruziyeti azaltabilir") ve ilgili satırı adıyla anar.

## 8. Sınırlılıklar

1. **Senaryo tahmini:** Sonuç kişisel ölçüm değildir; tıbbi değerlendirme yerine geçmez.
2. **Ham sensör verisi:** PurpleAir değerleri düzeltilmemiştir; yüksek nemde PM₂.₅'i olduğundan yüksek okuyabilir.
   (Planlanan: US EPA düzeltmesi, bkz. §10.)
3. **Mevsimsellik yok:** P, tüm ölçüm dönemlerinin ortalamasıdır; mevsimsel ve günlük olaylar (inversiyon, toz taşınımı) ayrılmaz.
4. **Bina oranı:** Kısa süreli saha ölçümlerine dayanır; az ölçümlü binalarda belirsizlik yüksektir.
5. **İç kaynaklar dahil değil:** Sınıf, laboratuvar ve yemekhane gibi yerlerde gerçek değer daha yüksek olabilir.
6. **Tek kişi profili:** Solunum hızları yetişkin ortalamasıdır; yaş, cinsiyet, beden ve sağlık durumu dikkate alınmaz.
7. **WHO ile karşılaştırma yok:** Birkaç saatlik ortalama, WHO'nun 24 saatlik kılavuz değeriyle (15 µg/m³) doğrudan
   karşılaştırılamaz; bu nedenle arayüz böyle bir karşılaştırma yapmaz.
8. **Veri kesintisi:** PurpleAir 4 Ağustos 2026'dan beri veri göndermiyor; profil o tarihe kadarki ölçümlerle kurulur.

## 9. Gizlilik (KVKK)

Girilen saat, yer ve etkinlik bilgileri yalnızca kullanıcının tarayıcısında hesaplanır, sunucuya gönderilmez. Kullanıcı
"Bu cihazda hatırla"yı işaretlerse satırlar tarayıcının yerel deposunda (`localStorage`, anahtar `gtu.exp.rows`) saklanır;
işaretlemezse sayfa kapanınca silinir.

## 10. İleride kontrol ve geliştirme listesi

- [ ] **EPA Bölüm 6 güncellemesi:** EPA yeni solunum hızı değerleri yayımladı mı? (EPA bir sonraki sürümde metabolik
      yaklaşımla güncelleme yapmayı planladığını belirtiyor.)
- [ ] **PurpleAir US EPA düzeltmesi** (nem düzeltmeli PM₂.₅) ile P'nin yeniden hesaplanması.
- [ ] **Mevsimsel profil:** P'nin ay ya da mevsime göre ayrılması (ör. kış/yaz) ve F için mevsimsel değerler.
- [ ] **Binaya özgü F:** GTÜ binalarının havalandırma türünün (doğal / mekanik, filtre sınıfı) envanteri.
- [ ] **İç ortam ölçümü ile doğrulama:** Seçili sınıf ve ofislerde eş zamanlı iç/dış ölçümle F'nin kampüse özgü kalibrasyonu.
- [ ] **Duyarlılık analizi:** F ve IR'nin belirsizlik aralıklarıyla (§4.4, §4.5) sonuç aralığının gösterilmesi.

## 11. Kod ile belge eşlemesi

| Belgede | `maruziyet.js` içinde |
|---|---|
| F değerleri (§4.4) | `ENV` |
| IR değerleri (§4.5) | `ACT` |
| P ve R (§4.1, §4.3) | `buildModel()` |
| P̄ (§4.2) | `pOver()` |
| C, D, TWA (§4) | `compute()` |
| Öneri kuralı (§7) | `resultHtml()` → `best`, `outdoorActive` |
| Yöntem metni (arayüzde) | `methodHtml()` |

## 12. Kaynakça

- Afroz, R., Alonzo, J., Omar, S., Cheng, C., Schneider, S., Zhao, R. (2025). Impact of wildfire smoke PM2.5 on indoor air
  quality of public buildings on a university campus. *ACS ES&T Air*, 2, 625–636. https://doi.org/10.1021/acsestair.4c00342
- Branco, P., Sousa, S., Dudzińska, M., Ruzgar, D., Mutlu, M., Panaras, G. ve ark. (2024). A review of relevant parameters for
  assessing indoor air quality in educational facilities. *Environmental Research*, 261, 119713.
  https://doi.org/10.1016/j.envres.2024.119713
- Chen, C., Zhao, B. (2011). Review of relationship between indoor and outdoor particles: I/O ratio, infiltration factor and
  penetration factor. *Atmospheric Environment*, 45, 275–288. https://doi.org/10.1016/j.atmosenv.2010.09.048
- Hänninen, O., Hoek, G., Mallone, S., Chellini, E., Katsouyanni, K., Gariazzo, C. ve ark. (2011). Seasonal patterns of outdoor
  PM infiltration into indoor environments: review and meta-analysis of available studies from different climatological
  zones in Europe. *Air Quality, Atmosphere & Health*, 4, 221–233. https://doi.org/10.1007/s11869-010-0076-5
- Salamalikis, V., Hassani, A., Zawadzki, P., Bykuć, S., Castell, N. (2025). Citizen-operated low-cost sensors for estimating
  outdoor particulate matter infiltration. *Air Quality, Atmosphere & Health*, 18, 2609–2624.
  https://doi.org/10.1007/s11869-025-01787-4
- U.S. EPA (2011). *Exposure Factors Handbook: 2011 Edition*, Chapter 6: Inhalation Rates (EPA/600/R-09/052F).
  https://www.epa.gov/sites/production/files/2015-09/documents/efh-chapter06.pdf
  (Erişilebilir sürüm, 2025: https://origin-awswest-www.epa.gov/system/files/documents/2025-01/efh-chapter06_508.pdf)

Künyeler Crossref kayıtlarından, EPA değerleri bölümün PDF'inden (Tablo 6-2) 3 Ekim 2026'da doğrulanmıştır.

## 13. Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| 1.0 | 3 Ekim 2026 | İlk sürüm. IR değerleri EPA Tablo 6-2'ye göre kesinleştirildi (0,25 / 0,72 / 1,56 / 3,0); "mekanik havalandırma" (F = 0,25) eklendi; güncel I/O kaynakları eklendi. |
