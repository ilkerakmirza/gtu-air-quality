# GTÜ AirLab (kampüs hava kalitesi) — Claude çalışma kuralları

Bu proje hem Claude masaüstü uygulamasında hem de Claude Code web (bulut) oturumlarında geliştiriliyor.
Tek bir güncel sürüm olması için **tek kaynak `main` branch'idir**.

## Her oturumun başında
1. `git fetch origin main`
2. `main`'e geç ve güncelle: `git checkout main && git pull origin main`
   (Yerelde commit'lenmemiş değişiklik varsa önce kullanıcıya sor.)
3. Kullanıcıya ilk yanıtında kısaca hatırlat: "`main`'den en güncel sürümü çektim (son commit: `<hash> <mesaj>`).
   Bu projede tek kaynak `main`; iş bitince `main`'e push edeceğim."
   `git pull` başarısız olduysa veya `main`'e geçilemediyse bunu açıkça söyle; kullanıcı eski sürümle çalışmasın.

## Bekleyen işler (oturum başında kullanıcıya kısaca hatırlat, bitenleri buradan sil)
- **Tuzla resmî ÇŞB toplayıcısı Haziran 2026'dan beri çalışmıyor** (yerel bilgisayardaki zamanlanmış görev); Tuzla saatlik
  arşivi 6 Ekim 2026'dan beri sunucuda İBB'den toplanıyor (`collector.collect_hourly`).
- **CO₂ sensörlerinden 21 Temmuz 2026'dan beri veri yok:** Tuya IoT Platform'daki bulut geliştirme planının süresi dolmuş;
  kullanıcı Tuya'da planı yenilemeli/uzatmalı.
- **Tuzla PM₂.₅ geçmişi (kampüs–bölge karşılaştırması için):** İBB açık verisi Tuzla'nın PM₂.₅ geçmişini vermiyor,
  ÇŞB sitesi yalnızca Türkiye'den erişilebiliyor. **Masaüstü oturumunda** (kullanıcının Türkiye'deki bilgisayarı) çalıştır:
  `pip install requests && python scripts/csb_gecmis.py 2026-04-01`, sonra `frontend_v2/data/tuzla_saatlik.json`'u commit'leyip
  `main`'e push et. Karşılaştırma ekranları (WHO sekmesi, Özet aylık, Canlı "Kampüs vs Bölge") kendiliğinden dolar.
  Kullanıcı yeni PurpleAir verisi ekleyince aynı komutu güncel tarih aralığıyla tekrar çalıştır.
- **KVKK, git geçmişi:** Kişisel veri içeren belgeler (2209 kabul, BAP/1002 formları, ekip fotoğrafları, `link/` ekip sayfası)
  3 Ekim 2026'da repodan kaldırıldı ama eski commit'lerde duruyor. Kullanıcının kararı: **gtuairlab organizasyonuna geçişte
  geçmişsiz yeni repo** kurulacak, eski kişisel repo sonra silinip yerine yönlendirme konacak (silme adımı ayrıca onayla).
- **KVKK, kullanıcı tutmaya karar verdi:** `proje_animasyon.html`, `backend/seed.sql`, `create_demo_ilker_serra.py` (3 Ekim 2026).
- **Sunucu güvenliği (kullanıcı "sonra" dedi, 4 Ekim 2026; hatırlat):**
  1. `/api/upload` (CSV yükleme) korumasız: adresi bilen herkes veritabanına veri yükleyebilir. Öneri: `_admin_required()` eklemek;
     önce ekipte elle CSV yükleyen var mı sor (eski arayüzdeki form kapandı, yükleme için yeni yol gerekebilir).
  2. `ADMIN_TOKEN` varsayılanı `"changeme"` (`backend/config.py`): Render → Environment'ta uzun, rastgele bir değerle tanımlı mı,
     kullanıcı kontrol etmeli (değeri isteme).
- **Tanıtım videoları (6 Ekim 2026 deneme sürümü hazır):** `scripts/tanitim_video/` (Shorts 9:16 → Instagram/LinkedIn, uzun 16:9 → YouTube).
  Yayın sürümü PurpleAir veri göndermeye başlayınca `GERCEK=1` ile ve kalıcı adres (gtuairlab / airlab.gtu.edu.tr) karekodla yeniden kaydedilecek.
- **Adsız 20 bina:** ekip numaralı haritadan eşleştirince `campus.geojson`'a adları işle.

## Gizlilik ve KVKK (her değişiklikte kontrol et)
Repo ve GitHub Pages sitesi **herkese açık**: repoya giren her dosya (kök dizin dahil) bir bağlantıyla indirilebilir.
- **Kişisel veri repoya girmez:** ad-soyad, e-posta, telefon, öğrenci/TC no, fotoğraf, imzalı form, başvuru/kabul belgeleri.
  Böyle bir dosya görürsen kullanıcıya bildir; silmeden önce onay al.
