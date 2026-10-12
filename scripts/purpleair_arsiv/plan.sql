-- ════════════════════════════════════════════════════════════════════════════
-- PurpleAir geçmişi (27 Nisan – 6 Ekim 2026) içe aktarma planı · purpleair_readings
-- Kaynak: docs/veri/purpleair_229263_2dk_2026-04-27_2026-10-06.csv (PurpleAir Data Download Tool, sensör 229263,
--         Average 0 = 2 dk), hazırlık tablosu gecici_pa_indirme(t, rh, atm_a, atm_b, cf1_a, cf1_b), 110 752 satır.
--
-- Kurallar
--   * Her adım ayrı çalıştırılır (her biri tek ifade/tek işlem, 60 s sınırının çok altında).
--   * Her adım tekrar çalıştırılabilir (idempotent): yarıda kalırsa aynı adım yeniden çalıştırılır.
--   * Sıra: 0 (ön kontrol) → A (yedek) → B (silme) → C (cf_1) → D (eklemeler) → E (doğrulama).  Geri alma: F.
--   * "DURUN" yazan kontrol beklenen sonucu vermezse sonraki adıma geçilmez.
--   * Bütün zamanlar timestamptz; sınırlar Türkiye saatiyle (+03) yazıldı.
-- Beklenen sonuç (koordinatörün ön hesabı): Nisan'daki 781 kayıt yedeklenip silinir, 3341 sunucu kaydına cf_1 eklenir,
--   107 361 yeni kayıt eklenir; 110 752 − 3341 − 107 361 = 50 indirme satırı eklenmez: 43'ünün sunucu kaydında cf_1 zaten
--   var (6 Ekim), 6'sı sunucu kaydından 1 s kayık (aynı ölçüm), 1'i 22 Haziran 11:50:28Z sunucu kaydıyla aynı zamanlı ama
--   B kanalı farklı (9,0 / 8,3; "kaynaklar arası tutarsızlık", sunucu kaydı korunur, cf_1 eklenmez).
-- Veri denetimi (Ajan 1): dönemdeki 3391 sunucu kaydının 3385'i (%99,82) dosyayla aynı zaman damgalı; cf_atm farkı ≤ 0,05
--   (sunucu 2, dosya 1 ondalık); nem aynı. Sonuçta tabloda 2026-10-06T21:00Z öncesi 110 752 kayıt, 110 745'inde cf_1 olur.
-- ════════════════════════════════════════════════════════════════════════════


-- ── 0. Ön kontroller (salt okunur) ───────────────────────────────────────────

-- 0.1 Hazırlık tablosu: t timestamptz olmalı, 110 752 satır, 27 Nis 00:00 – 6 Eki 23:59 (+03), t tekil.
SELECT pg_typeof(min(t)) AS t_turu, count(*) AS satir, count(DISTINCT t) AS tekil_t,
       min(t) AT TIME ZONE 'Europe/Istanbul' AS ilk_tr, max(t) AT TIME ZONE 'Europe/Istanbul' AS son_tr,
       count(*) FILTER (WHERE cf1_a IS NULL OR cf1_b IS NULL) AS cf1_eksik,
       count(*) FILTER (WHERE atm_a IS NULL OR atm_b IS NULL) AS atm_eksik
FROM gecici_pa_indirme;
-- DURUN: t_turu 'timestamp with time zone' değilse ya da satir ≠ tekil_t ise.

