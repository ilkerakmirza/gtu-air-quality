# GTÜ AirLab — hesaplamalar, eşikler ve kaynaklar

**Amaç:** Uygulamada gösterilen her sınıflandırmanın, eşiğin ve hesabın neye dayandığını tek yerde kayda geçirmek;
ileride değerlerin ve kaynakların güncelliğini denetleyebilmek.
**Belge sürümü:** 1.6 · 8 Ekim 2026
**İlgili belge:** Kişisel maruziyet hesabının ayrıntılı yöntemi → [`maruziyet_yontemi.md`](maruziyet_yontemi.md)

> Koddaki bir eşik ya da kaynak değişirse bu belge aynı commit'te güncellenmelidir. Her bölümün sonunda değerin kodda
> nerede durduğu yazılıdır. "Doğrulama" sütunu, değerin bu belgenin tarihinde birincil kaynaktan mı yoksa ikincil
> kaynaktan mı doğrulandığını gösterir.

---

## 1. Ölçüm verileri

| Veri | Kaynak | Not |
|---|---|---|
| Kampüs PM₂.₅, PM₁₀, sıcaklık, nem | PurpleAir PA-II (SUMER çatısı, sensör 229263); sunucu PurpleAir API'den 2 dakikada bir okur | Kampüsün genel (dış ortam) hava kalitesini temsil eder. Sunucu `pm2.5_atm` (A ve B kanalı) değerini **ham** kaydeder; ekranda ve bütün hesaplarda PM₂.₅ **US EPA düzeltmeli** kullanılır (§1a). PM₁₀ düzeltilmez. 2 Ekim 16:59 – 6 Ekim 16:53 (TR) arasında sensör çevrimdışıydı, veri yok; 7 Ekim 2026'dan beri PurpleAir veri erişim kotası yeterli. |
| Kampüs sıcaklık ve nem (PurpleAir) | PurpleAir PA-II gövde içi sensör | Düzeltilmeden gösterilir; sıcaklık ortamdan ~4 °C (8 °F) yüksek, nem ~4 puan düşük okunur (PurpleAir'in sensör açıklaması; **ikincil**, bu tarihte birincil kaynağa erişilemedi). Arayüzde "*" ve açıklama ile işaretli. |
| Saha ölçümleri | Atmotube Pro (yürüyüş ölçümleri, GPS'li) | Amaç: bina bazlı karakterizasyon (§5). Kısa süreli; WHO 24 saatlik değeriyle karşılaştırılmaz (§5). |
| İç mekân CO₂ | Tuya CO₂ sensörleri | 21 Temmuz 2026'dan beri veri yok. |
| Bölge (Tuzla istasyonu, ~6,4 km) | İBB hava kalitesi servisi (canlı); ÇŞB SİM arşivi (yerel toplayıcı); geçmiş için `data/tuzla_saatlik.json` | PM₁₀ geçmişi İBB açık verisinden (`scripts/tuzla_gecmis.py`), PM₂.₅ geçmişi ÇŞB'den (`scripts/csb_gecmis.py`, yalnızca Türkiye'den çalışır). |

Saatlik değerler sunucuda `interval=hourly` ile ortalanır; uygulamadaki tüm gün ve saat gruplamaları **Türkiye saatine**
(Europe/Istanbul) göredir.

**Veri denetimi kuralları (6 Ekim 2026):**

| Kural | Neden | Kodda |
|---|---|---|
| PurpleAir API'si aynı son ölçümü (aynı `last_seen`) döndürürse kayıt yapılmaz. | Sensör çevrimdışıyken her 2 dakikada aynı ölçüm tekrar yazılıyordu (6 Ekim 2026 itibarıyla 2005 yinelenen satır; değerler aynı, saatlik ortalamaya etkisi en çok 0,77, ortalama 0,08 µg/m³). | `backend/purpleair.py` → `poll()` |
| Kampüs sınırı: merkez 40,8114 K, 29,3563 D; yarıçap 2 km. Dışındaki Atmotube konumları harita izlerine, ısı haritasına, saha oturumlarına ve canlı cihaz konumuna alınmaz; CSV dışa aktarımda konum boş bırakılır. | Cihazlar eve/yola götürüldüğünde kampüs dışı noktalar kaydediliyordu (39 nokta, 11–44 km); hem kişisel konum (KVKK) hem kampüs ortalamasını bozan veri. Merkez `campus.geojson` binalarının kapsadığı alanın ortası; en uzak bina ~1,06 km. Ham arşiv (`measurements`) değiştirilmez. | `backend/kampus.py`, `backend/config.py` (`CAMPUS_*`), `frontend_v2/js/app.js` (`offCampus`) |
| CSV dışa aktarımda saha ölçümlerinin cihaz adı `saha-1, saha-2…` olarak verilir. | Saha cihaz adları kişi adı içeriyor. | `backend/archive.py` → `iter_csv()` |
| Tuzla istasyonu saatlik arşivi İBB'den sürdürülür. | ÇŞB yerel toplayıcısı Haziran 2026'dan beri çalışmıyor; arşiv 16 Haziran'dan beri boştu. | `backend/collector.py` → `collect_hourly()` |
| Veritabanında `purpleair_readings.recorded_at` tekil; 7 Ekim 2026'da 2011 yinelenen satır (değerleri birebir aynı) ve `atmotube_readings`'ten 40 kampüs dışı nokta silindi. | Tek kayıt, tek ölçüm; kişisel konum tutulmaz. | Supabase (dizin `purpleair_readings_recorded_at_key`), `backend/db.py` (`ON CONFLICT DO NOTHING`) |

## 1a. PurpleAir PM₂.₅ düzeltmesi (US EPA, 8 Ekim 2026)

Optik sensörün ham PM₂.₅ değeri referans cihazlara göre yaklaşık %40 yüksek okur ve nemden etkilenir. EPA'nın AirNow
Yangın ve Duman Haritası'nda uyguladığı genişletilmiş ABD geneli düzeltmesi kullanılır (PA = A/B ortalaması `pm2.5_atm`,
RH = PurpleAir nemi; nem eksikse %50):

