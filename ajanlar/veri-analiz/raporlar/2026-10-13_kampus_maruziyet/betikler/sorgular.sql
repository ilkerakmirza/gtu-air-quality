-- GTÜ AirLab · Ajan 5 · Kampüs hava kalitesi ve kişisel maruziyet raporu (13 Ekim 2026)
-- Supabase projesi wgirpaysokuoygycmdst üzerinde çalıştırılan SALT OKUMA sorguları (execute_sql).
-- Çıktıları olduğu gibi (MCP yanıtı) <ham klasörü>/Q1.txt, Q2.txt, Q3.txt olarak kaydedilir; betikler bu dosyaları okur.
-- Analiz dönemi sonu: 13 Ekim 2026 00:00 Türkiye saati = 2026-10-12T21:00:00Z.
-- KVKK: oturum adı ve saha cihaz adı döndürülmez (yalnızca ad ön ekinin md5 özetinin 8 karakteri döner; betik bunu
-- app.js → PEOPLE ile "Saha ekibi A/B/C"ye çevirir: ortak.py → ekip_esleme). Atmotube canlı kayıtlarında
-- koordinat döndürülmez, yalnızca "kampüs içi" bayrağı (backend/kampus.py kuralı) döner.

-- ───────────────────────────────────────────────────────────────────────────────────────
-- Q1 · PurpleAir saatlik (sunucunun interval=hourly sorgusuyla aynı toplama ve yuvarlama; ek olarak saatteki kayıt sayısı n)
-- ───────────────────────────────────────────────────────────────────────────────────────
WITH h AS (
  SELECT date_trunc('hour', recorded_at) AS t,
         ROUND(AVG(pm2_5)::numeric, 2)::float8 AS pm2_5, ROUND(AVG(pm2_5_a)::numeric, 2)::float8 AS pm2_5_a, ROUND(AVG(pm2_5_b)::numeric, 2)::float8 AS pm2_5_b,
         ROUND(AVG(pm2_5_cf1_a)::numeric, 2)::float8 AS pm2_5_cf1_a, ROUND(AVG(pm2_5_cf1_b)::numeric, 2)::float8 AS pm2_5_cf1_b, ROUND(AVG(pm10_0)::numeric, 2)::float8 AS pm10_0,
         ROUND(AVG(temperature_c)::numeric, 2)::float8 AS temperature_c, ROUND(AVG(humidity_pct)::numeric, 2)::float8 AS humidity_pct,
         count(*) AS n
  FROM purpleair_readings
  WHERE recorded_at >= '2026-04-27T00:00:00Z' AND recorded_at < '2026-10-12T21:00:00Z'
  GROUP BY 1)