- Saha ölçümü yapan kişilerin adları arayüzde **varsayılan olarak hiçbir yerde** gösterilmez; `app.js` → `PEOPLE` listesi
  "Saha ekibi A/B/C" etiketlerini kullanır. Ham `session_name` ekrana yazılmaz.
- Adlar sunucuda/veritabanında olduğu gibi kalır (kullanıcının tercihi; sunucuda anonimleştirme yapma). Herkese açık
  uçların çıktısında ise ad ve kampüs dışı konum yer almaz: CSV dışa aktarımda saha cihazları `saha-1…`, kampüs merkezine
  2 km'den uzak konumlar (`backend/kampus.py`) harita, saha oturumu, canlı cihaz ve CSV'de gösterilmez.
- **Ekip görünümü:** Saha panelinin altındaki "🔒 Ekip görünümü" bağlantısı ekip kodunu sorar. Gerçek adlar kaynak kodda
  düz metin olarak **yoktur**; `TEAM_VAULT` içinde ekip koduyla şifrelidir (PBKDF2 → AES-GCM). Kod ya da ad değişirse:
  `node scripts/ekip_kasasi.js "<kod>" '<ad JSON>'` çıktısını `TEAM_VAULT`'a yaz. Kaynak koda asla düz metin ad yazma.
- **Üçüncü taraflar:** Yazı tipleri ve kütüphaneler `frontend_v2/vendor/` altından yerel yüklenir (Google Fonts / CDN yok).
  Yeni bir dış servis ekleme; zorunluysa "Hakkında · Yöntem · Gizlilik" panelindeki KVKK bölümünü güncelle.
- Analitik, çerez, izleme aracı ekleme. Tarayıcıda yalnızca tercihler (localStorage) tutulur.
- **API anahtarları ve parolalar repoya asla girmez** (PurpleAir, Atmotube, Tuya, veritabanı, admin token): yalnızca sunucu ortam
  değişkenlerinde (Render → Environment). Tarayıcı koduna anahtar gömülmez. `.claude/settings.local.json` izin listesine komutla
  birlikte anahtar girebilir; commit'ten önce kontrol et. 4 Ekim 2026'da bu dosyada ve eski ekip sayfasında PurpleAir okuma anahtarı
  (76E9… ile başlayan) bulundu ve git geçmişinde duruyor. **Kullanıcının kararı (7 Ekim 2026): bu anahtar kullanılmaya devam edecek,
  yenilenmeyecek; tekrar önerme.** Risk yalnızca başkasının puanları harcaması (veri zaten herkese açık); kullanıcı PurpleAir panelinden
  puan kullanımını izler, beklenmedik artışta yeniler. gtuairlab'a geçmişsiz depoyla taşınınca anahtar herkese açık yerden kalkar.

## Arayüz ilkeleri (benzer uygulamalarla karşılaştırarak, akademik üslupla)
- Arayüz değişikliğinden önce benzer uygulamalardaki karşılığına bak: IQAir AirVisual, PurpleAir haritası,
  Sensor.Community, İBB Hava Kalitesi, ÇŞB SİM. Yaygın ve anlaşılır kalıbı seç; gösterişten çok netlik.
- **Akademik üslup:** birimler her zaman yazılı (µg/m³, ppm); veri kaynağı ve ölçüm zamanı görünür; sınırlılıklar
  saklanmaz; tavsiye dili ölçülü ("önerilir", "düşünebilir"), kesin sağlık hükmü yok. Yöntemde değişiklik olursa
  "Hakkında · Yöntem · Gizlilik" panelini güncelle.
- **Bileşen tutarlılığı:** mevcut bileşenleri yeniden kullan (panel/`news-dock`, `oz-card`, `wt` kutucukları, `pd-chip`,
  `oz-line`, `who-legend`, `who-cap`). Yeni renk ekleme; grafik renklerini dataviz doğrulayıcısından geçir.
- **Görsel dil:** GTÜ lacivertine dayalı koyu yüzeyler (`:root` belirteçleri), tek vurgu rengi (`--accent`), degrade/parlama yok.
  Panel ve bölüm başlıkları serif (`var(--serif)`, Source Serif 4), metin ve rakamlar Inter (`var(--num)`, tabular rakamlar).
  Arayüz ikonları emoji değil, `js/icons.js` (Lucide, ISC) çizgi ikonlarıdır: HTML'de `<svg class="i"><use href="#i-ad"></use></svg>`,
  JS'te `ico("ad")`; yeni ikon gerekirse `ICONS` listesine Lucide'dan ekle. Harita üzerindeki bina etiketi simgeleri (🎓, 🔬…) bilinçli olarak emojidir.