- PA < 30: **0,524 × PA − 0,0862 × RH + 5,75** (Barkjohn vd., 2021); 50–210: 0,786 × PA − 0,0862 × RH + 5,75;
  30–50 ve 210–260 ağırlıklı geçiş; ≥ 260: 2,966 + 0,69 × PA + 8,84×10⁻⁴ × PA² (Barkjohn vd., 2022). Negatif sonuç 0 alınır (uygulama kuralı).
- Kalite kontrolü: A ve B kanalları hem ≥ 5 µg/m³ hem ≥ %70 ayrışırsa ölçüm hesaplara girmez.
- Yerel tutarlılık: Tuzla istasyonuyla aynı 241 saatte ortalama fark ham +%43 → düzeltilmiş −%2 (kolokasyon değil).
- Ham değer veritabanında ve Araştırma panelinde; düzeltme yalnızca gösterim/hesap katmanında (formül değişirse geçmiş yeniden hesaplanır).
- Aynı temelde karşılaştırma: Tuzla (resmî ölçüm) ile düzeltilmiş PurpleAir; Atmotube (düzeltilmez) ile ham PurpleAir (sensör karşılaştırma grafiği).

Formülün tamamı, çalışılmış örnekler, doğrulama, etki tabloları, sınırlılıklar ve kaynakların doğrulama durumu:
[`purpleair_epa_duzeltmesi.md`](purpleair_epa_duzeltmesi.md). Kaynakların durumu **ikincil** (EPA ve yayıncı sitelerine bu
ortamdan erişilemedi; aynı denklem birden çok bağımsız kaynakta aynı); kontrol listesinde (§12).

**Kodda:** `colorscale.js` → `epaPM25()`, `paChannelsAgree()`, `paCorrect()`; tek uygulama noktası `api.js`
(`purpleairLatest`, `purpleairHistory`); sunucu `db.py` → `get_purpleair_history()` A/B saatlik ortalamaları.

## 2. Ulusal Hava Kalitesi İndeksi (HKİ)

Herkesin gördüğü tek sınıflandırma budur (Özet kartı, harita lejantı, sensör panelleri, otomatik uyarılar).

**Kesim noktaları (PM₂.₅, 24 saatlik ortalama, µg/m³):**

| HKİ | Sınıf | PM₂.₅ | Renk (koddaki) | Yüz simgesi |
|---|---|---|---|---|
| 0–50 | İyi | 0,0–12,0 | `#00cc00` | laugh |
| 51–100 | Orta | 12,1–35,4 | `#ffcc00` | smile |
| 101–150 | Hassas | 35,5–55,4 | `#ff8800` | meh |
| 151–200 | Sağlıksız | 55,5–150,4 | `#ff0000` | frown |
| 201–300 | Kötü | 150,5–250,4 | `#bb44bb` | annoyed |
| 301–500 | Tehlikeli | 250,5–500,4 | `#7e0023` | angry |

**Hesap (doğrusal ara değer):**