-- 0.2 Silinecek Nisan kayıtları (15 Haziran'da içe aktarılanlar). Beklenen: 781.
SELECT count(*) AS nisan_15haziran, min(recorded_at), max(recorded_at), min(created_at), max(created_at)
FROM purpleair_readings
WHERE recorded_at >= '2026-04-27 00:00+03' AND recorded_at < '2026-05-01 00:00+03'
  AND created_at  >= '2026-06-15 00:00+03' AND created_at  < '2026-06-16 00:00+03';
-- DURUN: 781 değilse. (Ölçüt farklıysa A.1'deki WHERE'i aynı biçimde düzeltin.)

-- 0.3 Dönemdeki mevcut kayıtlar (karşılaştırma için not edin).
SELECT count(*) AS toplam,
       count(*) FILTER (WHERE pm2_5_cf1_a IS NOT NULL) AS cf1_var,
       count(*) FILTER (WHERE pm10_0 IS NULL) AS pm10_yok
FROM purpleair_readings
WHERE recorded_at >= '2026-04-27 00:00+03' AND recorded_at < '2026-10-07 00:00+03';


-- ── A. Yedek ────────────────────────────────────────────────────────────────

-- A.1 Yedek tablo (yalnızca yoksa oluşturulur; varsa dokunulmaz).
CREATE TABLE IF NOT EXISTS yedek_purpleair_nisan AS
SELECT * FROM purpleair_readings
WHERE recorded_at >= '2026-04-27 00:00+03' AND recorded_at < '2026-05-01 00:00+03'
  AND created_at  >= '2026-06-15 00:00+03' AND created_at  < '2026-06-16 00:00+03';

-- A.2 Erişim kapalı (diğer tablolar gibi RLS açık, politika yok) ve açıklama.
ALTER TABLE yedek_purpleair_nisan ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE yedek_purpleair_nisan IS
  'Yedek (12 Ekim 2026): 15 Haziran 2026''da içe aktarılmış 27-30 Nisan PurpleAir kayıtları (781). '
  'PurpleAir Data Download Tool 2 dk verisiyle (cf_1 dahil) değiştirildi. Geri alma: plan.sql F.3.';

-- A.3 Kontrol. Beklenen: 781 ve purpleair_readings'te hâlâ 781 eşi var.
SELECT (SELECT count(*) FROM yedek_purpleair_nisan) AS yedek,
       (SELECT count(*) FROM purpleair_readings p JOIN yedek_purpleair_nisan y ON y.id = p.id) AS esi_duruyor;


-- ── B. Nisan kayıtlarını silme (yalnızca yedekteki id'ler) ────────────────────

DELETE FROM purpleair_readings p USING yedek_purpleair_nisan y WHERE p.id = y.id;
-- Kontrol: A.3 tekrar → esi_duruyor = 0.


-- ── C. Mevcut sunucu kayıtlarına cf_1 ekleme ─────────────────────────────────
-- Eşleşme kuralı (6–12 Ekim'deki gibi): zaman damgası aynı VE A/B cf_atm değerleri aynı (yuvarlama payı 0,06 µg/m³).

-- C.1 Günlük (log) tablosu: cf_1 eklenen kayıtların id'leri (geri alma için).
CREATE TABLE IF NOT EXISTS gecici_cf1_eklenen (id bigint PRIMARY KEY);
ALTER TABLE gecici_cf1_eklenen ENABLE ROW LEVEL SECURITY;

-- C.2 Önizleme. Beklenen: eslesen 3341, zaman_ayni_deger_farkli 1 (22 Haziran 11:50:28Z). (Zaman eşleşip değeri tutmayan da sayılır; büyükse inceleyin.)
SELECT count(*) FILTER (WHERE abs(p.pm2_5_a - g.atm_a) <= 0.06 AND abs(p.pm2_5_b - g.atm_b) <= 0.06) AS eslesen,
       count(*) FILTER (WHERE NOT (abs(p.pm2_5_a - g.atm_a) <= 0.06 AND abs(p.pm2_5_b - g.atm_b) <= 0.06)) AS zaman_ayni_deger_farkli,
       count(*) FILTER (WHERE abs(p.humidity_pct - g.rh) > 1) AS nem_farkli
FROM purpleair_readings p JOIN gecici_pa_indirme g ON g.t = p.recorded_at
WHERE p.recorded_at >= '2026-04-27 00:00+03' AND p.recorded_at < '2026-10-07 00:00+03'
  AND p.pm2_5_cf1_a IS NULL;

-- C.3 Eşleşen id'leri günlüğe yaz.
INSERT INTO gecici_cf1_eklenen (id)
SELECT p.id
FROM purpleair_readings p JOIN gecici_pa_indirme g ON g.t = p.recorded_at
WHERE p.recorded_at >= '2026-04-27 00:00+03' AND p.recorded_at < '2026-10-07 00:00+03'
  AND p.pm2_5_cf1_a IS NULL AND p.pm2_5_cf1_b IS NULL
  AND abs(p.pm2_5_a - g.atm_a) <= 0.06 AND abs(p.pm2_5_b - g.atm_b) <= 0.06
  AND g.cf1_a IS NOT NULL AND g.cf1_b IS NOT NULL
ON CONFLICT DO NOTHING;

-- C.4 cf_1 değerlerini yaz (yalnızca günlükteki ve hâlâ boş olanlar).
UPDATE purpleair_readings p
SET pm2_5_cf1_a = g.cf1_a, pm2_5_cf1_b = g.cf1_b
FROM gecici_cf1_eklenen e, gecici_pa_indirme g
WHERE p.id = e.id AND g.t = p.recorded_at AND p.pm2_5_cf1_a IS NULL;

-- C.5 Kontrol. Beklenen: gunluk = cf1_yazildi = 3341.
SELECT (SELECT count(*) FROM gecici_cf1_eklenen) AS gunluk,
       (SELECT count(*) FROM purpleair_readings p JOIN gecici_cf1_eklenen e ON e.id = p.id
         WHERE p.pm2_5_cf1_a IS NOT NULL AND p.pm2_5_cf1_b IS NOT NULL) AS cf1_yazildi;


-- ── D. Eksik zamanları yeni kayıt olarak ekleme ─────────────────────────────
-- Kural: ±60 s içinde herhangi bir kayıt varsa eklenmez (sunucu kaydı korunur); recorded_at tekil → ON CONFLICT.
-- Yeni kayıtta yalnızca PM₂.₅ alanları ve nem var; pm1_0, pm10_0, temperature_c NULL (indirme dosyasında yok).
-- pm2_5 = cf_atm (A/B ortalaması, 0,1'e yuvarlı, round(numeric) = yarım yukarı; yalnızca ham gösterim değerini etkiler,
-- EPA hesabı cf_1'den yapılır). lat/lon = 40.8062, 29.361 (bütün sunucu kayıtlarındaki
-- değer; sütun varsayılanı 40.80380, 29.44690 farklı olduğu için açıkça yazılır).
-- Eklenen id'ler gecici_pa_eklenen'e yazılır (geri alma için).

-- D.0 Günlük tablosu.
CREATE TABLE IF NOT EXISTS gecici_pa_eklenen (id bigint PRIMARY KEY);
ALTER TABLE gecici_pa_eklenen ENABLE ROW LEVEL SECURITY;

-- D.1 … D.12: aynı ifade, yalnızca dönem sınırları değişir. Her birini ayrı çalıştırın.
-- Şablon (:bas, :son yerine aşağıdaki çiftleri yazın):
--   WITH ins AS (
--     INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
--     SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
--     FROM gecici_pa_indirme g
--     WHERE g.t >= :bas AND g.t < :son
--       AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
--                       WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
--     ON CONFLICT (recorded_at) DO NOTHING
--     RETURNING id)
--   INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;
-- Not: ON CONFLICT (recorded_at), recorded_at üzerindeki tekil kısıtı/dizini kullanır. Hata verirse "ON CONFLICT DO NOTHING" yazın.

-- D.1  27–30 Nisan (~2868 satır)
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-04-27 00:00+03' AND g.t < '2026-05-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.2  1–15 Mayıs
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-05-01 00:00+03' AND g.t < '2026-05-16 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.3  16–31 Mayıs
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-05-16 00:00+03' AND g.t < '2026-06-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.4  1–15 Haziran
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-06-01 00:00+03' AND g.t < '2026-06-16 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.5  16–30 Haziran
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-06-16 00:00+03' AND g.t < '2026-07-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.6  1–15 Temmuz
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-07-01 00:00+03' AND g.t < '2026-07-16 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.7  16–31 Temmuz
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-07-16 00:00+03' AND g.t < '2026-08-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.8  1–15 Ağustos
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-08-01 00:00+03' AND g.t < '2026-08-16 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.9  16–31 Ağustos
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-08-16 00:00+03' AND g.t < '2026-09-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.10 1–15 Eylül
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-09-01 00:00+03' AND g.t < '2026-09-16 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.11 16–30 Eylül
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-09-16 00:00+03' AND g.t < '2026-10-01 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- D.12 1–6 Ekim (~1431 satır)
WITH ins AS (
  INSERT INTO purpleair_readings (recorded_at, pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, humidity_pct, lat, lon)
  SELECT g.t, round(((g.atm_a + g.atm_b) / 2)::numeric, 1), g.atm_a, g.atm_b, g.cf1_a, g.cf1_b, g.rh, 40.8062, 29.361
  FROM gecici_pa_indirme g
  WHERE g.t >= '2026-10-01 00:00+03' AND g.t < '2026-10-07 00:00+03'
    AND NOT EXISTS (SELECT 1 FROM purpleair_readings p
                    WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds')
  ON CONFLICT (recorded_at) DO NOTHING
  RETURNING id)
INSERT INTO gecici_pa_eklenen (id) SELECT id FROM ins ON CONFLICT DO NOTHING;

-- Her D adımından sonra hızlı kontrol (ilgili dönem): indirme satırı = eklenen + atlanan.
-- SELECT count(*) AS indirme,
--        count(p.id) AS tabloda_ayni_t,
--        count(*) - count(p.id) AS eklenmeyen
-- FROM gecici_pa_indirme g LEFT JOIN purpleair_readings p ON p.recorded_at = g.t
-- WHERE g.t >= :bas AND g.t < :son;


-- ── E. Doğrulama (salt okunur) ──────────────────────────────────────────────

-- D.13 27–30 Nisan sıcaklığını yedekten taşı (kullanıcı kararı "taşı", 12 Ekim 2026): yeni eklenen Nisan kaydına,
-- ±60 s içindeki en yakın yedek kaydın temperature_c değeri yazılır (yalnızca boşsa).
UPDATE purpleair_readings p SET temperature_c = y.temperature_c
FROM gecici_pa_eklenen e,
     LATERAL (SELECT temperature_c FROM yedek_purpleair_nisan y
              WHERE y.recorded_at BETWEEN p.recorded_at - interval '60 seconds' AND p.recorded_at + interval '60 seconds'
                AND y.temperature_c IS NOT NULL
              ORDER BY abs(extract(epoch FROM y.recorded_at - p.recorded_at)) LIMIT 1) y
WHERE p.id = e.id AND p.temperature_c IS NULL AND p.recorded_at < '2026-05-01 00:00+03';

-- E.1 Sayılar. Beklenen: cf1_eklenen 3341, yeni_eklenen 107 361, nisan_silinen 781, atlanan 50.
SELECT (SELECT count(*) FROM gecici_cf1_eklenen) AS cf1_eklenen,
       (SELECT count(*) FROM gecici_pa_eklenen)  AS yeni_eklenen,
       (SELECT count(*) FROM yedek_purpleair_nisan) AS nisan_silinen,
       (SELECT count(*) FROM gecici_pa_indirme)
         - (SELECT count(*) FROM gecici_cf1_eklenen) - (SELECT count(*) FROM gecici_pa_eklenen) AS atlanan_indirme_satiri;

-- E.1b Tablo geneli. Beklenen: toplam 114 144 (+ içe aktarma sırasında gelen canlı kayıtlar), oncesi 110 752,
--      oncesi_cf1 110 745.
SELECT count(*) AS toplam,
       count(*) FILTER (WHERE recorded_at < '2026-10-06T21:00Z') AS oncesi,
       count(*) FILTER (WHERE recorded_at < '2026-10-06T21:00Z' AND pm2_5_cf1_a IS NOT NULL AND pm2_5_cf1_b IS NOT NULL) AS oncesi_cf1
FROM purpleair_readings;

-- E.2 İndirme satırlarının hepsi açıklanıyor mu? (ne cf_1 eklendi ne yeni kayıt oldu → ±60 s içinde başka kayıt olmalı)
SELECT count(*) AS aciklanamayan
FROM gecici_pa_indirme g
WHERE NOT EXISTS (SELECT 1 FROM purpleair_readings p
                  WHERE p.recorded_at BETWEEN g.t - interval '60 seconds' AND g.t + interval '60 seconds');
-- Beklenen: 0.

-- E.3 Ay ay kapsam (Türkiye saati): kayıt, cf_1'i olan, cf_1'i olmayan, PM10'u olan.
SELECT to_char(recorded_at AT TIME ZONE 'Europe/Istanbul', 'YYYY-MM') AS ay,
       count(*) AS kayit,
       count(*) FILTER (WHERE pm2_5_cf1_a IS NOT NULL AND pm2_5_cf1_b IS NOT NULL) AS cf1_var,
       count(*) FILTER (WHERE pm2_5_cf1_a IS NULL OR pm2_5_cf1_b IS NULL) AS cf1_yok,
       count(*) FILTER (WHERE pm10_0 IS NOT NULL) AS pm10_var
FROM purpleair_readings
GROUP BY 1 ORDER BY 1;

-- E.4 cf_1'i olmayan kalan kayıtlar (27 Nis – 6 Eki). Beklenen: 7 (id 901, 1233, 1652, 1766, 2110, 3829 ve
--     2026-06-22 11:50:28Z kaydı).
SELECT (recorded_at AT TIME ZONE 'Europe/Istanbul')::date AS gun, count(*)
FROM purpleair_readings
WHERE recorded_at >= '2026-04-27 00:00+03' AND recorded_at < '2026-10-07 00:00+03'
  AND (pm2_5_cf1_a IS NULL OR pm2_5_cf1_b IS NULL)
GROUP BY 1 ORDER BY 1;

-- E.5 Gün kapsamı (WHO ölçütleri): ≥18 saat tam gün, ≥6 saat gösterge gün. Beklenen (27 Nis – 6 Eki): 153 tam gün,
--     4 gösterge gün (4 ve 8 Temmuz, 2 ve 6 Ekim); tablo genelinde 6 Ekim sonrası günler de eklenir.
WITH s AS (
  SELECT (recorded_at AT TIME ZONE 'Europe/Istanbul')::date AS gun,
         count(DISTINCT date_trunc('hour', recorded_at)) AS saat
  FROM purpleair_readings
  WHERE pm2_5 IS NOT NULL
  GROUP BY 1)
SELECT count(*) AS olcum_gunu, count(*) FILTER (WHERE saat >= 18) AS tam_gun, count(*) FILTER (WHERE saat >= 6) AS gosterge_gun
FROM s;

-- E.6 Yeni kayıtların alanları: pm2_5 = A/B ortalaması (0,1), pm10/sıcaklık/pm1 boş, nem dolu.
SELECT count(*) AS n,
       count(*) FILTER (WHERE abs(p.pm2_5 - round(((p.pm2_5_a + p.pm2_5_b) / 2)::numeric, 1)) > 0.051) AS pm25_tutarsiz,
       count(*) FILTER (WHERE p.pm10_0 IS NOT NULL OR p.temperature_c IS NOT NULL OR p.pm1_0 IS NOT NULL) AS beklenmedik_alan,
       count(*) FILTER (WHERE p.humidity_pct IS NULL) AS nem_yok
FROM purpleair_readings p JOIN gecici_pa_eklenen e ON e.id = p.id;
-- Beklenen: pm25_tutarsiz 0, beklenmedik_alan 0.

-- E.7 Tekil zaman (recorded_at tekil kısıt zaten var; ±60 s içinde iki kayıt olan çift sayısı, bilgi için).
--     En ağır doğrulama sorgusu (yerelde ~3,5 s); zaman aşımı olursa dönemi aylara bölün.
SELECT count(*) AS yakin_cift
FROM purpleair_readings a JOIN purpleair_readings b
  ON b.recorded_at > a.recorded_at AND b.recorded_at <= a.recorded_at + interval '60 seconds'
WHERE a.recorded_at >= '2026-04-27 00:00+03' AND a.recorded_at < '2026-10-07 00:00+03';
-- Beklenen: yalnızca sunucunun kendi yakın kayıtları (yeni kayıtlardan kaynaklı çift olmamalı).

-- E.7b Saatlik US EPA kontrolü (uygulamadaki hesapla aynı: saatlik cf_1 A/B ve nem ortalaması).
--      Beklenen (Türkiye saati): 15 Mayıs 14:00 → 11,053 · 1 Ağustos 08:00 → 7,370 · 6 Mayıs 08:00 → 27,931.
SELECT (date_trunc('hour', recorded_at) AT TIME ZONE 'Europe/Istanbul') AS saat_tr, count(*) AS kayit,
       round((0.524 * (AVG(pm2_5_cf1_a) + AVG(pm2_5_cf1_b)) / 2 - 0.0862 * AVG(humidity_pct) + 5.75)::numeric, 3) AS epa
FROM purpleair_readings
WHERE date_trunc('hour', recorded_at) IN ('2026-05-15 14:00+03', '2026-08-01 08:00+03', '2026-05-06 08:00+03')
GROUP BY 1 ORDER BY 1;

-- E.8 Uygulamanın kullandığı saatlik sorgu hızlı mı? (WHO/Özet: 1 Ocak'tan bugüne saatlik)
EXPLAIN ANALYZE
SELECT date_trunc('hour', recorded_at), ROUND(AVG(pm2_5)::numeric, 2)
FROM purpleair_readings WHERE recorded_at BETWEEN '2026-01-01' AND now() GROUP BY 1 ORDER BY 1;


-- ── F. Geri alma (yalnızca gerekirse; her adım ayrı ve tekrar çalıştırılabilir) ─

-- F.1 Eklenen yeni kayıtları sil (günlükteki id'ler; ek güvenlik: PM1/PM10 boş ve dönem içinde).
-- (D.13 Nisan sıcaklığını taşıdığı için sıcaklık ölçüt değildir.)
DELETE FROM purpleair_readings p USING gecici_pa_eklenen e
WHERE p.id = e.id AND p.pm10_0 IS NULL AND p.pm1_0 IS NULL
  AND p.recorded_at >= '2026-04-27 00:00+03' AND p.recorded_at < '2026-10-07 00:00+03';
-- Günlük tablosu kaybolduysa yedek ölçüt (created_at penceresini içe aktarmanın gerçek başlangıç/bitişiyle doldurun):
-- DELETE FROM purpleair_readings p USING gecici_pa_indirme g
-- WHERE p.recorded_at = g.t AND p.pm10_0 IS NULL AND p.temperature_c IS NULL AND p.pm1_0 IS NULL
--   AND p.created_at BETWEEN '<<ICE_AKTARMA_BASI>>' AND '<<ICE_AKTARMA_SONU>>';

-- F.2 Eklenen cf_1 değerlerini geri boşalt.
UPDATE purpleair_readings p SET pm2_5_cf1_a = NULL, pm2_5_cf1_b = NULL
FROM gecici_cf1_eklenen e WHERE p.id = e.id;

-- F.3 Nisan kayıtlarını yedekten geri yükle (aynı id ve değerlerle; F.1'den SONRA çalıştırın).
INSERT INTO purpleair_readings SELECT * FROM yedek_purpleair_nisan
ON CONFLICT DO NOTHING;
-- Kontrol: SELECT count(*) FROM purpleair_readings p JOIN yedek_purpleair_nisan y ON y.id = p.id;  → 781

-- F.4 Günlük tablolarını sıfırla (F.1–F.3'ten sonra; plan yeniden çalıştırılacaksa ZORUNLU, yoksa E.1 sayıları şişer).
TRUNCATE gecici_pa_eklenen, gecici_cf1_eklenen;

-- Yerel deneme (12 Ekim 2026, PostgreSQL 16, gerçek indirme dosyası + benzetilmiş sunucu kayıtları): 0→E adımları
-- her biri < 0,3 s (E.7 ~3,5 s), F geri alma tabloyu ilk hâline döndürdü, F.4 sonrası plan yeniden çalıştırıldı.


-- ── G. Temizlik (doğrulama bitip kullanıcı onaylayınca) ──────────────────────
-- Yedek tablo kalır. Günlük ve hazırlık tabloları, geri alma artık gerekmeyince kaldırılabilir:
-- DROP TABLE gecici_pa_eklenen; DROP TABLE gecici_cf1_eklenen; DROP TABLE gecici_pa_indirme;
-- Not: gecici_pa_indirme'de RLS açık değilse (Supabase uyarısı) kaldırılana kadar açın:
-- ALTER TABLE gecici_pa_indirme ENABLE ROW LEVEL SECURITY;
