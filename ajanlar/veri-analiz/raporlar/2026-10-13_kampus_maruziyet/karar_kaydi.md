# Karar kaydı · Kampüs maruziyet raporu, sürüm 1.2 (saha ölçümlerinin karşılaştırması)

Hazırlayan: Ajan 5 (veri analizi) · 13 Ekim 2026 · Rapor: `rapor.md` §2.8 ve §3.4 · Betik: `betikler/g_saha_kiyas.py`

Her karar için: **ne kullanıldı**, **neden**, **alternatif neydi**, **kaynak**, **doğrulama durumu**.
Doğrulama durumu: "arama özeti" = künye ve bulgu web arama sonuçlarından ve katalog kayıtlarından denetlendi, tam metin açılamadı
(bu ortamdan yayıncı sitelerine erişilemedi); "uygulama belgesi" = `docs/` belgelerinde kayıtlı; "bu çalışmanın kuralı" = kaynağı
yok, gerekçesi burada.

---

## A. Veri seçimi

**A1. Hangi kayıtlar?**
- Ne: PM₂.₅'i ve ±3 dakika içinde düzeltilmiş PurpleAir değeri olan 4.008 saha kaydı (27–30 Nisan; 12 oturum).
- Neden: oran (K) ancak aynı anın çatı değeriyle hesaplanabilir. Eşleştirme sürüm 1.1 ile aynıdır, sayılar karşılaştırılabilir kalır.
- Alternatif: saatlik çatı ortalamasıyla eşleştirme. Daha kaba; saat içindeki değişimi kaçırır.
- Kaynak: sürüm 1.1 yöntemi (§2.4, §2.5). Doğrulama: Ajan 1 sürüm 1.1'de bu eşleştirmeye dayanan sayıları doğruladı.

**A2. Nisan çatı verisi nereden?**
- Ne: depodaki sensör arşivi `docs/veri/purpleair_229263_2dk_2026-04-27_2026-10-06.csv` (2 dk, cf_1 dahil), uygulamanın US EPA
  düzeltmesi ve A/B kanal kuralıyla.
- Neden: veritabanındaki 27–30 Nisan kayıtları eski biçimde (cf_1 yok); arşiv tam. Yeni sorgu çekilmedi (kota).
- Alternatif: veritabanındaki eski kayıtlar (genişletilmiş denklem, cf_atm). Uygulamanın asıl yöntemi değil.
- Kaynak: `docs/purpleair_epa_duzeltmesi.md`; Barkjohn vd. (2021). Doğrulama: uygulama belgesi.

**A3. Kişi etiketi**
- Ne: "Ölçümcü A/B/C" = uygulamadaki "Saha ekibi A/B/C" (`app.js` → `PEOPLE`, ad ön ekinin md5 özetiyle eşlenir; ad yazılmaz).
- Neden: kullanıcı kişi karşılaştırması istedi; uygulamayla aynı harfler karışıklığı önler.
- Alternatif: anonim "Kişi 1/2/3". Uygulamayla eşleşmezdi.
- Doğrulama: betik eşlenemeyen oturum olursa durur.

## B. Ölçüler

**B1. TWA ve K_TWA: "toplamların oranı"**
- Ne: TWA = Σc·Δt / ΣΔt, K_TWA = Σc·Δt / ΣP·Δt. Gün, ölçümcü ve tüm oturumlar için kayıtlar birleştirilir.
- Neden: K_TWA, kişinin soluduğu miktarın aynı sürede çatı havasında solunacak miktara oranına eşittir (anlamı açık). Δt ağırlığı
  1 ve 2 dakikalık kayıtları adil tartar.
- Alternatif: kayıt oranlarının (c/P) ortancası ya da ortalaması. Ortalama, çatı değeri küçükken tek kayıtla şişer; ortanca kısa
  tepeleri yok sayar (tepeler ayıklanmaz kararıyla çelişir). Ortanca sürüm 1.1'de mekânsal analizde kullanıldı, burada değil.
