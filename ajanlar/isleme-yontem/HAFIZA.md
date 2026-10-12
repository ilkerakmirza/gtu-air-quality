# İşleme, yöntem, yazılım · hafıza

## Kararlar ve dersler
- **Supabase MCP aracı:** her çağrı 60 sn'de kesilir ve işlem geri alınır; büyük işi küçük, tekrar çalıştırılabilir adımlara böl.
  `DELETE` bu araçtan çalışmıyor (onay bekleyip iptal oluyor): silme adımını kullanıcı Supabase SQL Editor'de çalıştırır.
- PurpleAir arşiv içe aktarma planı ve geri alma bölümü: `scripts/purpleair_arsiv/plan.sql` (durum: `scripts/purpleair_arsiv/BENIOKU.md`).
  Eklenen kayıtlarda `pm2_5` = A/B cf_atm ortalaması (0,1'e, yarım yukarı); lat/lon 40,8062 / 29,361 açıkça yazılır
  (sütun varsayılanı farklı). Nisan sıcaklığı yedekten taşınır (kullanıcı kararı "taşı"); geri alma bu yüzden `pm1_0 IS NULL` kullanır.
- `backend/db.py` saatlik/günlük ortalamaları 2 ondalığa yuvarlar (yanıt ~%30 küçüldü).
- Arayüz kararları (12 Ekim 2026): Sağlık sekmesinde PM₁₀ kaç güne dayandığını yazar, PM₂.₅ günlerinin yarısından azsa büyük değer
  "—"; Özet'te aydan aya fark %5 altıysa "… ayıyla benzer" (karar ve yazı aynı yuvarlanmış sayı); oynatmada arşiv kaydı PM₁₀/sıcaklığı
  10 dk içindeki sunucu kaydından alır; Atmotube listesinde 24 saatten eski ölçüm renkli gösterilmez.

## Açık işler
- PurpleAir içe aktarımının Nisan adımı bitince belge taslağını uygula (`scripts/purpleair_arsiv/belge_taslagi.patch`) ve
  `<<KESINLESECEK>>` yerlerini doldur.