- **Basit / Araştırma görünümü:** Varsayılan görünüm herkes içindir (öğrenci, akademik ve idari personel):
  Özet, Harita, Sağlık (WHO), Duyuru. Teknik içerik (sensör panelleri, saha ölçümleri, oynatma, karşılaştırma grafiği)
  yalnızca **Araştırma**'dadır: masaüstünde üst çubuktaki düğme (`body.research`, tercih `gtu.view.research`),
  telefonda "Araştırma" sekmesi ve içindeki Sensörler / Saha ölçümleri geçişi. Yeni teknik özellikleri Araştırma'ya koy.
- **HKİ (Ulusal Hava Kalitesi İndeksi):** Herkesin gördüğü tek sınıflandırma budur (`colorscale.js` → `hki()`, `HKI_PM25`;
  `pm25Label` HKİ sınıf adını döndürür). PM₂.₅ kesim noktaları İBB'nin yayımladığı ulusal tablodan: 12,0 / 35,4 / 55,4 / 150,4 / 250,4.
  Sınıflar: İyi, Orta, Hassas, Sağlıksız, Kötü, Tehlikeli; her birinin yüz simgesi var (laugh … angry). Özet kartı IQAir düzeninde:
  büyük HKİ sayısı + yüz + sınıf, PM₂.₅ ikincil. WHO karşılaştırması ayrı kavram olarak Sağlık sekmesinde kalır.
  Sınır değerler (WHO 2021, Türkiye, AB 2030) Hakkında panelinde "Sınır değerler ve HKİ" bölümünde.
- **Otomatik durum duyuruları** (`shell.js` → `statusNotices`): sensör kesintisi (PurpleAir > 2 sa, Tuzla > 6 sa, CO₂ > 24 sa) ve
  HKİ > 100 (Hassas ve üstü) olduğunda Duyurular'a kendiliğinden kart düşer, sorun bitince kalkar; elle duyuru eklemeye gerek yok.
- **Kişisel maruziyet** (`maruziyet.js`): varsayılan girdi yolu kural tabanlı **asistan** (sohbet; yapay zekâ/dış servis yok; yüzü HKİ'ye
  göre değişir), ikinci yol tablo. C = P(saat) × R(bina) × F(ortam), solunum hızları US EPA (2011). Varsayımlar panelde
  yazılıdır; girilen bilgiler cihazdan çıkmaz (yalnızca "Bu cihazda hatırla" ile localStorage).
  Yöntem belgesi: `docs/maruziyet_yontemi.md`. `ENV`/`ACT` değerleri ya da hesap değişirse belgeyi aynı commit'te güncelle.
- **Sayı biçimi:** Ekranda gösterilen ölçüm değerleri Türkçe biçimdedir (12,3): `colorscale.js` → `f1tr()`. `toFixed` yalnızca hesap/CSS içinde kullanılır.
- **Kaynak kaydı:** Uygulamadaki her eşik, sınıflandırma ve hesap `docs/hesaplama_ve_kaynaklar.md`'de kaynağı ve doğrulama durumuyla
  kayıtlı. Bir eşik/kaynak değişirse ya da yeni hesap eklenirse belgeyi aynı commit'te güncelle; doğrulanmamış değeri "ikincil" diye işaretle.
- Kısa süreli saha ölçümleri WHO 24 saatlik değeriyle karşılaştırılmaz (kampüs saha ortalamasıyla karşılaştırılır).

## İş bitince
1. Değişiklikleri açıklayıcı bir mesajla commit'le.
2. Push'tan hemen önce tekrar `git pull origin main` (diğer ortamda yapılan iş varsa birleştir).
3. `git push origin main`
4. Bulut oturumunda ayrı bir çalışma branch'i kullanılıyorsa, o branch'i de `main` ile aynı commit'e getir ve push et.

Değişiklikler `main`'e geldiğinde GitHub Pages sitesi de güncellenir:
https://ilkerakmirza.github.io/gtu-air-quality/frontend_v2/

## Duyuru eklemek
Duyurular `frontend_v2/data/duyurular.json` dosyasında. Kullanıcı "duyuru ekle: …" dediğinde listeye yeni bir öğe ekle
(sıra önemli değil, uygulama tarihe göre sıralar), commit'le ve `main`'e push et. Birkaç dakika içinde herkesin uygulamasına gelir.

Sade duyuru (çoğu duyuru için yeterli):
```json
{
  "id": "2026-10-15-saha-olcumu",      // benzersiz; okunmamış sayacı buna göre çalışır, sonradan değiştirme
  "tarih": "2026-10-15",               // YYYY-AA-GG
  "etiket": "Saha",                    // isteğe bağlı: Duyuru, Saha, Toplantı, Sensör…
  "baslik": "Kısa başlık",
  "metin": "Açıklama. **kalın** yazılabilir, satır atlamak için \\n",
  "link": "https://…",                 // isteğe bağlı
  "link_metni": "Formu aç"             // isteğe bağlı
}
```