```
C  = PM₂.₅ değeri, 0,1 µg/m³'e kesilir
I  = (I_üst − I_alt) / (C_üst − C_alt) × (C − C_alt) + I_alt     → en yakın tam sayıya yuvarlanır
     (C, tablodaki ilk "C ≤ C_üst" satırına göre; 500,4'ün üstü 500)
Örnek: C = 21,0 → (100 − 51) / (35,4 − 12,1) × (21,0 − 12,1) + 51 = 69,7 → HKİ 70 (Orta)
```

**Kabuller ve sınırlılıklar:**
* Resmî HKİ 24 saatlik ortalamaya göre hesaplanır; Özet'teki değer **son ölçüme göre gösterge** değerdir (kartta yazılı).
* Resmî HKİ PM₁₀, CO, SO₂, NO₂ ve O₃ için hesaplanır; sabit hava kalitesi sensörü PM₂.₅ ölçtüğü için tablonun PM₂.₅ sütunu kullanılır.
* ÇŞB SİM'in yayımladığı ulusal tablo ile İBB'nin yayımladığı tablo **PM₁₀ için farklıdır**: ÇŞB sayfaları
  0–50 / 51–100 / 101–260 / 261–400 / 401–520 / >520 µg/m³ veriyor; İBB tablosu 0–54 / 55–154 / 155–254 / … (EPA ile aynı).
  Uygulama PM₁₀ için HKİ hesaplamadığından bu fark şu an sonucu etkilemiyor; PM₁₀ HKİ eklenecekse hangi tablonun
  kullanılacağına karar verilmeli.
* Renkler resmî HKİ renklerinin uygulamanın mevcut paletindeki karşılıklarıdır (yeni renk eklenmedi).

| Değer | Kaynak | Doğrulama |
|---|---|---|
| PM₂.₅ kesim noktaları, sınıf adları | İBB Çevre Koruma ve Kontrol Dairesi, "Hava Kalitesi İndeksi" sayfası (ÇŞB ulusal tablosu, EPA uyarlaması) | Birincil: sayfa 4 Ekim 2026'da okundu. 151–200 ve 201–300 satırları sayfa çıktısında okunamadı; EPA tablosunun aynı satırlarıyla (55,5–150,4; 150,5–250,4) tamamlandı, diğer tüm satırlar EPA ile birebir aynı. |
| ÇŞB PM₁₀ kesim noktaları | ÇŞB il müdürlüğü/temiz hava merkezi HKİ sayfaları | İkincil (arama özeti); sayfalara doğrudan erişilemedi (zaman aşımı). |

**Kodda:** `frontend_v2/js/colorscale.js` → `HKI_PM25`, `hki()`, `pm25Label()`; Özet kartı `ozet.js` → `ADVICE`, `scaleHtml()`.

**Sınıflara göre öneri metinleri** (`ozet.js` → `ADVICE`) uygulama ekibince ölçülü dille yazılmıştır ("önerilir",
"düşünebilir"); ÇŞB'nin resmî sağlık mesajlarının birebir aktarımı değildir.

## 3. Sınır ve kılavuz değerler (Hakkında paneli)

| | PM₂.₅ yıllık | PM₂.₅ 24 sa | PM₁₀ yıllık | PM₁₀ 24 sa |
|---|---|---|---|---|
| WHO kılavuzu (2021) | 5 | 15 | 15 | 45 |
| Türkiye, yürürlükte | — | — | 40 | 50 (yılda en çok 35 aşım) |
| AB, 1 Ocak 2030'dan itibaren | 10 | 25 (yılda en çok 18 aşım) | 20 | 45 (yılda en çok 18 aşım) |

**WHO ara hedefleri (AH)** — Sağlık sekmesinde kullanılır (µg/m³):

| | AH-1 | AH-2 | AH-3 | AH-4 | Kılavuz |
|---|---|---|---|---|---|
| PM₂.₅ 24 sa | 75 | 50 | 37,5 | 25 | 15 |
| PM₂.₅ yıllık | 35 | 25 | 15 | 10 | 5 |
| PM₁₀ 24 sa | 150 | 100 | 75 | 50 | 45 |
| PM₁₀ yıllık | 70 | 50 | 30 | 20 | 15 |

