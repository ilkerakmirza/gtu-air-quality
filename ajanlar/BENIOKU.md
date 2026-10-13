# Ajanlar

Kullanıcı yalnızca **ana ajanla** (koordinatör) konuşur. Ana ajan işi beş uzman ajana dağıtır, raporlarını birbirine
karşı kontrol eder ve uygular. Veritabanına yazmak, commit ve `main`'e göndermek **yalnızca ana ajanın** işidir; silme gibi geri
dönüşü zor kararlar kullanıcıya sorulur.

| Ajan | Kimlik kartı | Görev | Yazma |
|---|---|---|---|
| 1 · Veri kontrolü | `.claude/agents/veri-kontrol.md` | Uygunluk, literatür, beklenen sayılar | Yok (salt okur) |
| 2 · İşleme, yöntem, yazılım | `.claude/agents/isleme-yontem.md` | Geri alınabilir plan, belgeler, kod, test | Repoda düzenler; commit yok |
| 4 · Arayüz kalitesi | `.claude/agents/arayuz-kalitesi.md` | İşlev, grafikler, anlaşılırlık (ekran görüntüsüyle) | Yok (bulur, önerir) |
| 3 · Son kontrol | `.claude/agents/son-kontrol.md` | Geri alınamazlık, tutarlılık, onay/ret, anlatım notu | Yok (salt okur) |
| 5 · Veri analizi | `.claude/agents/veri-analiz.md` | Analiz ve akademik rapor: sorunlu alanlar, kişisel maruziyet, grafik ve harita | Yalnızca `ajanlar/veri-analiz/`; commit yok |

**Akış:** 1 kontrol eder → 2 hazırlar → 4 ekranı test eder (sorun varsa 2'ye döner) → 3 son onay → ana ajan uygular ve
sonucu 1'in beklediği sayılarla karşılaştırır → kullanıcıya kısa özet. Her işte tüm ajanlar gerekmez: yalnızca kod/ekran
değişikliğinde 2 → 4 → 3 yeterli; yalnızca veri sorusunda 1.

**Analiz ve raporlama işlerinin sahibi Ajan 5'tir** (kullanıcının kararı, 13 Ekim 2026): kampüste sorunlu alanlar, kişisel maruziyet,
en kötü durum ve senaryolar, dönemsel raporlar; yeni veri gelince raporu o günceller.

**Analiz akışı:** 5 analiz eder ve her sayıyı `sayilar.json`'a yazar → 1 kritik sayıları bağımsız yeniden hesaplar → 3 KVKK, tutarlılık
ve dil açısından onaylar → ana ajan raporu yayımlar.

**Taslaklar:** ajanların yarım ya da onaylanmamış çıktıları `ajanlar/<ad>/taslak/` altında git dışında kalır (`.gitignore`);
kişisel veri ve sayı kontrolünden geçen çıktıyı ana ajan kalıcı klasöre taşır ve commit'ler.

**Hafıza:** her ajanın klasöründe `HAFIZA.md` var. Ajan işe başlarken okur. Salt okuyan ajanlar raporlarının sonuna
"Hafızaya eklenecek" maddeleri yazar, ana ajan işler. Hafızaya kişisel veri, ad, anahtar ve parola yazılmaz (repo herkese açık).

**Sorumluluk:** her ajan kendi alanının cevabından sorumludur; ana ajan yayımlanan her şeyden kullanıcıya karşı sorumludur
ve raporları körü körüne kabul etmez; son karar kullanıcınındır.