- Doğrulama: bu çalışmanın kuralı; Tablo 4'teki oturum K_TWA'larıyla birebir aynı (aynı tanım).

**B2. Solunan miktara göre oran K_D**
- Ne: K_D = Σc·IR·Δt / ΣP·IR·Δt; IR bina içinde (poligon içi ya da ≤ 15 m) 0,25 m³/sa (oturma), dışında 1,56 m³/sa (tempolu yürüme).
  Duyarlılık: bina içi 0,72 m³/sa (hafif etkinlik).
- Neden: kullanıcı "solunan miktara göre" de istedi. Sabit IR ile K_D = K_TWA olurdu ve bilgi taşımazdı. Konuma göre IR, uygulamanın
  varsayılan gününün (iç ortamda oturma, açık havada yürüme) mantığıdır.
- Alternatif: ölçülen etkinlik (ivmeölçer, kalp hızı, günlük). Veri yok → gelecek çalışma.
- Kaynak: U.S. EPA (2011) Exposure Factors Handbook, Tablo 6-2; `docs/maruziyet_yontemi.md`. Doğrulama: uygulama belgesi (3 Ekim 2026).
- Not: IR bir varsayımdır; K_D'nin K_TWA'dan farkı ölçülmüş değil, varsayımdan gelir.

**B3. Bina içi/dışı**
- Ne: uygulamanın 15 m kuralı (`campus.js` → `nearestBuilding`); üç katman: Kimya binası, diğer binalar, bina dışı.
- Neden: uygulamayla tutarlılık; Kimya binası noktaların çoğunu oluşturduğu ve K'si belirgin farklı olduğu için ayrı katman.
- Alternatif: yalnızca iki katman (içi/dışı). Denendi: K ile bina dışı süre payı arasındaki ilişki zayıf (ρ = 0,28), "hangi bina"
  daha belirleyici (ρ = 0,44) → üç katman seçildi.
- Sınırlılık: 15 m kuralı kafe önü gibi açık alanları "bina" sayar; GPS bina içinde sapabilir. Doğrulama: uygulama kuralı.

## C. Belirsizlik

**C1. Güven aralığı: oturum içi blok bootstrap**
- Ne: her oturum 30 dakikalık bloklara bölünür, bloklar yerine konarak yeniden örneklenir; 2000 yineleme, %2,5–97,5 yüzdelikleri.
  Sabit tohum (20261013) → her çalıştırmada aynı sonuç.
- Neden: ardışık dakikalar birbirine bağımlıdır; kayıtları tek tek yeniden örneklemek aralığı yapay olarak daraltır. 30 dakika,
  kısa tepelerin ve bina içi dönemlerin bir blokta kalmasına yetecek, oturum başına 6–19 blok bırakacak kadar kısadır.
- Alternatif: (a) kayıt düzeyinde bootstrap (çok dar, yanlış); (b) oturum düzeyinde küme bootstrap (her ölçümcü-gün tek oturum →
  uygulanamaz); (c) 15 ya da 60 dk blok (duyarlılık olarak denenmedi; kota).
- Kaynak: Künsch (1989), *Annals of Statistics* 17(3), 1217–1241, https://doi.org/10.1214/aos/1176347265. Doğrulama: arama özeti.
- Kapsamı: yalnızca örnekleme belirsizliği. Cihaz kalibrasyonu ve PurpleAir düzeltmesi dahil değil (raporda ayrıca yazıldı).

**C2. Atmotube çözünürlüğü (1 µg/m³)**
- Ne: K, c − 0,5 ve c + 0,5 µg/m³ ile yeniden hesaplandı (sınır).
- Neden: değerlerin çoğu tam sayı; cihazın yuvarladığı mı kestiği mi bilinmiyor. ±0,5 en kötü sistematik kaymadır.
- Alternatif: yok sayma. Temiz günde (çatı ~4 µg/m³) K'yi %12'ye kadar kaydırdığı için yok sayılamaz.
- Doğrulama: bu çalışmanın kuralı.