| Değer | Kaynak | Doğrulama |
|---|---|---|
| WHO 2021 kılavuz ve ara hedefler | WHO (2021). *WHO global air quality guidelines: particulate matter (PM2.5 and PM10), ozone, nitrogen dioxide, sulfur dioxide and carbon monoxide.* Cenevre: WHO. ISBN 978-92-4-003422-8 | Yaygın bilinen resmî değerler; bu belgenin tarihinde kaynağın kendisi yeniden açılmadı. |
| Türkiye PM₁₀ 50 / 40 µg/m³ (2019'dan beri), PM₂.₅ sınırı yok | Hava Kalitesi Değerlendirme ve Yönetimi Yönetmeliği (RG 06.06.2008, sayı 26898), Ek I; geçiş dönemi 2019'da tamamlandı | İkincil: yönetmelik PDF'i indirildi ama Ek I tablosu metin olarak çıkarılamadı; değerler hakemli bir makaleden (PMC8975334) ve arama özetlerinden doğrulandı. PM₂.₅ için yürürlükte sınır olmadığı ve taslakta 2029 için 25 µg/m³ önerildiği ikincil kaynaklardan. |
| AB yıllık 10 / 20 µg/m³ | Directive (EU) 2024/2881, Annex I | Birincil'e yakın: Avrupa Parlamentosu prosedür özeti ve bir sektör analizi 4 Ekim 2026'da okundu. |
| AB günlük 25 / 45 µg/m³, yılda 18 aşım | Directive (EU) 2024/2881, Annex I | İkincil: Konsey çalışma belgesine dayanan arama özeti; EUR-Lex metnine bu ortamdan erişilemedi. **Kontrol listesinde.** |

**Kodda:** WHO değerleri `who.js` → `G`; tablo `index.html` → `#inf-sinir` bölümü.

## 4. WHO değerlendirmesi (Sağlık sekmesi)

* **Günlük ortalama:** O gün ölçülen saatlik değerlerin ortalaması (Türkiye saatine göre gün).
* **Kapsam kuralları:** En az **18 saat** ölçülen gün *tam gün*, en az **6 saat** ölçülen gün *gösterge gün*;
  daha az ölçülen günler değerlendirmeye alınmaz (grafikte soluk gösterilir).
* **Aşım günü:** Günlük ortalaması 15 µg/m³'ü (PM₂.₅) aşan gösterge/tam gün. WHO'ya göre 24 saatlik değer yılda en çok
  3–4 gün aşılmalıdır (99. yüzdelik ≈ günlerin %1'i). Bir yıldan kısa dönemde mutlak sayı değil **oran** karşılaştırılır:
  aşım günlerinin oranı ≤ %1 ise kutucuk "uygun", değilse "aşıldı" gösterilir (8 Ekim 2026'ya kadar mutlak sayı ≤ 3 kullanılıyordu;
  2 ölçülen günün ikisi de aşılmışken yanlışlıkla "uygun" görünüyordu).
* **Dönem ortalaması:** Değerlendirmeye giren günlerin ortalaması; yıllık kılavuz değerle (5 µg/m³) karşılaştırılır
  ("yıllık kılavuz değerinin X katı"). Dönem bir yıldan kısaysa bu karşılaştırma göstergedir.
* Veri: PurpleAir saatlik geçmişi, 1 Ocak 2026'dan bugüne.

**Kodda:** `who.js` → `FULL_H = 18`, `MIN_H = 6`, `EXCEED_SHARE = 0.01`, `dailyMeans()`, `HISTORY_FROM`.

## 5. Bina değerleri (saha ölçümleri)

* Saha ölçümü GPS noktaları bina poligonlarıyla eşleştirilir (`data/campus.geojson`).
* En az **3** ölçümü olan binalar gösterilir; **30**'dan az ölçümü olanlar "az ölçüm" diye işaretlenir.
* Kısa süreli oldukları için WHO 24 saatlik değeriyle **karşılaştırılmaz**; aynı dönemdeki tüm saha ölçümlerinin
  ortalamasıyla karşılaştırılır (binanın kampüs ortalamasına göre konumu).
* Binada geçen süre: ardışık ölçümler arası boşluk ≤ 5 dk ise aynı ziyaret sayılır.
* **Atmotube ham kullanılır; EPA formülü uygulanmaz** (8 Ekim 2026 araştırması):
  - Kılavuzda PM için düzeltme faktörü yoktur. Üretici, PM sensörünün (Sensirion SPS30, MCERTS sertifikalı) fabrikada referans
    cihaza göre kontrol edildiğini ve kullanıcı ayarı gerekmediğini belirtir; uygulamada yalnızca sıcaklık/nem için elle sapma ayarı vardır.
  - Bağımsız testlerde Atmotube PRO'nun saatlik PM₂.₅'i resmî cihazlarla neredeyse bire birdir: Leeds'te 8 cihaz 14 hafta
    FIDAS 200S yanında, ortalama eğim 0,99, kesişim −1,6 µg/m³; aynı çalışmada ham PurpleAir eğimi 1,37 (Shittu vd., 2025).
    Güney Kaliforniya AQMD saha testinde R² 0,79–0,90 (PM₁₀ zayıf).
  - Bu yüzden PurpleAir'in EPA formülü Atmotube'a uygulanmaz; uygulansa değerleri haksız yere ~%35 düşürürdü
    (ör. 20 µg/m³, nem %35 → 13,2).
  - Bilinen zayıflıklar: nem > %80'de fazla okur (bizim saha verimizde nem hiç %80'i geçmedi: en yüksek %65, ortanca %35);
    cihazdan cihaza fark olabilir (Leeds'te 8 cihazdan biri belirgin sapmış; bizde kısa yan yana ölçümlerde ATP-2/ATP-4 yakın,
    ATP-3/ATP-4 uzak); PM₁₀ güvenilir değildir; düşük derişimde tek ölçümün belirsizliği büyüktür (üretici: ±(5 µg/m³ + %5)).
  - **Yan yana ölçüm (karar: 8 Ekim 2026; sonuç bekleniyor):** beş cihaz SUMER çatısında PurpleAir'in yanında en az 24 saat
    (tercihen 48) birlikte ölçer. Bu, EPA'nın PurpleAir için yaptığının küçük ölçekli karşılığıdır.
    - Kurulum: cihazlar PurpleAir'le aynı yükseklikte ve 1–2 m içinde, hava delikleri açık; yağmurdan ve doğrudan güneşten korunur.
      Uygulamada PM modu "Always ON" (sürekli ölçüm, dakikalık ortalama kaydı). Bu modda pil yaklaşık 1 gün dayandığı için cihazlar
      USB'ye ya da powerbank'e bağlı kalır. "Upload historical data to the cloud" ayarı açık olur.
    - Cihazda gerçek zamanlı saat yoktur, saat telefondan alınır: ölçümden hemen önce telefonla eşitlenir, ölçüm boyunca kapatılmaz.
      Başlangıç ve bitiş saati not edilir. Telefon bağlı olmadan da ölçer ve belleğine yazar (yaklaşık 10 gün); ölçüm bitince
      telefona bağlanınca kayıt buluta gider. Yedek: uygulamadan CSV (Settings → Export Data to File).
    - Analiz: saatlik ortalamalar (saatin en az 45 dakikası dolu). Önce her cihaz beş cihazın ortancasıyla, sonra düzeltilmiş
      PurpleAir'le karşılaştırılır (oran, eğim, kesişim, R², ortalama fark). Oran 1 ± %10 içindeyse cihaza dokunulmaz (uygulama kuralı);
      dışındaysa o cihazın değerleri tek bir çarpanla ölçeklenir, ham değer veritabanında kalır.
    - Derişimler düşük ve dar aralıkta kalırsa (ör. hep 10 µg/m³'ün altında) üreticinin ±(5 µg/m³ + %5) belirsizliği oranı
      bozar; o zaman çarpan uygulanmaz, ölçüm uzatılır. Sonuçlar bu bölüme ve `purpleair_epa_duzeltmesi.md` §9'a yazılır.
* **Ani yükselmeler ayıklanmaz (ekip kararı, 8 Ekim 2026):** Yürüyüş sırasındaki tek noktalık yüksek değerler
  (ör. 8 → 522 → 65 µg/m³) yakında sigara içilmesi gibi gerçek, kısa süreli bir kaynaktan gelebilir ve maruziyetin parçasıdır.
  Bu nedenle bütün ölçümler bina ortalamalarına, kampüs saha ortalamasına ve saha özetine dahil edilir; hiçbir ölçüm silinmez.
  Sınırlılık: 8 Ekim 2026 itibarıyla 4285 kampüs içi saha ölçümünün 9'u, aynı yürüyüşteki komşu ölçümlerin 5 katını aşıyor.
  Kampüs saha ortalamasına etkileri küçüktür (8,80 µg/m³; bu 9 değer olmasa 8,49), ama az ölçümlü binalarda belirgindir
  (Kelebek Cafe 24,0 µg/m³, 7 ölçüm; bu değer olmasa 13,1). Az ölçümlü binalar arayüzde "az ölçüm" diye işaretlenir.
  (1.2 sürümünde bu değerleri ortalamalardan çıkaran bir kural denendi; aynı gün kaldırıldı.)

**Kodda:** `campus.js` → `MIN_PTS = 3`, `FEW = 30`, `buildingStats()`, `durationOf()`.

## 6. Kampüs–bölge karşılaştırması

* Kampüs PurpleAir saatlik PM₂.₅ ile Tuzla istasyonu PM₂.₅ **aynı saatlerde** eşleştirilir; yalnızca iki tarafın da
  ölçüm yaptığı saatler kullanılır.
* Fark yüzdesi = (kampüs ortalaması − Tuzla ortalaması) / Tuzla ortalaması × 100.
* Yorum: fark ≤ −%5 → "daha temiz"; ≥ +%5 → "daha kirli"; arası → "benzer".
* Anlık karşılaştırmada (Özet, Canlı) ±0,5 µg/m³ eşiği kullanılır. Burada da **aynı saat** eşleştirilir: Tuzla'nın son
  yayımlanan saatlik değeri, o saatin PurpleAir saatlik ortalamasıyla karşılaştırılır (8 Ekim 2026). Tuzla değeri İBB yayın
  gecikmesi yüzünden 1–3 saat geride olabildiğinden, önceden kampüsün son (çoğu zaman henüz dolmamış) saati ya da anlık değeri
  ile farklı saatler karşılaştırılıyordu. O saat için kampüs verisi yoksa Özet satırı gösterilmez; Canlı kartta kampüsün son
  saati kullanılır ve notta "saatler farklı" yazar. Kodda: `app.js` → `paSameHour()`.
* **Bölge istasyonu seçimi:** Yalnızca kampüse en fazla **15 km** uzaklıktaki İBB istasyonu (pratikte Tuzla) kullanılır;
  Tuzla o saat PM₂.₅ vermezse uzak bir istasyona geçilmez, veri yok sayılır (8 Ekim 2026; daha önce bir saat için Avrupa
  yakasındaki Avcılar istasyonu kullanılmıştı). Kodda: `backend/ibb.py` → `MAX_KM`, `app.js` → `ibbDirect()`.

**Kodda:** `kiyas.js` → `data()`, `summary()`, `verdict()`; `ozet.js` günlük satır.

## 7. Özet ekranı kuralları

* **Gösterilen değer:** PurpleAir son ölçümü 2 saatten yeniyse kampüs değeri; değilse Tuzla istasyonu (güncelse).
* **Aylık özet:** Ay ortalaması, değerlendirmeye giren (≥ 6 saat) günlerin ortalamasıdır; en yüksek ve en düşük binalar
  o ayın saha ölçümlerinden.
* **Ay karşılaştırması:** Yüzde değişim yalnızca gösterilen ay ile karşılaştırılan önceki ayın **her ikisinde de en az 7
  değerlendirilebilir gün** varsa verilir; karşılaştırılan ay, bu koşulu sağlayan en yakın önceki aydır. (1–2 günlük
  ölçümle hesaplanan aylık yüzde değişim yanıltıcıdır.)

**Kodda:** `ozet.js` → `PA_FRESH_MIN = 120`, `TREND_MIN_DAYS = 7`, `monthStats()`.

## 8. İç mekân CO₂ ölçeği

| ppm | Etiket |
|---|---|
| < 600 | mükemmel (dış ortam ~420) |
| 600–800 | iyi |
| 800–1000 | yeterli havalandırma |
| 1000–1500 | zayıf |
| 1500–2000 | kötü |
| 2000–5000 | çok kötü |
| > 5000 | tehlikeli (mesleki sınır) |

* CO₂ bir kirletici sınıflandırması değil, **havalandırma göstergesi** olarak kullanılır.
* 5000 ppm: OSHA'nın 8 saatlik zaman ağırlıklı mesleki maruziyet sınırı (PEL).
* 4 Ekim 2026'da etiketlerden "WHO hedefi" ifadesi kaldırıldı: WHO'nun iç ortam CO₂ için bir kılavuz değeri yoktur.
  Koddaki açıklamada 800 ppm'in WHO'nun COVID-19 havalandırma rehberine dayandığı yazıyor; **bu iddia doğrulanmadı
  (kontrol listesinde).** 1000 ppm yaygın kullanılan bir havalandırma göstergesidir.

**Kodda:** `colorscale.js` → `CO2_SCALE`.

## 9. Renkler ve grafikler

- **PM₂.₅ rengi = HKİ sınıf rengi** (8 Ekim 2026): harita işaretçileri, bina boyaması, paneller, listeler ve lejant aynı
  6 rengi kullanır (§2 tablosu). Önceki 18 renkli uygulama içi ölçek kaldırıldı; aynı değerin bir yerde "Orta" (sarı),
  başka yerde kırmızı görünmesine yol açıyordu. Lejant tek ölçektir: 6 sınıf, adı ve PM₂.₅ aralığı. Isı haritası renk
  geçişi HKİ sınırlarına (12 / 35,4 / 55,4) hizalıdır.
- **Cihaz renkleri** her grafikte aynıdır: PurpleAir `#6380f0`, Tuzla `#bf8418`, Atmotube `#2fa79a`. Üçü birlikte veri
  görselleştirme renk doğrulayıcısından geçti (koyu zemin; tüm ikililer renk körlüğü ΔE ≥ 14,5, normal görüş ΔE ≥ 19,3, kontrast ≥ 3:1).
  Önceki sensör karşılaştırma grafiğinde Atmotube rengi kişiye göre değişiyor, bazı kişilerde PurpleAir'den ayırt edilemiyordu (ΔE 1,8).
- **Takvim ekseni:** Günlük grafiklerde (Sağlık › günlük PM₂.₅, kampüs–bölge) dönemdeki her gün bir sütundur; ölçüm olmayan gün boş kalır.
- Çizgi grafiklerde dolgu ve yumuşatma yoktur (tepe değerler olduğu gibi). Logaritmik eksene geçilirse eksen başlığında yazar.

**Kodda:** `colorscale.js` → `pm25Color()`, `DEVICE_COLOR`, `buildLegend()`; `who.js` → `calendarDays()`.

## 10. Otomatik durum duyuruları

| Durum | Eşik |
|---|---|
| PurpleAir kesintisi | Son ölçüm 2 saatten eski |
| Tuzla istasyonu kesintisi | Son ölçüm 6 saatten eski ya da kaynak "eski" işaretli |
| CO₂ sensörleri kesintisi | En yeni ölçüm 24 saatten eski |
| Hava kalitesi uyarısı | Güncel değerin HKİ'si > 100 (Hassas ve üstü; PM₂.₅ ≥ 35,5 µg/m³) |

Duyurunun kimliği olayın başlangıç tarihine bağlıdır (aynı kesinti okununca tekrar "yeni" görünmez); sorun bitince kalkar.

**Kodda:** `shell.js` → `statusNotices()`.

## 11. Kişisel maruziyet

C = P(saat) × R(bina) × F(ortam); doz = C × solunum hızı × süre. Solunum hızları US EPA *Exposure Factors Handbook*
(2011), Bölüm 6, Tablo 6-2; iç/dış oranları Chen ve Zhao (2011), Hänninen ve ark. (2011), Salamalikis ve ark. (2025),
Afroz ve ark. (2025), Branco ve ark. (2024). Ayrıntılar, sayısal örnek ve kaynakça: [`maruziyet_yontemi.md`](maruziyet_yontemi.md).

## 12. Kontrol listesi (ileride doğrulanacaklar)

- [ ] AB 2024/2881 Ek I günlük değerleri (25 / 45 µg/m³, 18 aşım) EUR-Lex metninden birincil olarak doğrulanmalı.
- [ ] Türkiye yönetmeliği Ek I tablosu (PM₁₀ 50 / 40) resmî metinden okunmalı; yeni "Dış Ortam Hava Kalitesi Yönetimi
      Yönetmeliği" yürürlüğe girdiyse PM₂.₅ sınırı eklenmeli.
- [ ] HKİ: ÇŞB SİM'in güncel ulusal tablosunda PM₂.₅ sütunu var mı, İBB tablosuyla aynı mı?
- [ ] CO₂ 800 ppm eşiğinin dayandığı kaynak (iddia: WHO COVID-19 havalandırma rehberi) doğrulanmalı.
- [x] PurpleAir için US EPA düzeltmesi uygulandı (8 Ekim 2026, §1a).
- [ ] US EPA beş bölümlü denklemi ve kanal kuralı birincil kaynaktan (EPA "Sensor Data Cleaning and Correction" sunumu,
      AirNow Soru-Cevap denklem tablosu, Barkjohn vd. 2021) teyit edilmeli.
- [ ] PurpleAir'in resmî bir istasyon yanında (kolokasyon) yerel doğrulaması yapılabilirse yapılmalı.
- [ ] WHO 2021 değerleri kaynağın kendisinden yeniden kontrol edilmeli (değişiklik beklenmiyor).

## 13. Kaynakça

- Shittu ve ark. (2025). Performance evaluation of Atmotube PRO sensors for air quality measurements in an urban location.
  *Atmospheric Measurement Techniques*, 18, 817–828. https://doi.org/10.5194/amt-18-817-2025
- South Coast AQMD AQ-SPEC. Atmotube Pro saha ve laboratuvar değerlendirme raporları.
  https://www.aqmd.gov/docs/default-source/aq-spec/field-evaluations/atmotube-pro---field-evaluation.pdf
- Atmotube destek sayfaları: Sensor Accuracy and Technical Specifications; How is Atmotube PRO calibrated?;
  How often does the Atmotube take measurements?; Data Storage and Collection (erişim 8 Ekim 2026)
- Barkjohn, K. K., Gantt, B., Clements, A. L. (2021). *Atmospheric Measurement Techniques*, 14, 4617–4637. https://doi.org/10.5194/amt-14-4617-2021
- Barkjohn, K. K., Holder, A. L., Frederick, S. G., Clements, A. L. (2022). *Sensors*, 22(24), 9669. https://doi.org/10.3390/s22249669
- Jaffe, D. A. ve ark. (2023). *Atmospheric Measurement Techniques*, 16, 1311. https://doi.org/10.5194/amt-16-1311-2023
- U.S. EPA / AirNow. AirNow Fire and Smoke Map: Questions and Answers. https://document.airnow.gov/airnow-fire-and-smoke-map-questions-and-answers.pdf
- Afroz, R. ve ark. (2025). *ACS ES&T Air*, 2, 625–636. https://doi.org/10.1021/acsestair.4c00342
- Avrupa Parlamentosu ve Konseyi (2024). Directive (EU) 2024/2881 on ambient air quality and cleaner air for Europe (recast), Annex I.
  Prosedür özeti: https://oeil.europarl.europa.eu/oeil/en/document-summary?id=1796087
- Branco, P. ve ark. (2024). *Environmental Research*, 261, 119713. https://doi.org/10.1016/j.envres.2024.119713
- Chen, C., Zhao, B. (2011). *Atmospheric Environment*, 45, 275–288. https://doi.org/10.1016/j.atmosenv.2010.09.048
- Hänninen, O. ve ark. (2011). *Air Quality, Atmosphere & Health*, 4, 221–233. https://doi.org/10.1007/s11869-010-0076-5
- Hava Kalitesi Değerlendirme ve Yönetimi Yönetmeliği (Resmî Gazete, 6 Haziran 2008, sayı 26898).
  https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=12188&mevzuatTur=KurumVeKurulusYonetmeligi&mevzuatTertip=5
- İBB Çevre Koruma ve Kontrol Dairesi Başkanlığı. Hava Kalitesi İndeksi. https://cevre.ibb.istanbul/hava-kalitesi/hava-kalitesi-indeksi/
- ÇŞB Sürekli İzleme Merkezi (SİM), HKİ. https://sim.csb.gov.tr/Home/HKI
- Türkiye PM₁₀ geçiş dönemi ve 2019 değerleri için hakemli kaynak: https://pmc.ncbi.nlm.nih.gov/articles/PMC8975334
- Salamalikis, V. ve ark. (2025). *Air Quality, Atmosphere & Health*, 18, 2609–2624. https://doi.org/10.1007/s11869-025-01787-4
- U.S. EPA (2011). *Exposure Factors Handbook: 2011 Edition*, Bölüm 6 (EPA/600/R-09/052F).
- WHO (2021). *WHO global air quality guidelines.* ISBN 978-92-4-003422-8.

## 14. Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| 1.6 | 8 Ekim 2026 | §5: Atmotube yan yana ölçüm kararı (SUMER çatısı): kurulum, analiz ve karar kuralı. |
| 1.5 | 8 Ekim 2026 | §1a: PurpleAir PM₂.₅ US EPA düzeltmesi ve kanal kalite kontrolü (ayrıntı: purpleair_epa_duzeltmesi.md). §9: PM₂.₅ rengi = HKİ sınıf rengi (18 renkli ölçek kaldırıldı), sabit cihaz renkleri, takvim ekseni. |
| 1.4 | 8 Ekim 2026 | §6: anlık kampüs–Tuzla karşılaştırması (Özet, Canlı) aynı saati eşleştirir. |
| 1.3 | 8 Ekim 2026 | §5: ani yükselmeleri ortalamalardan çıkaran kural kaldırıldı (ekip kararı: sigara dumanı gibi gerçek kısa süreli maruziyet olabilir); bütün saha ölçümleri ortalamalara dahil. |
| 1.2 | 8 Ekim 2026 | §4: aşım günü kutucuğu oranla değerlendirilir (≤ %1). §5: ani sıçrama kuralı (1.3'te kaldırıldı). §7: ay karşılaştırması en az 7 gün. §1: PurpleAir sıcaklık/nem notu. Bölge istasyonu 15 km sınırı (§6). |
| 1.1 | 6 Ekim 2026 | §1'e veri denetimi kuralları eklendi: yinelenen PurpleAir kaydı engeli, 2 km kampüs sınırı, CSV'de saha cihaz adlarının gizlenmesi, Tuzla arşivinin İBB'den sürdürülmesi. PurpleAir durumu güncellendi. |
| 1.0 | 4 Ekim 2026 | İlk sürüm: HKİ, sınır değerler, WHO değerlendirmesi, bina ve bölge karşılaştırmaları, Özet kuralları, CO₂ ölçeği, harita ölçeği, otomatik duyurular. CO₂ etiketinden doğrulanmamış "WHO hedefi" ifadesi kaldırıldı. |
