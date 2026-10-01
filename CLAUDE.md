# GTÜ Hava Kalitesi — Claude çalışma kuralları

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
- **Adsız 20 bina:** ekip numaralı haritadan eşleştirince `campus.geojson`'a adları işle.

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
- `frontend_v2/` — yayındaki arayüz (`index.html`, `js/app.js`, `js/api.js`, `js/campus.js`, `js/colorscale.js`, `js/shell.js`, `js/who.js` (WHO durumu sekmesi), `data/campus.geojson`, `data/duyurular.json`)
- `frontend/` — önceki harita arayüzü (`map.html`)
- `backend/` — Python sunucu ve veri toplayıcılar (PurpleAir, Atmotube, Tuya CO2, ÇSB, İBB); arayüzün kullandığı API: https://gtu-air-quality.onrender.com (`frontend_v2/js/api.js`)
- Yerelde önizleme: `python -m http.server 8765 --directory frontend_v2` → http://localhost:8765