**C3. Cihaz farkı**
- Ne: düzeltilmedi (yan yana ölçüm yok); büyüklüğü literatürle ve aynı bina-aynı saat karşılaştırmasıyla (D5) tartışıldı.
- Neden: kullanıcı kararı (Atmotube ham ve göreli kullanılır; yan yana ölçüm sonrası tek çarpan).
- Kaynak: Shittu vd. (2025), *AMT* 18, 817–828, https://doi.org/10.5194/amt-18-817-2025 — cihazlar arası değişim katsayısı
  dakikalık %28, saatlik %18, günlük %15; bir cihazda belirgin sapma. Doğrulama: arama özeti (önbaskı sürümlerinde farklı sayılar
  var; yayımlanmış sürümün sayıları kullanıldı).

## D. Karşılaştırma ve ayrıştırma

**D1. Aynı gün farkının ölçüsü**
- Ne: en yüksek / en düşük oranı ve en yüksek − en düşük farkı (µg/m³), TWA, K_TWA ve saat başına solunan miktar için.
- Neden: kullanıcı "oran ve fark" istedi; oran göreli, fark mutlak büyüklüğü verir.
- Alternatif: değişim katsayısı (3 kişiyle kararsız).

**D2. Ortak zaman penceresi**
- Ne: aynı günün üç oturumunun zaman kesişimi (ör. 30 Nisan 10:01–12:35).
- Neden: oturumlar farklı saatlerde başlayıp bittiği için tam gün karşılaştırması saat dilimi farkını da içerir. Ortak pencere bu
  etkeni kaldırır (saat dilimi etkisinin en basit denetimi).
- Alternatif: saat dilimi için regresyon. Daha karmaşık, n küçük.

**D3. Gün mü, ölçümcü mü? (kareler toplamı ayrıştırması)**
- Ne: 3 ölçümcü × 4 gün, her hücrede bir değer; log K_TWA ve log TWA için toplamsal model; payların yüzdesi. 27 Nisan hariç
  duyarlılık.
- Neden: düzen dengeli olduğundan ayrıştırma kalansız ve saydamdır; log, oranlar için uygundur.
- Alternatif: karma model (12 gözlemle kararsız), anlamlılık testi (hücre başına tek gözlem → etkileşim sınanamaz; p değeri
  verilmedi).
- Doğrulama: bu çalışmanın kuralı; standart iki yönlü varyans çözümlemesi.

**D4. Kitagawa ayrıştırması**
- Ne: K = Σ w_s K_s (w_s: katmanın ΣP·Δt payı). İki ölçümcü arasındaki ΔK = yer dağılımı [Σ (w₂ − w₁)(K₁ + K₂)/2] + yerdeki düzey
  [Σ (K₂ − K₁)(w₁ + w₂)/2]; kalansız. Bir ölçümcünün bulunmadığı katmanda diğerinin K'si kullanıldı.
