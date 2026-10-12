# Arayüz kalitesi · hafıza

## Test düzeneği
- `test/mock.js`: Render API taklidi (27 Nisan'dan bugüne saatlik PurpleAir; PM₁₀/sıcaklık yalnızca seyrek saatlerde; canlı kayıt cf_1'li;
  bir saha oturumu). `test/run.js`: masaüstü ve telefonda Özet, Sağlık, Araştırma, oynatma; konsol hatası ve "NaN/undefined/null" taraması.
  `test/shot2.js`: ayrıntı ekran görüntüleri. Sunucu: `python3 -m http.server 8791 --directory frontend_v2`.
  Çıktı `OUT_DIR` (yoksa geçici klasör); repoya yazılmaz. Playwright yolu `PLAYWRIGHT_MODULE` ile değiştirilebilir.
- Bulut oturumu onrender.com'a ve harita karolarına ulaşamaz; karo hataları beklenen, gerçek veri denemesi masaüstü oturumunda.

## Geçmiş bulgular (12 Ekim 2026, hepsi kapatıldı)
- Sağlık: PM₁₀ ortalaması birkaç güne dayandığı hâlde dönem ortalaması gibi görünüyordu.
- Özet: "%0 daha temiz" ve "benzer (fark %5)" çelişkisi.
- Oynatma: PM₁₀/sıcaklık "--"ye düşüp titriyordu.
- PM₁₀ kutusunda birimsiz "günlük 45 aşılan" ve "(≥6 saat)" teknik ifadesi.

## İzlenecekler
- Araştırma'daki "PurpleAir aynı anda Δ" ham Atmotube ile düzeltilmiş PurpleAir'i karşılaştırıyor (grafik ikisini de ham kullanıyor); karar bekliyor.
