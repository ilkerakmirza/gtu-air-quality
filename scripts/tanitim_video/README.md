# Tanıtım videoları

Uygulamanın tanıtım videolarını otomatik kaydeder: Playwright uygulamayı yönetir, ekran 30 fps kaydedilir,
altta vurgulu altyazılar ve telifsiz (tamamen sentezlenmiş) fon müziği eklenir.

| Sürüm | Boyut | Süre | Platform |
|---|---|---|---|
| `short` | 1080×1920 (9:16) | ~80 sn | Instagram Reels, LinkedIn |
| `long` | 1920×1080 (16:9) | ~2,5 dk | YouTube |

## Kayıt

```bash
python -m http.server 8765 --directory frontend_v2 &        # uygulama yerelde açık olmalı
python -c "import qrcode; qrcode.make('<uygulama adresi>').save('scripts/tanitim_video/qr.png')"   # isteğe bağlı
node scripts/tanitim_video/video_kaydet.js short           # → scripts/tanitim_video/cikti/airlab-short.mp4
node scripts/tanitim_video/video_kaydet.js long
```

- **HD (yayın kalitesi):** `HD=1 node scripts/tanitim_video/video_kaydet.js short` → ekran 1,5 kat yüksek çözünürlükte yakalanıp
  1080×1920'ye küçültülür (daha keskin yazı), H.264 High profil, CRF 15. Müzik birleştirmede ses için `-b:a 256k -ar 48000` önerilir.

- **Sensör görselleri:** `foto/purpleair.jpg` ve `foto/atmotube.jpg` (ya da `.png`) konursa kartlarda fotoğraf gösterilir; yoksa kartlar yalnızca metindir
  Ekibin kendi çektiği (ya da kullanım izni olan) ve kişi/yüz içermeyen fotoğraflar kullanın.
- Varsayılan olarak **örnek veri** kullanılır ve videoda "TASLAK · ÖRNEK VERİ" etiketi görünür.
- Yayın sürümü için `GERCEK=1` ile canlı sunucu verisi kullanılır (etiket kalkar). Sensörlerin veri gönderdiği bir saatte kaydedin.
- Gerekenler: Node.js + `playwright` (Chromium), `ffmpeg`; müzik için Python + `numpy`.

## Müzik ve birleştirme

```bash
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 cikti/airlab-short.mp4)
python fon_muzigi.py $D cikti/muzik-short.wav 96            # uzun sürüm için tempo 84
ffmpeg -i cikti/airlab-short.mp4 -i cikti/muzik-short.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
       -af volume=0.85 -shortest -movflags +faststart cikti/AirLab-short.mp4
```

Müzik koddan üretildiği için telif sorunu yoktur. İsterseniz platformun kendi lisanslı müzik kütüphanesinden
müzik eklemek için sessiz MP4'ü kullanabilirsiniz.

## İçerik kuralları
- Gerçek kişi adı, yüzü ya da kampüs dışı konum videoya girmez (KVKK).
- Altyazılardaki bilgi uygulamadaki yöntemle tutarlı olmalı (`docs/hesaplama_ve_kaynaklar.md`); sağlık hükmü yerine ölçülü dil.
- Karekod ve adres, kalıcı uygulama adresini göstermelidir.
