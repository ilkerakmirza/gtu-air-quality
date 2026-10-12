# Ajanlar

Kullanıcı yalnızca **ana ajanla** (koordinatör) konuşur. Ana ajan işi dört uzman ajana dağıtır, raporlarını birbirine
karşı kontrol eder ve uygular. Veritabanına yazmak, commit ve `main`'e göndermek **yalnızca ana ajanın** işidir; silme gibi geri
dönüşü zor kararlar kullanıcıya sorulur.

| Ajan | Kimlik kartı | Görev | Yazma |
|---|---|---|---|
| 1 · Veri kontrolü | `.claude/agents/veri-kontrol.md` | Uygunluk, literatür, beklenen sayılar | Yok (salt okur) |
| 2 · İşleme, yöntem, yazılım | `.claude/agents/isleme-yontem.md` | Geri alınabilir plan, belgeler, kod, test | Repoda düzenler; commit yok |
| 4 · Arayüz kalitesi | `.claude/agents/arayuz-kalitesi.md` | İşlev, grafikler, anlaşılırlık (ekran görüntüsüyle) | Yok (bulur, önerir) |
| 3 · Son kontrol | `.claude/agents/son-kontrol.md` | Geri alınamazlık, tutarlılık, onay/ret, anlatım notu | Yok (salt okur) |

**Akış:** 1 kontrol eder → 2 hazırlar → 4 ekranı test eder (sorun varsa 2'ye döner) → 3 son onay → ana ajan uygular ve
sonucu 1'in beklediği sayılarla karşılaştırır → kullanıcıya kısa özet. Her işte dört ajan gerekmez: yalnızca kod/ekran
değişikliğinde 2 → 4 → 3 yeterli; yalnızca veri sorusunda 1.

**Hafıza:** her ajanın klasöründe `HAFIZA.md` var. Ajan işe başlarken okur. Salt okuyan ajanlar raporlarının sonuna
"Hafızaya eklenecek" maddeleri yazar, ana ajan işler. Hafızaya kişisel veri, ad, anahtar ve parola yazılmaz (repo herkese açık).

**Sorumluluk:** her ajan kendi alanının cevabından sorumludur; ana ajan yayımlanan her şeyden kullanıcıya karşı sorumludur
ve raporları körü körüne kabul etmez; son karar kullanıcınındır.
