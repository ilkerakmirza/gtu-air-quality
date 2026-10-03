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
- **PurpleAir verisi 4 Ağustos 2026'dan beri gelmiyor** (API kotası bitti). Çözüm: sensörün yerel ağdaki
  `http://<sensör-IP>/json` adresinden 2 dakikada bir okuyup veritabanına yazan yerel toplayıcı betiği
  (`csb_yerel_toplayici.py` gibi). Kullanıcıdan beklenen: sensörün yerel IP adresi ve sensörle aynı ağda
  sürekli açık kalacak bir bilgisayar. PurpleAir haritasından veri çekmek kullanım koşullarına aykırı, önerme.
- **Tuzla resmî ÇŞB toplayıcısı Haziran 2026'dan beri çalışmıyor** (yerel bilgisayardaki zamanlanmış görev);
  şimdilik İBB canlı verisi kullanılıyor.
- **CO₂ sensörlerinden 21 Temmuz 2026'dan beri veri yok** (Tuya).
- **Tuzla PM₂.₅ geçmişi (kampüs–bölge karşılaştırması için):** İBB açık verisi Tuzla'nın PM₂.₅ geçmişini vermiyor,
  ÇŞB sitesi yalnızca Türkiye'den erişilebiliyor. **Masaüstü oturumunda** (kullanıcının Türkiye'deki bilgisayarı) çalıştır:
  `pip install requests && python scripts/csb_gecmis.py 2026-04-01`, sonra `frontend_v2/data/tuzla_saatlik.json`'u commit'leyip
  `main`'e push et. Karşılaştırma ekranları (WHO sekmesi, Özet aylık, Canlı "Kampüs vs Bölge") kendiliğinden dolar.
  Kullanıcı yeni PurpleAir verisi ekleyince aynı komutu güncel tarih aralığıyla tekrar çalıştır.
- **Adsız 20 bina:** ekip numaralı haritadan eşleştirince `campus.geojson`'a adları işle.

## Gizlilik ve KVKK (her değişiklikte kontrol et)
Repo ve GitHub Pages sitesi **herkese açık**: repoya giren her dosya (kök dizin dahil) bir bağlantıyla indirilebilir.
- **Kişisel veri repoya girmez:** ad-soyad, e-posta, telefon, öğrenci/TC no, fotoğraf, imzalı form, başvuru/kabul belgeleri.
  Böyle bir dosya görürsen kullanıcıya bildir; silmeden önce onay al.
- Saha ölçümü yapan kişilerin adları arayüzde **varsayılan olarak hiçbir yerde** gösterilmez; `app.js` → `PEOPLE` listesi
  "Saha ekibi A/B/C" etiketlerini kullanır. Ham `session_name` ekrana yazılmaz.
- Adlar sunucuda/veritabanında olduğu gibi kalır (kullanıcının tercihi; sunucuda anonimleştirme yapma).
- **Ekip görünümü:** Saha panelinin altındaki "🔒 Ekip görünümü" bağlantısı ekip kodunu sorar. Gerçek adlar kaynak kodda
  düz metin olarak **yoktur**; `TEAM_VAULT` içinde ekip koduyla şifrelidir (PBKDF2 → AES-GCM). Kod ya da ad değişirse:
  `node scripts/ekip_kasasi.js "<kod>" '<ad JSON>'` çıktısını `TEAM_VAULT`'a yaz. Kaynak koda asla düz metin ad yazma.
- **Üçüncü taraflar:** Yazı tipleri ve kütüphaneler `frontend_v2/vendor/` altından yerel yüklenir (Google Fonts / CDN yok).
  Yeni bir dış servis ekleme; zorunluysa "Hakkında · Yöntem · Gizlilik" panelindeki KVKK bölümünü güncelle.
- Analitik, çerez, izleme aracı ekleme. Tarayıcıda yalnızca tercihler (localStorage) tutulur.

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
- **Otomatik durum duyuruları** (`shell.js` → `statusNotices`): sensör kesintisi (PurpleAir > 2 sa, Tuzla > 6 sa, CO₂ > 24 sa) ve
  PM₂.₅ > 25 µg/m³ olduğunda Duyurular'a kendiliğinden kart düşer, sorun bitince kalkar; elle duyuru eklemeye gerek yok.
- **Kişisel maruziyet** (`maruziyet.js`): C = P(saat) × R(bina) × F(ortam), solunum hızları US EPA (2011). Varsayımlar panelde
  yazılıdır; girilen bilgiler cihazdan çıkmaz (yalnızca "Bu cihazda hatırla" ile localStorage).
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
- `scripts/` — `ekip_kasasi.js` (ekip görünümü ad kasası), `tuzla_gecmis.py` (İBB'den Tuzla PM₁₀ geçmişi, her yerden çalışır), `csb_gecmis.py` (ÇŞB'den Tuzla PM₂.₅ geçmişi, yalnızca Türkiye'den)
- `frontend/` — önceki harita arayüzü (`map.html`)
- `backend/` — Python sunucu ve veri toplayıcılar (PurpleAir, Atmotube, Tuya CO2, ÇSB, İBB); arayüzün kullandığı API: https://gtu-air-quality.onrender.com (`frontend_v2/js/api.js`)
- Yerelde önizleme: `python -m http.server 8765 --directory frontend_v2` → http://localhost:8765
