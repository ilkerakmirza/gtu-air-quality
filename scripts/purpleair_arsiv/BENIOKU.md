# PurpleAir arşiv içe aktarımı (yarım kalan iş, 12 Ekim 2026)

Amaç: 27 Nisan – 6 Ekim 2026 PurpleAir geçmişini sensörün kendi arşivinden (`docs/veri/purpleair_229263_2dk_2026-04-27_2026-10-06.csv`)
veritabanına almak; tüm geçmişi tek yöntemle (EPA, cf_1) hesaplamak. Akış: veri kontrolü → işleme planı → son kontrol (üç ajan).

## Durum
- Yapıldı: 3341 sunucu kaydına cf_1 yazıldı (plan C); 1 Mayıs – 6 Ekim 104 493 arşiv kaydı eklendi (D.2–D.12).
  Sayılar veri kontrolü ajanının bağımsız hesabıyla birebir aynı.
- Yedek alındı: `yedek_purpleair_nisan` (781 eski Nisan kaydı, aynı id ve değerler).
- **Kalan:** 27–30 Nisan'daki 781 eski kayıt silinmedi (Supabase MCP aracı DELETE'te onay bekleyip 60 sn'de iptal ediyor).
  Kullanıcı Supabase → SQL Editor'de çalıştıracak (uyarı penceresinde "Run this query"):
  `DELETE FROM purpleair_readings p USING yedek_purpleair_nisan y WHERE p.id = y.id;`
- Sonra sırayla: `plan.sql` D.1 (Nisan ekleme, beklenen 2868) → D.13 (Nisan sıcaklığını yedekten taşı, kullanıcı kararı "taşı")
  → E (doğrulama; beklenen: 2026-10-06T21:00Z öncesi 110 752 kayıt, 110 745'inde cf_1; 153 tam gün; elle denetim
  15 Mayıs 14:00 → 11,053 · 1 Ağustos 08:00 → 7,370 · 6 Mayıs 08:00 → 27,931 µg/m³).
- Belgeler: `belge_taslagi.patch` (`git apply`) → `<<KESINLESECEK>>` yerlerini E sonuçlarıyla doldur → `main`.
- En son: hazırlık/günlük tabloları (`gecici_pa_indirme`, `gecici_pa_eklenen`, `gecici_cf1_eklenen`) kullanıcı onayıyla kaldırılır
  (plan.sql G); yedek tablo kalır. Bu klasör iş bitince silinir.

Uygulama bu ara durumda sorunsuz çalışır: Nisan'ın 4 günü eski kayıtlarla ve yedek yöntemle hesaplanır.