SELECT json_build_object('sorgu','Q1','alanlar', json_build_array('t_utc','pm2_5','pm2_5_a','pm2_5_b','pm2_5_cf1_a','pm2_5_cf1_b','pm10_0','temperature_c','humidity_pct','n'),
       'satirlar', json_agg(json_build_array(to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'), pm2_5, pm2_5_a, pm2_5_b, pm2_5_cf1_a, pm2_5_cf1_b, pm10_0, temperature_c, humidity_pct, n) ORDER BY t)) AS veri
FROM h;

-- ───────────────────────────────────────────────────────────────────────────────────────
-- Q2 · Saha oturumları (27–30 Nisan 2026, 12 oturum): nokta düzeyi. Oturum adı döndürülmez; yalnızca ad ön ekinin md5 özetinin
--      ilk 8 karakteri ('onek') döner ve betikte app.js → PEOPLE eşlemesiyle "Saha ekibi A/B/C"ye çevrilir (veri.py → saha).
-- ───────────────────────────────────────────────────────────────────────────────────────
WITH s AS (
  SELECT id, start_time, left(md5(substring(session_name FROM '^[A-Za-z0-9-]*')), 8) AS onek,
         row_number() OVER (ORDER BY start_time, id) AS oturum
  FROM upload_sessions
  WHERE micro_environment = 'outdoor' AND start_time < '2026-05-01')
SELECT json_build_object('sorgu','Q2',
  'alanlar', json_build_array('oturum','onek','ep','pm1_0','pm2_5','pm10_0','lat','lon','humidity_pct','temperature_c'),
  'satirlar', json_agg(json_build_array(s.oturum, s.onek, extract(epoch FROM r.recorded_at)::bigint, r.pm1_0, r.pm2_5, r.pm10_0,
                                        round(r.lat::numeric, 6), round(r.lon::numeric, 6), r.humidity_pct, r.temperature_c)
                       ORDER BY s.oturum, r.recorded_at)) AS veri
FROM atmotube_readings r JOIN s ON s.id = r.session_id;

-- ───────────────────────────────────────────────────────────────────────────────────────
-- Q3 (salt okuma) · (a) PurpleAir günlük en kötü 15/60 dk kayan ortalamalar (US EPA düzeltmesi SQL'de, Türkiye günü)
--   (b) Atmotube canlı kayıtları: yalnızca değer, zaman ve "kampüs içi" bayrağı (koordinat döndürülmez) + aynı anın PurpleAir ortalaması
--   (c) İç ortam CO₂ kayıtları (yalnızca değerler)
-- Pencere: 15 dk = (t − 15 dk, t] içindeki 2 dk kayıtlar, en az 6 kayıt (beklenen 7–8); 60 dk = (t − 60 dk, t], en az 23 kayıt (%75).
-- Pencere tamamen aynı Türkiye günü içinde olmalı (bitiş ≥ 00:15 / 01:00). Kampüs saatleri: pencere 08:00–18:00 içinde.
-- Düzeltme colorscale.js → paCorrect ile aynı: cf_1 varsa 0,524·cf1 − 0,0862·RH + 5,75 (≥ 0); yoksa genişletilmiş denklem (cf_atm);
-- kanal kuralı hem ≥ 5 µg/m³ hem ≥ %70 ise kayıt dışarıda; nem yoksa ya da 0–100 dışındaysa %50.
-- ───────────────────────────────────────────────────────────────────────────────────────
WITH r AS (
  SELECT recorded_at AS t,
         CASE WHEN humidity_pct IS NULL OR humidity_pct < 0 OR humidity_pct > 100 THEN 50 ELSE humidity_pct::float8 END AS rh,
         pm2_5_cf1_a::float8 AS ca, pm2_5_cf1_b::float8 AS cb, pm2_5::float8 AS x, pm2_5_a::float8 AS a, pm2_5_b::float8 AS b
  FROM purpleair_readings
  WHERE recorded_at >= '2026-04-30T21:00:00Z' AND recorded_at < '2026-10-12T21:00:00Z'),
c AS (
  SELECT t, x AS ham, CASE
    WHEN ca IS NOT NULL AND cb IS NOT NULL THEN
      CASE WHEN abs(ca-cb) >= 5 AND (ca+cb)/2 > 0 AND abs(ca-cb)/((ca+cb)/2) >= 0.70 THEN NULL
           ELSE greatest(0, 0.524*(ca+cb)/2 - 0.0862*rh + 5.75) END
    WHEN a IS NOT NULL AND b IS NOT NULL AND abs(a-b) >= 5 AND (a+b)/2 > 0 AND abs(a-b)/((a+b)/2) >= 0.70 THEN NULL
    WHEN x IS NULL THEN NULL
    WHEN x < 30  THEN greatest(0, 0.524*x - 0.0862*rh + 5.75)
    WHEN x < 50  THEN greatest(0, (0.786*(x/20-1.5) + 0.524*(1-(x/20-1.5)))*x - 0.0862*rh + 5.75)
    WHEN x < 210 THEN greatest(0, 0.786*x - 0.0862*rh + 5.75)
    WHEN x < 260 THEN greatest(0, (0.69*(x/50-4.2) + 0.786*(1-(x/50-4.2)))*x - 0.0862*rh*(1-(x/50-4.2))
                                   + 2.966*(x/50-4.2) + 5.75*(1-(x/50-4.2)) + 8.84e-4*x*x*(x/50-4.2))
    ELSE 2.966 + 0.69*x + 8.84e-4*x*x END AS pm
  FROM r),
w AS (
  SELECT t, pm, avg(pm) OVER w15 AS m15, count(pm) OVER w15 AS n15, avg(pm) OVER w60 AS m60, count(pm) OVER w60 AS n60
  FROM c
  WINDOW w15 AS (ORDER BY t RANGE BETWEEN INTERVAL '899 seconds' PRECEDING AND CURRENT ROW),
         w60 AS (ORDER BY t RANGE BETWEEN INTERVAL '3599 seconds' PRECEDING AND CURRENT ROW)),
l AS (
  SELECT w.*, (t AT TIME ZONE 'Europe/Istanbul') AS tl,
         n15 >= 6  AND (t AT TIME ZONE 'Europe/Istanbul')::time >= '00:14:59' AS g15,
         n60 >= 23 AND (t AT TIME ZONE 'Europe/Istanbul')::time >= '00:59:59' AS g60,
         n15 >= 6  AND (t AT TIME ZONE 'Europe/Istanbul')::time BETWEEN '08:14:59' AND '17:59:59' AS k15,
         n60 >= 23 AND (t AT TIME ZONE 'Europe/Istanbul')::time BETWEEN '08:59:59' AND '17:59:59' AS k60
  FROM w WHERE pm IS NOT NULL),
gun AS (
  SELECT to_char(tl, 'YYYY-MM-DD') AS gun, count(*) AS n, round(max(pm)::numeric, 2)::float8 AS pm2dk_max,
    round((max(m15) FILTER (WHERE g15))::numeric, 2)::float8 AS m15, to_char((array_agg(tl ORDER BY m15 DESC) FILTER (WHERE g15))[1], 'HH24:MI') AS m15_t,
    round((max(m60) FILTER (WHERE g60))::numeric, 2)::float8 AS m60, to_char((array_agg(tl ORDER BY m60 DESC) FILTER (WHERE g60))[1], 'HH24:MI') AS m60_t,
    round((max(m15) FILTER (WHERE k15))::numeric, 2)::float8 AS k15, to_char((array_agg(tl ORDER BY m15 DESC) FILTER (WHERE k15))[1], 'HH24:MI') AS k15_t,
    round((max(m60) FILTER (WHERE k60))::numeric, 2)::float8 AS k60, to_char((array_agg(tl ORDER BY m60 DESC) FILTER (WHERE k60))[1], 'HH24:MI') AS k60_t
  FROM l GROUP BY 1),
atp AS (
  SELECT m.device, m.recorded_at, m.pm2_5, m.humidity_pct,
         (m.lat IS NOT NULL AND m.lon IS NOT NULL AND
          sqrt(((m.lat - 40.8114) * 111.32)^2 + ((m.lon - 29.3563) * 111.32 * cos(radians(40.8114)))^2) <= 2.0) AS ic
  FROM measurements m WHERE m.source = 'atmotube'),
atp2 AS (
  SELECT atp.*, pa.pa_epa, pa.pa_ham, pa.pa_n
  FROM atp LEFT JOIN LATERAL (
    SELECT round(avg(c.pm)::numeric, 2)::float8 AS pa_epa, round(avg(c.ham)::numeric, 2)::float8 AS pa_ham, count(c.pm) AS pa_n
    FROM c WHERE c.t BETWEEN atp.recorded_at - INTERVAL '8 minutes' AND atp.recorded_at + INTERVAL '8 minutes') pa ON true)
SELECT json_build_object(
  'gunluk_tepe', (SELECT json_build_object('alanlar', json_build_array('gun','n','pm2dk_max','m15','m15_t','m60','m60_t','k15','k15_t','k60','k60_t'),
                  'satirlar', json_agg(json_build_array(gun, n, pm2dk_max, m15, m15_t, m60, m60_t, k15, k15_t, k60, k60_t) ORDER BY gun)) FROM gun),
  'atp_canli', (SELECT json_build_object('alanlar', json_build_array('cihaz','ep','pm2_5','humidity_pct','kampus_ici','pa_epa','pa_ham','pa_n'),
                  'satirlar', json_agg(json_build_array(device, extract(epoch FROM recorded_at)::bigint, pm2_5, humidity_pct, ic, pa_epa, pa_ham, pa_n)
                                       ORDER BY device, recorded_at)) FROM atp2),
  'co2', (SELECT json_build_object('alanlar', json_build_array('ep','co2_ppm','temperature_c','humidity_pct'),
                  'satirlar', json_agg(json_build_array(extract(epoch FROM recorded_at)::bigint, co2_ppm, temperature_c, humidity_pct) ORDER BY recorded_at))
          FROM measurements WHERE source = 'co2')
) AS veri;

-- Ek veri (sorgu değil): 27–30 Nisan saha oturumlarıyla eş zamanlı PurpleAir 2 dk kayıtları (cf_1 dahil) depodaki
-- docs/veri/purpleair_229263_2dk_2026-04-27_2026-10-06.csv dosyasından okunur (sensörün kendi arşivi; veritabanındaki
-- eski Nisan kayıtlarıyla aynı zaman damgalı kayıtlarda değerler aynı, ancak veritabanında bu günlerin saatleri eksik).