Renkli (zengin) duyuru — `renk` ya da `bolumler` varsa renkli başlık alanıyla kart olarak gösterilir
(örnek: `duyurular.json` içindeki uygulama tanıtımı):
- `renk`: `mor` | `mavi` | `yesil` | `turuncu` | `pembe` (başlık alanının degradesi)
- `ikon`: başlıktaki emoji · `ozet`: başlığın altındaki kısa cümle · `sabit: true`: listenin en üstünde kalır
- `bolumler`: sırayla gösterilen bölümler
  - `{ "tur": "ozellikler", "baslik": "…", "ogeler": [{ "ikon": "📡", "baslik": "…", "metin": "…" }] }` — renkli özellik kartları
  - `{ "tur": "adimlar", "ikon": "📱", "baslik": "…", "alt": "…", "renk": "#6c8cff", "adimlar": ["…", "…"] }` — numaralı adımlar
  - `{ "tur": "not", "ikon": "✨", "metin": "…" }` — yeşil not kutusu
  - `{ "tur": "metin", "baslik": "…", "metin": "…" }` — ara başlık / paragraf

## Telefon uygulaması (PWA)
- `frontend_v2/manifest.webmanifest`, `frontend_v2/sw.js`, `frontend_v2/icons/`, `frontend_v2/js/shell.js` (alt sekmeler, duyurular, kurulum).
- `sw.js` uygulama dosyalarını "önce ağ" ile sunar; güncellemeler bir sonraki açılışta gelir, önbellek sürümünü değiştirmek gerekmez.
- Telefon düzeni `index.html` içindeki `@media (max-width: 760px)` bloğunda; masaüstü düzenini bozmamaya dikkat et.

## Proje yapısı
- `frontend_v2/` — yayındaki arayüz (`index.html`, `js/icons.js` (ikon seti), `js/app.js`, `js/api.js`, `js/campus.js`, `js/colorscale.js`, `js/shell.js`, `js/who.js` (WHO durumu sekmesi), `js/ozet.js` (Özet: günlük ve aylık özet, açılış ekranı), `js/kiyas.js` (kampüs–Tuzla aynı saat karşılaştırması), `js/maruziyet.js` (kişisel maruziyet hesabı, taslak), `data/campus.geojson`, `data/duyurular.json`, `data/tuzla_saatlik.json` (Tuzla saatlik geçmişi))
- `frontend_v2/vendor/` — yerel Leaflet, Leaflet.heat, Chart.js ve yazı tipleri (Inter, Source Serif 4) (lisanslar `vendor/LICENSES/`)
- `docs/` — yöntem belgeleri: `hesaplama_ve_kaynaklar.md` (tüm sınıflandırma, eşik, hesap ve kaynakların kaydı + kontrol listesi), `maruziyet_yontemi.md` (kişisel maruziyet hesabı)
- **Sunucuyu uyanık tutma:** Asıl yöntem Supabase `pg_cron` işi `render-uyanik-tut` (5 dakikada bir `net.http_get` ile `/health`, 7 Ekim 2026).
  Yedek: `.github/workflows/sunucu-uyanik.yml` (GitHub zamanlaması 3–8 saatte bir çalışabiliyor). Render uyursa veri toplama durur.
  Render ücretsiz planı ayda 750 saat; tek servis 7/24 açık kalabilir.
- **Veritabanı (Supabase):** 4 tabloda RLS açık (7 Ekim 2026); sunucu `postgres` rolüyle bağlanır (RLS'yi atlar), anon/authenticated erişemez.
  `purpleair_readings.recorded_at` tekil (kopya kayıt yazılmaz).
- `scripts/` — `tanitim_video/` (tanıtım videosu kaydı ve fon müziği), `ekip_kasasi.js` (ekip görünümü ad kasası), `tuzla_gecmis.py` (İBB'den Tuzla PM₁₀ geçmişi, her yerden çalışır), `csb_gecmis.py` (ÇŞB'den Tuzla PM₂.₅ geçmişi, yalnızca Türkiye'den)
- `frontend/` — önceki harita arayüzü; **emekliye ayrıldı** (4 Ekim 2026): `map.html` ve kök `index.html` yeni arayüze (`frontend_v2/`) yönlendirir. Eski arayüz gerçek adları gösteriyor, CDN kullanıyor ve korumasız yükleme formu içeriyordu; geri getirme.
- `backend/` — Python sunucu ve veri toplayıcılar (PurpleAir, Atmotube, Tuya CO2, ÇSB, İBB); arayüzün kullandığı API: https://gtu-air-quality.onrender.com (`frontend_v2/js/api.js`)
- Yerelde önizleme: `python -m http.server 8765 --directory frontend_v2` → http://localhost:8765