- Neden: kullanıcının önerdiği "içeride/dışarıda geçen süre ile K'yi karşılaştır" sorusunun tam ve basit karşılığı.
- Alternatif: K'yi "dış süre payı" ile tek değişkenli ilişkilendirmek (ρ = 0,28; zayıf ve 12 nokta).
- Sınırlılık: boş katman doldurulması, o katmandaki tüm farkı "yer dağılımı"na yazar (28 Nisan'da C diğer binalarda hiç yok).
- Kaynak: Kitagawa (1955), *JASA* 50(272), 1168–1194 (JSTOR 2281213). Doğrulama: arama özeti (künye); DOI doğrulanamadı, verilmedi.

**D5. Aynı bina, aynı saatler (A–C)**
- Ne: A ve C'nin yalnızca Kimya binası kayıtları, iki oturumun ortak penceresinde; C/A oranı.
- Neden: yer ve saat sabitlenince kalan fark oda, etkinlik ve cihaz farkının toplamıdır; cihaz farkı için bir üst sınır verir.
- Alternatif: yan yana ölçüm (en iyisi; yapılmadı).

**D6. Kayıt düzeyinde regresyon — seçilmedi**
- Ne: log(K) ~ bina içi/dışı + saat + kişi + gün modeli kurulmadı.
- Neden: (1) ardışık kayıtlar bağımlı, etkin örneklem 4.008 değil çok daha küçük; (2) kişi, cihaz, örnekleme aralığı ve gezilen yer
  birbirine bağlı (B hem 2 dk, hem diğer binalarda); (3) yalnızca 12 oturum. Katsayılar yanıltıcı kesinlik gösterirdi.
- Alternatif yerine: D3 + D4 + tek etken denetimleri (D7–D9).

**D7. Kısa tepeler**
- Ne: her oturumun en yüksek %10 kaydı hesaptan çıkarılarak K yeniden hesaplandı — **yalnızca duyarlılık**; veri ayıklanmadı, ana
  sonuçlar tepeler dahildir.
- Neden: kullanıcı kararı (8 Ekim 2026: tepeler ayıklanmaz, gerçek maruziyettir); farkın ne kadarının kısa olaylardan geldiğini
  göstermek için. %10, sürüm 1.1'deki "en yüksek %10'un payı" göstergesiyle tutarlı.
- Alternatif: sabit eşik (ör. 100 µg/m³ üstü). Gün düzeyine göre keyfî olurdu.

**D8. Saat dilimi ve dış ortam sınıfı**
- Ne: dilimler 08–11, 11–14, 14–19 (sürüm 1.1'deki sabah/öğle/akşamüstü ile aynı); çatı sınıfları < 6, 6–12, ≥ 12 µg/m³.
- Neden: 6 µg/m³, sürüm 1.1'de 27 Nisan'ı (oranın bilgi taşımadığı temiz gün) ayıran eşik; 12 µg/m³ HKİ "İyi" üst sınırı.
- Doğrulama: bu çalışmanın kuralı (HKİ sınırı uygulama belgesi).

**D9. Örnekleme aralığı**
- Ne: 1 dakikalık 8 oturum her ikinci kayıt alınarak (iki evre) 2 dakikaya seyreltildi; K ve en yüksek 15 dk ortalama değişimi.
- Neden: B'nin 2 dk aralığının etkisini doğrudan ölçmenin tek yolu (B'yi 1 dk'ya çevirmek mümkün değil).

**D10. Nem**
- Ne: oturumlardaki en yüksek nem (çatı ve Atmotube), %75'i aşan kayıt sayısı.
- Neden: optik sensörlerde fazla okuma yüksek nemde belirginleşir.
- Kaynak: Jayaratne vd. (2018), *AMT* 11, 4883–4890 (~%75); Shittu vd. (2025) (> %80). Doğrulama: arama özeti.

## E. Şekiller ve renkler

**E1. Şekil türleri**
- Şekil 10: gün gruplu nokta grafiği (kişi yan yana) + çatı değeri için kısa yatay çizgi; K için log eksen ve güven aralığı.
  Neden: aynı günün üç kişisi yan yana, oran için log eksen (0,5 ve 2 simetrik). Alternatif: gruplu çubuk (oran için yanıltıcı).
- Şekil 11: (a) yatay çubuk (iki bileşen), (b) nokta-çizgi (önce/sonra), (c) %100 yığılmış çubuk. Neden: her biri tek bir soruyu
  yanıtlar. Alternatif: şelale grafiği (iki bileşen için gereksiz).
- Şekil 12: 30 dakikalık K çizgileri, 28 ve 30 Nisan (iki büyük farkın günleri). Konum gösterilmez.

**E2. Ölçümcü renkleri**
- Ne: A #eb6834 (turuncu, daire), B #c64f8d (pembe, kare), C #1baf7a (yeşil, üçgen); PurpleAir her yerde #6380f0.
- Neden: PurpleAir mavisiyle ve birbiriyle karışmayan renkler. Doğrulayıcı (dataviz `validate_palette.js`, açık zemin) PurpleAir ile
  birlikte geçti; yeşil–pembe renk körlüğü ayrımı sınırda (ΔE 7,7) → ikincil kodlama: işaret biçimi ve doğrudan harf etiketi.
  Mor (#6250d6) PurpleAir mavisine çok yakın çıktığı için (ΔE 11,7) kullanılmadı.
- Şekil 11c'de bileşenler nötr gri tonlardadır (ölçümcü ve cihaz renkleriyle karışmasın).

## F. Gizlilik (KVKK)

**F1. Dakikalık konum yok**
- Ne: ölçümcü etiketiyle birlikte bina içi/dışı zaman çizelgesi verilmedi; yalnızca oturum toplamı süre payları.
- Neden: kullanıcının kuralı. Her ölçümcü-gün tek oturum olduğundan oturum numarası değerlerden ölçümcüye eşlenebilir; bu yüzden
  Şekil 8'deki bina içi/dışı gölgelendirmesi ve §3.3'teki tek kaydın konum notu da kaldırıldı.
- Alternatif: Tablo 4'teki oturum değerlerini değiştirmek ya da yuvarlamak. Doğrulanabilirliği bozar; seçilmedi.

## G. Literatür (yeni eklenenler)

| Kaynak | Kullanıldığı yer | Doğrulama |
|---|---|---|
| Dons vd. (2011), *Atmos. Environ.* 45(21), 3594–3602, https://doi.org/10.1016/j.atmosenv.2011.03.064 | Kişiler arası fark (%30'a varan), zaman-etkinlik | Arama özeti (künye ve özet); yazar listesi tam metinden doğrulanmadı |
| Meng vd. (2005), *JEAEE* 15(1), 17–28, https://doi.org/10.1038/sj.jea.7500378 | Kişisel maruziyette dış ortam dışı kaynaklar (nitel) | Arama özeti; özetler arasında sayısal paylar farklı → sayı kullanılmadı |
| Morawska vd. (2018), *Environ. Int.* 116, 286–299, https://doi.org/10.1016/j.envint.2018.04.018 | Düşük maliyetli sensör belirsizliği | Arama özeti |
| Karagulian vd. (2019), *Atmosphere* 10(9), 506, https://doi.org/10.3390/atmos10090506 | Düşük maliyetli sensör belirsizliği | Arama özeti |
| Künsch (1989), *Ann. Stat.* 17(3), 1217–1241, https://doi.org/10.1214/aos/1176347265 | Blok bootstrap | Arama özeti |
| Kitagawa (1955), *JASA* 50(272), 1168–1194, JSTOR 2281213 | Fark ayrıştırması | Arama özeti; DOI doğrulanmadı |
| Shittu vd. (2025), *AMT* 18, 817–828, https://doi.org/10.5194/amt-18-817-2025 | Atmotube cihazlar arası değişkenlik | Arama özeti (sürüm 1.1'de de vardı; sayılar eklendi) |

Kullanılmayan aday: Avery vd. (2010, *Epidemiology* 21(2), 215–223; dış ortam–kişisel PM₂.₅ korelasyonu): künye bulundu, DOI
doğrulanamadı → kullanılmadı.


## Ek not (bağımsız denetim, 13 Ekim 2026)
- "En yüksek %10 kayıt" sayısı round(0,1·n) ile belirlenir; aşağı yuvarlamayla değerler en çok 0,01 değişir (ör. 28.04 B: 0,725 / 0,717).
- Dons vd. (2011) kara karbon üzerine bir çalışmadır; karşılaştırma yalnızca büyüklük mertebesi içindir.
- Kitagawa (1955) için DOI verilmez; aramada çıkan 10.1080/01621459.1955.10501294 başka sayfalara aittir.
